# Signal/Indicator Ontology — state of the work

**Not committed. Working note only.** Generated 2026-08-06.

---

## What we are doing, and why

We are building a **knowledge graph of the indicators and signals** in `mangrove_kb`, so an agent
can ask "what class is CCI", "what are RSI's bounds", "which indicators are unbounded", and
"how many bars before this is usable" — and get an answer from structured data rather than by
reading source.

The organising idea is a **class axis based on what an indicator's output tells you about its
input** — `averaging`, `momentum`, `oscillator`, `volatility`, `flow`, `pattern`, `unclassed`. This
replaced a layout that classified by *trader use case*, which mixed bases and could not be checked.

Two things came out of the work that were not the original goal but matter more:

1. **Building the graph required reading every `_compute` against the published literature.** That
   surfaced 22 verified implementation defects — real arithmetic and contract bugs, each confirmed
   by executing the indicator, not by inspection.
2. **It surfaced twelve implementations that are correct but disagree with common libraries.**
   These are landmines: an audit against pandas-ta or TA-Lib flags them, and "fixing" them breaks
   working code.

### The governing principle

**Align to the published literature, never to pandas-ta or TA-Lib.** Those libraries disagree with
each other and with the source material. The decision rule, applied throughout:

| Situation | Action |
|---|---|
| Literature is clear, a library disagrees | Follow the literature |
| Literature is genuinely split | Pick one, document which |
| Literature is silent | Decide, document the decision |
| Literature assumes something untrue for a 24/7 market | Deviate deliberately, document why |

That fourth row is not hypothetical. It is why `VWAP` uses a rolling window: anchoring presupposes a
session boundary, and a 24/7 market has none. An earlier research pass called this "the clearest
defect in the class". It was wrong, and it is now withdrawn.

---

## Where things live

The domain ontology moved **out of the workspace tooling repo and into MangroveKnowledgeBase**,
because it describes this package's indicators, its builder reads this package's source, and it is
only useful to someone who has this package. The *ecosystem-wide* knowledge graph stays in the
workspace — that split is deliberate.

| | Path | Note |
|---|---|---|
| Ontology of record | `ontology/signal-indicator-ontology.json` | **Committed.** 69 indicators, 83 atoms, 79 relations |
| Builder | `ontology/build_signal_indicator_ontology.py` | Lifts only; emits `null` for anything a human must author |
| Design doc | `ontology/signal-indicator-ontology.md` | Class axis, basis of division, what it rejects |
| Research | `ontology/research/{averaging,flow,momentum,oscillator,volatility}.md` | Literature behind every authored value |
| Worked example | `ontology/example-bollingerbands-subgraph.md` | |
| Authoring skill | `.claude/skills/author-indicator-properties/SKILL.md` | `.gitignore` has a narrow exception so skills are tracked |
| Convention guards | `tests/test_indicator_conventions.py` | The 12 correct-but-divergent implementations |
| Defect regressions | `tests/test_indicator_defect_fixes.py` | One test per fixed finding |
| Renderer + viewer | `tools/mangrove-kg/domain/render_signal_ontology.py`, `tools/mangrove-kg/vendor/` | **Stays in the workspace** — CC BY-NC-SA, and `mangrove-kb` is MIT on PyPI |
| Process notes | `tools/mangrove-kg/domain/AUTHORING-PROCESS.md` | **Stays private** — embeds home paths, Tailscale host, transcript paths |

### Key builder property

The builder **carries authored values forward**. A lift wins where a source supplies one; wherever a
run produces `null` and the previous build had a value, the previous value is kept. Keys absent from
the current schema are not resurrected. **Running it twice produces byte-identical output.** Before
this, any rebuild silently wiped every authored value.

---

## What has been done

Ten commits on `feat/indicator-output-metadata`, all pushed:

