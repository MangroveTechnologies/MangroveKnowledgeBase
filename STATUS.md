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
4   graph + skills into the wheel         NEXT
5   MCP rewrite                           deferred — kb_server gets overhauled
6   viz for the public repo               BLOCKED — jarvis-viewer licence call
7   LICENSE change, then undraft #105     LAST
```

### 4 — next

`pip install mangrove-kb` then `KnowledgeGraph.load()` raises: the wheel contains `mangrove_kb/` and
nothing else. Verified by building it —

```
python3 -m pip wheel --no-deps -w /tmp/w .
python3 -c "import zipfile,glob;print([n for n in zipfile.ZipFile(glob.glob('/tmp/w/*.whl')[0]).namelist() if n.endswith('.json')])"
```

Decided: **the graph and `skills/` both ship in the wheel.** The graph is now a pure build artifact,
so generating it into `mangrove_kb/data/` at build time is the clean route. Add a test asserting the
wheel really contains it, so the defect cannot return silently.

## Open decisions — do not guess

1. **Licence for the jarvis viewer.** The renderer in the workspace's `tools/mangrove-kg` vendors
   jarvis's `viz.py`, which is **CC BY-NC-SA 4.0**. This repo is MIT and public; NC/SA cannot ship
   inside it. Dual-licence those files, write a fresh viewer, or ship tools-only. **Blocks 6.**
2. **Package licence change.** Moving off MIT to restrict commercial use, landing immediately before
   undrafting. Contributors `ApexFutz` and `Maciej` are employees and Mangrove holds rights — not a
   blocker.
3. **Ordering within issue #112** (below). Findings agreed, order not.

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
