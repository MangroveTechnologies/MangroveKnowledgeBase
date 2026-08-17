# MangroveKnowledgeBase

## Default Persona

When working in this repo, you are the **product owner**. That agent spec and the repo memory live
in the private workspace, not here -- this is a public repository and carries no agent definitions.
`.claude/skills/author-*-properties/` are committed, because they describe how to author the values
this repo's docstrings and graph carry.

---

## Start Here

```bash
# Install the pip package
pip install -e ".[dev]"

# The MCP server over the graph (stdio; needs `pip install fastmcp`)
python mangrove_kb_mcp.py

# Run all tests
python -m pytest tests/ -q

# Run every audit + the ontology build (what CI's `audit` job runs)
python scripts/audit/run_all.py --quick

# Publish to PyPI (preferred: use GitHub Actions workflow)
# Go to Actions > "Release to PyPI" > Run workflow > pick bump type
# Local fallback:
./scripts/publish.sh patch   # or minor, major

```

**Verify it works:**
```bash
# The graph loads from the package, with no network and no configuration
python -c "from mangrove_kb.graph import KnowledgeGraph as K; g=K.load(); print(len(g.nodes), len(g.edges))"

# Search by words, then by meaning
python -c "from mangrove_kb.graph import KnowledgeGraph as K; print(K.load().find('divergence', limit=3).as_dict())"
python -c "from mangrove_kb.graph import KnowledgeGraph as K; print([r['id'] for r in K.load().ask('how far away from my entry should the stop go', limit=3)])"

# Evaluate a signal on sample bars
python -c "from mangrove_kb import RuleRegistry, sample_ohlcv; from mangrove_kb.signals import momentum; print(RuleRegistry.evaluate({'name':'rsi_oversold'}, sample_ohlcv()))"
```

## What This Is

Open-source trading signals, technical indicators, and knowledge base. Public developer docs now live in mangrove-platform-frontend-web (`content/docs/`), not here. Components:

1. **Python Package** (`mangrove_kb`) -- 249 signal functions, 80 indicator classes, RuleRegistry,
   docstring parser, **and a knowledge graph of itself** (see below). Published on PyPI as
   `mangrove-kb`.
2. **MCP server** (`mangrove_kb_mcp.py`) -- twelve read-only tools over the graph, run over stdio by whatever client wants them. A consumer of the installed package, not part of it. (It replaced `kb_server/`, a FastAPI + FastMCP server answering from SQLite FTS5 over markdown; that directory was deleted in 3.0.0 and is in git history.)
3. **Knowledge Base Content** (`knowledge-base/`) -- 11 markdown documents covering market foundations through quantitative analysis

MangroveAI consumes this as a pip dependency (`mangrove-kb`) and reads the graph in-process -- not over HTTP. The developer portal (admin UI) source code lives in MangroveAI, not here.

## Project Structure

```
mangrove_kb/                   # pip package: signals, indicators, registry, parser
knowledge-base/                # 11 trading education markdown documents
notebooks/                     # Signal explorer notebook
data/                          # 7 sample OHLCV datasets
tests/                         # pytest suite
scripts/                       # publish.sh, generation scripts
scripts/audit/                 # the audits + run_all.py (CI's `audit` job)
                               # audit_results/ is GENERATED and gitignored
```

## Serving the graph

`mangrove_kb_mcp.py` is an MCP server over the graph, run as a subprocess over stdio by whatever
client wants it. It holds no logic: every tool is a thin call onto `mangrove_kb.graph`, so there is
one implementation of "search the knowledge base" rather than two that drift.

It is a CONSUMER of the installed package, not part of it -- `pip install mangrove-kb fastmcp`, then
point a client at the file. See `mangrove_kb_mcp.md` for the tool reference and client config.

| | old (`kb_server`, deleted in 3.0.0) | now |
|---|---|---|
| answers from | SQLite FTS5 over markdown | the graph |
| transport | HTTP, mounted at `/mcp` | stdio subprocess |
| tools | 16 | 12 |
| payment | x402 middleware on HTTP | **none** -- stdio has no 402 to send |

**`evaluate_signal` and `compute_indicator` are ungated here.** That is a real difference from the
retired server, and gating has to be restored before this is served over HTTP to anyone.

## The Knowledge Graph

