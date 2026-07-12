# MangroveKnowledgeBase

## Default Persona

When working in this repo, you are the **product owner**. Read `.claude/agents/product-owner.md` for your full agent spec and follow it. Load your memory from the repo memory directory on every session start.

---

## Start Here

```bash
# Install the pip package
pip install -e ".[dev]"

# Start the KB server (REST + MCP, exposed on port 8081 locally)
docker compose up -d mkb-knowledge-base

# Run all tests (102 tests)
python -m pytest tests/ -v

# Publish to PyPI (preferred: use GitHub Actions workflow)
# Go to Actions > "Release to PyPI" > Run workflow > pick bump type
# Local fallback:
./scripts/publish.sh patch   # or minor, major

```

**Verify it works:**
```bash
# Signal metadata (free)
curl http://localhost:8081/api/signals | python3 -m json.tool | head -20

# Indicator metadata (free)
curl http://localhost:8081/api/indicators | python3 -m json.tool | head -20

# Search the knowledge base (free)
curl "http://localhost:8081/api/search?q=RSI" | python3 -m json.tool | head -20

# Evaluate a signal (x402 gated -- returns 402 without payment)
curl -X POST http://localhost:8081/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"name":"rsi_oversold","ohlcv":{"Close":[100,101,99,98,102,103]},"params":{"window":14,"threshold":30}}'
```

## What This Is

Open-source trading signals, technical indicators, and knowledge base. Public developer docs now live in mangrove-platform-frontend-web (`content/docs/`), not here. Components:

1. **Python Package** (`mangrove_kb`) -- 233 signal functions, 99 indicator classes (including 27 pattern indicators), RuleRegistry, docstring parser. Published on PyPI as `mangrove-kb`.
2. **KB Server** (`kb_server/`) -- Unified server with dual protocol access (REST + MCP) on the same port. FastAPI REST API + FastMCP tools. SQLite FTS5 full-text search, 11 trading education documents, glossary, cross-references, synonym expansion. Signal/indicator metadata (free) and computation (x402 gated).
3. **Knowledge Base Content** (`knowledge-base/`) -- 11 markdown documents covering market foundations through quantitative analysis

MangroveAI consumes this as a pip dependency (`mangrove-kb`) and connects to the KB server over HTTP. The developer portal (admin UI) source code lives in MangroveAI, not here.

## Project Structure

```
mangrove_kb/                   # pip package: signals, indicators, registry, parser
kb_server/                     # unified server (REST + MCP)
  main.py                      # FastAPI + FastMCP mounted at /mcp
  Dockerfile                   # KB server Docker image
  services/                    # shared service layer
    search_engine.py           # FTS5 document search
    cross_reference.py         # glossary, backlinks
    document_loader.py         # markdown loading
    signal_service.py          # signal metadata + evaluation
    indicator_service.py       # indicator metadata + computation
  routers/
    api.py                     # REST endpoints (free + x402 gated)
    ui.py                      # HTML UI routes
  mcp/
    tools.py                   # 16 MCP tools (free + x402 gated)
  x402/
    middleware.py              # payment validation
    pricing.py                 # per-tool pricing
knowledge-base/                # 11 trading education markdown documents
notebooks/                     # Signal explorer notebook
data/                          # 7 sample OHLCV datasets
tests/                         # 102 tests
scripts/                       # publish.sh, generation scripts
findings/                      # planning docs
```

## Server Architecture

Single process, dual protocol. Both REST and MCP call the same service layer:

