# MCP Server Plan for MangroveKnowledgeBase

**Date:** 2026-02-22
**Status:** Planning -- no implementation yet
**Author:** Mangrove Technologies

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [Specification](#2-specification)
3. [Architecture](#3-architecture)
4. [Security and Authentication](#4-security-and-authentication)
5. [Implementation Plan](#5-implementation-plan)

---

## 1. Requirements

### 1.1 Purpose

Expose the MangroveKnowledgeBase's capabilities to external AI agents via the Model Context Protocol (MCP). The server makes trading knowledge, signal metadata, indicator specifications, glossary terms, and full-text search available to any MCP-compatible client -- not just MangroveAI's AI Copilot.

Today, MangroveAI consumes the KB via direct HTTP calls to the FastAPI kb_server. This MCP server provides a standardized, agent-ergonomic interface that decouples consumers from the HTTP API and adds structured tool semantics that MCP clients can discover and invoke programmatically.

### 1.2 Consumers

| Consumer | Use Case |
|----------|----------|
| **AI Copilots** (MangroveAI, third-party) | RAG retrieval: search KB for context to augment LLM prompts about trading strategies, indicators, risk management |
| **Trading bots / strategy engines** | Look up signal metadata (parameters, types, required data columns) before configuring signal evaluation pipelines |
| **Agent orchestrators** (OpenClaw, LangChain, CrewAI) | Discover available signals and indicators, retrieve glossary definitions, navigate the knowledge graph via backlinks |
| **Research notebooks** | Query indicator specifications and parameter ranges during backtesting configuration |
| **MangroveMarkets MCP clients** | Cross-reference knowledge base content when evaluating marketplace listings related to trading signals |

### 1.3 Capabilities to Expose

#### Knowledge Base Search and Retrieval (wraps kb_server API)

- Full-text search with synonym expansion and tag filtering
- Document listing and retrieval (summaries and full content)
- Section-level document navigation
- Glossary term lookup (single term and full glossary)
- Tag browsing and tag-based document filtering
- Backlink traversal (which documents reference a given anchor)
- KB status/health check

#### Signal Metadata (wraps docstring_parser + RuleRegistry)

- List all registered signals with metadata
- Get single signal metadata (type, requires, params, description)
- Filter signals by category (momentum, trend, volume, volatility)
- Filter signals by type (TRIGGER vs FILTER)
- Filter signals by required data columns

#### Indicator Specifications (wraps indicator classes)

- List all available indicators
- Get single indicator specification (inputs, params, outputs)
- Filter indicators by category

### 1.4 What Should NOT Be Exposed

| Excluded | Reason |
|----------|--------|
| Signal evaluation / computation | Signals require a DataFrame of live market data. The KB is a metadata and documentation server, not a compute engine. Signal execution stays in MangroveAI. |
| Indicator computation | Same reason. `compute()` needs time-series data. The MCP server exposes specs, not compute. |
| KB reindex endpoint | Administrative mutation. Should not be triggerable by external agents. |
| KB UI endpoints (HTML rendering) | MCP tools return structured data, not HTML pages. |
| Raw SQLite database access | Internal implementation detail. |
| Social/X signals | Private to MangroveAI, not part of the public KB package. |
| MangroveAI authentication/tenant data | Out of scope. This server is about the KB content, not MangroveAI platform concerns. |

### 1.5 Performance Requirements

| Metric | Target | Rationale |
|--------|--------|-----------|
| Tool response latency (p95) | < 200ms | Agent workflows are latency-sensitive; LLM tool calls add to total response time |
| Search latency (p95) | < 300ms | FTS5 queries with synonym expansion are slightly heavier |
| Concurrent MCP sessions | >= 20 | Multiple agents and copilots may connect simultaneously |
| Cold start time | < 5s | KB indexing happens at startup; the FTS5 index over 11 documents is fast |
| Memory footprint | < 256MB | The KB is ~360KB of markdown plus a small SQLite database |
| Availability | 99.5% | Non-critical path (agents can fall back to cached data), but should be reliable |

### 1.6 Data Characteristics

- 11 knowledge base documents (~360KB total markdown)
- 85 glossary terms with cross-reference backlinks
- 42 tags across all documents
- 96 signal functions with structured docstring metadata
- 40+ indicator classes with defined inputs/params/outputs
- Data is read-only at runtime (changes only via reindex after editing markdown files)
- All content is public (MIT-licensed repository)

---

## 2. Specification

### 2.1 Tool Naming Convention

All tools use the prefix `kb_` to identify the knowledge base domain, following the pattern established by MangroveMarkets-MCP-Server (`marketplace_*`, `dex_*`, `wallet_*`).

### 2.2 Tool Definitions

#### Domain: Knowledge Base Search

##### `kb_search`

Search the knowledge base with full-text search, synonym expansion, and optional tag filtering.

**Input Schema:**
```json
{
  "query": {
    "type": "string",
    "description": "Search query (min 1 character). Supports natural language queries. Porter stemming and synonym expansion are applied automatically.",
    "required": true
  },
  "tags": {
    "type": "string",
    "description": "Comma-separated tag names to filter results (e.g., 'risk-management,position-sizing'). Only results tagged with ALL specified tags are returned.",
    "required": false,
    "default": null
  },
  "limit": {
    "type": "integer",
    "description": "Maximum number of results to return.",
    "required": false,
    "default": 20,
    "min": 1,
    "max": 100
  },
  "expand": {
    "type": "boolean",
    "description": "Enable synonym and stem expansion. When true, 'MA' also matches 'moving average', 'RSI' matches 'relative strength index', etc.",
    "required": false,
    "default": true
  }
}
```

**Output Schema:**
```json
{
  "query": "string",
  "expanded_query": "string | null",
  "total_results": "integer",
  "results": [
    {
      "document_slug": "string",
      "document_title": "string",
      "section_anchor": "string | null",
      "section_title": "string | null",
      "snippet": "string",
      "relevance_score": "float",
      "match_type": "string (document | section | tag)",
      "tags": ["string"]
    }
  ],
  "tags_matched": ["string"],
  "suggestions": ["string"]
}
```

**Error Codes:**
- `INVALID_QUERY` -- query string is empty or whitespace-only
- `SEARCH_FAILED` -- internal search engine error

---

#### Domain: Knowledge Base Documents

##### `kb_list_documents`

List all documents in the knowledge base with summaries (no full content).

**Input Schema:**
```json
{}
```
No parameters. Returns all documents.

**Output Schema:**
```json
{
  "total": "integer",
  "documents": [
    {
      "slug": "string",
      "title": "string",
      "summary": "string | null",
      "tags": ["string"],
      "section_count": "integer"
    }
  ]
}
```

---

##### `kb_get_document`

Get a single document by slug, including full content and section tree.

**Input Schema:**
```json
{
  "slug": {
    "type": "string",
    "description": "Document slug (e.g., '6-indicators', '5-risk-management'). Use kb_list_documents to discover available slugs.",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "slug": "string",
  "title": "string",
  "filename": "string",
  "summary": "string | null",
  "content": "string",
  "importance": "integer",
  "sections": [
    {
      "anchor": "string",
      "title": "string",
      "level": "integer",
      "content": "string",
      "parent_anchor": "string | null"
    }
  ],
  "tags": ["string"]
}
```

**Error Codes:**
- `DOCUMENT_NOT_FOUND` -- no document with the given slug exists

**Note on large responses:** Some documents (e.g., `6-indicators` at 96KB) are large. The tool returns the full document. If the caller only needs the section structure, use `kb_get_document_sections` instead.

---

##### `kb_get_document_sections`

Get the section tree for a document without full content. Useful for navigating document structure before retrieving specific sections.

**Input Schema:**
```json
{
  "slug": {
    "type": "string",
    "description": "Document slug.",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "document_slug": "string",
  "document_title": "string",
  "sections": [
    {
      "anchor": "string",
      "title": "string",
      "level": "integer",
      "content": "string",
      "parent_anchor": "string | null"
    }
  ]
}
```

**Error Codes:**
- `DOCUMENT_NOT_FOUND`

---

#### Domain: Knowledge Base Glossary

##### `kb_glossary_lookup`

Look up a specific glossary term with its definition and backlinks showing where the term is referenced across the knowledge base.

**Input Schema:**
```json
{
  "term": {
    "type": "string",
    "description": "Glossary term to look up (case-insensitive). Examples: 'VWAP', 'drawdown', 'Sharpe Ratio'.",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "term": "string",
  "abbreviation": "string | null",
  "definition": "string",
  "anchor": "string",
  "document_slug": "string",
  "backlinks": [
    {
      "term": "string",
      "source_document_slug": "string",
      "source_anchor": "string",
      "source_title": "string"
    }
  ]
}
```

**Error Codes:**
- `TERM_NOT_FOUND` -- no glossary entry for the given term

---

##### `kb_list_glossary`

Get the full glossary with all terms, definitions, and backlinks.

**Input Schema:**
```json
{
  "limit": {
    "type": "integer",
    "description": "Maximum number of glossary entries to return. Use for pagination.",
    "required": false,
    "default": 100,
    "min": 1,
    "max": 500
  },
  "offset": {
    "type": "integer",
    "description": "Number of entries to skip. Use with limit for pagination.",
    "required": false,
    "default": 0,
    "min": 0
  }
}
```

**Output Schema:**
```json
{
  "total": "integer",
  "offset": "integer",
  "limit": "integer",
  "entries": [
    {
      "term": "string",
      "abbreviation": "string | null",
      "definition": "string",
      "anchor": "string",
      "document_slug": "string",
      "backlinks": [],
      "related_terms": ["string"]
    }
  ]
}
```

**Note:** The current glossary has 85 entries. Pagination is included for forward compatibility as the glossary grows.

---

#### Domain: Knowledge Base Tags

##### `kb_list_tags`

List all tags in the knowledge base with their document counts.

**Input Schema:**
```json
{}
```

**Output Schema:**
```json
{
  "total": "integer",
  "tags": [
    {
      "name": "string",
      "count": "integer"
    }
  ]
}
```

---

##### `kb_get_documents_by_tag`

Get all documents that have a specific tag.

**Input Schema:**
```json
{
  "tag": {
    "type": "string",
    "description": "Tag name (e.g., 'risk-management', 'indicators', 'momentum').",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "tag": "string",
  "total": "integer",
  "documents": [
    {
      "slug": "string",
      "title": "string",
      "tags": ["string"]
    }
  ]
}
```

**Error Codes:**
- `TAG_NOT_FOUND` -- no documents have the given tag (returns empty list, not an error -- but the tool notes it in the response)

---

#### Domain: Knowledge Base Backlinks

##### `kb_get_backlinks`

Get all documents and sections that reference a specific anchor. Useful for navigating the knowledge graph.

**Input Schema:**
```json
{
  "anchor": {
    "type": "string",
    "description": "Target anchor ID (e.g., 'vwap', '8-1-position-sizing'). Anchors are stable identifiers for sections and glossary terms.",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "target_anchor": "string",
  "total": "integer",
  "backlinks": [
    {
      "term": "string",
      "source_document_slug": "string",
      "source_anchor": "string",
      "source_title": "string"
    }
  ]
}
```

---

#### Domain: Signal Metadata

##### `kb_list_signals`

List all registered trading signals with their metadata. Supports filtering by category, type, and required data columns.

**Input Schema:**
```json
{
  "category": {
    "type": "string",
    "description": "Filter by signal category.",
    "required": false,
    "enum": ["momentum", "trend", "volume", "volatility"],
    "default": null
  },
  "signal_type": {
    "type": "string",
    "description": "Filter by signal type.",
    "required": false,
    "enum": ["TRIGGER", "FILTER"],
    "default": null
  },
  "requires": {
    "type": "string",
    "description": "Filter to signals that require a specific data column (e.g., 'Volume', 'High', 'Close').",
    "required": false,
    "default": null
  },
  "limit": {
    "type": "integer",
    "description": "Maximum number of signals to return.",
    "required": false,
    "default": 100,
    "min": 1,
    "max": 200
  },
  "offset": {
    "type": "integer",
    "description": "Number of signals to skip for pagination.",
    "required": false,
    "default": 0,
    "min": 0
  }
}
```

**Output Schema:**
```json
{
  "total": "integer",
  "offset": "integer",
  "limit": "integer",
  "signals": [
    {
      "rule_name": "string",
      "description": "string",
      "type": "TRIGGER | FILTER",
      "category": "momentum | trend | volume | volatility",
      "requires": ["string"],
      "param_count": "integer"
    }
  ]
}
```

**Note:** This tool returns signal summaries. Use `kb_get_signal` for full metadata including parameter details.

---

##### `kb_get_signal`

Get full metadata for a specific trading signal, including all parameters with types, ranges, and defaults.

**Input Schema:**
```json
{
  "name": {
    "type": "string",
    "description": "Signal rule name (e.g., 'rsi_overbought', 'macd_crossover_bullish', 'obv_trending_up'). Use kb_list_signals to discover available signal names.",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "rule_name": "string",
  "description": "string",
  "type": "TRIGGER | FILTER",
  "category": "momentum | trend | volume | volatility",
  "requires": ["string"],
  "params": {
    "<param_name>": {
      "type": "string",
      "description": "string",
      "min": "number | null",
      "max": "number | null",
      "optional": "boolean",
      "default": "any | null"
    }
  }
}
```

**Error Codes:**
- `SIGNAL_NOT_FOUND` -- no signal registered with the given name

---

#### Domain: Indicator Specifications

##### `kb_list_indicators`

List all available technical indicators with their input/output specifications.

**Input Schema:**
```json
{
  "category": {
    "type": "string",
    "description": "Filter by indicator category.",
    "required": false,
    "enum": ["momentum", "trend", "volume", "volatility", "returns"],
    "default": null
  }
}
```

**Output Schema:**
```json
{
  "total": "integer",
  "indicators": [
    {
      "name": "string",
      "category": "string",
      "required_data": ["string"],
      "required_params": ["string"],
      "outputs": ["string"]
    }
  ]
}
```

---

##### `kb_get_indicator`

Get full specification for a specific technical indicator.

**Input Schema:**
```json
{
  "name": {
    "type": "string",
    "description": "Indicator class name (e.g., 'RSI', 'MACD', 'BollingerBands', 'ATR'). Use kb_list_indicators to discover available indicator names.",
    "required": true
  }
}
```

**Output Schema:**
```json
{
  "name": "string",
  "category": "string",
  "required_data": ["string"],
  "required_params": ["string"],
  "outputs": {
    "names": ["string"],
    "count": "integer"
  },
  "description": "string"
}
```

**Error Codes:**
- `INDICATOR_NOT_FOUND` -- no indicator with the given name

---

#### Domain: Server Metadata

##### `kb_status`

Get the current health and status of the knowledge base MCP server.

**Input Schema:**
```json
{}
```

**Output Schema:**
```json
{
  "status": "healthy | degraded | unhealthy",
  "documents_count": "integer",
  "tags_count": "integer",
  "terms_registered": "integer",
  "signals_count": "integer",
  "indicators_count": "integer",
  "version": "string",
  "uptime_seconds": "float"
}
```

---

### 2.3 Tool Summary

| # | Tool Name | Domain | Wraps |
|---|-----------|--------|-------|
| 1 | `kb_search` | Search | `GET /api/search` |
| 2 | `kb_list_documents` | Documents | `GET /api/documents` |
| 3 | `kb_get_document` | Documents | `GET /api/documents/{slug}` |
| 4 | `kb_get_document_sections` | Documents | `GET /api/documents/{slug}/sections` |
| 5 | `kb_glossary_lookup` | Glossary | `GET /api/glossary/{term}` |
| 6 | `kb_list_glossary` | Glossary | `GET /api/glossary` |
| 7 | `kb_list_tags` | Tags | `GET /api/tags` |
| 8 | `kb_get_documents_by_tag` | Tags | `GET /api/tags/{tag_name}` |
| 9 | `kb_get_backlinks` | Backlinks | `GET /api/backlinks/{anchor}` |
| 10 | `kb_list_signals` | Signals | RuleRegistry + docstring_parser |
| 11 | `kb_get_signal` | Signals | RuleRegistry + docstring_parser |
| 12 | `kb_list_indicators` | Indicators | IndicatorInterface subclasses |
| 13 | `kb_get_indicator` | Indicators | IndicatorInterface subclasses |
| 14 | `kb_status` | Metadata | `GET /api/status` + local state |

**Total: 14 MCP tools**

### 2.4 Error Handling Pattern

Every tool error follows the same structure used by MangroveMarkets-MCP-Server:

```json
{
  "error": true,
  "code": "MACHINE_READABLE_CODE",
  "message": "Human/agent-readable description of what went wrong.",
  "suggestion": "What the agent could do to fix or work around the error."
}
```

Standard error codes across all tools:

| Code | Meaning |
|------|---------|
| `INVALID_QUERY` | A required parameter was missing, empty, or malformed |
| `DOCUMENT_NOT_FOUND` | No document exists with the given slug |
| `TERM_NOT_FOUND` | No glossary term matches the given name |
| `SIGNAL_NOT_FOUND` | No signal registered with the given rule name |
| `INDICATOR_NOT_FOUND` | No indicator class with the given name |
| `TAG_NOT_FOUND` | No documents tagged with the given tag name |
| `SEARCH_FAILED` | Internal error during search execution |
| `SERVER_UNAVAILABLE` | KB server is not initialized or in a degraded state |
| `INTERNAL_ERROR` | Unexpected error; includes details in message |

### 2.5 Pagination Convention

Tools that return potentially large lists (`kb_list_glossary`, `kb_list_signals`) support pagination via `limit` and `offset` parameters. The response always includes the actual `total`, `offset`, and `limit` used so the caller can compute whether more pages exist.

Tools that return small, bounded lists (`kb_list_documents` with 11 entries, `kb_list_tags` with 42 entries, `kb_list_indicators` with ~40 entries) do not paginate. If the knowledge base grows significantly in the future, pagination can be added without breaking existing callers by making `limit` and `offset` optional with defaults that return all results.

---

## 3. Architecture

### 3.1 Repository Location

The MCP server lives as a new top-level directory within the MangroveKnowledgeBase repository:

```
MangroveKnowledgeBase/
    |
    +-- mangrove_knowledge_base/    # Python package (signals, indicators, registry)
    |
    +-- kb_server/                  # Existing FastAPI KB server
    |
    +-- mcp_server/                 # NEW: MCP server
    |       +-- __init__.py
    |       +-- server.py           # FastMCP server instance + tool registration
    |       +-- tools/
    |       |       +-- __init__.py
    |       |       +-- search.py       # kb_search
    |       |       +-- documents.py    # kb_list_documents, kb_get_document, kb_get_document_sections
    |       |       +-- glossary.py     # kb_glossary_lookup, kb_list_glossary
    |       |       +-- tags.py         # kb_list_tags, kb_get_documents_by_tag
    |       |       +-- backlinks.py    # kb_get_backlinks
    |       |       +-- signals.py      # kb_list_signals, kb_get_signal
    |       |       +-- indicators.py   # kb_list_indicators, kb_get_indicator
    |       |       +-- metadata.py     # kb_status
    |       +-- errors.py           # tool_error / tool_success utilities
    |       +-- config.py           # MCP server configuration
    |       +-- Dockerfile          # Container build for MCP server
    |
    +-- knowledge-base/             # Markdown content files
    +-- tests/
    +-- findings/
    +-- docker-compose.yml          # Updated to include MCP server service
```

**Rationale for a separate directory (not extending kb_server):**

- The kb_server is a FastAPI application serving both HTML UI and JSON API. The MCP server has a fundamentally different transport (Streamable HTTP via FastMCP) and a different purpose (agent-facing tools, not REST endpoints).
- Separation keeps each server independently deployable and testable.
- The MCP server can import and call kb_server services directly (same Python process or via HTTP) without entangling their lifecycles.

### 3.2 Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| MCP framework | **FastMCP** (`mcp[cli]>=1.2.0`) | Same library used by MangroveMarkets-MCP-Server. Handles MCP protocol, Streamable HTTP transport, tool registration, and schema generation. |
| Transport | **Streamable HTTP** | Standard MCP transport. Supports both streaming and request/response patterns. |
| Python version | **3.10+** | Matches MangroveKnowledgeBase's existing requirement. |
| Dependencies | `mcp[cli]>=1.2.0`, `pydantic>=2.0.0`, `httpx>=0.27.0` | Minimal additions. Pydantic is already used by kb_server. httpx for calling the KB API if running out-of-process. |

### 3.3 Relationship to the Existing KB FastAPI Server

**Recommended approach: In-process import with optional HTTP fallback.**

The MCP server imports and uses kb_server's service classes directly:

```
MCP Server (mcp_server/server.py)
    |
    +-- imports --> kb_server.services.SearchEngine
    +-- imports --> kb_server.services.CrossReferenceEngine
    +-- imports --> kb_server.services.DocumentLoader
    +-- imports --> mangrove_knowledge_base.registry.RuleRegistry
    +-- imports --> mangrove_knowledge_base.docstring_parser
    +-- imports --> mangrove_knowledge_base.indicators.*
```

**Why in-process, not HTTP proxy:**

1. The KB server services are stateless Python classes. Importing them avoids network overhead, serialization/deserialization, and the need to run two separate processes during development.
2. The SearchEngine, CrossReferenceEngine, and DocumentLoader can be instantiated directly by the MCP server's startup lifecycle, just as the kb_server's `main.py` does.
3. The signal and indicator metadata is entirely in-memory (parsed from docstrings and class attributes) -- no server needed.

**Optional HTTP fallback for deployment flexibility:**

If the MCP server and KB server are deployed as separate containers, the MCP tool implementations can be configured to call the KB server's REST API via httpx instead of importing services directly. This is a deployment-time configuration choice, not a code architecture change -- the tool layer abstracts the data source.

```python
# config.py
class MCPConfig:
    # If set, tools call KB server via HTTP instead of direct import
    kb_server_url: str | None = None  # e.g., "http://kb-server:8080"
```

### 3.4 Server Entry Point Pattern

Following MangroveMarkets-MCP-Server's pattern:

```python
# mcp_server/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MangroveKnowledgeBase")

def create_mcp_server() -> FastMCP:
    from mcp_server.tools.search import register as register_search
    from mcp_server.tools.documents import register as register_documents
    from mcp_server.tools.glossary import register as register_glossary
    from mcp_server.tools.tags import register as register_tags
    from mcp_server.tools.backlinks import register as register_backlinks
    from mcp_server.tools.signals import register as register_signals
    from mcp_server.tools.indicators import register as register_indicators
    from mcp_server.tools.metadata import register as register_metadata

    register_search(mcp)
    register_documents(mcp)
    register_glossary(mcp)
    register_tags(mcp)
    register_backlinks(mcp)
    register_signals(mcp)
    register_indicators(mcp)
    register_metadata(mcp)

    return mcp
```

Each tools module exports a `register(server: FastMCP)` function that registers its tools on the server instance using the `@server.tool(name="kb_*")` decorator pattern.

### 3.5 Deployment Model

#### Option A: Standalone container (recommended for production)

```yaml
# docker-compose.yml addition
  mcp-server:
    build:
      context: .
      dockerfile: mcp_server/Dockerfile
    container_name: mkb-mcp-server
    ports:
      - "${MCP_PORT:-8090}:8090"
    volumes:
      - ./knowledge-base:/kb:ro
      - kb-data:/app/kb_server/data
    environment:
      - MCP_SERVER_PORT=8090
      - KB_SERVER_KB_PATH=/kb
      - KB_SERVER_DB_PATH=/app/kb_server/data/knowledge.db
    restart: unless-stopped
    networks:
      - mangrove-network
```

The MCP server runs its own process, initializes its own SearchEngine/DocumentLoader instances (pointing at the same knowledge-base files and SQLite database), and serves MCP tools on port 8090. The KB FastAPI server continues to run on port 8080 for its existing consumers (MangroveAI HTTP clients, the HTML UI).

#### Option B: Sidecar to KB server

Both the FastAPI KB server and the MCP server run in the same container, managed by a process supervisor (e.g., supervisord) or a single Python entrypoint that starts both. This shares the in-memory index and reduces resource usage.

**Recommendation:** Start with Option A (standalone container) for simplicity and operational independence. Consider Option B as an optimization if the two services are always deployed together and the memory footprint of a second index becomes a concern.

### 3.6 State Management

The MCP server is **stateless between tool calls**. There are no sessions, no caches that persist across requests, and no server-side state tied to a client identity.

Internal state that exists at the process level:
- The FTS5 search index (SQLite database, built at startup)
- The cross-reference term registry (in-memory dict, built at startup)
- The RuleRegistry (class-level dict, populated on import of signal modules)
- Indicator class metadata (class attributes, available on import)

All of this is read-only after initialization. Multiple concurrent tool calls are safe.

---

## 4. Security and Authentication

### 4.1 Comparison with MangroveMarkets-MCP-Server

| Aspect | MangroveMarkets MCP Server | MangroveKnowledgeBase MCP Server |
|--------|---------------------------|----------------------------------|
| Data sensitivity | High (wallet keys, transactions, financial offers) | Low (public documentation and metadata) |
| Mutation operations | Yes (create listings, make offers, escrow) | No (read-only) |
| Auth requirement | Mandatory (wallet-based identity, API keys) | Optional (see below) |
| Rate limiting | Strict (financial operations, anti-spam) | Moderate (prevent abuse, protect availability) |
| Settlement | XRPL escrow, x402 payments | None |

### 4.2 Authentication Model

The MangroveKnowledgeBase is an MIT-licensed, public repository. All content -- documents, signals, indicators, glossary -- is intended to be openly accessible. This is fundamentally different from MangroveMarkets, where authentication is required because agents interact with financial instruments.

**Recommended tiered approach:**

| Tier | Auth | Rate Limit | Access |
|------|------|------------|--------|
| **Public (default)** | None | 60 requests/minute per IP | All read-only tools |
| **Authenticated** | API key (header: `X-API-Key`) | 300 requests/minute per key | All read-only tools + priority queue |
| **Admin** | API key + admin flag | Unlimited | All tools + future admin tools (if any) |

**API key implementation:**

- API keys are static strings stored in environment variables or a keys file
- No user database, no OAuth flow, no token refresh -- this is intentionally simple
- The MCP server checks for `X-API-Key` header (or equivalent MCP metadata field) on each request
- If no key is provided, the request is treated as public tier
- API keys are provisioned manually by the operator (no self-service registration)

**Why not x402 or OAuth:**

- x402 (pay-per-request) adds overhead for what is essentially a documentation lookup service. The content is already public. Charging for metadata queries would discourage adoption without meaningful revenue.
- OAuth adds complexity (token flows, refresh, scopes) that is not justified for a read-only, public-content service.
- If a future tier with premium content is added (e.g., proprietary signal metadata), authentication can be upgraded to OAuth or x402 at that time.

### 4.3 Rate Limiting

Rate limiting protects the server from abuse and ensures fair access for all clients.

**Implementation:** Token bucket algorithm per client identity (IP for public tier, API key for authenticated tier).

| Resource | Public Tier | Authenticated Tier |
|----------|------------|-------------------|
| All tools combined | 60 req/min | 300 req/min |
| `kb_search` specifically | 30 req/min | 150 req/min |
| Burst allowance | 10 requests | 30 requests |

**Response on rate limit exceeded:**
```json
{
  "error": true,
  "code": "RATE_LIMITED",
  "message": "Rate limit exceeded. 60 requests per minute allowed for unauthenticated clients.",
  "suggestion": "Wait 30 seconds and retry, or authenticate with an API key for higher limits."
}
```

### 4.4 Data Classification

| Data | Classification | Notes |
|------|---------------|-------|
| KB document content | Public | MIT-licensed markdown files |
| Glossary terms and definitions | Public | Part of the KB |
| Signal names, types, descriptions | Public | Published in the open-source package |
| Signal parameter ranges and defaults | Public | Embedded in docstrings, published code |
| Indicator specifications | Public | Class attributes, published code |
| Backlinks and cross-references | Public | Derived from public content |
| Server status and health | Public | Operational metadata |
| API keys themselves | Secret | Never returned in responses, never logged |
| Client request logs (IP, key ID, query) | Internal | Retained for rate limiting and debugging; not exposed via tools |

### 4.5 Tenant Isolation

Not applicable. The MangroveKnowledgeBase is a single-tenant system. All clients see the same knowledge base content. There is no per-tenant data, no per-tenant configuration, and no per-tenant access control.

If multi-tenancy is needed in the future (e.g., clients can upload their own signals or private KB content), it would require a significant architecture change and should be designed as a separate service, not bolted onto this one.

### 4.6 Audit Logging

All MCP tool invocations are logged with:
- Timestamp
- Tool name
- Input parameters (with sensitive values redacted -- though none exist today)
- Client identity (API key ID if authenticated, IP hash if not)
- Response status (success / error code)
- Response time (ms)

Logs are written to stdout (for container log aggregation) in structured JSON format. No PII is collected. Queries are logged for analytics (e.g., popular search terms, most-requested signals) but are not tied to identifiable users.

---

## 5. Implementation Plan

### 5.1 Phase 1: Core KB Tools (MVP)

**Goal:** Ship a working MCP server that wraps the existing kb_server's search and document retrieval, proving the architecture and deployment model.

**Tools implemented:**
1. `kb_search`
2. `kb_list_documents`
3. `kb_get_document`
4. `kb_get_document_sections`
5. `kb_status`

**Scope:**
- Set up `mcp_server/` directory structure
- Implement `server.py` with FastMCP entry point
- Implement `errors.py` (copy and adapt from MangroveMarkets-MCP-Server)
- Implement `config.py` with MCP server settings
- Implement 5 tool functions in `tools/search.py`, `tools/documents.py`, `tools/metadata.py`
- Initialize KB services (SearchEngine, DocumentLoader) at MCP server startup
- Write a `Dockerfile` for standalone deployment
- Update `docker-compose.yml` with `mcp-server` service
- Write integration tests for all 5 tools

**Dependencies:**
- `mcp[cli]>=1.2.0` added to project dependencies
- `pydantic>=2.0.0` (already present via kb_server)
- KB server services must be importable from the MCP server process

**Testing strategy:**
- Unit tests: Mock the SearchEngine/DocumentLoader, test tool input validation and error handling
- Integration tests: Start the MCP server with real KB data, invoke each tool via the MCP client SDK, assert response structure and content
- Manual smoke test: Connect Claude Desktop (or another MCP client) and invoke tools interactively

**Estimated effort:** 2-3 days

---

### 5.2 Phase 2: Glossary, Tags, and Backlinks

**Goal:** Complete the knowledge base navigation tools, enabling agents to browse the knowledge graph.

**Tools implemented:**
6. `kb_glossary_lookup`
7. `kb_list_glossary`
8. `kb_list_tags`
9. `kb_get_documents_by_tag`
10. `kb_get_backlinks`

**Scope:**
- Implement tool functions in `tools/glossary.py`, `tools/tags.py`, `tools/backlinks.py`
- Initialize CrossReferenceEngine at MCP server startup
- Add pagination support to `kb_list_glossary`
- Write integration tests for all 5 tools
- Add rate limiting middleware (basic token bucket)

**Dependencies:**
- Phase 1 complete
- CrossReferenceEngine must be initialized with documents (requires DocumentLoader to run first)

**Testing strategy:**
- Unit tests for pagination logic and error handling
- Integration tests with real glossary data (85 terms)
- Test backlink traversal: pick a known term, verify backlinks match expected cross-references

**Estimated effort:** 1-2 days

---

### 5.3 Phase 3: Signal and Indicator Metadata

**Goal:** Expose the signal registry and indicator specifications to MCP clients, enabling agents to discover and configure trading signals without reading source code.

**Tools implemented:**
11. `kb_list_signals`
12. `kb_get_signal`
13. `kb_list_indicators`
14. `kb_get_indicator`

**Scope:**
- Implement tool functions in `tools/signals.py` and `tools/indicators.py`
- Import and initialize signal modules to populate the RuleRegistry
- Use `docstring_parser.parse_all_signals()` to build the signal metadata index at startup
- Build indicator metadata index from IndicatorInterface subclass introspection (`_data`, `_params`, `_outputs`, docstrings)
- Implement category-based filtering for both signals and indicators
- Implement signal-type and requires-column filtering
- Add pagination to `kb_list_signals`
- Write integration tests for all 4 tools, including filter combinations

**Dependencies:**
- Phase 1 complete (Phase 2 is independent and can run in parallel)
- `mangrove_knowledge_base` package must be importable (it is -- the MCP server lives in the same repo)
- All 96 signal functions must have valid structured docstrings (they do -- validated by 27 existing tests)

**Testing strategy:**
- Unit tests: Mock the RuleRegistry, test filtering logic and pagination
- Integration tests: Import real signal modules, verify all 96 signals are discoverable via `kb_list_signals`, verify each signal's metadata via `kb_get_signal`
- Cross-reference test: Compare `kb_get_signal("rsi_overbought")` output against the known metadata from `test_docstring_parser.py`
- Indicator introspection tests: Verify all 40+ indicators are listed with correct inputs/outputs

**Estimated effort:** 2-3 days

---

### 5.4 Phase 4: Authentication, Rate Limiting, and Hardening

**Goal:** Add the public/authenticated tier system, rate limiting, structured logging, and operational readiness.

**Scope:**
- Implement API key authentication middleware
- Implement rate limiting (token bucket per IP / per key)
- Add structured JSON logging for all tool invocations
- Add health check endpoint for container orchestrators
- Write a `AGENTS.md` documenting how MCP clients should connect and use the tools
- Performance testing: measure p95 latency for each tool under load
- Update README with MCP server documentation

**Dependencies:**
- Phases 1, 2, and 3 complete
- Decide on API key storage mechanism (environment variables vs. keys file)

**Testing strategy:**
- Rate limiting tests: Send burst requests, verify 429-equivalent error responses
- Auth tests: Verify unauthenticated access works for public tier, verify API key grants higher limits
- Load testing: Simulate 20 concurrent MCP sessions with mixed tool calls
- Latency benchmarks: Ensure all tools meet the <200ms / <300ms targets

**Estimated effort:** 2 days

---

### 5.5 Phase 5: Deployment and Integration

**Goal:** Deploy the MCP server alongside the existing KB server and validate end-to-end with real MCP clients.

**Scope:**
- Finalize Dockerfile and docker-compose.yml
- Set up GitHub Actions CI for the MCP server (lint, test, build)
- Deploy to the mangrove-network Docker network
- Test with MangroveAI's AI Copilot as an MCP client (replacing or supplementing direct HTTP calls)
- Test with Claude Desktop as an MCP client
- Test with a generic MCP client library (e.g., the `mcp` Python SDK)
- Document the MCP server URL and connection instructions

**Dependencies:**
- Phase 4 complete
- Docker network `mangrove-network` must be available (it is -- defined as external in docker-compose.yml)

**Testing strategy:**
- End-to-end: MangroveAI copilot issues a RAG query -> MCP client calls `kb_search` -> MCP server returns results -> copilot uses results in LLM prompt
- Cross-project: MangroveMarkets MCP client discovers and calls KB tools
- Smoke test all 14 tools from each client type

**Estimated effort:** 1-2 days

---

### 5.6 Summary Timeline

| Phase | Tools | Effort | Cumulative |
|-------|-------|--------|------------|
| Phase 1: Core KB Tools | 5 tools | 2-3 days | 2-3 days |
| Phase 2: Glossary, Tags, Backlinks | 5 tools | 1-2 days | 3-5 days |
| Phase 3: Signal and Indicator Metadata | 4 tools | 2-3 days | 5-8 days |
| Phase 4: Auth, Rate Limiting, Hardening | 0 tools (cross-cutting) | 2 days | 7-10 days |
| Phase 5: Deployment and Integration | 0 tools (ops) | 1-2 days | 8-12 days |

**Total: 14 tools, 8-12 days of implementation effort.**

Phases 2 and 3 are independent of each other and can be executed in parallel if two developers are available.

---

## Appendix A: Decision Log

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| MCP framework | FastMCP | Custom MCP server, LangChain MCP adapter | FastMCP is proven in MangroveMarkets-MCP-Server, handles protocol details, matches team expertise |
| Tool prefix | `kb_` | `knowledge_`, `mkb_`, no prefix | Short, clear, follows `marketplace_`/`dex_`/`wallet_` convention |
| KB data access | In-process import | HTTP proxy to kb_server, shared database | Simplest, fastest, avoids network hop; HTTP fallback available for split deployment |
| Deployment | Standalone container | Sidecar, embedded in kb_server, Lambda | Independent lifecycle, operational simplicity, matches existing docker-compose pattern |
| Authentication | Optional API key tiers | Mandatory OAuth, x402 payments, no auth | Content is public; auth protects availability (rate limits), not data secrecy |
| Reindex exposure | Not exposed | Exposed with admin auth | Reindex is a mutation that affects all clients; should be triggered by operators, not agents |
| Signal computation | Not exposed | Exposed as tools | Computation requires live market data (DataFrames) which MCP transport is not designed for; metadata is the correct abstraction |

## Appendix B: Open Questions

1. **Should `kb_get_document` return section content?** Currently the section objects include their `content` field. For large documents this inflates the response significantly. Consider adding a `include_content` boolean parameter that defaults to `true` for backward compatibility but allows lightweight retrieval.

2. **Should there be a `kb_search_signals` tool?** The current design has `kb_list_signals` with filters and `kb_search` for KB content. An agent wanting to find "signals related to RSI" would need to either use `kb_list_signals(category="momentum")` or `kb_search(query="RSI")`. A dedicated signal search tool with fuzzy matching on signal names and descriptions could improve discoverability.

3. **MCP Resources vs. Tools.** The MCP protocol supports both Tools (invoked by the client) and Resources (exposed as URI-addressable data). The glossary, document list, and tag list could alternatively be exposed as MCP Resources that clients can read without invoking a tool. This is a protocol-level design decision that should be evaluated during Phase 1 implementation.

4. **Indicator parameter documentation.** The IndicatorInterface only defines `_data`, `_params`, and `_outputs` as lists of names. It does not include parameter types, ranges, or defaults (unlike signals, which have this in their docstrings). To provide rich indicator metadata via `kb_get_indicator`, we would need to either (a) add structured docstrings to indicator classes, or (b) accept that indicator metadata is less detailed than signal metadata for now.

5. **Versioning.** Should the MCP server version be tied to the `mangrove-knowledge-base` package version (currently 0.1.0), or should it have its own version? If the KB content changes (documents added/updated) without code changes, does the version change?
