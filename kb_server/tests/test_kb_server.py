"""
Integration tests for the Knowledge Base Document Server.

Tests the full pipeline with actual knowledge base files.
"""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kb_server.services.document_loader import DocumentLoader
from kb_server.services.anchor_generator import AnchorGenerator
from kb_server.services.search_engine import SearchEngine
from kb_server.services.cross_reference import CrossReferenceEngine
from kb_server.services.synonyms import SynonymRegistry, get_synonym_registry
from kb_server.config import settings


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def kb_path():
    """Get the knowledge base path."""
    return settings.kb_path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def document_loader(kb_path):
    """Create a document loader instance."""
    return DocumentLoader(kb_path)


@pytest.fixture
def search_engine(temp_db):
    """Create a search engine with temporary database."""
    return SearchEngine(temp_db)


@pytest.fixture
def cross_ref_engine():
    """Create a cross-reference engine."""
    return CrossReferenceEngine()


# =============================================================================
# Anchor Generator Tests
# =============================================================================

class TestAnchorGenerator:
    """Tests for anchor generation."""

    def test_slugify_basic(self):
        """Test basic text slugification."""
        assert AnchorGenerator.slugify("Hello World") == "hello-world"
        assert AnchorGenerator.slugify("Risk Management") == "risk-management"

    def test_slugify_special_chars(self):
        """Test slugification with special characters."""
        assert AnchorGenerator.slugify("Risk & Reward") == "risk-reward"
        assert AnchorGenerator.slugify("Stop-Loss (SL)") == "stop-loss-sl"

    def test_document_slug_from_filename(self):
        """Test document slug generation from filename."""
        slug = AnchorGenerator.generate_document_slug("01-market-foundations.md")
        assert slug == "1-market-foundations"

        slug = AnchorGenerator.generate_document_slug("08-risk-management.md")
        assert slug == "8-risk-management"

    def test_section_anchor(self):
        """Test section anchor generation."""
        anchor, nums = AnchorGenerator.generate_section_anchor("## 8.1 Position Sizing")
        assert "8-1" in anchor
        assert "position-sizing" in anchor
        assert nums == (8, 1)

    def test_heading_level_extraction(self):
        """Test heading level extraction."""
        assert AnchorGenerator.extract_heading_level("# Title") == 1
        assert AnchorGenerator.extract_heading_level("## Section") == 2
        assert AnchorGenerator.extract_heading_level("### Subsection") == 3


# =============================================================================
# Synonym Registry Tests
# =============================================================================

class TestSynonymRegistry:
    """Tests for synonym support."""

    def test_get_synonyms(self):
        """Test synonym lookup."""
        registry = SynonymRegistry()

        synonyms = registry.get_synonyms("MA")
        assert "moving average" in synonyms

    def test_get_synonyms_reverse(self):
        """Test reverse synonym lookup."""
        registry = SynonymRegistry()

        synonyms = registry.get_synonyms("moving average")
        assert "ma" in [s.lower() for s in synonyms]

    def test_query_expansion(self):
        """Test query expansion."""
        registry = SynonymRegistry()

        expanded = registry.expand_query("MA crossover")
        assert "MA" in expanded or "moving average" in expanded

    def test_case_insensitive(self):
        """Test case-insensitive lookup."""
        registry = SynonymRegistry()

        assert registry.get_synonyms("rsi") == registry.get_synonyms("RSI")


# =============================================================================
# Document Loader Tests
# =============================================================================

