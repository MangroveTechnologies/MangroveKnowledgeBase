# MangroveKnowledgeBase

## What This Is

Open-source trading signals, technical indicators, and knowledge base. Three components:

1. **Python Package** (`mangrove_knowledge_base`) -- 136 signal functions, 70 indicator classes (including 27 pattern indicators), RuleRegistry, docstring parser
2. **KB Server** (`kb_server/`) -- FastAPI service with SQLite FTS5 full-text search, 11 trading education documents, glossary, cross-references, synonym expansion
3. **Knowledge Base Content** (`knowledge-base/`) -- 11 markdown documents covering market foundations through quantitative analysis

MangroveAI consumes this as a pip dependency and connects to the KB server over HTTP. The developer portal (admin UI) source code lives in MangroveAI, not here.

## Project Structure

```
mangrove_knowledge_base/       # pip package: signals, indicators, registry, parser
kb_server/                     # FastAPI KB server (port 8080)
knowledge-base/                # 11 trading education markdown documents
docs/                          # Mintlify public docs site
notebooks/                     # Signal explorer notebook
data/                          # 7 sample OHLCV datasets
tests/                         # Docstring parser + pattern signal validation
scripts/                       # Signal catalog generator
findings/                      # Planning docs and session notes
```

## Key Architecture Decisions

- **Docstrings are the single source of truth** for signal metadata (Type, Requires, param ranges). No separate JSON or YAML config.
- **MangroveAI uses `USE_EXTERNAL_KB` env var** (default: `false`) to toggle between local signal implementations and this package. All MangroveAI import paths stay the same regardless of mode.
- **5 social signals stay private** in MangroveAI. They are not in this open-source repo.
- **KB server is standalone** -- zero code dependencies on MangroveAI. All communication is over HTTP.
- **Public documentation** -- API docs, signal catalog, and knowledge base are publicly accessible via Mintlify. No authentication required.
- **Docker networking** -- the KB server joins `mangrove-network` (created by MangroveAI's docker-compose) as an external network.

## Working Here

- **Signal functions** are in `mangrove_knowledge_base/signals/` (momentum.py, trend.py, volume.py, volatility.py, patterns.py)
- **Indicator classes** are in `mangrove_knowledge_base/indicators/` -- all use the `IndicatorInterface.compute()` pattern
- **KB server endpoints** are documented in `kb_server/API.md` (13 REST endpoints)
- **Mintlify docs** are in `docs/` -- public-facing site with API reference, signal catalog, guides, and knowledge base. `docs/knowledge-base-source/` is generated (not checked in) -- run `python scripts/generate-kb-docs.py` before Mintlify builds
- **Tests**: `pytest tests/ -v` validates docstring parser and pattern signal outputs
- **Docker**: `docker compose up -d mkb-knowledge-base` starts the KB server on port 8081

## Signal Conventions

- Every signal function is decorated with `@RuleRegistry.register("signal_name")`
- Every signal docstring must include `Type:` (TRIGGER or FILTER) and `Requires:` (comma-separated column names)
- Every parameter must include `Range: min-max` and `Default: value` in the Args section
- The `df` parameter is always first and excluded from metadata output
- Signal counts: 136 signals in this repo (66 TRIGGER, 70 FILTER). MangroveAI has 5 additional private social signals.
- Categories: Momentum (26), Trend (38), Volume (22), Volatility (10), Patterns (40)

## Upcoming Work

- MCP server to expose KB capabilities to external AI agents (see `findings/mcp-server-plan.md`)
- Mintlify docs deployment to docs.mangrovetechnologies.ai
- Signal catalog auto-generation in CI (see `scripts/generate-signal-catalog.py`)
- KB docs generation in CI (see `scripts/generate-kb-docs.py`)

## GitHub

- Repo: [MangroveTechnologies/MangroveKnowledgeBase](https://github.com/MangroveTechnologies/MangroveKnowledgeBase)
- Pip package name: `mangrove-knowledge-base`
- Python package name: `mangrove_knowledge_base`
