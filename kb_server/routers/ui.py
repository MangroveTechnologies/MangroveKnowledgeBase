"""
HTML UI routes for the Knowledge Base Document Server.
"""

import re
import markdown
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..services import SearchEngine, CrossReferenceEngine, DocumentLoader
from ..config import settings


router = APIRouter(tags=["ui"])

# Set up templates directory
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Dependency injection for services
_search_engine: Optional[SearchEngine] = None
_cross_ref_engine: Optional[CrossReferenceEngine] = None
_document_loader: Optional[DocumentLoader] = None
_initialized: bool = False


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


def ensure_initialized():
    """Ensure the knowledge base is indexed on first request."""
    global _initialized
    if not _initialized:
        loader = get_document_loader()
        search = get_search_engine()
        cross_ref = get_cross_ref_engine()

        documents = loader.load_all_documents()
        search.build_index(documents)
        cross_ref.build_term_registry(documents)

        _initialized = True


# Global state for anchor lookup during rendering
_current_anchor_queue = []

# Custom slugify function for markdown TOC that uses our pre-computed anchors
def custom_slugify(text, separator):
    """
    Custom slugify that uses our pre-computed anchor queue.
    This is called by the markdown TOC extension for each heading.
    """
    from collections import defaultdict

    # Check if we have pre-computed anchors queued
    for i, (title, anchor) in enumerate(_current_anchor_queue):
        if title == text:
            # Remove this entry and return the anchor
            _current_anchor_queue.pop(i)
            return anchor

    # Fallback to simple slugify
    from ..services.anchor_generator import AnchorGenerator
    return AnchorGenerator.slugify(text)

# Markdown renderer with extensions
md = markdown.Markdown(
    extensions=[
        'tables',
        'fenced_code',
        'codehilite',
        'toc',
        'md_in_html'
    ],
    extension_configs={
        'codehilite': {
            'css_class': 'highlight',
            'guess_lang': False
        },
        'toc': {
            'permalink': False,
            'slugify': custom_slugify  # Use our custom anchor generation
        }
    }
)


def inject_anchor_ids(html_content: str, sections: list) -> str:
    """
    Post-process HTML to add proper id attributes to headings.
    This replaces or adds id attributes to match our section anchors.
    """
    if not sections:
        return html_content

    result = html_content

    for section in sections:
        title = section['title'] if isinstance(section, dict) else section.title
        anchor = section['anchor'] if isinstance(section, dict) else section.anchor
        level = section.get('level', 2) if isinstance(section, dict) else getattr(section, 'level', 2)

        # Escape special regex characters in title
        title_pattern = re.escape(title)

        # Match <h2> or <h3> tags containing this exact title
        # The title now includes numbers (e.g., "1.1 Market Microstructure" or just "Definition")
        # Pattern: <h2 ...>(exact title)</h2>
        pattern = rf'(<h{level}[^>]*>)({title_pattern})(</h{level}>)'

        def make_replacer(anchor_val, level_val):
            def replacer(match):
                opening = match.group(1)
                title_text = match.group(2)
                closing = match.group(3)

                # Remove any existing id attribute and add our anchor
                opening_clean = re.sub(r'\s+id="[^"]*"', '', opening)
                opening_with_id = opening_clean.replace(f'<h{level_val}', f'<h{level_val} id="{anchor_val}"', 1)

                return f'{opening_with_id}{title_text}{closing}'
            return replacer

        result = re.sub(pattern, make_replacer(anchor, level), result, count=1, flags=re.IGNORECASE)

    return result


def render_markdown(content: str, sections: list = None) -> str:
    """Render markdown to HTML with our custom anchors."""
    global _current_anchor_queue

    # Build anchor queue from sections before rendering (in order)
    if sections:
        _current_anchor_queue = []
        for section in sections:
            title = section['title'] if isinstance(section, dict) else section.title
            anchor = section['anchor'] if isinstance(section, dict) else section.anchor
            # Append tuples of (title, anchor) in order
            _current_anchor_queue.append((title, anchor))

    md.reset()
    html = md.convert(content)

    # Clear the queue after rendering
    _current_anchor_queue = []

    return html


