# Docs-site search — why it's dead, and how to turn it on

**Status:** broken in production for everyone, signed in or not (tracked in issue #85).
The search box at `docs.mangrovedeveloper.ai` renders but returns no results — it has no
search backend. This is an **architecture / provisioning** gap, not a content bug.

## Root cause

The docs site is **self-hosted**, not deployed on Mintlify's platform. `Dockerfile.docs`
runs `mintlify dev` only to download Mintlify's pre-built Next.js client
(`~/.mintlify/mint/apps/client`), then serves that client statically via nginx + the Next.js
standalone server. `build-docs.yml` builds this `mangrove-ai-docs` image; MangroveAI deploys
it to Cloud Run behind `docs.mangrovedeveloper.ai`.

Mintlify's **search/assistant is a hosted feature** — it needs a Mintlify cloud backend (a
Trieve vector DB) **with the site's content indexed into it**. That backend is not part of the
self-hosted client bundle, and the self-hosted build never indexes content into Mintlify's
cloud. So the search box has nothing to call.

Reverse-engineering the pinned client (`mintlify@4.2.414`, client bundle `0.0.2662`) shows
exactly where the box tries to go — two routes, both pointing at an unset backend:

| Surface | Client route | Forwards to | Env it needs |
|---|---|---|---|
| Public search box (no login) | `POST /_mintlify/api-public/search/<subdomain>` | `${API_ENDPOINT:-http://localhost:5000}/api/end-user-public/<subdomain>/search` | `API_ENDPOINT` (+ optional `ADMIN_TOKEN`) |
| "Ask a question" assistant | `POST /_mintlify/api/search` | `${NEXT_PUBLIC_AI_MESSAGE_HOST}/api/end-user/search` | `NEXT_PUBLIC_AI_MESSAGE_HOST`, `NEXT_PUBLIC_TRIEVE_API_KEY` |

In the self-hosted build none of `API_ENDPOINT` / `NEXT_PUBLIC_AI_MESSAGE_HOST` /
`NEXT_PUBLIC_TRIEVE_API_KEY` is set, so `API_ENDPOINT` falls back to `http://localhost:5000`
(nothing listening) and the assistant host is undefined. Every query fails at the forward.

> The exact dead-state UI differs by client/runtime: an older/local-CLI client renders the
> explicit **"Login into CLI to enable search"** prompt (what the tester's 2026-06-19
> screenshot shows — Mintlify only enables CLI-preview search for an authenticated CLI user);
> the current pinned client renders a normal **"Search…"** box that simply returns nothing.
> Both are the same root cause: no search backend is provisioned.

The earlier planning docs assumed Mintlify search "just works with no configuration." That is
true **only when hosting on Mintlify's platform** (they index content and provision the backend
for you), which this repo does not do.

## Resolution options (pick one — this is a product/infra decision)

1. **Host the docs on Mintlify's platform** (the original plan). Search + assistant work out of
   the box (Mintlify indexes content and provisions the backend). Cost: a Mintlify plan + a DNS
   change. Least code.
2. **Keep self-hosting, provision Mintlify's cloud search.** Index the site via Mintlify's API
   (a CI step) and set, at deploy time (Cloud Run env/secret in MangroveAI — read at runtime by
   the standalone server):
   - `NEXT_PUBLIC_AI_MESSAGE_HOST` — Mintlify search/assistant API host
   - `NEXT_PUBLIC_TRIEVE_API_KEY` — public assistant key (`mint_dsc_…`)
   - `API_ENDPOINT` — Mintlify API host backing the public search box
   `Dockerfile.docs` now declares all three (empty by default — a no-op, see below) so this is
   an explicit override surface. Requires a Mintlify account/secret + a CI indexing step.
3. **Self-hosted search, no Mintlify cloud.** Stand up a small backend that implements the
   public-search contract above (`POST /api/end-user-public/<subdomain>/search`, Trieve-shaped
   response) and point `API_ENDPOINT` at it — backed by a static index (e.g.
   [Pagefind](https://pagefind.app/) built over the docs at image-build time) or by Mangrove's
   **existing** free, no-auth full-text endpoint `https://kb.mangrovedeveloper.ai/api/search`.
   Most consistent with the current self-hosted model; most code (and it must match Mintlify's
   response schema, which is version-pinned to the client bundle).

## The no-op build change in this PR

`Dockerfile.docs` declares `API_ENDPOINT`, `NEXT_PUBLIC_AI_MESSAGE_HOST`, and
`NEXT_PUBLIC_TRIEVE_API_KEY` with empty defaults. Empty `API_ENDPOINT` falls back to the
client's built-in `http://localhost:5000`, and Mintlify's env schema (`emptyStringAsUndefined`)
treats the empty `NEXT_PUBLIC_*` values as undefined — so **behavior is identical to today**.
The declarations only document the contract and give deploy an explicit override surface. They
do **not** enable search on their own; that needs the chosen option above (plus indexed
content). See issue #85.

## Verifying the dead state (live prod + local container)

```bash
# Live production — the real public-search route has no backend:
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  https://docs.mangrovedeveloper.ai/_mintlify/api-public/search/docs \
  -H 'Content-Type: application/json' -d '{"query":"backtest"}'
# -> a non-200 (no search backend provisioned)

# Mangrove already runs a free, no-auth full-text search that *does* work — it is just
# not wired into the docs UI (this is the basis for option 3):
curl -s "https://kb.mangrovedeveloper.ai/api/search?q=backtest" | head -c 200
# -> {"query":"backtest","total_results":20,"results":[ ... ]}
```
