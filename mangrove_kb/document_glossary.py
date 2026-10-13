"""Glossary extraction retained from the document service Michael consumes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
import re
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from .documents import DocumentNotFoundError, get_document_store


@dataclass
class GlossaryEntry:
    term: str
    definition: str
    anchor: str
    document_slug: str
    abbreviation: Optional[str] = None
    backlinks: list = field(default_factory=list)
    related_terms: list = field(default_factory=list)


@dataclass
class TermDefinition:
    term: str
    anchor: str
    document_slug: str
    abbreviation: Optional[str] = None
    definition: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


class _Glossary:
    GLOSSARY_TABLE_PATTERN = re.compile(
        "\\|\\s*([^|]+?)\\s*\\|\\s*([^|]+?)\\s*\\|\\s*([^|]*?)\\s*\\|\\s*([^|]+?)\\s*\\|",
        re.MULTILINE,
    )

    def __init__(self):
        self.term_registry: Dict[str, TermDefinition] = {}
        self.backlinks: Dict[str, List[Any]] = {}
        self._case_insensitive_map: Dict[str, str] = {}

    def build_term_registry(self, documents: List[Any]):
        self.term_registry.clear()
        self._case_insensitive_map.clear()
        for doc in documents:
            if "glossary" in doc.filename.lower():
                self._extract_glossary_terms(doc)
            elif "indicator" in doc.filename.lower():
                self._extract_indicator_terms(doc)
            elif "pattern" in doc.filename.lower():
                self._extract_pattern_terms(doc)
        for term in self.term_registry:
            self._case_insensitive_map[term.lower()] = term

    def _extract_glossary_terms(self, doc: Any):
        for match in self.GLOSSARY_TABLE_PATTERN.finditer(doc.content):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            abbreviation = match.group(3).strip() if match.group(3) else None
            if term.lower() in ("term", "definition", "---", "----", "------"):
                continue
            if "---" in term:
                continue
            term_anchor = re.sub("[^\\w\\s-]", "", term.lower())
            term_anchor = re.sub("\\s+", "-", term_anchor)
            term_anchor = re.sub("[-]+", "-", term_anchor)
            term_anchor = term_anchor.strip("-")
            term_def = TermDefinition(
                term=term,
                anchor=term_anchor,
                document_slug=doc.slug,
                abbreviation=abbreviation
                if abbreviation not in ("", "-", "N/A")
                else None,
                definition=definition,
            )
            self.term_registry[term] = term_def
            if abbreviation and abbreviation not in ("", "-", "N/A"):
                for abbr in abbreviation.split(","):
                    abbr = abbr.strip()
                    if abbr and abbr != "-":
                        self.term_registry[abbr] = term_def

    def _extract_indicator_terms(self, doc: Any):
        for section in doc.sections:
            if section.level > 2:
                continue
            match = re.search("([A-Za-z\\s]+)\\s*\\(([A-Z]+)\\)", section.title)
            if match:
                full_name = match.group(1).strip()
                abbrev = match.group(2).strip()
                term_def = TermDefinition(
                    term=full_name,
                    anchor=section.anchor,
                    document_slug=doc.slug,
                    abbreviation=abbrev,
                )
                self.term_registry[full_name] = term_def
                self.term_registry[abbrev] = term_def
            else:
                term_def = TermDefinition(
                    term=section.title, anchor=section.anchor, document_slug=doc.slug
                )
                self.term_registry[section.title] = term_def

    def _extract_pattern_terms(self, doc: Any):
        for section in doc.sections:
            if section.level > 2:
                continue
            term_def = TermDefinition(
                term=section.title, anchor=section.anchor, document_slug=doc.slug
            )
            self.term_registry[section.title] = term_def

    def get_glossary_entries(self) -> List[GlossaryEntry]:
        entries = []
        for term, term_def in self.term_registry.items():
            if term != term_def.term:
                continue
            entry = GlossaryEntry(
                term=term_def.term,
                abbreviation=term_def.abbreviation,
                definition=term_def.definition or "",
                anchor=term_def.anchor,
                document_slug=term_def.document_slug,
                backlinks=self.backlinks.get(term_def.anchor, []),
                related_terms=self._find_related_terms(term_def),
            )
            entries.append(entry)
        return sorted(entries, key=lambda e: e.term.lower())

    def _find_related_terms(self, term_def: TermDefinition) -> List[str]:
        related = []
        term_words = set(term_def.term.lower().split())
        for other_term, other_def in self.term_registry.items():
            if other_term == term_def.term:
                continue
            other_words = set(other_term.lower().split())
            if term_words & other_words:
                related.append(other_term)
        return related[:5]


@lru_cache(maxsize=1)
def _glossary_entries():
    store = get_document_store()
    documents = []
    for summary in store.list_documents()["documents"]:
        doc = store.get_document(summary["slug"])
        sections = [SimpleNamespace(**section) for section in doc.pop("sections")]
        documents.append(
            SimpleNamespace(**doc, filename=doc["slug"] + ".md", sections=sections)
        )
    glossary = _Glossary()
    glossary.build_term_registry(documents)
    return tuple(asdict(entry) for entry in glossary.get_glossary_entries())


def glossary_entries():
    from copy import deepcopy

    return deepcopy(_glossary_entries())


def get_glossary_entry(term):
    from copy import deepcopy

    if not isinstance(term, str) or not term.strip() or len(term) > 200:
        raise ValueError("term must be non-empty text of at most 200 characters")
    wanted = term.lower().strip()
    entries = _glossary_entries()
    matches = [entry for entry in entries if entry["term"].casefold() == wanted.casefold()]
    if not matches:
        matches = [entry for entry in entries if wanted.casefold() in {
            alias.strip().casefold()
            for alias in re.split(r"[,/]", entry.get("abbreviation") or "")
            if alias.strip()
        }]
    if not matches:
        pattern = re.compile(r"(?<!\w)" + re.escape(wanted) + r"(?!\w)", re.IGNORECASE)
        matches = [entry for entry in entries if pattern.search(entry["term"])]
    if not matches:
        raise DocumentNotFoundError("No glossary entry matches the term")
    if len(matches) > 1:
        raise ValueError("Ambiguous glossary term; use the full term: " +
                         ", ".join(entry["term"] for entry in matches[:5]))
    return deepcopy(matches[0])
