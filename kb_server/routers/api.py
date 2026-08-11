"""
REST API endpoints for the Knowledge Base Document Server.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends, Request

from ..models import (
    DocumentListResponse, DocumentSummary, Document, Section,
    SearchResponse, TagListResponse, GlossaryResponse, GlossaryEntry
)
from ..services import SearchEngine, CrossReferenceEngine, DocumentLoader
from ..services.signal_service import SignalService, SIGNAL_CATEGORIES
from ..services.indicator_service import IndicatorService
from ..config import settings

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api", tags=["api"])


# Dependency injection for services
_search_engine: Optional[SearchEngine] = None
_cross_ref_engine: Optional[CrossReferenceEngine] = None
_document_loader: Optional[DocumentLoader] = None
_signal_service: Optional[SignalService] = None
_indicator_service: Optional[IndicatorService] = None


def get_search_engine() -> SearchEngine:
    """Get the search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine


def get_cross_ref_engine() -> CrossReferenceEngine:
    """Get the cross-reference engine instance."""
    global _cross_ref_engine
    if _cross_ref_engine is None:
        _cross_ref_engine = CrossReferenceEngine()
    return _cross_ref_engine


def get_document_loader() -> DocumentLoader:
    """Get the document loader instance."""
    global _document_loader
    if _document_loader is None:
        _document_loader = DocumentLoader(settings.kb_path)
    return _document_loader


def get_signal_service() -> SignalService:
    """Get the signal service instance."""
    global _signal_service
    if _signal_service is None:
        _signal_service = SignalService()
    return _signal_service


def get_indicator_service() -> IndicatorService:
    """Get the indicator service instance."""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorService()
    return _indicator_service


# =============================================================================
# Document Endpoints
# =============================================================================

@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    List all documents in the knowledge base.

    Returns document summaries without full content.
    """
    docs = search_engine.get_all_documents()

    return DocumentListResponse(
        total=len(docs),
        documents=[
            DocumentSummary(
                slug=d['slug'],
                title=d['title'],
                summary=d['summary'],
                tags=d['tags'],
                section_count=d['section_count']
            )
            for d in docs
        ]
    )


@router.get("/documents/{slug}")
def get_document(
    slug: str,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Get a single document by slug.

    Returns full document content with sections.
    """
    doc = search_engine.get_document(slug)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{slug}' not found")

    return doc


@router.get("/documents/{slug}/sections")
def get_document_sections(
    slug: str,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Get the section tree for a document.

    Returns hierarchical section structure.
    """
    doc = search_engine.get_document(slug)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{slug}' not found")

    return {
        "document_slug": slug,
        "document_title": doc['title'],
        "sections": doc['sections']
    }


# =============================================================================
# Search Endpoints
# =============================================================================

@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    expand: bool = Query(True, description="Enable synonym/stem expansion"),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Search the knowledge base.

    Supports:
    - Full-text search with Porter stemming
    - Synonym expansion (e.g., "MA" matches "moving average")
    - Tag-based filtering
    - BM25 relevance ranking
    """
    tag_list = None
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(',') if t.strip()]

    logger.info(f"[SEARCH] query='{q}', tags={tag_list}, limit={limit}")

    return search_engine.search(
        query=q,
        tags=tag_list,
        limit=limit,
        expand=expand
    )


# =============================================================================
# Tag Endpoints
# =============================================================================

