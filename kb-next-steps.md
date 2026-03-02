# MangroveKnowledgeBase -- Next Steps

## Current State

The repo has three clean components, no developer portal code:

```
MangroveKnowledgeBase/
  mangrove_kb/     # Pip package: 136 signals, 70 indicators, registry, parser
  kb_server/                   # FastAPI KB server (standalone, port 8080)
  knowledge-base/              # 11 trading education markdown documents (source of truth)
  docs/                        # Mintlify public docs site (docs.mangrovedeveloper.ai)
  notebooks/                   # Signal explorer notebook (updated with patterns)
  data/                        # 7 sample OHLCV datasets
  tests/                       # 51 tests (docstring parser + pattern signals)
  scripts/                     # Signal catalog + KB docs generators
  findings/                    # Planning docs and session notes
```

docker-compose.yml has 3 services: test, lint, mkb-knowledge-base

## Two Subdomains, Cross-linked

- `mangrovedeveloper.ai` -- MangroveAdmin (auth-gated interactive features)
- `docs.mangrovedeveloper.ai` -- Mintlify (all public docs, guides, KB, signal reference, API docs)

Navigation links between them:
- Mintlify topbar: "Developer Portal" link to mangrovedeveloper.ai, "Login" CTA button
- MangroveAdmin navbar: "Docs" link to docs.mangrovedeveloper.ai (works for both logged-in and logged-out users)

## Content Pipeline

### Source of Truth

| Content | Source of truth | Flows to |
|---------|----------------|----------|
| Knowledge base (11 trading docs) | `knowledge-base/*.md` in this repo | `docs/knowledge-base-source/` (generated), KB server SQLite FTS5 |
| Signal/indicator catalog | Docstrings in `mangrove_kb/` | `docs/signals/catalog.mdx` (generated) |
| API reference (OpenAPI) | MangroveAI live swagger.json | Mintlify fetches at build time |
| User guides | MangroveAI `src/MangroveAdmin/frontend/public/docs/guides/` | `docs/guides/` in this repo (to be generated) |

### Mintlify Pre-build Steps

Run before Mintlify deploys:

1. `python scripts/generate-kb-docs.py` -- copies `knowledge-base/*.md` into `docs/knowledge-base-source/`
2. `python scripts/generate-signal-catalog.py` -- generates `docs/signals/catalog.mdx` from docstring metadata
3. Copy guides from MangroveAI (script TBD) -- copies guide .md files from MangroveAI into `docs/guides/`

Generated directories (.gitignored):
- `docs/knowledge-base-source/` -- full KB documents
- `docs/signals/catalog.mdx` -- signal catalog (currently checked in, should be gitignored)

Hand-maintained in this repo:
- `docs/knowledge-base/*.mdx` -- condensed overview pages (nav summaries)
- `docs/introduction.mdx`, `docs/quickstart.mdx`, `docs/authentication.mdx`
- `docs/api-reference/`, `docs/architecture/`, `docs/development/`

## Changes Needed in MangroveAI

### 1. Add "Docs" link to MangroveAdmin navbar

**File**: `src/MangroveAdmin/frontend/src/components/common/Navbar.jsx`

Add a link to `docs.mangrovedeveloper.ai` in the navbar. This should be visible to both authenticated and unauthenticated users. Currently the navbar has: Dashboard, Chat, Playground, Docs (internal), Admin.

The internal `/docs` route (which serves markdown from the public/docs/ folder behind auth) can either:
- Stay as-is for internal/developer docs that don't belong on the public site
- Be replaced with a redirect to docs.mangrovedeveloper.ai
- Be removed entirely if all docs move to Mintlify

Recommended: replace the internal Docs nav link with an external link to `docs.mangrovedeveloper.ai`. Keep the internal `/docs` route functional for now but deprioritize it.

### 2. Add "Docs" link to LandingPage

**File**: `src/MangroveAdmin/frontend/src/components/landing/LandingPage.jsx`

The landing page (shown to unauthenticated users at `/`) should include a visible link to `docs.mangrovedeveloper.ai` so visitors can browse docs without logging in.

### 3. Consolidate guides as source of truth

**Directory**: `src/MangroveAdmin/frontend/public/docs/guides/`

Current MangroveAI guides:
- ai-copilot-workflow.md
- backtesting-guide.md
- rag-system.md
- signal-architecture.md
- subscription-system.md

These should be the source of truth for guide content. When guides are updated in MangroveAI, they flow to the Mintlify site via the pre-build copy step. Additional user-facing guides (understanding-signals, creating-a-strategy, running-a-backtest, using-the-ai-copilot, risk-management) currently only exist in MangroveKnowledgeBase's docs/guides/ and should be moved to MangroveAI's guides directory so all guides have a single source of truth.

### 4. Update MangroveAI docs references

Update MangroveAI's CLAUDE.md to note:
- MangroveKnowledgeBase no longer contains the developer portal
- Public docs served via Mintlify at docs.mangrovedeveloper.ai
- Guides in public/docs/guides/ are the source of truth; they flow to the Mintlify site

### 5. Update environment config

Ensure MangroveAI's docker-compose and .env reference the correct KB_SERVER_URL. Currently the KB server runs as `mangrove-kb` on port 8080 inside MangroveAI's docker-compose. For production, this will point to a Cloud Run deployment.

No changes needed to kb_client.py -- it already reads KB_SERVER_URL from env.

## Hosting Strategy

### KB Server

Two options:
1. Docker on mangrove-network (current) -- works for local dev and single-server deployments
2. GCP Cloud Run (production) -- deploy kb_server/Dockerfile, set env vars, get a public URL

### Mintlify

Deploy from `docs/` directory to `docs.mangrovedeveloper.ai`.
- Run pre-build scripts first (generate KB docs, signal catalog, copy guides)
- Mintlify fetches OpenAPI spec from live MangroveAI swagger endpoint
- No auth required for any Mintlify content

## Local Development Setup

1. Start MangroveAI stack: `cd MangroveAI && docker compose up -d` (starts postgres, mangrove-app, mangrove-kb, mangrove-admin)
2. Start MangroveKnowledgeBase KB server (optional, if running standalone): `cd MangroveKnowledgeBase && docker compose up -d mkb-knowledge-base`
3. Generate Mintlify docs: `cd MangroveKnowledgeBase && python scripts/generate-kb-docs.py && python scripts/generate-signal-catalog.py`
4. Preview Mintlify locally: `cd MangroveKnowledgeBase/docs && mintlify dev`

Services:
- MangroveAI backend: http://localhost:5001
- MangroveAdmin frontend: http://localhost:3589
- KB server (MangroveAI): http://localhost:8080
- KB server (standalone): http://localhost:8081
- Mintlify preview: http://localhost:3000
