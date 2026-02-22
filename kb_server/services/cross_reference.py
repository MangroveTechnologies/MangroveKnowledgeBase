"""
Cross-Reference Engine with code-block safety.

Automatically detects and links glossary terms, indicators, and patterns
while safely avoiding code blocks and inline code.
"""

import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

try:
    from ..models import Document, Section, GlossaryEntry, TermReference, SeeAlso
except ImportError:
    from models import Document, Section, GlossaryEntry, TermReference, SeeAlso


@dataclass
class ProtectedRegion:
    """Represents a region of text that should not be modified."""
    start: int
    end: int
    type: str  # 'fenced_code', 'inline_code', 'html_code'


@dataclass
class TermDefinition:
    """A term that can be cross-referenced."""
    term: str
    anchor: str
    document_slug: str
    abbreviation: Optional[str] = None
    definition: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


class CrossReferenceEngine:
    """
    Engine for automatic cross-referencing in markdown documents.

    Features:
    - Builds term registry from glossary and indicator chapters
    - Safely skips code blocks (fenced and inline)
    - Links only first occurrence per section
    - Generates backlinks and "See Also" sections
    """

    # Patterns for protected regions (code blocks)
    FENCED_CODE_PATTERN = re.compile(r'```[\s\S]*?```', re.MULTILINE)
    INLINE_CODE_PATTERN = re.compile(r'`[^`\n]+`')
    HTML_CODE_PATTERN = re.compile(r'<code>[\s\S]*?</code>', re.IGNORECASE)
    HTML_PRE_PATTERN = re.compile(r'<pre>[\s\S]*?</pre>', re.IGNORECASE)

    # Pattern to extract glossary terms from tables (4 columns: Term, Definition, Abbreviation, Category)
    GLOSSARY_TABLE_PATTERN = re.compile(
        r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)\s*\|',
        re.MULTILINE
    )

    def __init__(self):
        """Initialize the cross-reference engine."""
        self.term_registry: Dict[str, TermDefinition] = {}
        self.backlinks: Dict[str, List[TermReference]] = {}
        self._case_insensitive_map: Dict[str, str] = {}

    def build_term_registry(self, documents: List[Document]):
        """
        Build the term registry from knowledge base documents.

        Extracts terms from:
        - Glossary chapter (09-glossary.md)
        - Indicators chapter (04-indicators.md)
        - Chart patterns chapter (05-chart-patterns.md)

        Args:
            documents: List of all documents
        """
        self.term_registry.clear()
        self._case_insensitive_map.clear()

        for doc in documents:
            if 'glossary' in doc.filename.lower():
                self._extract_glossary_terms(doc)
            elif 'indicator' in doc.filename.lower():
                self._extract_indicator_terms(doc)
            elif 'pattern' in doc.filename.lower():
                self._extract_pattern_terms(doc)

        # Build case-insensitive lookup
        for term in self.term_registry:
            self._case_insensitive_map[term.lower()] = term

    def _extract_glossary_terms(self, doc: Document):
        """Extract terms from the glossary document.

        New format: | Term | Definition | Abbreviation | Category |
        All terms link directly to the glossary page.
        """
        # Parse glossary tables (4 columns: Term, Definition, Abbreviation, Category)
        for match in self.GLOSSARY_TABLE_PATTERN.finditer(doc.content):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            abbreviation = match.group(3).strip() if match.group(3) else None
            # category = match.group(4).strip()  # Available if needed

            # Skip table headers and separator rows
            if term.lower() in ('term', 'definition', '---', '----', '------'):
                continue
            if '---' in term:
                continue

            # Generate anchor from term name for direct linking
            term_anchor = re.sub(r'[^\w\s-]', '', term.lower())
            term_anchor = re.sub(r'\s+', '-', term_anchor)
            term_anchor = re.sub(r'[-]+', '-', term_anchor)  # Collapse multiple dashes
            term_anchor = term_anchor.strip('-')  # Remove leading/trailing dashes

            term_def = TermDefinition(
                term=term,
                anchor=term_anchor,  # Link to specific term anchor (e.g., "vwap", "support")
                document_slug=doc.slug,
                abbreviation=abbreviation if abbreviation not in ('', '-', 'N/A') else None,
                definition=definition
            )

            self.term_registry[term] = term_def

            # Also register by abbreviation if present
            if abbreviation and abbreviation not in ('', '-', 'N/A'):
                # Handle multiple abbreviations like "ES, NQ"
                for abbr in abbreviation.split(','):
                    abbr = abbr.strip()
                    if abbr and abbr != '-':
                        self.term_registry[abbr] = term_def

    def _extract_indicator_terms(self, doc: Document):
        """Extract indicator names from the indicators document."""
        # Look for section headings that define indicators
        for section in doc.sections:
            # Skip high-level category sections
            if section.level > 2:
                continue

            # Extract indicator names from heading
            # Format: "4.1.1 Simple Moving Average (SMA)"
            match = re.search(r'([A-Za-z\s]+)\s*\(([A-Z]+)\)', section.title)
            if match:
                full_name = match.group(1).strip()
                abbrev = match.group(2).strip()

                term_def = TermDefinition(
                    term=full_name,
                    anchor=section.anchor,
                    document_slug=doc.slug,
                    abbreviation=abbrev
                )

                self.term_registry[full_name] = term_def
                self.term_registry[abbrev] = term_def
            else:
                # Just use the section title
                term_def = TermDefinition(
                    term=section.title,
                    anchor=section.anchor,
                    document_slug=doc.slug
                )
                self.term_registry[section.title] = term_def

    def _extract_pattern_terms(self, doc: Document):
        """Extract pattern names from the chart patterns document."""
        for section in doc.sections:
            if section.level > 2:
                continue

            term_def = TermDefinition(
                term=section.title,
                anchor=section.anchor,
                document_slug=doc.slug
            )
            self.term_registry[section.title] = term_def

    def _find_term_anchor(self, term: str, doc: Document) -> str:
        """Find or generate an anchor for a term in a document."""
        # Try to find a section that matches
        term_lower = term.lower()
        for section in doc.sections:
            if term_lower in section.title.lower():
                return section.anchor

        # Generate anchor from term
        anchor = re.sub(r'[^\w\s-]', '', term.lower())
        anchor = re.sub(r'\s+', '-', anchor)
        return f"{doc.slug}#{anchor}"

    def find_protected_regions(self, content: str) -> List[ProtectedRegion]:
        """
        Find all regions in the content that should not be modified.

        This includes:
        - Fenced code blocks (``` ... ```)
        - Inline code (`...`)
        - HTML code/pre tags

        Args:
            content: The markdown content

        Returns:
            List of protected regions sorted by start position
        """
        regions = []

        # Find fenced code blocks
        for match in self.FENCED_CODE_PATTERN.finditer(content):
            regions.append(ProtectedRegion(
                start=match.start(),
                end=match.end(),
                type='fenced_code'
            ))

        # Find inline code
        for match in self.INLINE_CODE_PATTERN.finditer(content):
            regions.append(ProtectedRegion(
                start=match.start(),
                end=match.end(),
                type='inline_code'
            ))

        # Find HTML code tags
        for match in self.HTML_CODE_PATTERN.finditer(content):
            regions.append(ProtectedRegion(
                start=match.start(),
                end=match.end(),
                type='html_code'
            ))

        # Find HTML pre tags
        for match in self.HTML_PRE_PATTERN.finditer(content):
            regions.append(ProtectedRegion(
                start=match.start(),
                end=match.end(),
                type='html_code'
            ))

        # Sort by start position
        regions.sort(key=lambda r: r.start)

        return regions

    def is_in_protected_region(self, pos: int, regions: List[ProtectedRegion]) -> bool:
        """Check if a position is within a protected region."""
        for region in regions:
            if region.start <= pos < region.end:
                return True
            # Since regions are sorted, we can stop early
            if region.start > pos:
                break
        return False

    def apply_cross_references(
        self,
        content: str,
        source_doc_slug: str,
        max_links_per_term: int = 1
    ) -> Tuple[str, List[TermReference]]:
        """
        Apply cross-reference links to content.

        Only links terms outside of code blocks and only the first
        occurrence of each term per section.

        Args:
            content: The markdown content to process
            source_doc_slug: The slug of the source document
            max_links_per_term: Maximum times to link each term

        Returns:
            Tuple of (modified content, list of term references)
        """
        if not self.term_registry:
            return content, []

        # Find protected regions on original content
        protected = self.find_protected_regions(content)

        # Track which terms have been linked (reset per section)
        linked_terms: Dict[str, int] = {}
        references: List[TermReference] = []

        # Process entire content at once, tracking section boundaries
        current_anchor = source_doc_slug

        # Find all section headers to track current section
        section_headers = list(re.finditer(r'^## .+$', content, flags=re.MULTILINE))

        # Process the content, respecting protected regions
        processed, refs = self._process_content_with_sections(
            content,
            source_doc_slug,
            protected,
            section_headers,
            max_links_per_term
        )

        return processed, refs

    def _process_content_with_sections(
        self,
        content: str,
        source_doc_slug: str,
        protected: List[ProtectedRegion],
        section_headers: List,
        max_links: int
    ) -> Tuple[str, List[TermReference]]:
        """Process entire content while tracking section boundaries."""
        references = []
        result = []
        last_end = 0

        # Track linked terms per section
        linked_terms: Dict[str, int] = {}
        current_section_start = 0
        current_anchor = source_doc_slug

        # Sort terms by length (longer first) to match multi-word terms first
        sorted_terms = sorted(self.term_registry.keys(), key=len, reverse=True)

        # Build pattern for all terms
        patterns = []
        for term in sorted_terms:
            escaped = re.escape(term)
            patterns.append(rf'\b{escaped}\b')

        if not patterns:
            return content, references

        combined_pattern = '|'.join(patterns)

        # Find all term matches
        matches = list(re.finditer(combined_pattern, content, re.IGNORECASE))

        for match in matches:
            matched_text = match.group(0)
            pos = match.start()

            # Check if we've entered a new section (reset linked_terms)
            for header in section_headers:
                if current_section_start < header.start() <= pos:
                    linked_terms.clear()
                    current_section_start = header.start()
                    current_anchor = self._extract_anchor_from_heading(header.group(0))

            # Check if in protected region (code block, inline code, etc.)
            if self.is_in_protected_region(pos, protected):
                continue

            # Find the canonical term
            term_key = matched_text
            if matched_text.lower() in self._case_insensitive_map:
                term_key = self._case_insensitive_map[matched_text.lower()]
            elif matched_text in self.term_registry:
                term_key = matched_text
            else:
                continue

            term_def = self.term_registry.get(term_key)
            if not term_def:
                continue

            # Don't link to self
            if term_def.document_slug == source_doc_slug and term_def.anchor == current_anchor:
                continue

            # Check link count for this section
            if linked_terms.get(term_key, 0) >= max_links:
                continue

            # Add the link
            result.append(content[last_end:pos])

            link_url = f"/doc/{term_def.document_slug}#{term_def.anchor}"
            result.append(f"[{matched_text}]({link_url})")

            last_end = match.end()
            linked_terms[term_key] = linked_terms.get(term_key, 0) + 1

            # Record reference
            references.append(TermReference(
                term=term_key,
                source_anchor=current_anchor,
                target_anchor=term_def.anchor,
                source_document=source_doc_slug,
                target_document=term_def.document_slug
            ))

        result.append(content[last_end:])
        return ''.join(result), references

    def _extract_anchor_from_heading(self, heading: str) -> str:
        """Extract or generate an anchor from a heading."""
        # Remove markdown heading prefix
        text = re.sub(r'^#+\s*', '', heading)
        # Remove numbers
        text = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', text)
        # Generate slug
        anchor = re.sub(r'[^\w\s-]', '', text.lower())
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor

    def get_glossary_entries(self) -> List[GlossaryEntry]:
        """Get all glossary entries with backlinks."""
        entries = []

        for term, term_def in self.term_registry.items():
            # Skip abbreviations that point to full terms
            if term_def.abbreviation and term == term_def.abbreviation:
                continue

            entry = GlossaryEntry(
                term=term_def.term,
                abbreviation=term_def.abbreviation,
                definition=term_def.definition or '',
                anchor=term_def.anchor,
                document_slug=term_def.document_slug,
                backlinks=self.backlinks.get(term_def.anchor, []),
                related_terms=self._find_related_terms(term_def)
            )
            entries.append(entry)

        return sorted(entries, key=lambda e: e.term.lower())

    def _find_related_terms(self, term_def: TermDefinition) -> List[str]:
        """Find terms related to a given term."""
        related = []
        term_words = set(term_def.term.lower().split())

        for other_term, other_def in self.term_registry.items():
            if other_term == term_def.term:
                continue

            other_words = set(other_term.lower().split())

            # Check for word overlap
            if term_words & other_words:
                related.append(other_term)

        return related[:5]  # Limit to 5 related terms

    def generate_see_also(
        self,
        doc: Document,
        all_docs: List[Document]
    ) -> List[SeeAlso]:
        """
        Generate "See Also" suggestions based on shared tags.

        Args:
            doc: The current document
            all_docs: All documents in the knowledge base

        Returns:
            List of related documents/sections
        """
        see_also = []
        doc_tags = set(doc.tags)

        for other_doc in all_docs:
            if other_doc.slug == doc.slug:
                continue

            other_tags = set(other_doc.tags)
            shared_tags = doc_tags & other_tags

            if shared_tags:
                see_also.append(SeeAlso(
                    anchor=other_doc.slug,
                    title=other_doc.title,
                    document_slug=other_doc.slug,
                    relevance=f"Shared topics: {', '.join(sorted(shared_tags)[:3])}"
                ))

        # Sort by number of shared tags (relevance)
        see_also.sort(key=lambda s: len(s.relevance.split(',')), reverse=True)

        return see_also[:5]  # Top 5 related

    def record_backlink(self, reference: TermReference):
        """Record a backlink for a term reference."""
        target = reference.target_anchor
        if target not in self.backlinks:
            self.backlinks[target] = []

        # Avoid duplicates
        for existing in self.backlinks[target]:
            if (existing.source_anchor == reference.source_anchor and
                existing.source_document == reference.source_document):
                return

        self.backlinks[target].append(reference)
