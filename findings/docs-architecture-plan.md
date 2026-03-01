# Documentation Architecture and Implementation Plan

**Date:** 2026-02-22
**Status:** Approved direction, ready for implementation

---

## Problem Statement

Documentation content is duplicated across 4 locations in MangroveKnowledgeBase, causing drift and maintenance burden:

1. `knowledge-base/*.md` -- source KB content (11 files)
2. `docs/knowledge-base/*.mdx` -- Mintlify copies of KB content (manually maintained)
3. `developer-portal/frontend/public/docs/api/*.md` -- API docs in the portal (auth-gated)
4. `docs/api-reference/*.mdx` -- Mintlify copies of API docs (manually maintained)

This already caused 15 phantom signal names to appear in Mintlify docs that did not exist in code. Hand-maintained copies will always drift from source.

---

## Target Architecture

### Principle: Every piece of content has exactly one source

```
SOURCES (single source of truth for each)        CONSUMERS
============================================      ====================

Signal docstrings (Python)                   ---> Docstring parser
  |                                                |
  +-> Runtime metadata (RuleRegistry)              +-> Generated signal reference
  +-> Param validation                             +-> Mintlify signal catalog page

knowledge-base/*.md (11 markdown files)      ---> KB FastAPI server (FTS5 search, agents)
  |                                                |
  +-> Mintlify reads directly (no copy)            +-> Public docs site

OpenAPI spec (Flask-RESTX auto-generated)    ---> Mintlify OpenAPI renderer
  |                                                |
  +-> Three-panel API reference                    +-> "Try It" playground
  +-> Multi-language code examples                 +-> Request/response schemas

User guides (new, in docs/guides/)           ---> Mintlify guides section
  |
  +-> Workflow walkthroughs with examples
  +-> Not duplicated anywhere else

Developer portal                             ---> Authenticated workspace only
  |
  +-> Dashboard, Chat, Playground, Settings
  +-> Links OUT to public Mintlify docs
  +-> No internal docs viewer
```

### What goes where

| Content | Source Location | Served By | Public? |
|---------|---------------|-----------|---------|
| API reference (endpoints, schemas, examples) | OpenAPI spec JSON | Mintlify OpenAPI renderer | Yes |
| Trading knowledge (indicators, strategies, risk) | `knowledge-base/*.md` | KB server (agents) + Mintlify (humans) | Yes |
| Signal catalog (all 96 signals with metadata) | Signal docstrings | Generated page via docstring parser | Yes |
| User guides (workflows, tutorials, how-tos) | `docs/guides/*.mdx` | Mintlify | Yes |
| Architecture docs | `docs/architecture/*.mdx` | Mintlify | Yes |
| Development docs | `docs/development/*.mdx` | Mintlify | Yes |
| Dashboard, chat, playground, settings | `developer-portal/` | Developer portal (React) | No (auth) |

### What gets deleted (from MangroveKnowledgeBase)

| Delete | Reason |
|--------|--------|
| `docs/api-reference/*.mdx` (8 files) | Replaced by OpenAPI spec rendering |
| `docs/knowledge-base/*.mdx` (10 files) | Replaced by direct reference to `knowledge-base/*.md` |
| `developer-portal/frontend/public/docs/` (30 files) | Portal links to Mintlify instead of serving its own docs |
| `developer-portal/frontend/src/components/docs/` | Docs viewer components no longer needed |

### What gets created

| Create | Purpose |
|--------|---------|
| `docs/openapi/mangroveai-spec.json` | Exported OpenAPI spec from Flask-RESTX |
| `docs/guides/*.mdx` (rewritten) | User-guide-style walkthroughs with tested examples |
| `docs/signals/catalog.mdx` | Auto-generated signal reference from docstring parser |
| Script: `scripts/export-openapi.py` | Fetches spec from running MangroveAI and saves to repo |
| Script: `scripts/generate-signal-catalog.py` | Generates signal catalog MDX from docstring parser |

---

## Mintlify Configuration

### mint.json structure

