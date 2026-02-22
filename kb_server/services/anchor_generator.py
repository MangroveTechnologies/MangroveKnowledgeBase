"""
Anchor Generator for stable, deterministic URL slugs.

Creates slugs based on hierarchical numbering in the content itself,
ensuring anchors survive file reorganization.
"""

import re
import unicodedata
from typing import Optional, Tuple


class AnchorGenerator:
    """Generates deterministic, stable anchors for documents and sections."""

    # Pattern to extract document number from filename (e.g., "01-market-foundations.md" -> 1)
    FILENAME_NUMBER_PATTERN = re.compile(r'^(\d+)-')

    # Pattern to extract section number from heading (e.g., "## 8.1 Trading Rules" -> (8, 1))
    SECTION_NUMBER_PATTERN = re.compile(r'^#+ (\d+)\.(\d+)(?:\.(\d+))?\s+(.+)$')

    # Pattern for chapter heading (e.g., "# 8. Risk Management" -> (8, "Risk Management"))
    CHAPTER_NUMBER_PATTERN = re.compile(r'^# (\d+)\.\s+(.+)$')

    @staticmethod
    def slugify(text: str) -> str:
        """
        Convert text to a URL-safe slug.

        Args:
            text: The text to slugify

        Returns:
            URL-safe slug string
        """
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')

        # Convert to lowercase
        text = text.lower()

        # Replace spaces and underscores with hyphens
        text = re.sub(r'[\s_]+', '-', text)

        # Remove all non-alphanumeric characters except hyphens
        text = re.sub(r'[^a-z0-9-]', '', text)

        # Collapse multiple hyphens
        text = re.sub(r'-+', '-', text)

        # Strip leading/trailing hyphens
        text = text.strip('-')

        return text

    @classmethod
    def generate_document_slug(cls, filename: str, title: Optional[str] = None) -> str:
        """
        Generate a stable slug for a document.

        Uses the document number from the filename for stability.

        Args:
            filename: The markdown filename (e.g., "01-market-foundations.md")
            title: Optional document title for fallback

        Returns:
            Document slug (e.g., "1-market-foundations")
        """
        # Extract number from filename
        match = cls.FILENAME_NUMBER_PATTERN.match(filename)
        if match:
            doc_num = int(match.group(1))
            # Get the rest of the filename without number and extension
            rest = filename[match.end():].replace('.md', '')
            return f"{doc_num}-{cls.slugify(rest)}"

        # Fallback to slugified filename
        return cls.slugify(filename.replace('.md', ''))

    @classmethod
    def generate_section_anchor(
        cls,
        heading: str,
        doc_number: Optional[int] = None
    ) -> Tuple[str, Optional[Tuple[int, ...]]]:
        """
        Generate a stable anchor for a section heading.

        Args:
            heading: The full heading line (e.g., "## 8.1 Trading Rules")
            doc_number: Optional document number for context

        Returns:
            Tuple of (anchor_slug, section_numbers) where section_numbers
            is a tuple like (8, 1) or (8, 1, 2) for subsections
        """
        # Try to match numbered section pattern
        section_match = cls.SECTION_NUMBER_PATTERN.match(heading)
        if section_match:
            major = int(section_match.group(1))
            minor = int(section_match.group(2))
            subsection = section_match.group(3)
            title = section_match.group(4)

            if subsection:
                sub = int(subsection)
                anchor = f"{major}-{minor}-{sub}-{cls.slugify(title)}"
                return anchor, (major, minor, sub)
            else:
                anchor = f"{major}-{minor}-{cls.slugify(title)}"
                return anchor, (major, minor)

        # Try to match chapter heading pattern
        chapter_match = cls.CHAPTER_NUMBER_PATTERN.match(heading)
        if chapter_match:
            num = int(chapter_match.group(1))
            title = chapter_match.group(2)
            anchor = f"{num}-{cls.slugify(title)}"
            return anchor, (num,)

        # Fallback: extract heading text and slugify
        heading_text = re.sub(r'^#+\s*', '', heading)
        anchor = cls.slugify(heading_text)

        # Prepend document number if available
        if doc_number:
            anchor = f"{doc_number}-{anchor}"

        return anchor, None

    @classmethod
    def extract_heading_level(cls, heading: str) -> int:
        """
        Extract the heading level from a markdown heading.

        Args:
            heading: The heading line (e.g., "## Section")

        Returns:
            Heading level (1-6)
        """
        match = re.match(r'^(#+)', heading)
        if match:
            return len(match.group(1))
        return 0

    @classmethod
    def extract_heading_text(cls, heading: str) -> str:
        """
        Extract the text content from a heading, removing markdown and numbers.

        Args:
            heading: The heading line

        Returns:
            Clean heading text
        """
        # Remove leading hashes
        text = re.sub(r'^#+\s*', '', heading)

        # Remove leading numbers (e.g., "8.1 " or "8. ")
        text = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', text)

        return text.strip()

    @classmethod
    def parse_section_numbers(cls, heading: str) -> Optional[Tuple[int, ...]]:
        """
        Parse section numbers from a heading.

        Args:
            heading: The heading line

        Returns:
            Tuple of section numbers or None
        """
        # Match patterns like "8.1.2" or "8.1" or "8."
        match = re.search(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?', heading)
        if match:
            nums = [int(g) for g in match.groups() if g is not None]
            return tuple(nums) if nums else None
        return None

    @classmethod
    def build_hierarchy_path(cls, section_numbers: Tuple[int, ...]) -> str:
        """
        Build a hierarchical path string from section numbers.

        Args:
            section_numbers: Tuple like (8, 1, 2)

        Returns:
            Path string like "8/8.1/8.1.2"
        """
        paths = []
        for i in range(len(section_numbers)):
            paths.append('.'.join(str(n) for n in section_numbers[:i+1]))
        return '/'.join(paths)
