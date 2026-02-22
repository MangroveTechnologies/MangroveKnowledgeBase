# MangroveKnowledgeBase

## What This Is

Open-source trading signals, technical indicators, and knowledge base. Three components:

1. **Python Package** (`mangrove_knowledge_base`) -- 96 signal functions, 40+ indicator classes, RuleRegistry, docstring parser
2. **KB Server** (`kb_server/`) -- FastAPI service with SQLite FTS5 full-text search, 11 trading education documents, glossary, cross-references, synonym expansion
3. **Knowledge Base Content** (`knowledge-base/`) -- 11 markdown documents covering market foundations through quantitative analysis

MangroveAI consumes this as a pip dependency and connects to the KB server over HTTP.

## Project Structure

```
mangrove_knowledge_base/       # pip package: signals, indicators, registry, parser
kb_server/                     # FastAPI KB server (port 8080)
knowledge-base/                # 11 trading education markdown documents
notebooks/                     # Signal explorer notebook
data/                          # 7 sample OHLCV datasets
tests/                         # Docstring parser validation tests
findings/                      # Planning docs and session notes
```

## Key Architecture Decisions

- **Docstrings are the single source of truth** for signal metadata (Type, Requires, param ranges). No separate JSON or YAML config.
- **MangroveAI uses `USE_EXTERNAL_KB` env var** (default: `false`) to toggle between local signal implementations and this package. All MangroveAI import paths stay the same regardless of mode.
- **Social signals (5 disabled X/Twitter signals) stay private** in MangroveAI. They are not in this repo.
- **KB server is standalone** -- zero code dependencies on MangroveAI. All communication is over HTTP.
- **Docker networking** -- the KB server joins `mangrove-network` (created by MangroveAI's docker-compose) as an external network.

## Working Here

- **Signal functions** are in `mangrove_knowledge_base/signals/` (momentum.py, trend.py, volume.py, volatility.py)
- **Indicator classes** are in `mangrove_knowledge_base/indicators/` -- all use the `IndicatorInterface.compute()` pattern
- **KB server endpoints** are documented in `kb_server/API.md` (13 REST endpoints)
- **Tests**: `pytest tests/ -v` validates docstring parser output against the original signals_metadata.json schema
- **Docker**: `docker compose up -d knowledge-base` starts the KB server on port 8080

## Signal Conventions

- Every signal function is decorated with `@RuleRegistry.register("signal_name")`
- Every signal docstring must include `Type:` (TRIGGER or FILTER) and `Requires:` (comma-separated column names)
- Every parameter must include `Range: min-max` and `Default: value` in the Args section
- The `df` parameter is always first and excluded from metadata output
- Signal counts: 96 active (34 TRIGGER, 62 FILTER) plus 5 disabled social in MangroveAI = 101 total

## Upcoming Work

- MCP server to expose KB capabilities to external AI agents (see `findings/mcp-server-plan.md`)
- Mintlify docs platform for public-facing documentation (see `findings/docs-and-admin-plan.md`)
- MangroveAdmin frontend extraction (copy, not move) from MangroveAI

## GitHub

- Repo: [MangroveTechnologies/MangroveKnowledgeBase](https://github.com/MangroveTechnologies/MangroveKnowledgeBase)
- Pip package name: `mangrove-knowledge-base`
- Python package name: `mangrove_knowledge_base`
