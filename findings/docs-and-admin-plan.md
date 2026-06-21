# Planning Document: Mintlify Public Docs + MangroveAdmin Extraction

> ⚠️ **Historical — superseded by #271 (2026-06-15).** No cloud dev environment exists; everything runs in **`mangroveai-prod`** (deploy via `deploy-kb-prod`). Any `mangroveai-dev` / `*-dev` deploy reference below is historical.

**Date:** 2026-02-22
**Status:** Planning only -- no implementation
**Author:** Claude (Opus 4.6)

---

## Table of Contents

1. [Requirements](#1-requirements)
   - 1.1 [Mintlify Public Docs](#11-mintlify-public-docs)
   - 1.2 [MangroveAdmin Extraction](#12-mangroveadmin-extraction)
2. [Specification](#2-specification)
   - 2.1 [Mintlify Site Structure](#21-mintlify-site-structure)
   - 2.2 [MangroveAdmin in MangroveKnowledgeBase](#22-mangroveadmin-in-mangroveknowledgebase)
3. [Architecture](#3-architecture)
   - 3.1 [Repository Layout](#31-repository-layout)
   - 3.2 [Service Topology](#32-service-topology)
   - 3.3 [Toggle Mechanism](#33-toggle-mechanism)
   - 3.4 [Docker Compose Services](#34-docker-compose-services)
4. [Security](#4-security)
5. [Implementation Plan](#5-implementation-plan)

---

## 1. Requirements

### 1.1 Mintlify Public Docs

#### What goes on the public docs site

The public Mintlify site replaces MangroveAdmin's broken docs viewer (9 of 30 markdown files visible in manifest, no search, auth-gated, Swagger iframe). It serves as the primary documentation surface for developers, API consumers, and AI agents.

**Content to publish publicly:**

| Category | Files | Source Location |
|----------|-------|-----------------|
| API Reference (generated) | 1 OpenAPI spec | Flask-RESTX auto-generated at `/api/v1/docs/` (Swagger JSON at `/api/v1/swagger.json`) |
| API Guides | 9 files | `MangroveAdmin/frontend/public/docs/api/` -- ai-copilot.md, authentication.md, backtesting.md, crypto-assets.md, execution.md, market-data.md, signals.md, signal-validation.md, strategies.md |
| Architecture Docs | 2 files | `MangroveAdmin/frontend/public/docs/architecture/` -- architectural-patterns.md, domain-driven-design.md |
| Guides | 5 files | `MangroveAdmin/frontend/public/docs/guides/` -- rag-system.md, signal-architecture.md, subscription-system.md, backtesting-guide.md, ai-copilot-workflow.md |
| Development Docs | 7 files | `MangroveAdmin/frontend/public/docs/development/` -- logging-guide.md, api-versioning.md, getting-started.md, commit-standards.md, testing-guide.md, pull-request-process.md, github-issues.md |
| Deployment Docs | 5 files | `MangroveAdmin/frontend/public/docs/deployment/` -- overview.md, README.md, docker-setup.md, google-cloud/secret-manager.md, google-cloud/terraform-guide.md, google-cloud/firebase-setup.md |
| Knowledge Base | 11 files | `MangroveKnowledgeBase/knowledge-base/` -- 00-table-of-contents.md through 10-signals-quick-reference.md |
| KB Server API | 1 file | `MangroveKnowledgeBase/kb_server/API.md` |
| README / TOC | 1 file | `MangroveAdmin/frontend/public/docs/README.md` |

**Total: ~42 markdown source files + 1 OpenAPI spec**

#### What stays internal (auth-gated in MangroveAdmin)

The following remain behind Firebase Auth in the MangroveAdmin portal and are NOT published to Mintlify:

- Admin dashboard (user management, feedback review, system operations)
- AI Copilot chat interface
- Strategy playground (signal evaluation UI)
- User profile and metrics
- API key management
- Subscription and billing management
- Organization management and team settings
- Any internal operational runbooks or credentials documentation

#### Target audience

1. **Developers** -- building integrations with the MangroveAI API. Need API reference, authentication guides, code examples.
2. **API consumers (agents)** -- AI agents using MangroveAI endpoints. Need structured, machine-readable API docs with clear parameter schemas.
3. **Contributors** -- developers contributing to the platform. Need architecture docs, development guides, deployment instructions.
4. **Traders/researchers** -- exploring signals and indicators. Need the knowledge base content (indicators, strategies, glossary).

#### Domain and hosting

- **Primary domain:** `docs.mangrovetechnologies.ai` (or `docs.mangrove.trade` if shorter domain preferred)
- **Hosting:** Mintlify-managed hosting (default). Mintlify deploys from a GitHub repo via webhook on push.
- **Source repo:** Content lives in `MangroveKnowledgeBase` repo, under a `docs/` or `mintlify/` directory. Mintlify watches this directory.
- **Custom domain:** Configured via Mintlify dashboard with CNAME DNS record.

#### Content sources

1. **Markdown files** -- the 30 existing docs from MangroveAdmin's `public/docs/` directory, restructured for Mintlify's `mint.json` navigation
2. **OpenAPI spec** -- exported from MangroveAI's Flask-RESTX API (available at `/api/v1/swagger.json` when the server is running). Mintlify's OpenAPI integration generates an interactive API playground from this spec.
3. **Knowledge base docs** -- the 11 markdown files in `MangroveKnowledgeBase/knowledge-base/`, covering trading concepts, indicators, and glossary
4. **KB Server API docs** -- the `kb_server/API.md` reference for the Knowledge Base FastAPI service

### 1.2 MangroveAdmin Extraction

#### What gets copied to MangroveKnowledgeBase

The entire MangroveAdmin application is copied. This includes:

| Component | File Count | Description |
|-----------|------------|-------------|
| React components | ~47 JSX files | All components in `frontend/src/components/` (admin, auth, chat, common, dashboard, docs, landing, organizations, playground, profile, settings, subscription) |
| API services | 12 JS files | All service clients in `frontend/src/services/api/` |
| Firebase config | 1 JS file | `frontend/src/services/firebase/config.js` |
| Context | 1 JSX file | `frontend/src/context/AuthContext.jsx` |
| Hooks | 4 JS files | `frontend/src/hooks/` (useAuth, useAdmin, useApiKeys, useChat) |
| Utils | 3 JS files | `frontend/src/utils/` (constants, formatters, tokenManager) |
| Constants | 1 JS file | `frontend/src/constants/strategyTypes.js` |
| Styles | 2 CSS files | `frontend/src/styles/` (index.css, tailwind.css) |
| Entry point | 2 JSX files | `frontend/src/main.jsx`, `frontend/src/App.jsx` |
| Build config | 4 files | vite.config.js, tailwind.config.js, postcss.config.js, package.json |
| Static docs | 30 MD files + manifest | `frontend/public/docs/` |
| Docker/Nginx | 3 files | Dockerfile, docker-compose.yml, nginx.conf |
| Env configs | 4 files | `config/` directory (dev.env, prod.env, test.env, local-example.env) |
| Scripts | 1 file | `scripts/deploy.sh` |
| Other | 3 files | README.md, .gitignore, .dockerignore |

**Total: approximately 118 files copied.**

#### What stays in MangroveAI

- The original `src/MangroveAdmin/` directory remains untouched in MangroveAI
- It continues to be the default admin portal (built and served from MangroveAI's docker-compose)
- No files are deleted, moved, or modified in MangroveAI as part of this extraction

#### How the toggle works

Following the established `USE_EXTERNAL_KB` pattern, a new environment variable `USE_EXTERNAL_ADMIN` controls which admin portal MangroveAI uses.

```
USE_EXTERNAL_ADMIN=false   (default -- use MangroveAI's internal MangroveAdmin)
USE_EXTERNAL_ADMIN=true    (use the copy in MangroveKnowledgeBase)
```

**Key difference from USE_EXTERNAL_KB:** The admin portal is a standalone frontend SPA served by Nginx. The "toggle" does not affect Python imports (unlike signals). Instead, it controls which docker-compose service is started and which URL the user accesses:

- `USE_EXTERNAL_ADMIN=false` -- MangroveAI's docker-compose starts `mangrove-admin` service on port 3589 as it does today
- `USE_EXTERNAL_ADMIN=true` -- MangroveAI's docker-compose skips `mangrove-admin`; the admin portal runs from MangroveKnowledgeBase's docker-compose instead

The toggle is implemented via a Docker Compose profile or a conditional in the docker-compose.yml (see Architecture section for details).

#### Relationship between MangroveAdmin and the KB server

Both live in MangroveKnowledgeBase but serve different purposes:

| Component | Port | Purpose | Auth |
|-----------|------|---------|------|
| KB Server (FastAPI) | 8080 | Knowledge base search, glossary, documents API | None (internal) |
| MangroveAdmin (Nginx/React) | 3589 | Developer portal UI (chat, admin, playground, docs) | Firebase Auth + JWT |
| Mintlify | N/A | Public documentation site (hosted externally) | None (public) |

The KB server and MangroveAdmin do not directly communicate. Both connect to MangroveAI's Flask backend independently:
- KB Server is consumed by MangroveAI's backend for RAG retrieval
- MangroveAdmin's React frontend calls MangroveAI's REST API for all data

---

## 2. Specification

### 2.1 Mintlify Site Structure

#### Site configuration (`mint.json`)

Mintlify uses a `mint.json` file at the root of the docs directory to configure navigation, theme, and OpenAPI integration.

```json
{
  "$schema": "https://mintlify.com/schema.json",
  "name": "Mangrove",
  "logo": {
    "dark": "/logo/dark.svg",
    "light": "/logo/light.svg"
  },
  "favicon": "/favicon.svg",
  "colors": {
    "primary": "#0F172A",
    "light": "#38BDF8",
    "dark": "#0F172A"
  },
  "topbarLinks": [
    {
      "name": "Developer Portal",
      "url": "https://app.mangrovedeveloper.ai"
    }
  ],
  "topbarCtaButton": {
    "name": "Sign Up",
    "url": "https://app.mangrovedeveloper.ai/login"
  },
  "tabs": [
    {
      "name": "API Reference",
      "url": "api-reference"
    },
    {
      "name": "Knowledge Base",
      "url": "knowledge-base"
    }
  ],
  "anchors": [
    {
      "name": "GitHub",
      "icon": "github",
      "url": "https://github.com/MangroveTechnologies"
    }
  ],
  "navigation": [
    {
      "group": "Getting Started",
      "pages": [
        "introduction",
        "quickstart",
        "authentication"
      ]
    },
    {
      "group": "Guides",
      "pages": [
        "guides/ai-copilot-workflow",
        "guides/signal-architecture",
        "guides/backtesting-guide",
        "guides/subscription-system",
        "guides/rag-system"
      ]
    },
    {
      "group": "Architecture",
      "pages": [
        "architecture/architectural-patterns",
        "architecture/domain-driven-design"
      ]
    },
    {
      "group": "Development",
      "pages": [
        "development/getting-started",
        "development/api-versioning",
        "development/logging-guide",
        "development/testing-guide",
        "development/commit-standards",
        "development/pull-request-process",
        "development/github-issues"
      ]
    },
    {
      "group": "Deployment",
      "pages": [
        "deployment/overview",
        "deployment/docker-setup",
        "deployment/google-cloud/firebase-setup",
        "deployment/google-cloud/terraform-guide",
        "deployment/google-cloud/secret-manager"
      ]
    },
    {
      "group": "API Reference",
      "pages": [
        "api-reference/overview",
        "api-reference/authentication",
        "api-reference/ai-copilot",
        "api-reference/backtesting",
        "api-reference/crypto-assets",
        "api-reference/execution",
        "api-reference/market-data",
        "api-reference/signals",
        "api-reference/signal-validation",
        "api-reference/strategies"
      ]
    },
    {
      "group": "Knowledge Base",
      "pages": [
        "knowledge-base/overview",
        "knowledge-base/market-foundations",
        "knowledge-base/instruments-market-mechanics",
        "knowledge-base/core-trading-concepts",
        "knowledge-base/strategy-design-modeling",
        "knowledge-base/risk-management",
        "knowledge-base/indicators",
        "knowledge-base/chart-patterns",
        "knowledge-base/quantitative-analysis",
        "knowledge-base/glossary",
        "knowledge-base/signals-quick-reference"
      ]
    },
    {
      "group": "Knowledge Base API",
      "pages": [
        "knowledge-base/api/endpoints"
      ]
    }
  ],
  "openapi": "openapi/mangroveai-spec.json",
  "api": {
    "baseUrl": "https://api.mangrovedeveloper.ai/api/v1",
    "auth": {
      "method": "bearer"
    },
    "playground": {
      "mode": "simple"
    }
  }
}
```

#### Mapping existing markdown files to Mintlify pages

| Source File | Mintlify Page Path | Notes |
|-------------|-------------------|-------|
| `MangroveAdmin/frontend/public/docs/README.md` | `introduction.mdx` | Rewrite as Mintlify intro page with hero section |
| `MangroveAdmin/frontend/public/docs/api/authentication.md` | `authentication.mdx` or `api-reference/authentication.mdx` | Top-level quickstart reference + API reference section |
| `MangroveAdmin/frontend/public/docs/api/ai-copilot.md` | `api-reference/ai-copilot.mdx` | Convert to Mintlify MDX format |
| `MangroveAdmin/frontend/public/docs/api/backtesting.md` | `api-reference/backtesting.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/api/crypto-assets.md` | `api-reference/crypto-assets.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/api/execution.md` | `api-reference/execution.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/api/market-data.md` | `api-reference/market-data.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/api/signals.md` | `api-reference/signals.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/api/signal-validation.md` | `api-reference/signal-validation.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/api/strategies.md` | `api-reference/strategies.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/guides/ai-copilot-workflow.md` | `guides/ai-copilot-workflow.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/guides/signal-architecture.md` | `guides/signal-architecture.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/guides/backtesting-guide.md` | `guides/backtesting-guide.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/guides/subscription-system.md` | `guides/subscription-system.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/guides/rag-system.md` | `guides/rag-system.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/architecture/architectural-patterns.md` | `architecture/architectural-patterns.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/architecture/domain-driven-design.md` | `architecture/domain-driven-design.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/getting-started.md` | `development/getting-started.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/api-versioning.md` | `development/api-versioning.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/logging-guide.md` | `development/logging-guide.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/testing-guide.md` | `development/testing-guide.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/commit-standards.md` | `development/commit-standards.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/pull-request-process.md` | `development/pull-request-process.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/development/github-issues.md` | `development/github-issues.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/deployment/overview.md` | `deployment/overview.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/deployment/README.md` | (merged into overview) | Deduplicate with overview.md |
| `MangroveAdmin/frontend/public/docs/deployment/docker-setup.md` | `deployment/docker-setup.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/deployment/google-cloud/firebase-setup.md` | `deployment/google-cloud/firebase-setup.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/deployment/google-cloud/terraform-guide.md` | `deployment/google-cloud/terraform-guide.mdx` | Convert |
| `MangroveAdmin/frontend/public/docs/deployment/google-cloud/secret-manager.md` | `deployment/google-cloud/secret-manager.mdx` | Convert |
| `knowledge-base/00-table-of-contents.md` | `knowledge-base/overview.mdx` | Rewrite as KB landing page |
| `knowledge-base/01-market-foundations.md` | `knowledge-base/market-foundations.mdx` | Convert |
| `knowledge-base/02-instruments-market-mechanics.md` | `knowledge-base/instruments-market-mechanics.mdx` | Convert |
| `knowledge-base/03-core-trading-concepts.md` | `knowledge-base/core-trading-concepts.mdx` | Convert |
| `knowledge-base/04-strategy-design-modeling.md` | `knowledge-base/strategy-design-modeling.mdx` | Convert |
| `knowledge-base/05-risk-management.md` | `knowledge-base/risk-management.mdx` | Convert |
| `knowledge-base/06-indicators.md` | `knowledge-base/indicators.mdx` | Convert (largest file, 96KB) |
| `knowledge-base/07-chart-patterns.md` | `knowledge-base/chart-patterns.mdx` | Convert |
| `knowledge-base/08-quantitative-analysis.md` | `knowledge-base/quantitative-analysis.mdx` | Convert |
| `knowledge-base/09-glossary.md` | `knowledge-base/glossary.mdx` | Convert |
| `knowledge-base/10-signals-quick-reference.md` | `knowledge-base/signals-quick-reference.mdx` | Convert |
| `kb_server/API.md` | `knowledge-base/api/endpoints.mdx` | Convert |

#### Conversion notes (MD to MDX)

Mintlify uses MDX format. The conversion involves:
1. Adding frontmatter to each file (`title`, `description`, `icon` fields)
2. Replacing raw HTML with Mintlify components (`<CodeGroup>`, `<Card>`, `<Tabs>`, `<Accordion>`)
3. Converting inline code examples to use Mintlify's multi-language `<CodeGroup>` blocks where appropriate
4. Adding `<Note>`, `<Warning>`, `<Tip>` callouts where admonitions exist
5. Ensuring all relative links use Mintlify's page path format (no `.md` extension)

#### OpenAPI spec integration plan

MangroveAI uses Flask-RESTX, which auto-generates an OpenAPI/Swagger spec. The integration:

1. **Export the spec:** Run the MangroveAI server and fetch `GET /api/v1/swagger.json`. Save to `mintlify/openapi/mangroveai-spec.json` in the MangroveKnowledgeBase repo.
2. **Configure Mintlify:** Point `mint.json` at the spec file via the `openapi` field.
3. **Auto-generated pages:** Mintlify generates interactive API playground pages from each endpoint in the spec. These supplement (not replace) the hand-written API guide pages.
4. **Refresh cadence:** Re-export the spec whenever MangroveAI's API changes. This can be automated via CI (see Implementation Plan).

The current spec includes these namespaces (from `__init__.py`):
- `health` -- Health check
- `auth` -- Authentication (login, refresh, profile, switch-org)
- `organizations` -- Organization CRUD and membership
- `users` -- User management
- `admin` -- Admin operations
- `subscriptions` -- Subscription and billing
- `wallets` -- Wallet management
- `ai_copilot` -- AI Copilot chat
- `backtesting` -- Backtest creation and results
- `strategies` -- Strategy CRUD
- `signals` -- Signal listing, evaluation, multi-series evaluation
- `managers` -- Execution management
- `crypto_assets` -- Crypto asset data and risk scoring
- `docs` -- Documentation endpoints
- `batch` -- Batch operations

#### Code example languages

Mintlify supports multi-language code examples via `<CodeGroup>`. Target languages:

1. **Python** (primary) -- requests library and httpx examples
2. **cURL** -- universal baseline
3. **JavaScript/TypeScript** -- fetch and axios examples
4. **MCP tool call** (custom) -- show how an AI agent would invoke the endpoint via MCP (future, when MCP server is built)

#### Search, versioning, changelog requirements

- **Search:** Mintlify includes built-in full-text search across all pages. No additional configuration needed. This replaces MangroveAdmin's complete lack of search.
- **Versioning:** Not needed initially. MangroveAI has a single API version (`v1`). When `v2` is introduced, Mintlify supports version tabs in `mint.json`.
- **Changelog:** Add a `changelog/` section in Mintlify navigation. Start with a single "Initial Release" entry. Future releases get dated entries. Mintlify supports `<Update>` components for changelog formatting.

### 2.2 MangroveAdmin in MangroveKnowledgeBase

#### Directory structure

```
MangroveKnowledgeBase/
|-- mangrove_kb/     # (existing) Python signals + indicators package
|-- kb_server/                   # (existing) FastAPI KB service
|-- knowledge-base/              # (existing) 11 markdown files for KB
|-- tests/                       # (existing) Docstring parser tests
|-- data/                        # (existing) Sample OHLCV data
|-- notebooks/                   # (existing) Signal explorer notebook
|-- findings/                    # (existing) Analysis documents
|-- admin/                       # (NEW) MangroveAdmin React app
|   |-- frontend/
|   |   |-- src/
|   |   |   |-- components/
|   |   |   |   |-- admin/       # AdminPage, UserManagement, UsersTable, etc.
|   |   |   |   |-- auth/        # LoginPage, ProtectedRoute
|   |   |   |   |-- chat/        # ChatPage, ChatWindow, MessageBubble, etc.
|   |   |   |   |-- common/      # Layout, Navbar, Sidebar, ErrorBoundary, etc.
|   |   |   |   |-- dashboard/   # DeveloperDashboardPage
|   |   |   |   |-- docs/        # DocumentationPage, MarkdownRenderer, etc.
|   |   |   |   |-- landing/     # LandingPage
|   |   |   |   |-- organizations/ # OrganizationSettings, TeamManagement, etc.
|   |   |   |   |-- playground/  # StrategyPlayground, SignalSelector, etc.
|   |   |   |   |-- profile/     # ProfilePage, MetricsCard, etc.
|   |   |   |   |-- settings/    # SettingsPage, ApiKeyList, etc.
|   |   |   |   |-- subscription/ # SubscriptionStatus, UsageProgressBar, etc.
|   |   |   |-- services/
|   |   |   |   |-- api/         # client.js, authService.js, chatService.js, etc.
|   |   |   |   |-- firebase/    # config.js
|   |   |   |-- context/         # AuthContext.jsx
|   |   |   |-- hooks/           # useAuth.js, useAdmin.js, useApiKeys.js, useChat.js
|   |   |   |-- utils/           # constants.js, formatters.js, tokenManager.js
|   |   |   |-- constants/       # strategyTypes.js
|   |   |   |-- styles/          # index.css, tailwind.css
|   |   |   |-- App.jsx
|   |   |   |-- main.jsx
|   |   |-- public/
|   |   |   |-- docs/            # 30 markdown files + manifest.json
|   |   |-- package.json
|   |   |-- vite.config.js
|   |   |-- tailwind.config.js
|   |   |-- postcss.config.js
|   |   |-- env-example.txt
|   |-- config/
|   |   |-- dev.env
|   |   |-- prod.env
|   |   |-- test.env
|   |   |-- local-example.env
|   |-- scripts/
|   |   |-- deploy.sh
|   |-- Dockerfile
|   |-- docker-compose.yml       # Standalone admin docker-compose (for local dev)
|   |-- nginx.conf
|   |-- .gitignore
|   |-- .dockerignore
|   |-- README.md
|-- mintlify/                    # (NEW) Mintlify docs source
|   |-- mint.json
|   |-- introduction.mdx
|   |-- quickstart.mdx
|   |-- authentication.mdx
|   |-- api-reference/
|   |-- guides/
|   |-- architecture/
|   |-- development/
|   |-- deployment/
|   |-- knowledge-base/
|   |-- openapi/
|   |   |-- mangroveai-spec.json
|   |-- logo/
|   |-- images/
|-- docker-compose.yml           # (UPDATED) Add admin service
|-- Dockerfile                   # (existing) For tests/lint
|-- pyproject.toml               # (existing)
|-- README.md                    # (existing, update to mention admin + mintlify)
|-- STATUS.md                    # (existing)
```

#### Build and deployment configuration

The MangroveAdmin copy uses the same build pipeline as the original:

1. **Dockerfile:** Multi-stage build (Node 18 build stage + Nginx serve stage). Copied as-is from `MangroveAI/src/MangroveAdmin/Dockerfile`.
2. **Nginx:** Same `nginx.conf` for SPA fallback routing and static asset serving.
3. **Vite config:** Same `vite.config.js` (port 3589, React plugin, sourcemaps).
4. **Environment selection:** The `scripts/deploy.sh` copies the appropriate env file (dev/prod/test) to `frontend/.env` before build. This mechanism is preserved.

**Build command (from `admin/` directory):**
```bash
cd frontend && npm install && npm run build
```

**Docker build (from `admin/` directory):**
```bash
docker build -t mangrove-admin:latest .
```

#### API connection configuration

MangroveAdmin connects to MangroveAI's Flask backend via two environment variables set at build time (Vite inlines them during build):

```env
VITE_BACKEND_URL=http://localhost:5001      # MangroveAI backend URL
VITE_API_BASE_ROUTE=/api/v1                 # API route prefix
```

These are resolved in `frontend/src/utils/constants.js`:
```javascript
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5001';
const API_BASE_ROUTE = import.meta.env.VITE_API_BASE_ROUTE || '/api/v1';
export const API_BASE_URL = `${backendUrl}${apiRoute}`;
```

When running from MangroveKnowledgeBase, these values point to the same MangroveAI backend. The admin portal does not need its own backend -- it talks to MangroveAI's existing REST API.

**Environment configs to copy:**

| Config File | `VITE_BACKEND_URL` | Firebase Project |
|------------|-------------------|-----------------|
| `local-example.env` | `http://localhost:5001` | `mangroveai-dev` |
| `dev.env` | `https://devapi.mangrove.trade` | `mangroveai-dev` |
| `prod.env` | `https://api.mangrovedeveloper.ai` | `mangroveai-prod` |
| `test.env` | (check file) | (check file) |

#### Auth flow

The auth flow is identical whether MangroveAdmin runs from MangroveAI or MangroveKnowledgeBase:

```
User -> MangroveAdmin (React SPA)
         |
         |--(1)-- Firebase Google OAuth popup
         |         |
         |         +--(2)-- Firebase returns ID token
         |
         |--(3)-- POST /api/v1/auth/login { firebase_token }
         |         |
         |         +--(4)-- MangroveAI backend verifies token, returns JWT
         |
         |--(5)-- All subsequent API calls use JWT Bearer token
         |
         |--(6)-- On 401, POST /api/v1/auth/refresh { refresh_token }
```

Firebase Auth configuration (API keys, auth domains, project IDs) is baked into the build via `VITE_FIREBASE_*` environment variables. No runtime Firebase server is needed -- Firebase JS SDK talks directly to Google's servers.

**Important:** When deploying the external admin portal, the Firebase authorized domains list must include the new domain. Currently authorized:
- `localhost`
- Whatever Cloud Run domains are currently configured

If the external admin portal runs on a different domain or port, that domain must be added to the Firebase Console's authorized domains for both `mangroveai-dev` and `mangroveai-prod` projects.

---

## 3. Architecture

### 3.1 Repository Layout

After implementation, MangroveKnowledgeBase contains four logical components:

```
MangroveKnowledgeBase
|
+-- mangrove_kb/   [Python package: signals + indicators]
|     Published to PyPI or installed via git
|     Consumed by MangroveAI as pip dependency
|
+-- kb_server/                 [FastAPI service: knowledge base search]
|     Docker container on port 8080
|     Consumed by MangroveAI backend for RAG
|
+-- admin/                     [React SPA: developer portal]
|     Docker container (Nginx) on port 3589
|     Consumed by end users (developers, admins)
|     Talks to MangroveAI backend REST API
|
+-- mintlify/                  [Static docs site]
|     Deployed to Mintlify hosting (external)
|     Consumed by anyone (public)
|     Contains OpenAPI spec + markdown content
|
+-- knowledge-base/            [Markdown source files]
      Mounted into kb_server container
      Also referenced by mintlify docs
```

### 3.2 Service Topology

#### Production deployment

```
                                    Internet
                                       |
                    +------------------+------------------+
                    |                  |                  |
           docs.mangrove...     app.mangrove...     api.mangrove...
            (Mintlify CDN)       (Cloud Run)         (Cloud Run)
                    |                  |                  |
               Public docs     MangroveAdmin        MangroveAI
               (no auth)       (Firebase Auth)    (Flask backend)
                                       |                  |
                                       +--------+---------+
                                                |
                                          REST API calls
                                          (Bearer JWT)
                                                |
                                       +--------+---------+
                                       |                  |
                                   PostgreSQL        KB Server
                                   (pgvector)        (FastAPI)
                                   Cloud SQL          port 8080
```

#### Local development

```
localhost:3589  ------>  MangroveAdmin (Nginx or Vite dev server)
                              |
                              | REST API calls (Bearer JWT)
                              v
localhost:5001  ------>  MangroveAI (Flask)
                              |
                    +---------+---------+
                    |                   |
               PostgreSQL          KB Server
               port 5432          port 8080
               (pgvector)         (FastAPI)
```

When `USE_EXTERNAL_ADMIN=true`, the MangroveAdmin container runs from MangroveKnowledgeBase's docker-compose instead of MangroveAI's docker-compose. The user's browser still connects to `localhost:3589` either way.

### 3.3 Toggle Mechanism

#### Design principles

1. MangroveAI's internal MangroveAdmin is the **default** (same pattern as signals)
2. The toggle is an **environment variable** (`USE_EXTERNAL_ADMIN`)
3. Only one admin portal runs at a time on port 3589
4. The backend (MangroveAI Flask) is **unaware** of which admin portal is running -- it serves the same REST API regardless

#### Implementation approach: Docker Compose profiles

Docker Compose profiles are the cleanest way to conditionally start services. MangroveAI's `docker-compose.yml` gains a profile on the admin service:

```yaml
# MangroveAI/docker-compose.yml (modified)
services:
  mangrove-admin:
    profiles: ["internal-admin"]    # Only starts when profile is active
    container_name: mangrove-admin
    build:
      context: ./src/MangroveAdmin
      dockerfile: Dockerfile
    ports:
      - "${ADMIN_PORT:-3589}:80"
    depends_on:
      mangrove-app:
        condition: service_healthy
    # ... rest unchanged
```

MangroveKnowledgeBase's `docker-compose.yml` adds the admin service with its own profile:

```yaml
# MangroveKnowledgeBase/docker-compose.yml (modified)
services:
  knowledge-base:
    # ... existing KB service unchanged

  mangrove-admin:
    profiles: ["external-admin"]    # Only starts when profile is active
    container_name: mangrove-admin
    build:
      context: ./admin
      dockerfile: Dockerfile
    ports:
      - "${ADMIN_PORT:-3589}:80"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - mangrove-network
```

**Usage:**

```bash
# Default: use internal admin (from MangroveAI)
cd MangroveAI
docker compose --profile internal-admin up -d

# Alternative: use external admin (from MangroveKnowledgeBase)
cd MangroveAI
docker compose up -d   # starts postgres + mangrove-app only (no profile = no admin)

cd ../MangroveKnowledgeBase
docker compose --profile external-admin up -d   # starts kb + admin
```

**Simpler alternative (no profiles):** Keep MangroveAI's docker-compose unchanged. When using external admin, just stop the internal one and start the external one:

```bash
# Switch to external admin
docker compose -f MangroveAI/docker-compose.yml stop mangrove-admin
docker compose -f MangroveKnowledgeBase/docker-compose.yml up -d mangrove-admin
```

Both approaches work. The profiles approach is cleaner for documentation and scripts.

#### Helper script

A helper script in MangroveAI (e.g., `scripts/toggle-admin.sh`) wraps the toggle:

```bash
#!/bin/bash
# Usage: ./toggle-admin.sh [internal|external]

if [ "$1" = "external" ]; then
    docker compose stop mangrove-admin 2>/dev/null
    docker compose -f ../MangroveKnowledgeBase/docker-compose.yml up -d mangrove-admin
    echo "Admin portal: MangroveKnowledgeBase (external)"
elif [ "$1" = "internal" ]; then
    docker compose -f ../MangroveKnowledgeBase/docker-compose.yml stop mangrove-admin 2>/dev/null
    docker compose up -d mangrove-admin
    echo "Admin portal: MangroveAI (internal)"
else
    echo "Usage: $0 [internal|external]"
fi
```

### 3.4 Docker Compose Services

#### MangroveKnowledgeBase docker-compose.yml (updated)

```yaml
services:
  # Existing services
  test:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["pytest", "tests/", "-v"]

  lint:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["flake8", "mangrove_kb/", "--max-line-length=120", "--ignore=E501,W503"]

  knowledge-base:
    build:
      context: .
      dockerfile: kb_server/Dockerfile
    container_name: mkb-knowledge-base
    ports:
      - "${KB_PORT:-8080}:8080"
    volumes:
      - ./knowledge-base:/kb:ro
      - kb-data:/app/kb_server/data
    environment:
      - KB_SERVER_KB_PATH=/kb
      - KB_SERVER_DB_PATH=/app/kb_server/data/knowledge.db
      - KB_SERVER_PORT=8080
      - KB_SERVER_DEBUG=${KB_DEBUG:-false}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - mangrove-network

  # New service
  mangrove-admin:
    build:
      context: ./admin
      dockerfile: Dockerfile
    container_name: mkb-mangrove-admin
    ports:
      - "${ADMIN_PORT:-3589}:80"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - mangrove-network

networks:
  mangrove-network:
    name: mangrove-network
    external: true

volumes:
  kb-data:
    name: mangrove-kb-data
```

Note: The `mangrove-admin` container name is `mkb-mangrove-admin` (prefixed with `mkb-`) to avoid collision with MangroveAI's `mangrove-admin` container. However, only one should run at a time on port 3589.

#### Mintlify dev server (optional, for local preview)

Mintlify provides a CLI for local preview:

```bash
cd mintlify
npx mintlify dev
# Opens at http://localhost:3000
```

This is a development-only tool and does not need a Docker service. However, if desired, it can be added as a compose service:

```yaml
  mintlify-dev:
    image: node:18-alpine
    working_dir: /docs
    volumes:
      - ./mintlify:/docs
    ports:
      - "3000:3000"
    command: ["npx", "mintlify", "dev", "--host", "0.0.0.0"]
    profiles: ["mintlify-dev"]
```

### 3.5 Shared network and service discovery

All services connect via the `mangrove-network` Docker bridge network. Service discovery by container name:

| Container Name | Service | Accessible At |
|---------------|---------|---------------|
| `mangrove-app` | MangroveAI Flask backend | `http://mangrove-app:5001` |
| `postgres` | PostgreSQL + pgvector | `postgres:5432` |
| `mkb-knowledge-base` | KB FastAPI server | `http://mkb-knowledge-base:8080` |
| `mkb-mangrove-admin` | Admin portal (external) | `http://mkb-mangrove-admin:80` (port 3589 on host) |
| `mangrove-admin` | Admin portal (internal) | `http://mangrove-admin:80` (port 3589 on host) |

**Network creation order:** The `mangrove-network` is defined as `external: true` in MangroveKnowledgeBase's compose file, meaning it must be created before starting services. MangroveAI's compose file creates the network (`driver: bridge`). Therefore, MangroveAI's docker-compose must start first (or the network must be pre-created with `docker network create mangrove-network`).

---

## 4. Security

### 4.1 Public docs (Mintlify) vs auth-gated admin portal

**Clear separation:**

| Surface | Auth | Content | Risk |
|---------|------|---------|------|
| Mintlify (docs.mangrove...) | None (public) | API docs, guides, knowledge base, architecture | Low -- all content is meant to be public |
| MangroveAdmin (app.mangrove...) | Firebase Auth + JWT | User data, chat, strategies, backtests, admin panel | High -- contains PII and financial data |
| MangroveAI API (api.mangrove...) | JWT Bearer token | All operations | High -- must validate every request |

**Key principle:** Mintlify never exposes user data, operational secrets, or authenticated functionality. It only shows documentation that is explicitly placed in the `mintlify/` directory.

### 4.2 CORS configuration

MangroveAI's Flask backend uses `flask-cors`. When the admin portal runs from MangroveKnowledgeBase, the origin may differ if deployed to a different domain.

**Current CORS setup:** Needs to be verified, but likely allows all origins in development. For production:

```python
# MangroveAI config.py
CORS_ORIGINS = [
    "http://localhost:3589",           # Local admin (Vite dev or Docker)
    "https://app.mangrovedeveloper.ai", # Production admin portal
    "https://devapp.mangrove.trade",    # Dev admin portal
    # Add external admin domain if different
]
```

**Action required:** If the external admin portal runs on a domain not already in the CORS allowlist, add it. In local Docker development, both internal and external admin use `http://localhost:3589`, so no CORS change is needed locally.

### 4.3 Firebase Auth token flow when admin is external

No change to the token flow. The Firebase JS SDK in the React app communicates directly with Firebase's servers (Google infrastructure), not with MangroveAI. The flow:

1. React app loads Firebase SDK with the project's config (`VITE_FIREBASE_*` env vars)
2. Firebase SDK opens Google OAuth popup directly to Google's auth servers
3. Google returns auth tokens to the Firebase SDK in the browser
4. React app sends the Firebase ID token to MangroveAI's `/api/v1/auth/login`
5. MangroveAI backend verifies the Firebase token using `firebase-admin` SDK
6. MangroveAI returns its own JWT (access + refresh tokens)
7. All subsequent API calls use MangroveAI's JWT

**The only requirement:** The domain where MangroveAdmin is served must be in Firebase Console's "Authorized domains" list. This is configured per Firebase project (`mangroveai-dev` and `mangroveai-prod`).

### 4.4 API key management in external admin portal

API keys are managed via MangroveAI's backend (`/api/v1/auth/api-keys/*` endpoints). The admin portal (whether internal or external) is just a UI that calls these endpoints. No keys are stored in the admin portal itself.

**Sensitive data in the admin portal:**

| Data | Where Stored | Risk |
|------|-------------|------|
| Firebase config (API key, project ID) | `.env` file, baked into build | Low -- Firebase API keys are client-side by design |
| JWT access token | Browser `localStorage` | Medium -- standard for SPAs, protected by HTTPS |
| JWT refresh token | Browser `localStorage` | Medium -- same |
| User profile data | React state (memory only) | Low -- not persisted |
| API keys (displayed to user) | Shown once on creation, then masked | Low -- backend never returns full keys after creation |

**No secrets are stored in the MangroveKnowledgeBase repo.** The `config/*.env` files contain:
- Firebase API keys (client-safe, meant to be public per Google's design)
- Backend URLs (not secrets)

However, the Firebase config values differ between dev and prod. The `prod.env` contains the production Firebase project config. While these are not "secrets" in the traditional sense (Firebase is designed for client-side config to be public), they do identify the production Firebase project. Consider whether to include `prod.env` in the public repo or only include `local-example.env` and `dev.env`.

**Recommendation:** Only include `local-example.env` in the public repo's `admin/config/`. Keep `dev.env` and `prod.env` out of version control (add to `.gitignore`) and document them as "copy from MangroveAI or configure manually." This reduces the risk surface even though Firebase API keys are client-safe.

### 4.5 Additional security considerations

1. **The `admin/` directory in a public repo** contains the full admin portal source code including admin dashboard views. This is not a security risk because:
   - Admin endpoints are protected server-side by role checks (`is_mgmt`)
   - The source code is just React UI -- no server-side logic or secrets
   - Open-source admin interfaces are common practice

2. **Content Security Policy (CSP):** The Nginx config should include a CSP header that restricts script sources. Current nginx.conf does not have one. Consider adding:
   ```
   add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://apis.google.com; connect-src 'self' https://*.firebaseapp.com https://api.mangrovedeveloper.ai;" always;
   ```

3. **Rate limiting:** Not handled by the admin portal (it is a static SPA). MangroveAI's backend should have rate limiting on auth endpoints.

---

## 5. Implementation Plan

### Overview

Three phases, ordered by dependency and complexity:

| Phase | Scope | Effort Estimate | Dependencies |
|-------|-------|-----------------|--------------|
| Phase 1 | Mintlify setup with existing content | 1-2 days | None |
| Phase 2 | MangroveAdmin copy to MangroveKnowledgeBase | 1 day | None (independent of Phase 1) |
| Phase 3 | Toggle infrastructure in MangroveAI | 0.5 days | Phase 2 complete |

### Phase 1: Mintlify setup with existing content

**Goal:** Public docs site live at `docs.mangrovetechnologies.ai` with all 42 markdown files and the OpenAPI spec.

#### Step 1.1: Mintlify project initialization
- Create `mintlify/` directory in MangroveKnowledgeBase
- Install Mintlify CLI: `npx mintlify@latest init`
- Configure `mint.json` with navigation structure, colors, logo, and OpenAPI pointer
- Verify local preview works: `npx mintlify dev`

#### Step 1.2: Export and include OpenAPI spec
- Start MangroveAI locally: `docker compose up -d mangrove-app`
- Wait for health check to pass
- Fetch spec: `curl http://localhost:5001/api/v1/swagger.json > mintlify/openapi/mangroveai-spec.json`
- Validate the spec is complete (all namespaces present)
- Add `openapi` field to `mint.json`

#### Step 1.3: Convert MangroveAdmin docs (30 files)
- Copy all 30 markdown files from `MangroveAI/src/MangroveAdmin/frontend/public/docs/`
- Rename `.md` to `.mdx` and add Mintlify frontmatter to each
- Restructure into Mintlify directory layout (`api-reference/`, `guides/`, etc.)
- Replace raw HTML and inline styles with Mintlify components
- Fix internal links to use Mintlify page paths
- Merge `deployment/README.md` into `deployment/overview.mdx` (deduplicate)

#### Step 1.4: Convert knowledge-base docs (11 files)
- Copy the 11 files from `MangroveKnowledgeBase/knowledge-base/`
- Rename to descriptive slugs (e.g., `01-market-foundations.md` becomes `market-foundations.mdx`)
- Add Mintlify frontmatter
- Fix internal cross-references between knowledge base documents

#### Step 1.5: Convert KB Server API doc (1 file)
- Copy `kb_server/API.md` to `mintlify/knowledge-base/api/endpoints.mdx`
- Add frontmatter and convert to MDX format

#### Step 1.6: Create new pages
- Write `introduction.mdx` -- hero page with overview of Mangrove platform
- Write `quickstart.mdx` -- 5-minute guide to getting an API key and making first call
- Write `authentication.mdx` -- top-level auth guide (complements the API-level auth doc)

#### Step 1.7: Deploy to Mintlify
- Create Mintlify account and project at mintlify.com
- Connect the MangroveKnowledgeBase GitHub repo
- Configure the docs directory as `mintlify/`
- Set up custom domain `docs.mangrovetechnologies.ai` (CNAME record)
- Verify deployment succeeds on push to `main`
- Test search, navigation, API playground

#### Step 1.8: CI automation for OpenAPI spec refresh
- Add a GitHub Actions workflow that:
  1. Checks if the OpenAPI spec has changed (by comparing against the committed spec)
  2. If changed, commits the updated spec and triggers a Mintlify rebuild
- This can be a manual trigger initially, automated later

### Phase 2: MangroveAdmin copy to MangroveKnowledgeBase

**Goal:** Complete copy of MangroveAdmin in `MangroveKnowledgeBase/admin/`, buildable and runnable from there.

#### Step 2.1: Copy the files
- Create `admin/` directory in MangroveKnowledgeBase
- Copy the entire `MangroveAI/src/MangroveAdmin/` directory tree into it
- Verify file count matches (~118 files)
- Exclude `node_modules/`, `dist/`, `.env` (only include `local-example.env` from config)

#### Step 2.2: Adjust .gitignore
- Update MangroveKnowledgeBase's `.gitignore` to include:
  ```
  admin/frontend/node_modules/
  admin/frontend/dist/
  admin/frontend/.env
  ```
- Decide whether to include `config/dev.env` and `config/prod.env` in the public repo (see Security section recommendation: exclude them)

#### Step 2.3: Update container naming
- In `admin/docker-compose.yml`, change `container_name` to `mkb-mangrove-admin` to avoid collision
- In `admin/Dockerfile`, no changes needed (it is self-contained)

#### Step 2.4: Verify standalone build
```bash
cd MangroveKnowledgeBase/admin
cp config/local-example.env frontend/.env
cd frontend
npm install
npm run build   # Verify build succeeds
```

#### Step 2.5: Verify Docker build
```bash
cd MangroveKnowledgeBase/admin
docker build -t mkb-mangrove-admin:latest .
docker run -p 3589:80 mkb-mangrove-admin:latest
# Verify http://localhost:3589 loads the landing page
```

#### Step 2.6: Add admin service to MangroveKnowledgeBase docker-compose
- Add the `mangrove-admin` service definition (as specified in section 3.4)
- Verify `docker compose up -d mangrove-admin` works from MangroveKnowledgeBase root

#### Step 2.7: Update MangroveKnowledgeBase README and STATUS
- Add MangroveAdmin to the README's component list
- Update STATUS.md with the new component
- Add build/run instructions for the admin portal

### Phase 3: Toggle infrastructure in MangroveAI

**Goal:** MangroveAI can switch between internal and external admin via environment variable or docker-compose profile.

#### Step 3.1: Add Docker Compose profile to MangroveAI
- Modify `MangroveAI/docker-compose.yml` to add `profiles: ["internal-admin"]` to the `mangrove-admin` service
- Verify `docker compose --profile internal-admin up -d` starts all services including admin
- Verify `docker compose up -d` starts everything except admin (default behavior preserved for backward compatibility)

**Alternative (simpler):** Instead of profiles, use the existing `docker compose up -d mangrove-app postgres` to start without admin, and `docker compose up -d` for everything. This requires no changes to the compose file. The "toggle" is simply which compose file you run admin from.

#### Step 3.2: Create toggle helper script
- Add `MangroveAI/scripts/toggle-admin.sh` (as described in section 3.3)
- Make it executable
- Document usage in MangroveAI README

#### Step 3.3: Document the toggle
- Update MangroveAI's README with instructions for switching between internal and external admin
- Update MangroveKnowledgeBase's README with instructions for running the external admin
- Add a note to MangroveAdmin's README in both locations explaining the dual-location setup

#### Step 3.4: Test both modes
- Start MangroveAI with internal admin, verify all features work
- Stop internal admin, start external admin from MangroveKnowledgeBase, verify all features work
- Verify no port conflicts
- Verify both portals connect to the same MangroveAI backend
- Verify Firebase auth works from both
- Test the toggle script

### Dependencies and Prerequisites

| Prerequisite | Needed For | Current Status |
|-------------|-----------|----------------|
| MangroveKnowledgeBase pushed to GitHub | Phase 1 (Mintlify connects to GitHub) | Exists but uncommitted changes pending |
| MangroveAI backend running | Phase 1 (OpenAPI spec export), Phase 2 (testing admin) | Works locally via docker-compose |
| Mintlify account | Phase 1 | Not created yet |
| Custom domain DNS access | Phase 1 (docs.mangrovetechnologies.ai) | Assumed available |
| `mangrove-network` Docker network | Phase 2, Phase 3 | Created by MangroveAI docker-compose |
| Firebase authorized domains updated | Phase 3 (if external admin uses different domain) | Only needed for non-localhost deployments |

### Testing Strategy

#### Phase 1 (Mintlify) testing
- [ ] Local preview renders all pages correctly (`npx mintlify dev`)
- [ ] OpenAPI spec generates interactive playground pages
- [ ] All 42 markdown files render without errors
- [ ] Internal links between pages resolve correctly
- [ ] Search returns relevant results for key terms (e.g., "RSI", "backtest", "authentication")
- [ ] Custom domain resolves and serves HTTPS
- [ ] Mobile layout is responsive

#### Phase 2 (MangroveAdmin copy) testing
- [ ] `npm install` succeeds with no dependency errors
- [ ] `npm run build` produces a `dist/` directory
- [ ] Docker build completes successfully
- [ ] Landing page loads at `http://localhost:3589`
- [ ] Login flow works (Firebase Google OAuth)
- [ ] Chat page connects to MangroveAI backend and sends messages
- [ ] Admin dashboard loads (for management users)
- [ ] Documentation page renders markdown files
- [ ] Strategy playground evaluates signals
- [ ] Settings page manages API keys
- [ ] All 14 routes are accessible and render correctly

#### Phase 3 (Toggle) testing
- [ ] `docker compose --profile internal-admin up -d` starts admin from MangroveAI
- [ ] `docker compose up -d` (no profile) does NOT start admin from MangroveAI
- [ ] MangroveKnowledgeBase's admin starts on port 3589 when internal is stopped
- [ ] Port 3589 is not occupied by two services simultaneously
- [ ] Toggle script switches cleanly in both directions
- [ ] After switching, browser reloads work (no stale cache issues)
- [ ] Backend logs show requests from whichever admin portal is active

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MangroveAdmin has undocumented backend dependencies | Medium | Build succeeds but features break | Test every feature after copy, not just build |
| Knowledge base files are too large for Mintlify (06-indicators.md is 96KB) | Low | Page loads slowly or fails | Split into sub-pages if needed |
| Firebase authorized domains block external admin | Medium | Login fails from external admin | Add domain before testing, document in runbook |
| Port 3589 conflict between internal and external admin | Medium | One service fails to start | Toggle script ensures only one runs; container naming prevents overlap |
| `prod.env` Firebase config exposed in public repo | Low | Minimal security impact (client-safe keys) but reveals project IDs | Exclude prod.env from public repo per recommendation |
| Mintlify free tier limits | Low | Might hit page or build limits | Mintlify's free tier supports most use cases; upgrade if needed |
| Docker network not created before MangroveKnowledgeBase starts | Medium | Services fail to connect | Document startup order or add `docker network create` to toggle script |

---

## Appendix A: File Inventory -- MangroveAdmin

Full list of files to copy (118 files, excluding node_modules and dist):

**Root (5 files):**
- Dockerfile
- docker-compose.yml
- nginx.conf
- .gitignore
- .dockerignore
- README.md

**Config (4 files):**
- config/dev.env
- config/prod.env
- config/test.env
- config/local-example.env

**Scripts (1 file):**
- scripts/deploy.sh

**Frontend root (6 files):**
- frontend/package.json
- frontend/package-lock.json
- frontend/vite.config.js
- frontend/tailwind.config.js
- frontend/postcss.config.js
- frontend/env-example.txt

**Frontend source -- components (47 JSX files):**
- admin/: AdminPage, UserManagement, CreateEnterpriseOrgModal, UserDetailView, SubscriptionManagement, EnterpriseOrgSuccessModal, UsersTable, SystemManagement (8)
- auth/: ProtectedRoute, LoginPage (2)
- chat/: ChatPage, ConversationItem, AssetSelector, StrategyConfigModal, ChatInput, ConversationList, MessageBubble, SurveyModal, ChatWindow, QuickActions, ConversationDebugPanel (11)
- common/: Layout, FeedbackModal, InvitationBanner, Navbar, Breadcrumbs, Sidebar, LoadingSpinner, ConfirmDialog, BrandLogo, ErrorBoundary, DevEnvironmentModal (11)
- dashboard/: DeveloperDashboardPage (1)
- docs/: DocumentationPage, MarkdownRenderer, SwaggerViewer, DocsSidebar (4)
- landing/: LandingPage (1)
- organizations/: InviteMemberModal, OrganizationSettings, TeamManagement (3)
- playground/: SignalMultiselect, IndicatorMultiselect, ChartControls, SignalSelector, ParameterSidebar, PlaygroundChart, StrategyPlayground, SignalLegend, SignalParameterPanel (9 -- note: counted from file listing, some may be unused)
- profile/: MetricsCard, StrategiesTable, ProfilePage, BacktestsTable (4)
- settings/: BillingSettings, SettingsPage, ApiKeyList, CreateApiKeyModal, ApiKeyTable (5)
- subscription/: SubscriptionStatus, UsageProgressBar, ResourceUtilization, UsageLimitWarning (4)

**Frontend source -- services (13 JS files):**
- api/: client.js, docsService.js, allowlistService.js, authService.js, subscriptionService.js, chatService.js, organizationService.js, playgroundService.js, apiKeyService.js, userService.js, adminService.js, cryptoAssetsService.js (12)
- firebase/: config.js (1)

**Frontend source -- other (12 files):**
- context/AuthContext.jsx (1)
- hooks/: useChat.js, useApiKeys.js, useAdmin.js, useAuth.js (4)
- utils/: constants.js, formatters.js, tokenManager.js (3)
- constants/: strategyTypes.js (1)
- styles/: index.css, tailwind.css (2)
- App.jsx (1)
- main.jsx (1)

**Frontend static docs (31 files):**
- public/docs/manifest.json (1)
- public/docs/*.md (30 markdown files across api/, architecture/, deployment/, development/, guides/, and root)

## Appendix B: MangroveAdmin Routes

| Route | Component | Auth Required | Description |
|-------|-----------|---------------|-------------|
| `/` | LandingPage | No | Public landing page |
| `/login` | LoginPage | No | Google SSO login |
| `/dashboard` | DeveloperDashboardPage | Yes | Main developer dashboard |
| `/chat` | ChatPage | Yes | AI Copilot chat |
| `/chat/:conversationId` | ChatPage | Yes | Chat with specific conversation |
| `/settings` | SettingsPage | Yes | API key management |
| `/profile` | ProfilePage | Yes | User metrics and data |
| `/admin` | AdminPage | Yes (mgmt only) | Admin dashboard |
| `/settings/organization` | OrganizationSettings | Yes | Org settings |
| `/settings/team` | TeamManagement | Yes | Team member management |
| `/settings/billing` | BillingSettings | Yes | Subscription and billing |
| `/playground` | StrategyPlayground | Yes | Signal testing playground |
| `/docs/*` | DocumentationPage | Yes | Documentation viewer |
| `*` (fallback) | DefaultRoute | -- | Redirects to /dashboard or /login |

## Appendix C: Existing Docs Manifest vs Actual Files

The current `manifest.json` lists 9 documents. The `public/docs/` directory contains 30 markdown files. The 21 files NOT in the manifest are:

**API docs not in manifest (4):**
- authentication.md
- signals.md
- signal-validation.md
- (note: the Swagger iframe route `/docs/api` is hardcoded, not from manifest)

**Architecture docs not in manifest (2):**
- architectural-patterns.md
- domain-driven-design.md

**Deployment docs not in manifest (5):**
- overview.md
- README.md
- docker-setup.md
- google-cloud/secret-manager.md
- google-cloud/terraform-guide.md
- google-cloud/firebase-setup.md

**Development docs not in manifest (7):**
- logging-guide.md
- api-versioning.md
- getting-started.md
- commit-standards.md
- testing-guide.md
- pull-request-process.md
- github-issues.md

**Guides not in manifest (2):**
- subscription-system.md
- backtesting-guide.md
- ai-copilot-workflow.md

All 30 files will be included in the Mintlify site, fixing the visibility gap entirely.