```
9aa240a refactor(mama): warmup is a parameter, not a hardcoded constant
3bc0573 fix(indicators): correct three weak spots in the previous fixes
60b925f fix(indicators): three defects introduced by the previous commit
11cdb16 fix(indicators): sixteen defects from the literature research
7131808 test(indicators): pin the twelve correct-but-divergent implementations
698954e fix(vwap): the rolling window is correct, and the docstring was not
909ebda feat(ontology): bring the signal/indicator ontology into this repository
1fa64b5 test(signals): close the coverage hole in the bool return contract
a74438f refactor(indicators): replace the 27 pattern indicators with two measurement layers
80ce401 docs: docstrings are not a blanket single source of truth
```

### 1. The pattern layer was restructured (breaking)

27 pattern indicator classes each folded measurement and interpretation into one class, re-deriving
the same candle arithmetic and exposing none of it. Replaced by two measurement indicators:

- **`CandleGeometry`** — one bar's shape: body, range, wicks, ratios. Translation invariant.
- **`CandleRelation`** — the relationship between consecutive bars, expressed in **percent of the
  previous close** so it is price-agnostic across instruments.

The 40 pattern signals now call these through 27 private detectors. Verified identical to the old
implementation across **6,400 comparisons** before anything was deleted. `pattern_utils.py` removed.

### 2. Twelve correct implementations are pinned

`CCI`, `SMMA`, `TRIMA`, `HMA`, `EMA`, `DPO`, `Aroon`, `EaseOfMovement`, `KST`, `Vortex`, `NVI`, `ADI`.
Each test asserts the published construction and records what it defends against. **Verified by
mutation** — each indicator was rewritten to the library form and the guard confirmed to fail.

`CCI` is the worst case: ours uses the published mean absolute deviation, most libraries use a
rolling-mean shortcut — **187 points apart** on an indicator whose conventional band is ±100.

### 3. Sixteen defects fixed, plus four self-review corrections

Value changes: `OBV` (flat closes), `ATR`/`ADX` (zero-filled warmup), `DonchianChannel.pband`
(described the wrong bar's bands, so breakouts were impossible), `MAMA` (consumed close, not median
price; published ~50%-off unconverged values), `KAMA` (seed).

Contract/API: `VPT.dropnans` (broke the aligned-index guarantee), `KeltnerChannel` inert params,
zero-width band guards, `TRIX` signal line added.

Documentation: `ATR`'s comment, Keltner's copy-pasted series names, `StochRSI`'s 0–1 scale,
`StochasticOscillator` being the Fast variant, `BOP` being unsmoothed.

**Four of my own fixes were then corrected** after a devil's-advocate pass: I zero-filled VPT's
warmup in the same commit that argued zero-fill is wrong; I seeded OBV's bar 0 with volume against
the research's own canon; I derived MAMA's warmup from random walks alone (understated by 20+ bars);
and I made MAMA's warmup a hardcoded constant when it is a caller's choice and belongs in `_params`.

### 4. Issue hygiene

- **#92** rewritten: the audit it proposed was never run and should not be run in that form. Records
  that the work was done against primary sources for 62 of 69 indicators, lists the 12 divergences.
- **#104** finding 14 (`VWAP`) withdrawn with reasoning. Count 23 → 22.

---

## Where we are now

- **191 tests pass**, 17 skipped.
- All 243 signals return a native Python `bool`; the registry contract test now actually covers all
  of them (it previously skipped four crossover signals via a blanket `except TypeError`).
- Graph: 69 indicators, one `warmup_bars` null remaining (`Divergence`, deliberately held).
- Working tree clean, everything pushed.

### Open blockers

**PR #105 is deliberately held open** until everything is fixed — it is a major version (27 public
indicator classes removed). Everything lands on that branch and it merges once.

**CI has not run since `909ebda`.** Neither a push nor a close/reopen triggers Actions, though
Actions is enabled, the workflow has no `types:` filter or draft condition, and no `.github/` file
was touched. The green checks on the PR are from `80ce401`, which predates all of this work. Local
verification is thorough but it is not CI.

