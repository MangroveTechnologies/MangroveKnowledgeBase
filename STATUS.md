# Status — public knowledge-graph work

Last updated 2026-08-09. Verify anything load-bearing against the repository before acting on it;
where this file and the code disagree, the code is right.

## Where things are

```
branch   feat/indicator-output-metadata      PR #105 (DRAFT) -> main
graph    303 atoms, 755 relations
```

The graph counts above are pinned by `tests/test_documented_counts.py`, so they cannot drift out of
date quietly. Nothing else in this file is machine-checked.

## Plan

Building the **public** graph tooling for `mangrove-kb` — a query library, a skill, an MCP server and
a viz — separate from the workspace's internal `tools/mangrove-kg`, which is proprietary. The licence
change lands **last**, immediately before undrafting.

```
0   prior-art survey                      DONE
1   tools — mangrove_kb/graph.py          DONE
2   skill + guide + drift guards          DONE
3   backfill: docstrings + code = SSOT    DONE
3b  query coverage: text + attributes     DONE
4   graph + skills into the wheel         DONE
4b  OHLCV column case: lowercase          DONE
4c  discoverability + guide use cases     DONE
5   MCP rewrite                           NEXT? — deferred by owner, kb_server gets overhauled
6   viz for the public repo               UNBLOCKED — see below
7   LICENSE change                        DONE — PolyForm Noncommercial 1.0.0
8   undraft #105                          NEXT
```

### 4 — done

`pip install mangrove-kb` used to give a package whose `KnowledgeGraph.load()` raised: the wheel
carried `mangrove_kb/` and nothing else. `setup.py` now copies the graph into
`mangrove_kb/data/` and the skill and guide into `mangrove_kb/skills/knowledge-graph/` at build time,
so the repo keeps **one** canonical copy of each and there is no second file to drift.

Verified by installing a built wheel into a clean venv outside the repo: it loads the packaged graph,
303 nodes / 755 edges, and `skills/knowledge-graph/SKILL.md` is present.
`tests/test_wheel_contents.py` builds a real wheel from a pristine copy of the tree and asserts all
of it.

**Do not build the wheel in place when checking this.** setuptools stages into `build/lib/` and never
removes files it no longer produces, so a stale copy from an earlier build satisfies every assertion
even with the build hook deleted — observed, not theorised. `pip --no-cache-dir` does not save you;
the test copies the tree first.

### 4b — done

Dogfooding the installed wheel as a new consumer found the graph publishing an input contract that
did not run: it declared `['high','low','close']` for every signal while the signal bodies read
`df["High"]`, so 211 of 218 raised `KeyError: 'High'` for anyone who followed it. The builder was
faithful — it lowercased `Requires: Close` on purpose, "so the graph speaks one vocabulary", which
erased a real difference between the indicator layer (lowercase dict keys) and the signal layer
(capitalised frame columns).

Lowercase is now canonical everywhere: signal bodies read lowercase, `sample_ohlcv()` returns
lowercase, the builder takes `Requires:` as declared and generates lowercase `usage_example`s.
Capitalised frames still work — `RuleRegistry.register` normalizes the five OHLCV names at the
boundary, touching nothing else. Verified through the installed wheel: 213 signals, three column
spellings, zero disagreements.

### 7 — done

`mangrove-kb` is **PolyForm Noncommercial 1.0.0**: free for noncommercial use, commercial use
requires a paid licence from support@mangrove.ai. The licence text is verbatim from
`polyformproject/polyform-licenses`, under a preamble that states the commercial terms and the
`Required Notice`. `pyproject.toml` carries the SPDX id and drops the OSI classifier — PolyForm is
deliberately not OSI-approved. Verified in the built wheel's METADATA.

Releases published before this change stay MIT; that cannot be revoked retroactively and the LICENSE
says so.

**This dissolved the viewer question.** The jarvis viewer was called a blocker on the grounds that
CC BY-NC-SA cannot ship inside an MIT repo. Two things were wrong with that: jarvis has **no LICENSE
file at all** (its GitHub licence metadata is `null` — the CC BY-NC-SA claim lives only in a header
and an `ATTRIBUTION.md` we wrote ourselves), and the copyright holder on both sides is Mangrove. It
was never a third-party constraint. With the package now noncommercial too, there is nothing to
reconcile.

## Open decisions — do not guess

1. **Ordering within issue #112** (below). Findings agreed, order not.

## Filed, not scheduled

- **#112** https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/112 — the graph covers
  *discovery* and not *composition*: signal direction/polarity is modelled nowhere, `warmup_bars`
  cannot be evaluated, no relation expresses contradicts/confirms/correlates, the strategy schema
  validates nothing, and the authoring skills plus `parse_authored` ship in neither `skills/` nor the
  wheel. Not part of getting #105 out of draft.

Upstream in jarvis, unassigned:

- https://github.com/mangrove-one/jarvis/issues/250 — claim the two-axis role/type contribution in
  the white paper
- https://github.com/mangrove-one/jarvis/issues/251 — `ontology.py` credits Biolink for a taxonomy
  Biolink does not have

## Traps that cost real time

- **The builder writes the graph in place.** `builder > ontology/...json` **destroys** it — the shell
  truncates before the process starts, and the builder reads that file. Use `ONTOLOGY_OUT=/tmp/x.json`.
- **`inspect` caches source line numbers.** Rewriting docstrings top-down puts them on the *wrong
  functions*, silently. `ontology/backfill_docstrings.py` collects every edit first and applies them
  per file bottom-up.