@router.get("/tags", response_model=TagListResponse)
def list_tags(
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    List all tags with document counts.
    """
    tags = search_engine.get_all_tags()

    return TagListResponse(
        total=len(tags),
        tags=[{"name": name, "count": count} for name, count in tags.items()]
    )


@router.get("/tags/{tag_name}")
def get_documents_by_tag(
    tag_name: str,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Get all documents with a specific tag.
    """
    # Use search with tag filter
    results = search_engine.search(
        query="*",  # Match all
        tags=[tag_name.lower()],
        limit=100,
        expand=False
    )

    # Deduplicate by document
    seen_docs = set()
    documents = []

    for result in results.results:
        if result.document_slug not in seen_docs:
            seen_docs.add(result.document_slug)
            documents.append({
                "slug": result.document_slug,
                "title": result.document_title,
                "tags": result.tags
            })

    return {
        "tag": tag_name,
        "total": len(documents),
        "documents": documents
    }


# =============================================================================
# Glossary Endpoints
# =============================================================================

@router.get("/glossary", response_model=GlossaryResponse)
def get_glossary(
    cross_ref: CrossReferenceEngine = Depends(get_cross_ref_engine),
    loader: DocumentLoader = Depends(get_document_loader)
):
    """
    Get the glossary with all terms and backlinks.
    """
    # Ensure term registry is built
    if not cross_ref.term_registry:
        documents = loader.load_all_documents()
        cross_ref.build_term_registry(documents)

    entries = cross_ref.get_glossary_entries()

    return GlossaryResponse(
        total=len(entries),
        entries=entries
    )


@router.get("/glossary/{term}")
def get_glossary_term(
    term: str,
    cross_ref: CrossReferenceEngine = Depends(get_cross_ref_engine),
    loader: DocumentLoader = Depends(get_document_loader),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Get a specific glossary term with backlinks.
    """
    # Ensure term registry is built
    if not cross_ref.term_registry:
        documents = loader.load_all_documents()
        cross_ref.build_term_registry(documents)

    # Find the term
    term_def = cross_ref.term_registry.get(term)
    if not term_def:
        # Try case-insensitive lookup
        term_lower = term.lower()
        for key in cross_ref.term_registry:
            if key.lower() == term_lower:
                term_def = cross_ref.term_registry[key]
                break

    if not term_def:
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found")

    # Get backlinks
    backlinks = search_engine.get_backlinks(term_def.anchor)

    return {
        "term": term_def.term,
        "abbreviation": term_def.abbreviation,
        "definition": term_def.definition,
        "anchor": term_def.anchor,
        "document_slug": term_def.document_slug,
        "backlinks": backlinks
    }


# =============================================================================
# Backlink Endpoints
# =============================================================================

@router.get("/backlinks/{anchor}")
def get_backlinks(
    anchor: str,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Get all documents/sections that reference a specific anchor.
    """
    backlinks = search_engine.get_backlinks(anchor)

    return {
        "target_anchor": anchor,
        "total": len(backlinks),
        "backlinks": backlinks
    }


# =============================================================================
# Signal Endpoints
# =============================================================================

@router.get("/signals")
def list_signals(
    category: Optional[str] = Query(
        None, description=f"Filter by category ({', '.join(SIGNAL_CATEGORIES)})"),
    signal_type: Optional[str] = Query(None, description="Filter by type (TRIGGER or FILTER)"),
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    List all signals with optional filtering by category and type.
    """
    signals = signal_service.list_signals(category=category, signal_type=signal_type)
    return {
        "total": len(signals),
        "signals": signals
    }


@router.get("/signals/{name}")
def get_signal(
    name: str,
    signal_service: SignalService = Depends(get_signal_service)
):
    """
    Get full metadata for a single signal by name.
    """
    signal = signal_service.get_signal(name)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Signal '{name}' not found")
    return signal


# =============================================================================
# Indicator Endpoints
# =============================================================================

@router.get("/indicators")
def list_indicators(
    category: Optional[str] = Query(None, description="Filter by category (Momentum, Trend, Volume, Volatility, Patterns, Returns)"),
    indicator_service: IndicatorService = Depends(get_indicator_service)
):
    """
    List all indicators with optional category filter.
    """
    indicators = indicator_service.list_indicators(category=category)
    return {
        "total": len(indicators),
        "indicators": indicators
    }


@router.get("/indicators/{name}")
def get_indicator(
    name: str,
    indicator_service: IndicatorService = Depends(get_indicator_service)
):
    """
    Get full spec for a single indicator by name.
    """
    indicator = indicator_service.get_indicator(name)
    if indicator is None:
        raise HTTPException(status_code=404, detail=f"Indicator '{name}' not found")
    return indicator


# =============================================================================
# x402-Gated Computation Endpoints
# =============================================================================

@router.post("/evaluate")
async def evaluate_signal_endpoint(request: Request, signal_svc=Depends(get_signal_service)):
    """Evaluate a signal against OHLCV data. x402 gated."""
    from kb_server.x402.middleware import validate_x402_payment
    import pandas as pd
    payment = validate_x402_payment(dict(request.headers), "evaluate_signal")
    if not payment["valid"]:
        raise HTTPException(status_code=402, detail=payment)
    body = await request.json()
    df = pd.DataFrame(body["ohlcv"])
    result = signal_svc.evaluate(body["name"], df, body.get("params", {}))
    return {"signal": body["name"], "result": result}

@router.post("/compute")
async def compute_indicator_endpoint(request: Request, indicator_svc=Depends(get_indicator_service)):
    """Compute an indicator. x402 gated."""
    from kb_server.x402.middleware import validate_x402_payment
    import pandas as pd
    payment = validate_x402_payment(dict(request.headers), "compute_indicator")
    if not payment["valid"]:
        raise HTTPException(status_code=402, detail=payment)
    body = await request.json()
    data = {k: pd.Series(v) for k, v in body["data"].items()}
    result = indicator_svc.compute(body["name"], data, body.get("params", {}))
    serialized = {}
    for k, v in result.items():
        if hasattr(v, "tolist"):
            # Replace NaN with None for JSON compatibility
            serialized[k] = [None if pd.isna(x) else x for x in v]
        else:
            serialized[k] = v
    return {"indicator": body["name"], "result": serialized}


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.post("/reindex")
def reindex_knowledge_base(
    search_engine: SearchEngine = Depends(get_search_engine),
    cross_ref: CrossReferenceEngine = Depends(get_cross_ref_engine),
    loader: DocumentLoader = Depends(get_document_loader)
):
    """
    Rebuild the search index and cross-references.

    Use this after updating knowledge base files.
    """
    # Load all documents
    documents = loader.load_all_documents()

    # Build search index
    search_engine.build_index(documents)

    # Build cross-reference registry
    cross_ref.build_term_registry(documents)

    # Apply cross-references and store backlinks
    for doc in documents:
        _, references = cross_ref.apply_cross_references(
            doc.content,
            doc.slug
        )
        for ref in references:
            cross_ref.record_backlink(ref)
            search_engine.store_term_reference(
                ref.term,
                ref.source_document,
                ref.source_anchor,
                ref.target_document,
                ref.target_anchor
            )

    return {
        "status": "success",
        "documents_indexed": len(documents),
        "terms_registered": len(cross_ref.term_registry)
    }


@router.get("/status")
def get_status(
    search_engine: SearchEngine = Depends(get_search_engine),
    cross_ref: CrossReferenceEngine = Depends(get_cross_ref_engine)
):
    """
    Get the current status of the knowledge base server.
    """
    docs = search_engine.get_all_documents()
    tags = search_engine.get_all_tags()

    return {
        "status": "healthy",
        "documents_count": len(docs),
        "tags_count": len(tags),
        "terms_registered": len(cross_ref.term_registry),
        "kb_path": str(settings.kb_path),
        "db_path": str(settings.db_path)
    }