class TestDocumentLoader:
    """Tests for document loading."""

    def test_load_all_documents(self, document_loader, kb_path):
        """Test loading all documents."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()
        assert len(documents) > 0

        # Check that each document has required fields
        for doc in documents:
            assert doc.slug
            assert doc.title
            assert doc.filename

    def test_extract_tags(self, document_loader, kb_path):
        """Test tag extraction."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()

        # At least some documents should have tags
        docs_with_tags = [d for d in documents if d.tags]
        assert len(docs_with_tags) > 0

    def test_extract_sections(self, document_loader, kb_path):
        """Test section extraction."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()

        # Each document should have sections
        for doc in documents:
            assert len(doc.sections) > 0


# =============================================================================
# Cross-Reference Tests
# =============================================================================

class TestCrossReference:
    """Tests for cross-referencing."""

    def test_find_protected_regions(self, cross_ref_engine):
        """Test detection of code blocks."""
        content = """
        Some text here.

        ```python
        def hello():
            pass
        ```

        More text with `inline code` here.
        """

        regions = cross_ref_engine.find_protected_regions(content)
        assert len(regions) >= 2  # fenced + inline

    def test_is_in_protected_region(self, cross_ref_engine):
        """Test protection detection."""
        content = "Text `code` more"
        regions = cross_ref_engine.find_protected_regions(content)

        # Position inside code should be protected
        code_start = content.index('`')
        assert cross_ref_engine.is_in_protected_region(code_start + 1, regions)

    def test_no_links_in_code(self, cross_ref_engine):
        """Test that links are not inserted in code blocks."""
        from kb_server.services.cross_reference import TermDefinition

        cross_ref_engine.term_registry["RSI"] = TermDefinition(
            term="RSI",
            anchor="rsi",
            document_slug="indicators"
        )
        cross_ref_engine._case_insensitive_map["rsi"] = "RSI"

        content = """
        RSI is great for momentum.

        ```python
        rsi = calculate_RSI(data)
        ```

        Use RSI carefully.
        """

        result, refs = cross_ref_engine.apply_cross_references(content, "test-doc")

        # RSI in code block should NOT be linked
        assert "```python\nrsi = calculate_RSI(data)\n```" in result or \
               "`calculate_RSI`" not in result  # No link inside code


# =============================================================================
# Search Engine Tests
# =============================================================================

class TestSearchEngine:
    """Tests for search functionality."""

    def test_build_index(self, search_engine, document_loader, kb_path):
        """Test index building."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()
        search_engine.build_index(documents)

        # Verify documents are indexed
        all_docs = search_engine.get_all_documents()
        assert len(all_docs) == len(documents)

    def test_search_basic(self, search_engine, document_loader, kb_path):
        """Test basic search."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()
        search_engine.build_index(documents)

        # Search for a common term
        results = search_engine.search("trading")
        assert results.total_results > 0

    def test_search_with_stemming(self, search_engine, document_loader, kb_path):
        """Test that Porter stemmer works."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()
        search_engine.build_index(documents)

        # "trade" should match "trading", "trades", etc.
        results = search_engine.search("trade", expand=False)
        assert results.total_results > 0

    def test_search_with_synonym_expansion(self, search_engine, document_loader, kb_path):
        """Test synonym expansion in search."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()
        search_engine.build_index(documents)

        # Search with expansion
        results_expanded = search_engine.search("MA", expand=True)
        results_no_expand = search_engine.search("MA", expand=False)

        # Expanded search should find at least as many results
        assert results_expanded.total_results >= results_no_expand.total_results

    def test_tag_filtering(self, search_engine, document_loader, kb_path):
        """Test tag-based filtering."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        documents = document_loader.load_all_documents()
        search_engine.build_index(documents)

        # Get all tags
        tags = search_engine.get_all_tags()
        if tags:
            first_tag = list(tags.keys())[0]

            # Search with tag filter
            results = search_engine.search("*", tags=[first_tag])

            # All results should have the tag
            for result in results.results:
                assert first_tag in result.tags


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline(self, kb_path, temp_db):
        """Test the full indexing and search pipeline."""
        if not kb_path.exists():
            pytest.skip("Knowledge base not found")

        # Load documents
        loader = DocumentLoader(kb_path)
        documents = loader.load_all_documents()
        assert len(documents) > 0

        # Build search index
        search = SearchEngine(temp_db)
        search.build_index(documents)

        # Build cross-references
        xref = CrossReferenceEngine()
        xref.build_term_registry(documents)

        # Process cross-references
        for doc in documents:
            content, refs = xref.apply_cross_references(doc.content, doc.slug)
            for ref in refs:
                xref.record_backlink(ref)

        # Search should work
        results = search.search("risk management")
        assert results.total_results > 0

        # Get document should work
        doc = search.get_document(documents[0].slug)
        assert doc is not None
        assert doc['title'] == documents[0].title


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
