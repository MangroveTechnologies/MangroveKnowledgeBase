"""
Knowledge Base Document Server - Main Application

FastAPI application that serves the trading knowledge base with:
- Full-text search using SQLite FTS5 with Porter stemming
- Automatic cross-referencing with code-block safety
- Synonym support and query expansion
- Navigable HTML UI with stable anchors
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import api_router, ui_router
from .services import DocumentLoader, SearchEngine, CrossReferenceEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global service instances
_search_engine: SearchEngine = None
_cross_ref_engine: CrossReferenceEngine = None
_document_loader: DocumentLoader = None


def initialize_services():
    """Initialize and index the knowledge base on startup."""
    global _search_engine, _cross_ref_engine, _document_loader

    logger.info(f"Initializing Knowledge Base from: {settings.kb_path}")

    # Create service instances
    _document_loader = DocumentLoader(settings.kb_path)
    _search_engine = SearchEngine(settings.db_path)
    _cross_ref_engine = CrossReferenceEngine()

    # Load and index documents
    documents = _document_loader.load_all_documents()
    logger.info(f"Loaded {len(documents)} documents")

    # Build search index
    _search_engine.build_index(documents)
    logger.info("Search index built")

    # Build cross-reference registry
    _cross_ref_engine.build_term_registry(documents)
    logger.info(f"Registered {len(_cross_ref_engine.term_registry)} terms for cross-referencing")

    # Process cross-references and store backlinks
    for doc in documents:
        _, references = _cross_ref_engine.apply_cross_references(
            doc.content,
            doc.slug
        )
        for ref in references:
            _cross_ref_engine.record_backlink(ref)
            _search_engine.store_term_reference(
                ref.term,
                ref.source_document,
                ref.source_anchor,
                ref.target_document,
                ref.target_anchor
            )

    logger.info("Cross-references processed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    initialize_services()
    logger.info(f"Knowledge Base Server ready at http://{settings.host}:{settings.port}")

    yield

    # Shutdown
    logger.info("Shutting down Knowledge Base Server")


# Create FastAPI application
app = FastAPI(
    title="Trading Knowledge Base",
    description="Comprehensive documentation for systematic trading strategies, market mechanics, and risk management.",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info(f"[KB] {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"[KB] {request.method} {request.url.path} -> {response.status_code}")
    return response

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(api_router)
app.include_router(ui_router)


def run_server():
    """Run the server using uvicorn."""
    import uvicorn

    uvicorn.run(
        "kb_server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )


if __name__ == "__main__":
    run_server()
