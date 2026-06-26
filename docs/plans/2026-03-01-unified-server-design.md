# Unified KB + MCP Server Design

**Date:** 2026-03-01
**Status:** Approved
**Scope:** MangroveKnowledgeBase server restructure, MCP integration, x402 payment gating

---

## Problem

The MangroveKnowledgeBase repository has three deliverables:

1. **Pip package** (`mangrove-kb`) -- signals, indicators, registry, parser
2. **KB server** (`kb_server/`) -- FastAPI REST API for document search, glossary, cross-references
3. **MCP server** (planned) -- MCP tools exposing KB resources to external AI agents

The KB server and MCP server access identical underlying resources. Building them as separate services creates duplication, deployment complexity, and inconsistent behavior. Signal/indicator metadata should be free; computation should be monetized via x402.

## Design

### Architecture: One Server, Dual Protocol

A single FastAPI process serves both REST and MCP on the same port. Both protocols call the same service layer.

```
mangrove_kb/          # pip package (signals, indicators, registry, parser)
        |
   [service layer]                # shared business logic
   SearchEngine                   # FTS5 document search (existing)
   CrossReferenceEngine           # glossary, backlinks (existing)
   DocumentLoader                 # markdown loading (existing)
   SignalService                  # NEW: docstring parser + RuleRegistry
   IndicatorService               # NEW: indicator metadata + compute
     /         \
  REST API    MCP Transport       # dual access to same services
  (FastAPI)   (FastMCP)           # same process
     |              |
  /api/*       /mcp/*             # same port (8080)
```

### Access Control: Free Metadata, x402 Computation

| Capability | Access | REST | MCP |
|-----------|--------|------|-----|
| Document search | Free | GET /api/search | kb_search |
| Document retrieval | Free | GET /api/documents/{slug} | kb_get_document |
| Glossary lookup | Free | GET /api/glossary/{term} | kb_glossary_lookup |
| Tag browsing | Free | GET /api/tags | kb_list_tags |
| Backlinks | Free | GET /api/backlinks/{anchor} | kb_get_backlinks |
| Signal metadata | Free | GET /api/signals | kb_list_signals |
| Signal detail | Free | GET /api/signals/{name} | kb_get_signal |
| Indicator metadata | Free | GET /api/indicators | kb_list_indicators |
| Indicator detail | Free | GET /api/indicators/{name} | kb_get_indicator |
| Signal evaluation | x402 | POST /api/evaluate | evaluate_signal |
| Indicator computation | x402 | POST /api/compute | compute_indicator |
| Server status | Free | GET /api/status | kb_status |

x402 payment is enforced on both HTTP and MCP transports via shared middleware.

### Directory Structure

```
kb_server/                        # keep existing name (no rename churn)
  main.py                         # FastAPI + FastMCP in one process
  config.py                       # environment-aware settings (existing)
  init_db.py                      # database initialization (existing)
  Dockerfile                      # single container (existing, updated)
  services/                       # shared service layer
    search_engine.py              # existing
    cross_reference.py            # existing
    document_loader.py            # existing
    synonyms.py                   # existing
    anchor_generator.py           # existing
    signal_service.py             # NEW: wraps docstring parser + RuleRegistry
    indicator_service.py          # NEW: wraps indicator compute
  routers/
    api.py                        # REST endpoints (existing, extended)
    ui.py                         # HTML UI routes (existing)
  mcp/
    tools.py                      # MCP tool definitions
  x402/
    middleware.py                  # payment validation for both REST and MCP
    pricing.py                    # per-tool pricing config
```

### MCP Tools (18 total)

**Knowledge Base (9 tools, all free):**
- kb_search -- full-text search with synonym expansion
- kb_list_documents -- list all 11 docs with summaries
- kb_get_document -- full document with sections and cross-references
- kb_get_document_sections -- section tree without content
- kb_glossary_lookup -- single term with backlinks
- kb_list_glossary -- all glossary entries
- kb_list_tags -- all tags with counts
- kb_get_documents_by_tag -- docs filtered by tag
- kb_get_backlinks -- knowledge graph navigation

**Signal & Indicator Metadata (4 tools, all free):**
- kb_list_signals -- filter by category/type
- kb_get_signal -- full metadata with params, ranges, defaults
- kb_list_indicators -- filter by category
- kb_get_indicator -- full spec with inputs/outputs

**Computation (2 tools, x402 gated):**
- evaluate_signal -- accepts signal name, OHLCV data, params; returns boolean
- compute_indicator -- accepts indicator name, data, params; returns computed values

**Status (1 tool, free):**
- kb_status -- health check, document count, signal count

### Signal & Indicator Services

**SignalService** (singleton, initialized at startup):
- Loads all signal metadata via docstring parser at startup (cached)
- list_signals(category, signal_type) -- returns metadata list
- get_signal(name) -- returns full metadata including params
- evaluate(name, ohlcv_data, params) -- calls RuleRegistry.evaluate(), x402 gated

**IndicatorService** (singleton, initialized at startup):
- Discovers all indicator classes from the package at startup (cached)
- list_indicators(category) -- returns metadata list
- get_indicator(name) -- returns full spec (inputs, outputs, params)
- compute(name, data, params) -- calls Indicator.compute(), x402 gated

### x402 Integration

Adapted from MangroveAI's existing x402 implementation (`src/MangroveAI/v402/`):
- Middleware validates x402 payment headers on gated endpoints
- Pricing config defines cost per tool/endpoint
- Works identically on REST (HTTP headers) and MCP (tool metadata)
- Facilitator URL configurable per environment

### Deployment

**Same infrastructure, same patterns:**
- Single Docker container running uvicorn
- GCP Cloud Run via existing Terraform module (`app-mangroveai-kb`)
- Domain mapping: devkb.mangrove.trade (dev), kb.mangrovedeveloper.ai (prod)
- Environment resolution handled by existing deployment automation
- Scale-to-zero, autoscaling, managed TLS -- all existing

**Why Cloud Run:** Stateless (SQLite read-only after init), low memory (<256MB), spiky traffic, needs scale-to-zero. Already have Terraform module, service account, domain mapping. No reason to change.

**Container startup:** init_db.py builds FTS5 index, then uvicorn serves both REST and MCP.

### PyPI Package

Publish `mangrove-kb` 0.1.0 to PyPI:
- Pure Python, no native dependencies
- numpy + pandas only
- 136 signals, 70 indicators, RuleRegistry, docstring parser
- MIT license
- Anyone can pip install and use locally without the server

## What This Replaces

- `findings/mcp-server-plan.md` -- superseded by this design (MCP was planned as separate service)
- `kb-next-steps.md` -- partially superseded (server architecture section)

## What This Does Not Change

- Pip package structure (mangrove_kb/)
- Knowledge base content (knowledge-base/)
- Mintlify docs site (docs/)
- Generation scripts (scripts/)
- Test structure (tests/)
- Docker networking patterns
- MangroveAI's USE_EXTERNAL_KB toggle
- URL resolution and deployment automation