def inject_glossary_anchors(html_content: str) -> str:
    """
    Inject anchor IDs into glossary table rows.
    Each term row gets an id attribute based on the term name.

    Transforms:
        <tr><td>VWAP</td><td>Definition...</td>...
    To:
        <tr id="vwap"><td>VWAP</td><td>Definition...</td>...
    """
    # Pattern to match table rows with term in first column
    # Skip header row (contains "Term" or starts with "---")
    def process_row(match):
        row_content = match.group(1)

        # Extract first <td> content (the term name)
        td_match = re.search(r'<td>([^<]+)</td>', row_content)
        if not td_match:
            return match.group(0)

        term = td_match.group(1).strip()

        # Skip header rows
        if term.lower() in ('term', '---', '----'):
            return match.group(0)

        # Generate anchor from term
        anchor = re.sub(r'[^\w\s-]', '', term.lower())
        anchor = re.sub(r'\s+', '-', anchor)
        anchor = re.sub(r'[-]+', '-', anchor)
        anchor = anchor.strip('-')

        # Add id attribute to the <tr> tag
        return f'<tr id="{anchor}">{row_content}'

    # Match <tr>...</tr> rows
    result = re.sub(r'<tr>([^<]*(?:<(?!/?tr>)[^<]*)*)</tr>',
                    lambda m: f'<tr id="{generate_term_anchor(m)}">{m.group(1)}</tr>' if generate_term_anchor(m) else m.group(0),
                    html_content)

    return result


def generate_term_anchor(match) -> str:
    """Generate anchor ID from a table row match."""
    row_content = match.group(1)

    # Extract first <td> content (the term name)
    # Handle both plain text and text wrapped in <a> tags
    # Pattern 1: <td>Plain Text</td>
    # Pattern 2: <td><a href="...">Link Text</a></td>
    td_match = re.search(r'<td>(?:<a[^>]*>)?([^<]+)(?:</a>)?</td>', row_content)
    if not td_match:
        return ""

    term = td_match.group(1).strip()

    # Skip header rows
    if term.lower() in ('term', '---', '----', 'definition', 'abbreviation', 'category'):
        return ""

    # Generate anchor from term
    anchor = re.sub(r'[^\w\s-]', '', term.lower())
    anchor = re.sub(r'\s+', '-', anchor)
    anchor = re.sub(r'[-]+', '-', anchor)
    anchor = anchor.strip('-')

    return anchor


def get_all_docs_for_nav(search_engine: SearchEngine) -> list:
    """Get all documents for sidebar navigation."""
    return search_engine.get_all_documents()


# =============================================================================
# Home / TOC
# =============================================================================

@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    search_engine: SearchEngine = Depends(get_search_engine),
    loader: DocumentLoader = Depends(get_document_loader)
):
    """
    Home page showing the actual Table of Contents file.
    """
    ensure_initialized()

    # Read and render the actual TOC markdown file
    toc_path = settings.kb_path / "00-table-of-contents.md"
    toc_content = ""
    if toc_path.exists():
        toc_content = toc_path.read_text(encoding='utf-8')

    toc_html = render_markdown(toc_content)

    docs = search_engine.get_all_documents()

    all_tags = search_engine.get_all_tags()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Table of Contents",
            "toc_html": toc_html,
            "all_docs": docs,
            "all_tags": all_tags,
            "selected_tags": [],
            "query": "",
            "sections": [],
            "current_page": "home",
            "current_doc": None
        }
    )


# =============================================================================
# Document View
# =============================================================================