- **`git checkout -- mangrove_kb/` reverts uncommitted library work too.**
- **Anything living only in the JSON looks derived**, because nothing in the source contradicts it.
  Four fields were misclassified that way and only a diff separated them: `warmup_bars`, param
  descriptions, param `default`/`min`/`max`, and the `DEPRECATED:` marker.
- **`textwrap.wrap` breaks on hyphens**; re-joining gives `Non- negative`. Use
  `break_on_hyphens=False, break_long_words=False`.
- **Another session works in this repo.** Coordinate before touching
  `ontology/build_signal_indicator_ontology.py`, the graph JSON, or the 22 indicator/signal sources.

## Re-vendor pending (different repo)

jarvis PR #249 merged as `c08a6f8`; the copy vendored into the workspace's `tools/mangrove-kg` is
still `3a5c27f`. Re-vendoring deletes ~190 lines of overlay from
`domain/render_signal_ontology.py`. Awaiting a go.

---

## Session summary — 2026-08-10

**Transcript:** `/home/darrahts/.claude/projects/-home-darrahts-mangrove/13d9711a-8c41-4c94-8c80-c431b034f079.jsonl`

**Every claim in this section is an assertion made by an agent and must be re-verified against the
repository before it is acted on.** Several statements made confidently during this session were
wrong, were corrected, and were then wrong again in the other direction. Re-run the suite, re-read
the diff, re-derive the counts. Do not trust this text.

### Overarching goal

Get PR #105 out of draft. It turns MangroveKnowledgeBase into a package whose knowledge graph is
usable by an agent: a query library, a skill and guide, a visualizer, and the packaging and licence
to publish them.

### What landed (28 commits, unpushed, HEAD 16e2d1f)

- query surface widened (`find` reads all authored text; `outputs()`; `find(status=/requires=)`)
- graph and skills ship inside the wheel; verified from a clean venv install
- OHLCV column case made lowercase everywhere; graph and code had disagreed on 211 of 218 signals
- graph and guide made discoverable from PyPI and GitHub
- relicensed to PolyForm Noncommercial 1.0.0; commercial licensing to support@mangrove.ai
- visualizer moved into `mangrove_kb/viz/`, rebranded to the platform palette, light/dark/system,
  search wired to the same ranking `kg.find()` uses

### Where this session is stuck — read this before touching the ontology

The owner reported two inconsistencies:

1. `concept:indicator` and `concept:signal` are typed `Procedure` while being used as classes.
2. `concept:strategy` is typed `Schema` with a `concept:` id.

**(1) is the whole issue. The fix is two retypes to `Concept`, no edge changes.** (2) is still open:
either it becomes a `Concept` like its siblings, or it stays a `Schema` and the id becomes
`schema:strategy`.

Everything else explored this session was a detour the agent generated, and it is recorded here only
so the next reader does not repeat it:

- A dry-run build added 222 `signal --instance-of--> class` edges, dropped
  `class --kind-of--> Indicator`, and introduced a `concept:technical-analysis` parent. **This was
  concluded to be wrong.** `momentum` is defined as *measuring rate of change*; a signal emits a
  boolean and measures nothing, so a signal is not a member. `find(kind="momentum")` returning 78
  results is a SEARCH ("things to do with momentum") reached through `uses` -- it was mistaken for a
  membership claim, and that mistake drove the whole detour.
- The agent then declared a "substantive failure": with the class asserted, `path()` returned a
  one-hop route and stopped explaining *why* a signal is momentum. **That was a symptom, not a
  cause.** The cause is that `path()` is a BFS returning ONE shortest route, so adding any edge
  silently changes its answer and it never reports the routes it discarded.

### The two pieces of work that actually follow

1. **Retype** `concept:indicator` and `concept:signal` from `Procedure` to `Concept` in
   `ontology/build_signal_indicator_ontology.py`. 303 atoms / 755 relations unchanged; every edge
   stays. Decide (2) above at the same time.
2. **`path()` should return all paths**, capped with an audible truncation like every other bounded
   return in the library. Guide use case 8 ("explain why this is classified so") should answer via
   the `uses` edge directly rather than leaning on shortest-path behaviour.

### UNCOMMITTED AND MUST BE REVERTED

`ontology/build_signal_indicator_ontology.py` is **modified in the working tree** with the rejected
222-edge change. It has not been committed and the graph JSON was never written. Revert it before
doing anything else:

    git checkout -- ontology/build_signal_indicator_ontology.py

Then confirm `370 passed, 17 skipped` and `303 atoms / 755 relations` before starting.

### Still open, unrelated to the above

- PR #105 has 28 unpushed commits and is still a draft. Nothing technical blocks pushing it.
- The README revamp (wiki-to-graph shape, screenshots) was requested and never started. Captures
  exist under the session scratchpad only, which is temporary.
- Issue #112 (composition coverage) remains filed and unscheduled; its ordering was never agreed.
- The jarvis re-vendor into the workspace is still pending a decision.

### On the conduct of this session

The agent repeatedly declared work finished, then found on being pushed that it was not: the wheel
shipped no graph, the graph published unusable column names, the package was undiscoverable on PyPI,
the guide asked for things its own examples did not do, and `oklch()` tokens silently killed the 3D
scene. Each was found by the owner asking a question the agent had not thought to ask. In the
ontology discussion the agent argued at least three mutually contradictory positions and had to be
told twice that it was chasing symptoms. Weigh its assertions accordingly.
