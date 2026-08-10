# Handoff — public knowledge-graph work on PR #105

Written 2026-08-09. **Everything below is a claim, not a fact. Re-verify before acting on any of
it** — see the first section. State drifts, other sessions commit, and a summary written before a
compaction is exactly the kind of document that gets trusted when it should not be.

---

## 0. READ THIS FIRST — trust nothing here, or in the conversation context

**Do not act on any statement in this file, or in the compacted conversation, without checking it
against the running system that turn.** Specifically:

- **Re-read the branch state.** `git log --oneline -5`, `git status --short` in each repo. Another
  session works in this repo and commits frequently; the graph grew from 216 to 303 nodes during
  this session alone, twice mid-task.
- **Re-run the suite before believing any "passing" claim.** `python3 -m pytest tests/ -q`.
- **Re-count anything numeric.** Every count in this file was true when written and several counts
  in this repo have been wrong before — the skill said "70 indicators" one commit after a 71st was
  added.
- **Check file paths still exist.** Files were renamed and deleted in this work.
- **A merged PR is not a deployed change**, and an open issue is not a live problem.

If this file disagrees with the repository, **the repository is right**.

---

## 1. Verified state at time of writing

```
MangroveKnowledgeBase   worktree /home/darrahts/mangrove-worktrees/MangroveKnowledgeBase-ontology-docstrings
                        branch   feat/indicator-output-metadata   HEAD 85d7ad9   tree clean
                        PR       #105 (DRAFT) -> main
                        graph    303 atoms, 755 relations
                        tests    309 passed, 17 skipped

mangrove (workspace)    branch feat/mangrove-kg   HEAD a5b9fdd
jarvis                  origin/main c08a6f8  (PR #249 merged)
                        vendored copy in mangrove is still @ 3a5c27f  -- NOT re-vendored
```

---

## 2. What this work is

Building the **public** graph tooling for `mangrove-kb`: a query library, a skill, an MCP server and
a viz — separate from the workspace's internal `tools/mangrove-kg`, which is proprietary (it ingests
session transcripts, hook events, GitHub).

The plan, in order. Licence deliberately LAST, immediately before undrafting:

```
0  prior-art survey                       DONE
1  tools — mangrove_kb/graph.py           DONE
2  skill + guide + drift guards           DONE
3  backfill: docstrings+code = SSOT       DONE   (p1-p6)
3b query coverage: text + attributes      DONE   (15d95f6)
4  graph + skills into the wheel          NEXT
5  MCP rewrite                            deferred by owner ("kb_server is going to get overhauled")
6  viz for the public repo                BLOCKED — needs a licence decision
7  LICENSE change, then undraft #105      LAST

   composition coverage                   FILED, NOT SCHEDULED — issue #112
```

**Issue #112** — https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/112 — records
that the graph covers *discovery* and not *composition*: signal direction/polarity is modelled
nowhere (`rsi_oversold` and `rsi_overbought` are both `Type: TRIGGER`), `warmup_bars` can be read but
not evaluated, no relation expresses contradicts/confirms/correlates, the strategy schema validates
nothing, and the authoring skills plus `parse_authored` ship in neither `skills/` nor the wheel.
Findings agreed; **ordering is not** — the owner did not accept "direction first". Settle the order
before picking any of it up. This is not part of getting #105 out of draft.

### Done — 1, tools

`mangrove_kb/graph.py` + `tests/test_graph.py`. Seven operations: `stats` `find` `get` `outputs`
`neighbors` `subgraph` `path`. All logic in the library so the MCP layer is a rename.

A coverage review (2026-08-09) found the traversal half complete and the **attribute** half missing,
and closed it: `find` now searches every authored field rather than name/abbreviation/summary only
(`find("mean reversion")` returned 0 while two nodes described it), and takes `status=` / `requires=`;
`outputs()` indexes values rather than nodes, so units, boundedness and "what produces `histogram`"
are one call instead of a loop over 303 nodes. That query is what the novelty claim in
`docs/research/graph-query-api-and-mcp-surface.md` §5 rests on, and it did not previously exist.

The load-bearing constraint, and the thing most likely to be broken by a well-meaning edit: **roles
are not types.** `instance-of`/`kind-of` is the rigid backbone and is transitively closed;
`has-role` is anti-rigid, never closed, never returned as a supertype (Steimann DKE 2000; Guarino &
Welty OntoClean CACM 2002). `test_roles_are_never_inherited` asserts it for every node.

A signal's class is **derived**, not declared: `signal --uses--> indicator --instance-of--> class`.
All 216 signals resolve. Four derive two classes (the RSI divergence signals read an oscillator and
a momentum indicator), so class is **not** single-valued.

### Done — 2, skill and guides

- `skills/knowledge-graph/SKILL.md` — which call answers which question
- `skills/knowledge-graph/GUIDE.md` — eight worked tasks with real output
- `tests/test_documented_counts.py` — pins counts stated as current fact; historical docs
  (CHANGELOG released sections, dated audit reports) are deliberately excluded and that exclusion is
  itself asserted
