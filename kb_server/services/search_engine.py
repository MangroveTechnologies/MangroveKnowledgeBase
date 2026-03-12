"""
Search Engine with SQLite FTS5 and Porter Stemmer.

Provides full-text search with stemming, synonym expansion, and relevance ranking.
"""

import sqlite3
import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

try:
    from ..models import Document, Section, SearchResult, SearchResponse
    from ..config import settings
    from .synonyms import SynonymRegistry, get_synonym_registry
except ImportError:
    from models import Document, Section, SearchResult, SearchResponse
    from config import settings
    from services.synonyms import SynonymRegistry, get_synonym_registry


class SearchEngine:
    """
    Full-text search engine using SQLite FTS5 with Porter stemmer.

    Features:
    - Porter stemmer for word variations
    - BM25 relevance ranking
    - Synonym expansion
    - Tag-based filtering
    - Snippet extraction with highlighting
    """

    # SQL schema for the knowledge base database
    SCHEMA = """
    -- Core tables
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        summary TEXT,
        content TEXT,
        importance INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        anchor TEXT NOT NULL,
        title TEXT NOT NULL,
        level INTEGER NOT NULL,
        content TEXT,
        parent_anchor TEXT,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS document_tags (
        document_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY (document_id, tag_id),
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS term_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term TEXT NOT NULL,
        source_document_slug TEXT NOT NULL,
        source_anchor TEXT NOT NULL,
        target_document_slug TEXT NOT NULL,
        target_anchor TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS synonyms (
        term TEXT PRIMARY KEY,
        synonyms_json TEXT NOT NULL
    );

    -- FTS5 virtual tables with Porter tokenizer
    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
        title,
        summary,
        content,
        content='documents',
        content_rowid='id',
        tokenize='porter'
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
        title,
        content,
        content='sections',
        content_rowid='id',
        tokenize='porter'
    );

    -- Triggers to keep FTS in sync
    CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
        INSERT INTO documents_fts(rowid, title, summary, content)
        VALUES (new.id, new.title, new.summary, new.content);
    END;

    CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
        INSERT INTO documents_fts(documents_fts, rowid, title, summary, content)
        VALUES ('delete', old.id, old.title, old.summary, old.content);
    END;

    CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
        INSERT INTO documents_fts(documents_fts, rowid, title, summary, content)
        VALUES ('delete', old.id, old.title, old.summary, old.content);
        INSERT INTO documents_fts(rowid, title, summary, content)
        VALUES (new.id, new.title, new.summary, new.content);
    END;

    CREATE TRIGGER IF NOT EXISTS sections_ai AFTER INSERT ON sections BEGIN
        INSERT INTO sections_fts(rowid, title, content)
        VALUES (new.id, new.title, new.content);
    END;

    CREATE TRIGGER IF NOT EXISTS sections_ad AFTER DELETE ON sections BEGIN
        INSERT INTO sections_fts(sections_fts, rowid, title, content)
        VALUES ('delete', old.id, old.title, old.content);
    END;

    CREATE TRIGGER IF NOT EXISTS sections_au AFTER UPDATE ON sections BEGIN
        INSERT INTO sections_fts(sections_fts, rowid, title, content)
        VALUES ('delete', old.id, old.title, old.content);
        INSERT INTO sections_fts(rowid, title, content)
        VALUES (new.id, new.title, new.content);
    END;

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_sections_document ON sections(document_id);
    CREATE INDEX IF NOT EXISTS idx_sections_anchor ON sections(anchor);
    CREATE INDEX IF NOT EXISTS idx_term_refs_term ON term_references(term);
    CREATE INDEX IF NOT EXISTS idx_term_refs_target ON term_references(target_anchor);
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the search engine.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or settings.db_path
        self.synonym_registry = get_synonym_registry()
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """
        Get a database connection with optimised settings for concurrent reads.

        WAL mode allows multiple simultaneous readers without blocking each other,
        which is essential now that sync route handlers run in Starlette's thread pool.
        cache_size and mmap_size keep the FTS5 inverted index in memory, avoiding
        repeated disk I/O on every BM25 ranking pass.
        """
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -32000")    # 32 MB page cache per connection
        conn.execute("PRAGMA mmap_size = 268435456")  # 256 MB memory-mapped I/O
        conn.execute("PRAGMA temp_store = MEMORY")
        try:
            yield conn
        finally:
            conn.close()

    def build_index(self, documents: List[Document]):
        """
        Build the search index from documents.

        Args:
            documents: List of Document objects to index
        """
        with self._get_connection() as conn:
            # Clear existing data
            conn.execute("DELETE FROM document_tags")
            conn.execute("DELETE FROM sections")
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM tags")

            for doc in documents:
                # Insert document
                cursor = conn.execute(
                    """INSERT INTO documents (slug, title, filename, summary, content, importance)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (doc.slug, doc.title, doc.filename, doc.summary, doc.content, doc.importance)
                )
                doc_id = cursor.lastrowid

                # Insert sections
                for section in doc.sections:
                    conn.execute(
                        """INSERT INTO sections (document_id, anchor, title, level, content, parent_anchor)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (doc_id, section.anchor, section.title, section.level,
                         section.content, section.parent_anchor)
                    )

                # Insert tags
                for tag_name in doc.tags:
                    # Get or create tag
                    conn.execute(
                        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                        (tag_name,)
                    )
                    tag_row = conn.execute(
                        "SELECT id FROM tags WHERE name = ?",
                        (tag_name,)
                    ).fetchone()

                    if tag_row:
                        conn.execute(
                            "INSERT OR IGNORE INTO document_tags (document_id, tag_id) VALUES (?, ?)",
                            (doc_id, tag_row['id'])
                        )

            # Store synonyms
            for term, synonyms in self.synonym_registry.to_dict().items():
                conn.execute(
                    "INSERT OR REPLACE INTO synonyms (term, synonyms_json) VALUES (?, ?)",
                    (term, json.dumps(synonyms))
                )

            conn.commit()

    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        expand: bool = True
    ) -> SearchResponse:
        """
        Search the knowledge base.

        Args:
            query: Search query string
            tags: Optional list of tags to filter by
            limit: Maximum number of results
            expand: Whether to expand query with synonyms

        Returns:
            SearchResponse with results
        """
        if not query.strip() or query.strip() == "*":
            # Handle tag-only filtering
            if tags:
                return self._search_by_tags_only(tags, limit)
            return SearchResponse(
                query=query,
                total_results=0,
                results=[]
            )

        # Expand query with synonyms if enabled
        expanded_query = None
        search_query = query
        if expand:
            expanded_query = self.synonym_registry.expand_query(query)
            if expanded_query != query:
                search_query = expanded_query

        results = []
        tags_matched = set()

        with self._get_connection() as conn:
            # Fetch raw rows from both FTS tables, then resolve tags in one batch
            doc_rows = self._fetch_document_rows(conn, search_query, tags, limit)
            sec_rows = self._fetch_section_rows(conn, search_query, tags, limit)

            # Single round-trip for all tags needed by both result sets
            all_slugs = list({r['slug'] for r in doc_rows} | {r['doc_slug'] for r in sec_rows})
            tags_by_slug = self._get_tags_for_slugs(conn, all_slugs)

            for row in doc_rows:
                doc_tags = tags_by_slug.get(row['slug'], [])
                results.append(SearchResult(
                    document_slug=row['slug'],
                    document_title=row['title'],
                    section_anchor=None,
                    section_title=None,
                    snippet=row['snippet'] or row['summary'] or '',
                    relevance_score=abs(row['score']) + (row['importance'] / 100),
                    match_type='document',
                    tags=doc_tags
                ))

            for row in sec_rows:
                doc_tags = tags_by_slug.get(row['doc_slug'], [])
                results.append(SearchResult(
                    document_slug=row['doc_slug'],
                    document_title=row['doc_title'],
                    section_anchor=row['anchor'],
                    section_title=row['title'],
                    snippet=row['snippet'] or '',
                    relevance_score=abs(row['score']),
                    match_type='section',
                    tags=doc_tags
                ))

            # Collect matched tags
            for result in results:
                tags_matched.update(result.tags)

        # Sort by relevance and deduplicate
        results = self._deduplicate_results(results)

        # Separate glossary matches - they go FIRST, not just boosted
        glossary_results, other_results = self._separate_glossary_matches(results, query)

        # Sort each group by relevance
        glossary_results.sort(key=lambda r: r.relevance_score, reverse=True)
        other_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Glossary first, then everything else
        results = glossary_results + other_results
        results = results[:limit]

        return SearchResponse(
            query=query,
            expanded_query=expanded_query if expanded_query != query else None,
            total_results=len(results),
            results=results,
            tags_matched=list(tags_matched)
        )

    def _search_by_tags_only(self, tags: List[str], limit: int) -> SearchResponse:
        """Search by tags - search the TOC document for sections with matching tags."""
        results = []

        with self._get_connection() as conn:
            # Search the TABLE OF CONTENTS document for sections with this tag
            sql = """
                SELECT
                    d.slug as doc_slug,
                    d.title as doc_title,
                    s.anchor,
                    s.title,
                    s.content
                FROM sections s
                JOIN documents d ON s.document_id = d.id
                WHERE d.slug LIKE '%table-of-contents%'
                ORDER BY s.id
            """

            rows = conn.execute(sql).fetchall()

            for row in rows:
                content = row['content'] or ''

                # Look for Tags: line in this section
                import re
                tags_match = re.search(r'Tags:\s*([^\n]+)', content, re.IGNORECASE)
                if not tags_match:
                    continue

                tags_line = tags_match.group(1).lower()
                tags_in_line = [t.strip() for t in tags_line.split(',')]

                # Check if any of the requested tags are in this section's tags
                matched = False
                for tag in tags:
                    if tag.lower() in tags_in_line:
                        matched = True
                        break

                if not matched:
                    continue

                # Extract the description (content before Tags:)
                desc_match = re.search(r'^(.+?)(?=Tags:)', content, re.DOTALL)
                snippet = desc_match.group(1).strip() if desc_match else content[:200]

                # Check if we already have this section
                key = (row['doc_slug'], row['anchor'])
                existing = next((r for r in results if (r.document_slug, r.section_anchor) == key), None)
                if existing:
                    continue

                results.append(SearchResult(
                    document_slug=row['doc_slug'],
                    document_title=row['doc_title'],
                    section_anchor=row['anchor'],
                    section_title=row['title'],
                    snippet=snippet,
                    relevance_score=10.0,
                    match_type='section',
                    tags=tags_in_line
                ))

        results = results[:limit]

        return SearchResponse(
            query="*",
            total_results=len(results),
            results=results,
            tags_matched=tags
        )

    def _separate_glossary_matches(self, results: List[SearchResult], query: str) -> tuple:
        """
        Separate glossary results from other results.
        Glossary matches go FIRST, always.

        Returns: (glossary_results, other_results)
        """
        query_lower = query.lower().strip()
        glossary_results = []
        other_results = []

        for result in results:
            # Check if this is a glossary result
            is_glossary = (
                result.document_slug == '9-glossary' or
                'glossary' in result.document_slug.lower()
            )

            if is_glossary:
                glossary_results.append(result)
            else:
                other_results.append(result)

        return glossary_results, other_results

    def _fetch_document_rows(
        self,
        conn: sqlite3.Connection,
        query: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[sqlite3.Row]:
        """Run FTS query against documents table, return raw rows."""
        sql = """
            SELECT
                d.slug,
                d.title,
                d.summary,
                d.importance,
                bm25(documents_fts) as score,
                snippet(documents_fts, 2, '<mark>', '</mark>', '...', 30) as snippet
            FROM documents_fts
            JOIN documents d ON documents_fts.rowid = d.id
        """
        params = []

        if tags:
            sql += """
                JOIN document_tags dt ON d.id = dt.document_id
                JOIN tags t ON dt.tag_id = t.id
                WHERE t.name IN ({})
                AND documents_fts MATCH ?
                AND d.slug NOT LIKE '%table-of-contents%'
            """.format(','.join('?' * len(tags)))
            params.extend(tags)
        else:
            sql += " WHERE documents_fts MATCH ? AND d.slug NOT LIKE '%table-of-contents%'"

        params.append(self._prepare_fts_query(query))
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        try:
            return conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []

    def _fetch_section_rows(
        self,
        conn: sqlite3.Connection,
        query: str,
        tags: Optional[List[str]],
        limit: int
    ) -> List[sqlite3.Row]:
        """Run FTS query against sections table, return raw rows."""
        sql = """
            SELECT
                d.slug as doc_slug,
                d.title as doc_title,
                s.anchor,
                s.title,
                bm25(sections_fts) as score,
                snippet(sections_fts, 1, '<mark>', '</mark>', '...', 30) as snippet
            FROM sections_fts
            JOIN sections s ON sections_fts.rowid = s.id
            JOIN documents d ON s.document_id = d.id
        """
        params = []

        if tags:
            sql += """
                JOIN document_tags dt ON d.id = dt.document_id
                JOIN tags t ON dt.tag_id = t.id
                WHERE t.name IN ({})
                AND sections_fts MATCH ?
            """.format(','.join('?' * len(tags)))
            params.extend(tags)
        else:
            sql += " WHERE sections_fts MATCH ?"

        params.append(self._prepare_fts_query(query))
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        try:
            return conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []

    def _get_tags_for_slugs(
        self,
        conn: sqlite3.Connection,
        slugs: List[str]
    ) -> Dict[str, List[str]]:
        """
        Fetch tags for multiple document slugs in a single query.

        Replaces the previous per-row _get_document_tags() pattern which caused
        up to 40 extra round-trips per search request.
        """
        if not slugs:
            return {}
        placeholders = ','.join('?' * len(slugs))
        rows = conn.execute(f"""
            SELECT d.slug, t.name
            FROM tags t
            JOIN document_tags dt ON t.id = dt.tag_id
            JOIN documents d ON dt.document_id = d.id
            WHERE d.slug IN ({placeholders})
        """, slugs).fetchall()

        result: Dict[str, List[str]] = {}
        for row in rows:
            result.setdefault(row['slug'], []).append(row['name'])
        return result

    def _prepare_fts_query(self, query: str) -> str:
        """
        Prepare a query string for FTS5.

        Handles special characters and query syntax.
        """
        # Remove or escape special FTS5 characters
        # Keep quotes for phrase searches
        query = re.sub(r'[^\w\s"()-]', ' ', query)

        # Collapse whitespace
        query = ' '.join(query.split())

        return query

    def _get_document_tags(self, conn: sqlite3.Connection, slug: str) -> List[str]:
        """Get tags for a document."""
        rows = conn.execute("""
            SELECT t.name FROM tags t
            JOIN document_tags dt ON t.id = dt.tag_id
            JOIN documents d ON dt.document_id = d.id
            WHERE d.slug = ?
        """, (slug,)).fetchall()

        return [row['name'] for row in rows]

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results, keeping highest scoring."""
        seen = {}

        for result in results:
            key = (result.document_slug, result.section_anchor)
            if key not in seen or result.relevance_score > seen[key].relevance_score:
                seen[key] = result

        return list(seen.values())

    def get_snippets(self, doc_slug: str, query: str, max_snippets: int = 3) -> List[str]:
        """
        Get highlighted snippets for a query within a document.

        Args:
            doc_slug: Document slug
            query: Search query
            max_snippets: Maximum number of snippets

        Returns:
            List of highlighted snippet strings
        """
        snippets = []

        with self._get_connection() as conn:
            # Get document content
            doc = conn.execute(
                "SELECT content FROM documents WHERE slug = ?",
                (doc_slug,)
            ).fetchone()

            if not doc:
                return snippets

            content = doc['content']

            # Find matches
            terms = query.lower().split()
            for term in terms:
                pattern = re.compile(
                    rf'(.{{0,100}})({re.escape(term)})(.{{0,100}})',
                    re.IGNORECASE
                )

                for match in pattern.finditer(content):
                    before, matched, after = match.groups()
                    snippet = f"...{before}<mark>{matched}</mark>{after}..."
                    snippets.append(snippet)

                    if len(snippets) >= max_snippets:
                        return snippets

        return snippets

    def get_all_tags(self) -> Dict[str, int]:
        """Get all tags with their document counts."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT t.name, COUNT(dt.document_id) as count
                FROM tags t
                LEFT JOIN document_tags dt ON t.id = dt.tag_id
                GROUP BY t.id
                ORDER BY count DESC, t.name
            """).fetchall()

            return {row['name']: row['count'] for row in rows}

    def get_document(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get a document by slug with its sections."""
        with self._get_connection() as conn:
            doc = conn.execute(
                "SELECT * FROM documents WHERE slug = ?",
                (slug,)
            ).fetchone()

            if not doc:
                return None

            sections = conn.execute(
                "SELECT * FROM sections WHERE document_id = ? ORDER BY id",
                (doc['id'],)
            ).fetchall()

            tags = self._get_document_tags(conn, slug)

            return {
                'id': doc['id'],
                'slug': doc['slug'],
                'title': doc['title'],
                'filename': doc['filename'],
                'summary': doc['summary'],
                'content': doc['content'],
                'importance': doc['importance'],
                'sections': [dict(s) for s in sections],
                'tags': tags
            }

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents (without full content)."""
        with self._get_connection() as conn:
            docs = conn.execute("""
                SELECT id, slug, title, filename, summary, importance
                FROM documents
                ORDER BY importance DESC, title
            """).fetchall()

            if not docs:
                return []

            slugs = [doc['slug'] for doc in docs]
            tags_by_slug = self._get_tags_for_slugs(conn, slugs)

            # Fetch all section counts in one query
            id_to_slug = {doc['id']: doc['slug'] for doc in docs}
            count_rows = conn.execute("""
                SELECT document_id, COUNT(*) as count
                FROM sections
                GROUP BY document_id
            """).fetchall()
            section_counts = {
                id_to_slug[row['document_id']]: row['count']
                for row in count_rows
                if row['document_id'] in id_to_slug
            }

            return [
                {
                    'slug': doc['slug'],
                    'title': doc['title'],
                    'summary': doc['summary'],
                    'tags': tags_by_slug.get(doc['slug'], []),
                    'section_count': section_counts.get(doc['slug'], 0),
                }
                for doc in docs
            ]

    def store_term_reference(
        self,
        term: str,
        source_doc: str,
        source_anchor: str,
        target_doc: str,
        target_anchor: str
    ):
        """Store a cross-reference between terms."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO term_references
                (term, source_document_slug, source_anchor, target_document_slug, target_anchor)
                VALUES (?, ?, ?, ?, ?)
            """, (term, source_doc, source_anchor, target_doc, target_anchor))
            conn.commit()

    def get_backlinks(self, target_anchor: str) -> List[Dict[str, str]]:
        """Get all documents/sections that reference a target anchor."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT
                    term,
                    source_document_slug,
                    source_anchor,
                    d.title as source_title
                FROM term_references tr
                JOIN documents d ON tr.source_document_slug = d.slug
                WHERE target_anchor = ?
            """, (target_anchor,)).fetchall()

            return [dict(row) for row in rows]
