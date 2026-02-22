"""
Pydantic models for the Knowledge Base Document Server.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# Document Models
# =============================================================================

class Section(BaseModel):
    """Represents a section within a document."""

    id: Optional[int] = None
    anchor: str = Field(..., description="Stable anchor/slug for this section")
    title: str = Field(..., description="Section heading text")
    level: int = Field(..., description="Heading level (1=H1, 2=H2, etc.)")
    content: str = Field(default="", description="Raw markdown content of section")
    parent_anchor: Optional[str] = Field(None, description="Parent section anchor")
    children: List["Section"] = Field(default_factory=list, description="Child sections")

    class Config:
        from_attributes = True


class Tag(BaseModel):
    """Represents a document tag for categorization."""

    id: Optional[int] = None
    name: str = Field(..., description="Tag name/keyword")

    class Config:
        from_attributes = True


class Document(BaseModel):
    """Represents a knowledge base document."""

    id: Optional[int] = None
    slug: str = Field(..., description="URL-safe document identifier")
    title: str = Field(..., description="Document title from H1 heading")
    filename: str = Field(..., description="Source markdown filename")
    summary: Optional[str] = Field(None, description="Document summary")
    content: str = Field(default="", description="Full raw markdown content")
    sections: List[Section] = Field(default_factory=list, description="Document sections")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    importance: int = Field(default=0, description="Document importance ranking")

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    """Lightweight document representation for listings."""

    slug: str
    title: str
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    section_count: int = 0


# =============================================================================
# Search Models
# =============================================================================

class SearchMatch(BaseModel):
    """Represents a highlighted match within content."""

    text: str = Field(..., description="Text snippet with match")
    start: int = Field(..., description="Start position in original content")
    end: int = Field(..., description="End position in original content")


class SearchResult(BaseModel):
    """Represents a single search result."""

    document_slug: str = Field(..., description="Parent document slug")
    document_title: str = Field(..., description="Parent document title")
    section_anchor: Optional[str] = Field(None, description="Section anchor if section match")
    section_title: Optional[str] = Field(None, description="Section title if section match")
    snippet: str = Field(..., description="Content snippet with highlighted matches")
    relevance_score: float = Field(..., description="BM25 relevance score")
    match_type: str = Field(..., description="Type of match: document, section, tag")
    tags: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Response model for search queries."""

    query: str = Field(..., description="Original search query")
    expanded_query: Optional[str] = Field(None, description="Query after expansion")
    total_results: int = Field(..., description="Total number of matches")
    results: List[SearchResult] = Field(default_factory=list)
    tags_matched: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list, description="Related search terms")


# =============================================================================
# Cross-Reference Models
# =============================================================================

class TermReference(BaseModel):
    """Represents a cross-reference link between terms."""

    term: str = Field(..., description="The referenced term")
    source_anchor: str = Field(..., description="Where the reference appears")
    target_anchor: str = Field(..., description="Where the term is defined")
    source_document: str = Field(..., description="Source document slug")
    target_document: str = Field(..., description="Target document slug")


class GlossaryEntry(BaseModel):
    """Represents a glossary term with backlinks."""

    term: str = Field(..., description="Glossary term")
    abbreviation: Optional[str] = Field(None, description="Term abbreviation if any")
    definition: str = Field(..., description="Term definition")
    anchor: str = Field(..., description="Anchor to this term's definition")
    document_slug: str = Field(..., description="Document containing definition")
    backlinks: List[TermReference] = Field(
        default_factory=list,
        description="Documents/sections referencing this term"
    )
    related_terms: List[str] = Field(
        default_factory=list,
        description="Related glossary terms"
    )


class SeeAlso(BaseModel):
    """Represents a 'See Also' suggestion."""

    anchor: str
    title: str
    document_slug: str
    relevance: str = Field(..., description="Why this is related")


# =============================================================================
# API Response Models
# =============================================================================

class DocumentListResponse(BaseModel):
    """Response model for document listing."""

    total: int
    documents: List[DocumentSummary]


class TagListResponse(BaseModel):
    """Response model for tag listing."""

    total: int
    tags: List[Dict[str, Any]]  # tag name -> count


class GlossaryResponse(BaseModel):
    """Response model for glossary listing."""

    total: int
    entries: List[GlossaryEntry]


# =============================================================================
# Navigation Models
# =============================================================================

class NavItem(BaseModel):
    """Navigation menu item."""

    title: str
    slug: str
    anchor: Optional[str] = None
    children: List["NavItem"] = Field(default_factory=list)
    is_active: bool = False


class Breadcrumb(BaseModel):
    """Breadcrumb navigation item."""

    title: str
    url: str
    is_current: bool = False


# Enable forward references
Section.model_rebuild()
NavItem.model_rebuild()