```json
{
  "name": "Mangrove Developer Docs",
  "openapi": "openapi/mangroveai-spec.json",
  "tabs": [
    {"name": "API Reference", "url": "api-reference"},
    {"name": "Knowledge Base", "url": "knowledge-base"}
  ],
  "navigation": [
    {
      "group": "Getting Started",
      "pages": ["introduction", "quickstart", "authentication"]
    },
    {
      "group": "API Reference",
      "pages": [
        "api-reference/overview",
        {"openapi": "GET /api/v1/strategies"},
        {"openapi": "POST /api/v1/strategies"},
        {"openapi": "GET /api/v1/strategies/{strategy_id}"},
        {"openapi": "POST /api/v1/execution/evaluate/{strategy_id}"},
        {"openapi": "GET /api/v1/signals"},
        {"openapi": "GET /api/v1/signals/{signal_name}"}
      ]
    },
    {
      "group": "Signals",
      "pages": [
        "signals/overview",
        "signals/catalog",
        "signals/momentum",
        "signals/trend",
        "signals/volume",
        "signals/volatility"
      ]
    },
    {
      "group": "Guides",
      "pages": [
        "guides/creating-a-strategy",
        "guides/running-a-backtest",
        "guides/using-the-ai-copilot",
        "guides/signal-architecture",
        "guides/understanding-risk-management"
      ]
    },
    {
      "group": "Knowledge Base",
      "pages": [
        "knowledge-base/market-foundations",
        "knowledge-base/instruments",
        "knowledge-base/trading-concepts",
        "knowledge-base/strategy-design",
        "knowledge-base/risk-management",
        "knowledge-base/indicators",
        "knowledge-base/chart-patterns",
        "knowledge-base/quantitative-analysis",
        "knowledge-base/glossary"
      ]
    },
    {
      "group": "Development",
      "pages": [
        "development/getting-started",
        "development/docker-setup",
        "development/testing"
      ]
    }
  ]
}
```

### OpenAPI integration

Mintlify natively renders OpenAPI specs with:
- Three-panel layout (description + parameters + response on left, code examples on right)
- "Try It" interactive playground
- Multi-language code examples (cURL, Python, JavaScript, Go)
- Request/response schema tables with types
- Authentication header injection
- Error code documentation

This replaces all 8 hand-written API reference MDX files with zero maintenance.

### Knowledge base integration

Mintlify can reference markdown files from anywhere in the repo. Instead of copying `knowledge-base/01-market-foundations.md` to `docs/knowledge-base/market-foundations.mdx`, we configure mint.json to read from the source:

```json
{
  "anchors": {
    "knowledge-base": "../knowledge-base"
  }
}
```

Or symlink:
```bash
ln -s ../../knowledge-base docs/knowledge-base-content
```

The KB markdown files need minimal frontmatter added (title, description) but the content stays in one place.

---

## Signal Catalog Generation

### Script: generate-signal-catalog.py

```
Input: Signal docstrings (via docstring parser)
Output: docs/signals/catalog.mdx (auto-generated)
```

The script:
1. Imports all signal modules
2. Runs the docstring parser to extract metadata
3. Generates an MDX page with:
   - Summary table (name, type, requires, category)
   - Per-signal detail sections with description, parameters table, ranges, defaults
   - Grouped by category (momentum, trend, volume, volatility)
4. Writes to `docs/signals/catalog.mdx`

This runs as a pre-commit hook or CI step. The generated file is committed to the repo so Mintlify can serve it without running Python.

### Script: export-openapi.py

```
Input: Running MangroveAI instance at http://localhost:5001
Output: docs/openapi/mangroveai-spec.json
```

The script:
1. Fetches `http://localhost:5001/api/v1/swagger.json`
2. Cleans up the spec (remove internal endpoints, fix base URL)
3. Saves to `docs/openapi/mangroveai-spec.json`
4. Committed to repo for Mintlify to consume

---

## Developer Portal Changes

### What stays

- Dashboard (DeveloperDashboardPage)
- AI Copilot chat (ChatPage, ChatWindow)
- Strategy playground (StrategyPlayground, SignalSelector)
- Settings and API key management (SettingsPage, ApiKeyList)
- Profile and metrics (ProfilePage)
- Subscription and billing (SubscriptionStatus)
- Organization and team management
- Admin page (user management)
- Login and auth flow (Firebase Auth)

### What changes

