"""Package-owned FTS5 search, preserving the document service's ranking rules."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from functools import lru_cache
import re
import json
import sqlite3
from threading import RLock
from typing import Any, Dict, List, Optional

from .documents import DocumentUnavailableError, get_document_store
from .document_synonyms import SynonymRegistry


@dataclass
class SearchResult:
    document_slug: str
    document_title: str
    snippet: str
    relevance_score: float
    match_type: str
    section_anchor: Optional[str] = None
    section_title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    tags_truncated: bool = False


@dataclass
class SearchResponse:
    query: str
    total_results: int
    results: List[SearchResult] = field(default_factory=list)
    expanded_query: Optional[str] = None
    tags_matched: List[str] = field(default_factory=list)
    tags_matched_truncated: bool = False


class _SearchQueries:
    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        expand: bool = True,
    ) -> SearchResponse:
        if not query.strip() or query.strip() == "*":
            if tags:
                return self._search_by_tags_only(tags, limit)
            return SearchResponse(query=query, total_results=0, results=[])
        search_query = self.synonym_registry.expand_query(query, expand=expand)
        if not search_query:
            return SearchResponse(query=query, total_results=0)
        expanded_query = search_query if expand else None
        results = []
        tags_matched = set()
        with self._get_connection() as conn:
            doc_rows = self._fetch_document_rows(conn, search_query, tags, -1)
            sec_rows = self._fetch_section_rows(conn, search_query, tags, -1)
            all_slugs = list(
                {r["slug"] for r in doc_rows} | {r["doc_slug"] for r in sec_rows}
            )
            tags_by_slug = self._get_tags_for_slugs(conn, all_slugs)
            for row in doc_rows:
                doc_tags = tags_by_slug.get(row["slug"], [])
                results.append(
                    SearchResult(
                        document_slug=row["slug"],
                        document_title=row["title"],
                        section_anchor=None,
                        section_title=None,
                        snippet=row["snippet"] or row["summary"] or "",
                        relevance_score=abs(row["score"]) + row["importance"] / 100,
                        match_type="document",
                        tags=doc_tags,
                    )
                )
            for row in sec_rows:
                doc_tags = tags_by_slug.get(row["doc_slug"], [])
                results.append(
                    SearchResult(
                        document_slug=row["doc_slug"],
                        document_title=row["doc_title"],
                        section_anchor=row["anchor"],
                        section_title=row["title"],
                        snippet=row["snippet"] or "",
                        relevance_score=abs(row["score"]),
                        match_type="section",
                        tags=doc_tags,
                    )
                )
            for result in results:
                tags_matched.update(result.tags)
        results = self._deduplicate_results(results)
        glossary_results, other_results = self._separate_glossary_matches(
            results, query
        )
        glossary_results.sort(key=lambda r: r.relevance_score, reverse=True)
        other_results.sort(key=lambda r: r.relevance_score, reverse=True)
        results = glossary_results + other_results
        total = len(results)
        results = results[:limit]
        return SearchResponse(
            query=query,
            expanded_query=expanded_query if expanded_query != query else None,
            total_results=total,
            results=results,
            tags_matched=sorted(tags_matched),
        )

    def _search_by_tags_only(self, tags: List[str], limit: int) -> SearchResponse:
        results = []
        with self._get_connection() as conn:
            sql = "\n                SELECT\n                    d.slug as doc_slug,\n                    d.title as doc_title,\n                    s.anchor,\n                    s.title,\n                    s.content\n                FROM sections s\n                JOIN documents d ON s.document_id = d.id\n                WHERE d.slug LIKE '%table-of-contents%'\n                ORDER BY s.id\n            "
            rows = conn.execute(sql).fetchall()
            for row in rows:
                content = row["content"] or ""
                import re

                tags_match = re.search("Tags:\\s*([^\\n]+)", content, re.IGNORECASE)
                if not tags_match:
                    continue
                tags_line = tags_match.group(1).lower()
                tags_in_line = [t.strip() for t in tags_line.split(",")]
                matched = False
                for tag in tags:
                    if tag.lower() in tags_in_line:
                        matched = True
                        break
                if not matched:
                    continue
                desc_match = re.search("^(.+?)(?=Tags:)", content, re.DOTALL)
                snippet = desc_match.group(1).strip() if desc_match else content[:200]
                key = (row["doc_slug"], row["anchor"])
                existing = next(
                    (r for r in results if (r.document_slug, r.section_anchor) == key),
                    None,
                )
                if existing:
                    continue
                results.append(
                    SearchResult(
                        document_slug=row["doc_slug"],
                        document_title=row["doc_title"],
                        section_anchor=row["anchor"],
                        section_title=row["title"],
                        snippet=snippet,
                        relevance_score=10.0,
                        match_type="section",
                        tags=tags_in_line,
                    )
                )
        total = len(results)
        results = results[:limit]
        return SearchResponse(
            query="*", total_results=total, results=results, tags_matched=tags
        )

    def _separate_glossary_matches(
        self, results: List[SearchResult], query: str
    ) -> tuple:
        glossary_results = []
        other_results = []
        for result in results:
            is_glossary = (
                result.document_slug == "9-glossary"
                or "glossary" in result.document_slug.lower()
            )
            if is_glossary:
                glossary_results.append(result)
            else:
                other_results.append(result)
        return (glossary_results, other_results)

    def _fetch_document_rows(
        self,
        conn: sqlite3.Connection,
        query: str,
        tags: Optional[List[str]],
        limit: int,
    ) -> List[sqlite3.Row]:
        sql = "\n            SELECT\n                d.slug,\n                d.title,\n                d.summary,\n                d.importance,\n                bm25(documents_fts) as score,\n                snippet(documents_fts, 2, '<mark>', '</mark>', '...', 30) as snippet\n            FROM documents_fts\n            JOIN documents d ON documents_fts.rowid = d.id\n        "
        params = []
        if tags:
            sql += "\n                JOIN document_tags dt ON d.id = dt.document_id\n                JOIN tags t ON dt.tag_id = t.id\n                WHERE t.name IN ({})\n                AND documents_fts MATCH ?\n                AND d.slug NOT LIKE '%table-of-contents%'\n            ".format(
                ",".join("?" * len(tags))
            )
            params.extend(tags)
        else:
            sql += (
                " WHERE documents_fts MATCH ? AND d.slug NOT LIKE '%table-of-contents%'"
            )
        params.append(query)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        try:
            return conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            raise ValueError("Invalid full-text query") from None

    def _fetch_section_rows(
        self,
        conn: sqlite3.Connection,
        query: str,
        tags: Optional[List[str]],
        limit: int,
    ) -> List[sqlite3.Row]:
        sql = "\n            SELECT\n                d.slug as doc_slug,\n                d.title as doc_title,\n                s.anchor,\n                s.title,\n                bm25(sections_fts) as score,\n                snippet(sections_fts, 1, '<mark>', '</mark>', '...', 30) as snippet\n            FROM sections_fts\n            JOIN sections s ON sections_fts.rowid = s.id\n            JOIN documents d ON s.document_id = d.id\n        "
        params = []
        if tags:
            sql += "\n                JOIN document_tags dt ON d.id = dt.document_id\n                JOIN tags t ON dt.tag_id = t.id\n                WHERE t.name IN ({})\n                AND sections_fts MATCH ?\n            ".format(
                ",".join("?" * len(tags))
            )
            params.extend(tags)
        else:
            sql += " WHERE sections_fts MATCH ?"
        params.append(query)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        try:
            return conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            raise ValueError("Invalid full-text query") from None

    def _get_tags_for_slugs(
        self, conn: sqlite3.Connection, slugs: List[str]
    ) -> Dict[str, List[str]]:
        if not slugs:
            return {}
        placeholders = ",".join("?" * len(slugs))
        rows = conn.execute(
            f"\n            SELECT d.slug, t.name\n            FROM tags t\n            JOIN document_tags dt ON t.id = dt.tag_id\n            JOIN documents d ON dt.document_id = d.id\n            WHERE d.slug IN ({placeholders})\n        ",
            slugs,
        ).fetchall()
        result: Dict[str, List[str]] = {}
        for row in rows:
            result.setdefault(row["slug"], []).append(row["name"])
        return result

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        seen = {}
        for result in results:
            key = (result.document_slug, result.section_anchor)
            if key not in seen or result.relevance_score > seen[key].relevance_score:
                seen[key] = result
        return list(seen.values())


class DocumentSearch(_SearchQueries):
    def __init__(self, store=None):
        self.store = store if store is not None else get_document_store()
        self.synonym_registry = SynonymRegistry()
        self._lock = RLock()
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript("""
                CREATE TABLE documents (id INTEGER PRIMARY KEY, slug TEXT, title TEXT,
                    summary TEXT, content TEXT, importance INTEGER);
                CREATE TABLE sections (id INTEGER PRIMARY KEY, document_id INTEGER,
                    anchor TEXT, title TEXT, content TEXT);
                CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
                CREATE TABLE document_tags (document_id INTEGER, tag_id INTEGER);
                CREATE VIRTUAL TABLE documents_fts USING fts5(title, summary, content,
                    content='documents', content_rowid='id', tokenize='porter');
                CREATE VIRTUAL TABLE sections_fts USING fts5(title, content,
                    content='sections', content_rowid='id', tokenize='porter');
            """)
            for row in self.store.list_documents()["documents"]:
                doc = self.store.get_document(row["slug"])
                number = int(doc["slug"].split("-", 1)[0])
                cursor = conn.execute(
                    "INSERT INTO documents(slug,title,summary,content,importance) VALUES(?,?,?,?,?)",
                    (
                        doc["slug"],
                        doc["title"],
                        doc["summary"],
                        doc["content"],
                        100 - number if number else 50,
                    ),
                )
                doc_id = cursor.lastrowid
                for section in doc["sections"]:
                    conn.execute(
                        "INSERT INTO sections(document_id,anchor,title,content) VALUES(?,?,?,?)",
                        (
                            doc_id,
                            section["anchor"],
                            section["title"],
                            section["content"],
                        ),
                    )
                for tag in doc["tags"]:
                    conn.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (tag,))
                    conn.execute(
                        "INSERT INTO document_tags SELECT ?,id FROM tags WHERE name=?",
                        (doc_id, tag),
                    )
            conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
            conn.execute("INSERT INTO sections_fts(sections_fts) VALUES('rebuild')")
            conn.commit()
            conn.execute("PRAGMA query_only=ON")
        except Exception:
            conn.close()
            raise DocumentUnavailableError(
                "The knowledge search index is unavailable"
            ) from None
        self._connection = conn

    @contextmanager
    def _get_connection(self):
        with self._lock:
            yield self._connection

    def query(self, query, *, tags=None, expand=True, limit=5):
        if not isinstance(query, str) or len(query) > 1000:
            raise ValueError("q must be text of at most 1000 characters")
        if type(limit) is not int or not 0 <= limit <= 100:
            raise ValueError("limit must be an integer between 0 and 100")
        if type(expand) is not bool:
            raise ValueError("expand must be a boolean")
        if tags is not None and (
            not isinstance(tags, list)
            or len(tags) > 10
            or any(
                not isinstance(t, str) or not t.strip() or len(t) > 100 for t in tags
            )
        ):
            raise ValueError("tags must contain at most 10 non-empty strings")
        try:
            result = asdict(self.search(query, tags=tags, expand=expand, limit=limit))
        except sqlite3.DatabaseError:
            raise DocumentUnavailableError(
                "The knowledge search index is unavailable"
            ) from None
        for row in result["results"]:
            row_tags = sorted(set(row["tags"]))
            preferred = [tag for tag in (tags or []) if tag in row_tags]
            row_tags = preferred + [tag for tag in row_tags if tag not in preferred]
            row["tags"] = row_tags[:16]
            row["tags_truncated"] = len(row_tags) > 16
            row["snippet"] = row["snippet"][:500]
        matched = sorted(set(result["tags_matched"]))
        result["tags_matched"] = matched[:64]
        result["tags_matched_truncated"] = len(matched) > 64
        result["source"] = self.store.list_documents()["source"]
        rows = result.pop("results")
        result.update(results=[], returned=0, truncated=True)
        used = len(json.dumps(result, ensure_ascii=True).encode())
        for row in rows:
            size = len(json.dumps(row, ensure_ascii=True).encode()) + 2
            if used + size > 24_000:
                break
            result["results"].append(row)
            used += size
        result["returned"] = len(result["results"])
        result["truncated"] = result["returned"] < result["total_results"]
        return result


@lru_cache(maxsize=1)
def get_document_search():
    return DocumentSearch()