`mangrove_kb/graph.py` is a query layer over `ontology/signal-indicator-ontology.json` -- 714 nodes
and 2342 edges, shipped inside the wheel. Two halves on one schema: the library compiled from its own
source, and the trading knowledge base ingested from its eight chapters.

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()
kg.stats()                                  # counts + every value a filter accepts. ALWAYS first.
kg.find(kind="momentum", role="trigger")    # two axes, intersected
kg.ask("why do breakouts fail")             # a QUESTION: meaning, then one hop over the edges
kg.all_paths("adosc_bearish", "momentum")   # the claim AND the reason
```

**Two axes.** `instance-of` (indicators) and `about` (signals) carry the class; `has-role` carries
the part it plays. An indicator *measures* its class; a signal is *about* its class, because of the
indicator it reads -- different claims, so different relations. Roles are never inherited.

**The six classes divide technical analysis**, not Indicator: they span both layers.

**Never edit the JSON.** It is regenerated by `ontology/build_signal_indicator_ontology.py`, and
`tests/test_build_is_deterministic.py` rebuilds it into an empty path and diffs. Change the docstring
or the builder, then rebuild. Authored values live in docstrings; everything else is read from code.

**The agent-facing docs are `skills/knowledge-graph/SKILL.md` (which call) and `GUIDE.md` (thirteen
whole tasks).** Both ship in the wheel, and every example in them is re-executed by the suite.

## Key Architecture Decisions

- **Docstrings carry signal metadata** (Type, Requires, param ranges), parsed by `docstring_parser.py`. They are **not** a "single source of truth" for anything beyond that -- do not treat this line as licence to write new kinds of metadata into docstrings. Ontology/knowledge-graph properties do NOT go here; they belong in the graph nodes.
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
On push/PR to main, the `ci` workflow runs two jobs:

- **test** -- pytest across Python 3.10, 3.11, 3.12. This includes the guards that build a real
  wheel, install it into a clean venv and run the viewer from it, so a packaging regression fails
  here rather than on someone's `pip install`.
- **audit** -- `scripts/audit/run_all.py --quick`: every audit script plus the ontology build. The
  build matters, because nine abort-invariants live in it and only fire when it actually builds.

`run_all.py` forces the repo onto `PYTHONPATH` and aborts if `import mangrove_kb` resolves anywhere
else. A copy installed in site-packages will otherwise shadow the checkout and the audits will
silently describe the wrong code.

## Deployment

**This repo publishes a pip package. It no longer builds or pushes a container image.**

`kb_server/` and `build-and-push.yaml` were deleted in 3.0.0, so nothing here produces
`mangrove-ai-kb` any more. The release path is: PR -> merge to main -> dispatch `release.yml` to cut
a `vX.Y.Z` tag -> the tag publishes to PyPI.

A Cloud Run service still answers at `https://kb.mangrovedeveloper.ai` from the last image built
before the removal. It is frozen by construction: its source is in git history and there is no
workflow that can rebuild it. Anything that needs changing there needs the service retired, or the
source restored from history first.

Consumers take the graph by installing the package, not by calling that host -- MangroveAI reads it
in-process through `mangrove_kb.graph`, and an MCP client runs `mangrove_kb_mcp.py` against its own
installed copy.

## Signal Conventions

- Every signal function is decorated with `@RuleRegistry.register("signal_name")`
- Every signal docstring must include `Type:` (TRIGGER or FILTER) and `Requires:` (comma-separated column names)
- Every parameter must include `Range: min-max` and `Default: value` in the Args section
- Use `window` for all windowing parameters (not `lookback`, `period`, `length`)
- Signal counts: 249 registered (119 TRIGGER, 130 FILTER); 218 are modelled in the graph
- Signal modules are named for the ontology class they hold: `averaging`, `flow`, `momentum`,
  `oscillator`, `pattern`, `volatility`, plus `trend`, `volume`, `onchain`, `defi_pro`
- On-Chain signals consume alternative-data columns (SmartMoneyNetflow, SmartMoneyHoldings, ExchangeNetflow, WhaleNetInflow, HolderConcentration) the caller populates time-aligned to OHLCV bars; sourced from Nansen tgm/flows + historical-top-holders via the MangroveAI data layer. There is no total-holder-count series upstream, so holder-count signals are intentionally not shipped.

## GitHub

- Repo: [MangroveTechnologies/MangroveKnowledgeBase](https://github.com/MangroveTechnologies/MangroveKnowledgeBase)
- Pip package name: `mangrove-kb`
- Python package name: `mangrove_kb`