- **DocumentationPage** -- replaced with a redirect/link to the public Mintlify docs site
- **DocsSidebar** -- removed (no longer needed)
- **MarkdownRenderer** -- removed (no longer needed)
- **SwaggerViewer** -- removed (Mintlify handles API reference)
- **docsService.js** -- removed (no longer fetching local markdown)
- **manifest.json** -- removed (no longer needed)
- **public/docs/** -- removed (30 markdown files, served by Mintlify instead)

### Navigation update

The portal sidebar "Documentation" link changes from an internal route to an external link:

```jsx
// Before
<NavLink to="/docs">Documentation</NavLink>

// After
<a href="https://docs.mangrovetechnologies.ai" target="_blank" rel="noopener">
  Documentation
</a>
```

---

## Reference: How Stripe/Nansen Do It

### Stripe
- API reference is 100% generated from OpenAPI spec
- Three-panel layout: endpoint description (left), code examples (right)
- 8 language tabs (cURL, Python, Ruby, PHP, Java, Node, Go, .NET)
- Every endpoint has a "Try It" button
- Guides are hand-written MDX, separate from API reference
- No login required for any documentation
- Dashboard (authenticated) links to docs, does not contain docs

### Nansen (Mintlify)
- Uses Mintlify with mint.json configuration
- OpenAPI spec generates API reference automatically
- Knowledge base content is markdown in the repo
- Code examples in multiple languages via CodeGroup
- Search powered by Algolia (built into Mintlify)
- Changelog built into the docs site
- Public, no login

### What we get from this architecture
- OpenAPI spec rendering gives us the Stripe-style three-panel layout for free
- Knowledge base markdown served directly eliminates duplication
- Signal catalog generated from docstrings eliminates drift
- Developer portal becomes a clean authenticated workspace
- All documentation is public and searchable

---

## Implementation Plan

### Phase 1: OpenAPI spec export (0.5 days)
1. Write `scripts/export-openapi.py`
2. Run it against the local MangroveAI instance
3. Save spec to `docs/openapi/mangroveai-spec.json`
4. Update `mint.json` to use the OpenAPI spec
5. Delete `docs/api-reference/*.mdx` (8 files)

### Phase 2: Signal catalog generation (0.5 days)
1. Write `scripts/generate-signal-catalog.py`
2. Generate `docs/signals/catalog.mdx` from docstring parser
3. Create `docs/signals/overview.mdx` (introduction to signals)
4. Create per-category pages (`docs/signals/momentum.mdx`, etc.) if needed, or keep as one catalog

### Phase 3: Knowledge base direct integration (0.5 days)
1. Add frontmatter to `knowledge-base/*.md` files (title, description)
2. Configure Mintlify to read from `knowledge-base/` directly (symlink or path config)
3. Delete `docs/knowledge-base/*.mdx` (10 files)
4. Test that Mintlify renders the KB content correctly

### Phase 4: User guides (1 day)
1. Rewrite `docs/guides/` as proper user guides with:
   - Step-by-step workflows
   - Tested code examples (cURL + Python + JavaScript)
   - Screenshots where helpful
   - Clear prerequisites and outcomes
2. Key guides:
   - "Creating Your First Strategy"
   - "Running a Backtest"
   - "Using the AI Copilot"
   - "Understanding Signals and Indicators"
   - "Risk Management Configuration"

### Phase 5: Developer portal cleanup (0.5 days)
1. Replace DocumentationPage with external link to Mintlify
2. Remove docs viewer components (DocsSidebar, MarkdownRenderer, SwaggerViewer)
3. Remove `public/docs/` directory and manifest.json
4. Remove docsService.js
5. Update navigation to link out to public docs
6. Test all remaining portal features still work

### Phase 6: Polish and deploy (0.5 days)
1. Set up Mintlify deployment (connect to GitHub repo)
2. Configure custom domain (docs.mangrovetechnologies.ai)
3. Test all pages render correctly
4. Verify OpenAPI playground works with live API
5. Run final cross-source harmony check

### Total estimated effort: 3.5 days

---

## Dependencies and Prerequisites

| Prerequisite | Status | Notes |
|-------------|--------|-------|
| MangroveAI running locally | Ready | Needed for OpenAPI spec export |
| Mintlify account | Not started | Sign up at mintlify.com |
| Custom domain DNS | Not started | CNAME for docs.mangrovetechnologies.ai |
| MangroveKnowledgeBase on GitHub | Done | Already published |
| Signal docstring parser | Done | Already built and validated |
| KB server running | Done | Already running on port 8080 |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenAPI spec from Flask-RESTX is incomplete or messy | API reference pages missing endpoints | Review and clean spec before committing; add descriptions to Flask-RESTX decorators |
| Mintlify free tier limitations | May not support all features (custom domain, search) | Evaluate plans; Growth plan at $150/mo if needed |
| KB markdown files need format changes for Mintlify | Content restructuring work | Add frontmatter only; Mintlify handles standard markdown well |
| Developer portal users expect docs inside the portal | Confusion during transition | Add clear "View Documentation" button linking to public docs |
| Generated signal catalog goes stale | Drift between code and docs | Run generation script in CI; fail build if output differs from committed file |