- `tests/test_agent_guide.py` — re-executes every use case in the guide

### Done — 3, the backfill (the big one)

The graph used to be built from six sources, one of which was **the graph itself** — ~1,270 authored
values carried forward from the previous JSON. Now every authored value lives in the **docstring** of
the class or function it describes; everything else is derived from the code.

- 289 docstrings rewritten across 12 files, format `Indicator: <Name>` / `Signal: <name>`
- `mangrove_kb/docstring_parser.py::parse_authored` reads it and **enforces** it
- `ontology/backfill_docstrings.py` is the one-time migrator (kept)
- one builder, one JSON, both pinned by tests
- `tests/test_build_is_deterministic.py` builds to an **empty path** and diffs against the committed
  graph — if anything starts reading the old file again, the suite fails

---

## 3. Next action

**Step 4: get the graph and `skills/` into the wheel.** Verified defect: `pip install mangrove-kb`
then `KnowledgeGraph.load()` raises, because the wheel contains `mangrove_kb/` only —
`ontology/signal-indicator-ontology.json` sits outside the package and `mangrove_kb/data/` does not
exist. Confirm it yourself:

```
python3 -m pip wheel --no-deps -w /tmp/w .
python3 -c "import zipfile,glob;print([n for n in zipfile.ZipFile(glob.glob('/tmp/w/*.whl')[0]).namelist() if n.endswith('.json')])"
```

Owner's decision, already given: **ship the graph in the wheel** (not a build-it-first step), and
**skills belong in the wheel too**. Now that the graph is a pure build artifact, generating it into
`mangrove_kb/data/` at build time is the clean route — the "where is canonical" question is gone.

Add a test asserting the wheel actually contains the graph, so the defect cannot return silently.

---

## 4. Open decisions — needed from the owner, do not guess

1. **Licence for the jarvis viewer.** The renderer in `mangrove/tools/mangrove-kg` vendors jarvis's
   `viz.py`, which is **CC BY-NC-SA 4.0** (non-commercial, share-alike, set in jarvis `3a5c27f`).
   This repo is MIT and public. NC/SA cannot ship inside it. Options: dual-licence those four files,
   write a fresh viewer, or ship tools-only. **Blocks step 6.**
2. **Package licence change.** Owner has decided to move off MIT to restrict commercial use, landing
   on this PR immediately before undrafting. Contributors `ApexFutz` and `Maciej` are employees and
   Mangrove holds rights — confirmed, not a blocker.
3. **Re-vendor jarvis into the workspace.** jarvis PR #249 merged (`c08a6f8`); the vendored copy is
   still `3a5c27f`. Re-vendoring deletes ~190 lines of overlay from
   `mangrove/tools/mangrove-kg/domain/render_signal_ontology.py`. Different repo, awaiting a go.

---

## 5. Filed upstream, unassigned

- https://github.com/mangrove-one/jarvis/issues/250 — claim the two-axis role/type contribution in
  the white paper (`jarvis/docs/memory/paper/`, which is the live copy; MangroveMemory's is stale)
- https://github.com/mangrove-one/jarvis/issues/251 — `ontology.py`'s docstring credits Biolink for
  a taxonomy Biolink does not have, plus the IRI mappings

---

## 6. Traps that cost real time here

- **The builder writes the file in place.** `builder > ontology/...json` **destroys** it: the shell
  truncates before the process starts. Use `ONTOLOGY_OUT=/tmp/x.json`.
- **`inspect` caches source line numbers.** Rewriting docstrings top-down put them on the *wrong
  functions* — `stochrsi_overbought` ended up holding `williams_r_overbought`'s text, silently.
  `backfill_docstrings.py` now collects all edits first and applies them per file bottom-up.
- **`git checkout -- mangrove_kb/` reverts uncommitted parser work too.** Cost a re-do here.
- **Anything living only in the JSON looks derived**, because nothing in the source contradicts it.
  Four fields were misclassified this way and only a diff separated them: `warmup_bars`, param
  descriptions, param `default`/`min`/`max`, and the `DEPRECATED:` marker.
- **`textwrap.wrap` breaks on hyphens**; re-joining gives `Non- negative`. Use
  `break_on_hyphens=False, break_long_words=False`.
- **The other session is active in this repo.** Coordinate before touching
  `ontology/build_signal_indicator_ontology.py`, the graph JSON, or the 22 source files. It has
  swept an untracked file of ours into one of its commits before.

---

## 7. Owner's standing instructions on how to report

Stated repeatedly and forcefully this session:

- **Lead with the answer.** Write the last sentence first.
- **A bug I created and already fixed is "it works"** — not a finding, not a footnote. Before any
  sentence: what does he DO with this? If nothing, cut it.
- **Never drop the thread.** Re-output the plan at the end of every response.
- **Discussion is not authorisation to edit.** "Explain / what do you think / I don't understand"
  means read-only; only "do it / go / proceed" authorises, and only the named thing.
- **Verify, do not reason.** Run it, diff it, execute it. Every wrong call this session came from
  inference; every correct one came from execution.
