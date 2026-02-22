"""
Document Loader for parsing and ingesting markdown files.

Extracts document structure, metadata, tags, and content for indexing.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Generator

try:
    from ..models import Document, Section, Tag
    from .anchor_generator import AnchorGenerator
except ImportError:
    from models import Document, Section, Tag
    from services.anchor_generator import AnchorGenerator


class DocumentLoader:
    """Loads and parses knowledge base markdown documents."""

    # Pattern to match tags line (e.g., "Tags: tag1, tag2, tag3")
    TAGS_PATTERN = re.compile(r'^Tags?:\s*(.+)$', re.IGNORECASE | re.MULTILINE)

    # Pattern to match any heading
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    # Pattern for fenced code blocks
    FENCED_CODE_PATTERN = re.compile(r'```[\s\S]*?```', re.MULTILINE)

    def __init__(self, kb_path: Path):
        """
        Initialize the document loader.

        Args:
            kb_path: Path to the knowledge base directory
        """
        self.kb_path = Path(kb_path)
        self.anchor_gen = AnchorGenerator()

    def load_all_documents(self) -> List[Document]:
        """
        Load all markdown documents from the knowledge base.

        Returns:
            List of Document objects
        """
        documents = []

        # Get all markdown files, sorted by name
        md_files = sorted(self.kb_path.glob("*.md"))

        for md_file in md_files:
            doc = self.load_document(md_file)
            if doc:
                documents.append(doc)

        return documents

    def load_document(self, file_path: Path) -> Optional[Document]:
        """
        Load a single markdown document.

        Args:
            file_path: Path to the markdown file

        Returns:
            Document object or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

        filename = file_path.name

        # Generate document slug
        slug = self.anchor_gen.generate_document_slug(filename)

        # Parse document structure
        title = self._extract_title(content)
        summary = self._extract_summary(content)
        tags = self._extract_tags(content)
        sections = self._extract_sections(content)

        # Determine importance based on document number (lower = more important)
        doc_number = self._extract_doc_number(filename)
        importance = 100 - doc_number if doc_number else 50

        return Document(
            slug=slug,
            title=title or filename,
            filename=filename,
            summary=summary,
            content=content,
            sections=sections,
            tags=tags,
            importance=importance
        )

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract the document title from the first H1 heading."""
        match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Remove leading numbers (e.g., "1. Market Foundations" -> "Market Foundations")
            title = re.sub(r'^\d+\.\s*', '', title)
            return title
        return None

    def _extract_summary(self, content: str) -> Optional[str]:
        """
        Extract the document summary.

        Looks for the first paragraph after the title that isn't a heading or tags.
        """
        # Split into lines
        lines = content.split('\n')

        # Find content after the first H1
        in_summary = False
        summary_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip empty lines before summary
            if not in_summary and not stripped:
                continue

            # Skip the title
            if stripped.startswith('# '):
                in_summary = True
                continue

            if in_summary:
                # Stop at next heading, tags, or horizontal rule
                if stripped.startswith('#') or stripped.startswith('Tags:') or stripped == '---':
                    break

                # Skip empty lines in summary
                if not stripped:
                    if summary_lines:
                        break
                    continue

                summary_lines.append(stripped)

        if summary_lines:
            return ' '.join(summary_lines)
        return None

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from the document."""
        tags = []

        for match in self.TAGS_PATTERN.finditer(content):
            tag_string = match.group(1)
            # Split by comma and clean up
            for tag in tag_string.split(','):
                tag = tag.strip().lower()
                # Remove any trailing punctuation
                tag = re.sub(r'[.;:]+$', '', tag)
                if tag and tag not in tags:
                    tags.append(tag)

        return tags

    def _extract_sections(self, content: str) -> List[Section]:
        """
        Extract all sections from the document.

        Returns a flat list of sections with parent references for hierarchy.
        """
        sections = []

        # Find all headings with their positions
        headings = list(self.HEADING_PATTERN.finditer(content))

        if not headings:
            return sections

        # Track current section hierarchy for context
        hierarchy_context = []  # List of (level, section_nums)

        # Process each heading
        for i, match in enumerate(headings):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            full_heading = match.group(0)

            # Skip H1 (document title)
            if level == 1:
                continue

            # Only include H2 and H3 in sidebar navigation (skip H4, H5, H6)
            if level > 3:
                continue

            # Generate anchor with hierarchy context
            anchor, section_nums = self.anchor_gen.generate_section_anchor(full_heading)

            # If anchor has no section numbers (unnumbered heading), prepend parent context
            if section_nums is None and hierarchy_context:
                # Find the most recent parent with numbers
                parent_nums = None
                for parent_level, parent_section_nums in reversed(hierarchy_context):
                    if parent_level < level and parent_section_nums:
                        parent_nums = parent_section_nums
                        break

                # Prepend parent numbers to anchor
                if parent_nums:
                    prefix = '-'.join(str(n) for n in parent_nums)
                    anchor = f"{prefix}-{anchor}"

            # Update hierarchy context
            # Remove entries at same or deeper level
            hierarchy_context = [(l, n) for l, n in hierarchy_context if l < level]
            # Add current level
            hierarchy_context.append((level, section_nums))

            # Extract section content (from this heading to the next)
            start_pos = match.end()
            end_pos = headings[i + 1].start() if i + 1 < len(headings) else len(content)
            section_content = content[start_pos:end_pos].strip()

            # Find parent anchor
            parent_anchor = self._find_parent_anchor(sections, level)

            # KEEP the full heading text WITH numbers for display
            title = heading_text  # Changed: keep original text including numbers

            section = Section(
                anchor=anchor,
                title=title,
                level=level,
                content=section_content,
                parent_anchor=parent_anchor
            )

            sections.append(section)

        return sections

    def _find_parent_anchor(self, sections: List[Section], current_level: int) -> Optional[str]:
        """Find the parent section anchor for a given heading level."""
        # Look backwards for the most recent section with a lower level
        for section in reversed(sections):
            if section.level < current_level:
                return section.anchor
        return None

    def _extract_doc_number(self, filename: str) -> Optional[int]:
        """Extract the document number from filename."""
        match = re.match(r'^(\d+)-', filename)
        if match:
            return int(match.group(1))
        return None

    def get_section_content_clean(self, content: str) -> str:
        """
        Get section content with code blocks removed for search indexing.

        Args:
            content: Raw section content

        Returns:
            Content with code blocks removed
        """
        # Remove fenced code blocks
        clean = self.FENCED_CODE_PATTERN.sub('', content)

        # Remove inline code
        clean = re.sub(r'`[^`]+`', '', clean)

        return clean

    def iter_documents(self) -> Generator[Document, None, None]:
        """
        Iterate over documents one at a time (memory efficient).

        Yields:
            Document objects
        """
        md_files = sorted(self.kb_path.glob("*.md"))

        for md_file in md_files:
            doc = self.load_document(md_file)
            if doc:
                yield doc

    def get_document_by_slug(self, slug: str) -> Optional[Document]:
        """
        Load a specific document by its slug.

        Args:
            slug: Document slug

        Returns:
            Document or None
        """
        for doc in self.iter_documents():
            if doc.slug == slug:
                return doc
        return None

    def build_section_tree(self, sections: List[Section]) -> List[Section]:
        """
        Build a hierarchical tree from flat section list.

        Args:
            sections: Flat list of sections with parent_anchor references

        Returns:
            List of top-level sections with nested children
        """
        # Create lookup by anchor
        section_map = {s.anchor: s for s in sections}

        # Clear any existing children
        for section in sections:
            section.children = []

        # Build tree
        roots = []
        for section in sections:
            if section.parent_anchor and section.parent_anchor in section_map:
                parent = section_map[section.parent_anchor]
                parent.children.append(section)
            else:
                roots.append(section)

        return roots