---

## What's next

**Immediately: step 3** — move the boolean outputs out of the indicator layer. `BollingerBands` and
`KeltnerChannel` still emit `hband_indicator`/`lband_indicator`, and `MARibbon` emits three boolean
flags. Those are *signals living in the indicator layer*; building signal nodes while they are
indicator outputs would bake the category error into the thing meant to fix it. The BB *state*
signals that replace them do not exist yet — the three existing BB signals are all crossings.

This needs no decision and is the last thing blocking signals entering the graph.

### Five decisions blocking the remaining 6 defects

- **Donchian** — make current-bar exclusion the default?
- **`wband`** — unify on each indicator's own mid-band, or rename Donchian's?
- **`APO`** — byte-identical to the MACD line. Keep or drop?
- **`KVO`** — keep the simplified variant, or implement Klinger's original (~145× scale difference)?
- **Zero-range** — one convention for `Stochastic`/`WilliamsR`/`StochRSI`/`CMF`, which currently
  fall to NaN by accident while `RSI` guards deliberately.

---

## On the horizon

- **Signals into the graph.** Blocked on the `Type:`/`Role:` naming decision (`Type:` currently
  means TRIGGER/FILTER, which is a *role*, not a type — the root category error behind the whole
  taxonomy mess) and on `RuleRegistry.names()`/`has()` so the builder can enumerate signals without
  touching private `_registry`.
- **`mangrove_kb.ontology` query module** so `pip install mangrove-kb` gives programmatic access
  instead of requiring consumers to find and parse the JSON.
- **The temporal-form axis (ARM).** Waits on MangroveOracle#467 landing.
- **Composition.** Explicitly deferred to a child issue of #1012.
- **Still unaudited:** #92's MACD-crossover-bar concern (signal-level, nobody has looked), the 5
  `unclassed` indicators, and the 2 new pattern indicators. All deliberately held.

---

## The plan we are following

All work lands on the **#105** branch and merges once, as a major version. Align to published
literature, never to pandas-ta or TA-Lib.

1. ~~Rewrite #92; add tests locking in the 12 correct-but-divergent implementations.~~ **Done.**
2. Fix the 22 defects on #104. **16 done + 4 self-review corrections.** 5 decisions outstanding.
3. Move boolean outputs out of the indicator layer; add the BB state signals replacing them.
4. Put signals into the graph. Blocked on the `Type:`/`Role:` decision and `RuleRegistry.names()`.
5. Re-author the graph nodes the fixes changed, rebuild, merge.

**Held:** the 5 unclassed indicators, the 2 new pattern indicators.

---

## Links

- Graph viz: <http://darrahts-server:8791/signal-indicator-ontology.html> — re-rendered against the
  current graph. Served from the workspace `out/`; the JSON is authored in the KB repo and copied
  across, so **it goes stale unless re-rendered after a rebuild.**
- PR: <https://github.com/MangroveTechnologies/MangroveKnowledgeBase/pull/105>
- Indicator defects: <https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/104>
- Accuracy audit (rewritten): <https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/92>
- Registry API: <https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/102>
- Social signals to KB: <https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/21>
- Signal classification design: <https://github.com/MangroveTechnologies/MangroveAI/issues/1012>
- Taxonomy deletion: <https://github.com/MangroveTechnologies/MangroveAI/issues/1010>
- Chart patterns must not be FILTER: <https://github.com/MangroveTechnologies/MangroveAI/issues/1008>
- Signal KB audit: <https://github.com/MangroveTechnologies/MangroveOracle/issues/470>
- Armed entries epic: <https://github.com/MangroveTechnologies/MangroveOracle/issues/468>
- Prior-art survey (must land first): <https://github.com/MangroveTechnologies/MangroveOracle/issues/467>

## Session transcript

`/home/darrahts/.claude/projects/-home-darrahts-mangrove/c51c7300-52c5-45cf-a3a2-0c6aaea7e776.jsonl`