@router.get("/doc/{slug}", response_class=HTMLResponse)
async def view_document(
    request: Request,
    slug: str,
    search_engine: SearchEngine = Depends(get_search_engine),
    cross_ref: CrossReferenceEngine = Depends(get_cross_ref_engine)
):
    """
    View a single document with rendered content.
    """
    ensure_initialized()

    doc = search_engine.get_document(slug)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{slug}' not found")

    # Apply cross-references
    content_with_refs, _ = cross_ref.apply_cross_references(
        doc['content'],
        slug
    )

    # Render markdown to HTML with section anchors
    html_content = render_markdown(content_with_refs, doc['sections'])

    # For glossary document, inject term-specific anchor IDs into table rows
    if 'glossary' in slug.lower():
        html_content = inject_glossary_anchors(html_content)

    # Get all documents for navigation
    all_docs = search_engine.get_all_documents()

    # Find previous and next documents
    doc_index = next((i for i, d in enumerate(all_docs) if d['slug'] == slug), -1)
    prev_doc = all_docs[doc_index - 1] if doc_index > 0 else None
    next_doc = all_docs[doc_index + 1] if doc_index < len(all_docs) - 1 else None

    all_tags = search_engine.get_all_tags()

    return templates.TemplateResponse(
        "document.html",
        {
            "request": request,
            "title": doc['title'],
            "document": doc,
            "html_content": html_content,
            "sections": doc['sections'],  # For inline sections in sidebar
            "all_docs": all_docs,
            "all_tags": all_tags,
            "selected_tags": [],
            "query": "",
            "prev_doc": prev_doc,
            "next_doc": next_doc,
            "current_page": "document",
            "current_doc": slug
        }
    )


# =============================================================================
# Search
# =============================================================================

@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: Optional[str] = None,
    tags: Optional[str] = None,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Search page with results.
    """
    ensure_initialized()

    # Parse tags from comma-separated string
    selected_tags = []
    if tags:
        selected_tags = [t.strip().lower() for t in tags.split(',') if t.strip()]

    results = None
    # Search if we have a query OR selected tags
    if q or selected_tags:
        results = search_engine.search(
            query=q or "*",  # Use wildcard if only filtering by tags
            tags=selected_tags if selected_tags else None,
            limit=50,
            expand=True
        )

    all_tags = search_engine.get_all_tags()
    all_docs = search_engine.get_all_documents()

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "title": "Search" + (f" - {q}" if q else ""),
            "query": q or "",
            "selected_tags": selected_tags,
            "results": results,
            "all_tags": all_tags,
            "all_docs": all_docs,
            "sections": [],
            "current_page": "search",
            "current_doc": None
        }
    )


# =============================================================================
# Glossary
# =============================================================================

@router.get("/glossary", response_class=HTMLResponse)
async def glossary_page(
    request: Request,
    search_engine: SearchEngine = Depends(get_search_engine),
    cross_ref: CrossReferenceEngine = Depends(get_cross_ref_engine),
    loader: DocumentLoader = Depends(get_document_loader)
):
    """
    Glossary page with all terms.
    """
    ensure_initialized()

    entries = cross_ref.get_glossary_entries()
    all_docs = search_engine.get_all_documents()

    # Group by first letter
    grouped = {}
    for entry in entries:
        letter = entry.term[0].upper()
        if letter not in grouped:
            grouped[letter] = []
        grouped[letter].append(entry)

    all_tags = search_engine.get_all_tags()

    return templates.TemplateResponse(
        "glossary.html",
        {
            "request": request,
            "title": "Glossary",
            "entries": entries,
            "grouped_entries": grouped,
            "all_docs": all_docs,
            "all_tags": all_tags,
            "selected_tags": [],
            "query": "",
            "sections": [],
            "current_page": "glossary",
            "current_doc": None
        }
    )


# =============================================================================
# Tags
# =============================================================================

@router.get("/tags/{tag_name}", response_class=HTMLResponse)
async def tag_page(
    request: Request,
    tag_name: str,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Page showing all documents with a specific tag.
    """
    ensure_initialized()

    # Get documents with this tag
    results = search_engine.search(
        query="*",
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
            doc = search_engine.get_document(result.document_slug)
            if doc:
                documents.append(doc)

    all_tags = search_engine.get_all_tags()
    all_docs = search_engine.get_all_documents()

    return templates.TemplateResponse(
        "tag.html",
        {
            "request": request,
            "title": f"Tag: {tag_name}",
            "tag_name": tag_name,
            "documents": documents,
            "all_tags": all_tags,
            "selected_tags": [],
            "query": "",
            "all_docs": all_docs,
            "sections": [],
            "current_page": "tags",
            "current_doc": None
        }
    )
