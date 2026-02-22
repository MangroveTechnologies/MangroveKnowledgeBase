
"""
Initialize the Knowledge Base Database

This script loads all markdown documents from the knowledge-base directory,
builds the SQLite FTS5 search index, and processes cross-references.

Usage:
    python init_db.py [--force]

Options:
    --force     Rebuild the database even if it already exists
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports when running standalone
sys.path.insert(0, str(Path(__file__).parent))

from services.document_loader import DocumentLoader
from services.search_engine import SearchEngine
from services.cross_reference import CrossReferenceEngine
from config import settings


def init_database(force: bool = False) -> dict:
    """
    Initialize the knowledge base database.

    Args:
        force: If True, rebuild even if database exists

    Returns:
        Dictionary with initialization statistics
    """
    stats = {
        "documents": 0,
        "sections": 0,
        "tags": 0,
        "terms": 0,
        "cross_references": 0,
    }

    # Check if database already exists
    if settings.db_path.exists() and not force:
        print(f"Database already exists at: {settings.db_path}")
        print("Use --force to rebuild")
        return stats

    # Ensure data directory exists
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database if forcing rebuild
    if settings.db_path.exists() and force:
        settings.db_path.unlink()
        print(f"Removed existing database")

    print(f"Knowledge base path: {settings.kb_path}")
    print(f"Database path: {settings.db_path}")
    print()

    # Load documents
    print("Loading documents...")
    loader = DocumentLoader(settings.kb_path)
    documents = loader.load_all_documents()
    stats["documents"] = len(documents)
    print(f"  Loaded {len(documents)} documents")

    # Count sections
    for doc in documents:
        stats["sections"] += len(doc.sections)
    print(f"  Found {stats['sections']} sections")

    # Build search index
    print("\nBuilding search index...")
    search = SearchEngine(settings.db_path)
    search.build_index(documents)

    # Count tags
    all_tags = search.get_all_tags()
    stats["tags"] = len(all_tags)
    print(f"  Indexed {stats['tags']} unique tags")

    # Build cross-reference registry
    print("\nBuilding cross-references...")
    xref = CrossReferenceEngine()
    xref.build_term_registry(documents)
    stats["terms"] = len(xref.term_registry)
    print(f"  Registered {stats['terms']} terms for linking")

    # Process cross-references
    print("\nProcessing cross-references...")
    for doc in documents:
        _, refs = xref.apply_cross_references(doc.content, doc.slug)
        stats["cross_references"] += len(refs)
        for ref in refs:
            xref.record_backlink(ref)
            search.store_term_reference(
                ref.term,
                ref.source_document,
                ref.source_anchor,
                ref.target_document,
                ref.target_anchor
            )
    print(f"  Created {stats['cross_references']} cross-reference links")

    # Summary
    print("\n" + "=" * 50)
    print("INITIALIZATION COMPLETE")
    print("=" * 50)
    print(f"  Documents:        {stats['documents']}")
    print(f"  Sections:         {stats['sections']}")
    print(f"  Tags:             {stats['tags']}")
    print(f"  Terms:            {stats['terms']}")
    print(f"  Cross-references: {stats['cross_references']}")
    print(f"\n  Database: {settings.db_path}")
    print(f"  Size: {settings.db_path.stat().st_size / 1024:.1f} KB")
    print("=" * 50)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Initialize the Knowledge Base database"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Rebuild the database even if it already exists"
    )

    args = parser.parse_args()

    try:
        init_database(force=args.force)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"\nMake sure the knowledge-base directory exists at:")
        print(f"  {settings.kb_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