| Protocol | Path | Transport |
|----------|------|-----------|
| REST API | /api/* | HTTP JSON |
| MCP | /mcp/* | Streamable HTTP |

### Access Control

| Capability | Access | REST | MCP |
|-----------|--------|------|-----|
| Document search | Free | GET /api/search | kb_search |
| Document retrieval | Free | GET /api/documents/{slug} | kb_get_document |
| Glossary lookup | Free | GET /api/glossary/{term} | kb_glossary_lookup |
| Signal metadata | Free | GET /api/signals | kb_list_signals |
| Indicator metadata | Free | GET /api/indicators | kb_list_indicators |
| Signal evaluation | x402 | POST /api/evaluate | evaluate_signal |
| Indicator computation | x402 | POST /api/compute | compute_indicator |

x402 payment is enforced on both HTTP and MCP via shared middleware.

## Key Architecture Decisions

- **Docstrings are the single source of truth** for signal metadata (Type, Requires, param ranges). No separate JSON or YAML config.
- **Metadata free, computation x402** -- signal/indicator discovery is open, evaluation/computation requires payment on both REST and MCP.
- **MangroveAI imports signals/indicators from `mangrove-kb` PyPI package** -- no embedded copy, no toggle.
- **5 social signals stay private** in MangroveAI. They are not in this open-source repo.
- **KB server is standalone** -- zero code dependencies on MangroveAI.
- **Signal parameter naming** -- standardized to `window` (not `lookback`, `period`, `length`). Backward compat mapping in `RuleRegistry.evaluate()`.

## CI/CD

### PyPI Package
**Preferred:** GitHub Actions > "Release to PyPI" > Run workflow > pick `patch`/`minor`/`major`. This runs tests, computes version from latest git tag, creates tag, builds, publishes to PyPI, and creates a GitHub Release.

**Local fallback:** `./scripts/publish.sh [patch|minor|major]`

**Versioning:** `setuptools-scm` derives version from git tags at build time. No hardcoded version strings in source. `__version__` reads from `importlib.metadata` at runtime.

### Docker Image (KB Server)
On push to main, the `build-and-push` GitHub Actions workflow builds the KB server image and pushes it to:
```
us-central1-docker.pkg.dev/mangroveai-platform/mangrove-ai-repo/mangrove-ai-kb
```
Tags: `latest` + commit SHA.

MangroveAI controls Cloud Run deployment separately (via its own `deploy-kb-prod` workflow). There is no cloud dev environment — dev was shut down (#271, 2026-06-15); everything runs in `mangroveai-prod`.

### CI
On push/PR to main, the `ci` workflow runs pytest across Python 3.10, 3.11, 3.12.

## Deployment

KB server image is built and pushed to Artifact Registry by this repo. Cloud Run deployment is managed by MangroveAI.

| Environment | URL | Managed By |
|------------|-----|------------|
| Local | http://localhost:8081 | docker-compose (this repo or MangroveAI) |
| Prod | https://kb.mangrovedeveloper.ai | MangroveAI deploy-kb-prod workflow (`mangroveai-prod`) |

Terraform module: `MangroveAI/infra/terraform/modules/app-mangroveai-kb/`

## Signal Conventions

- Every signal function is decorated with `@RuleRegistry.register("signal_name")`
- Every signal docstring must include `Type:` (TRIGGER or FILTER) and `Requires:` (comma-separated column names)
- Every parameter must include `Range: min-max` and `Default: value` in the Args section
- Use `window` for all windowing parameters (not `lookback`, `period`, `length`)
- Signal counts: 233 signals (112 TRIGGER, 121 FILTER) across 6 categories
- Categories: Momentum (42), Trend (88), Volume (33), Volatility (20), Patterns (40), On-Chain (10)
- On-Chain signals consume alternative-data columns (SmartMoneyNetflow, SmartMoneyHoldings, ExchangeNetflow, WhaleNetInflow, HolderConcentration) the caller populates time-aligned to OHLCV bars; sourced from Nansen tgm/flows + historical-top-holders via the MangroveAI data layer. There is no total-holder-count series upstream, so holder-count signals are intentionally not shipped.

## GitHub

- Repo: [MangroveTechnologies/MangroveKnowledgeBase](https://github.com/MangroveTechnologies/MangroveKnowledgeBase)
- Pip package name: `mangrove-kb`
- Python package name: `mangrove_kb`
