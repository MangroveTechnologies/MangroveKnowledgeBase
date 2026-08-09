# Scope: backfill authored values into docstrings, make the build deterministic

**Status:** scoped, not started. **Owner:** unassigned. **Blocks:** nothing. **Unblocks:** shipping
the graph in the wheel.

## The problem

The graph is built from **six** sources, and one of them is the graph itself:

| source | supplies |
|---|---|
| class attributes (`_data` / `_params` / `_outputs`) | inputs, params, outputs keys |
| indicator docstring | summary prose, reference URL, param types |
| signal docstrings, resolved by AST call-graph | param default / min / max / description |
| `min_periods` in `_compute` | `warmup_bars`, where unambiguous |
| `knowledge-base/*.md` | definition, formula, interpretation, applications, abbreviation |
| **the previous `signal-indicator-ontology.json`** | **~1,260 hand-authored values, carried forward** |

That last row is the defect. The build is a function of the source **plus its own previous output**,
so the JSON is simultaneously the artifact and the only store of 1,260 values whose sole backup is
git.

This has already gone wrong three times:

- `46e3af9` — "stop the builder erasing every authored value on rebuild"
- `437bd56` — "the documented rebuild command destroyed the file it rebuilds"
- and once by hand, a stray `>` truncating the file before the builder could read it

Three near-misses on one fragility is the argument. It is not hypothetical and it will happen again.

## Goal

Move every **authored** value into the docstring of the thing it describes, so that:

1. the build is a pure function of the source tree — delete the JSON, rebuild, get it back;
2. the carry-forward disappears, and with it the failure mode above;
3. the values land where library *users* see them — `help()`, IDE tooltips, generated docs — instead
   of a JSON only the graph reads;
4. the JSON becomes a plain build artifact, which is what makes shipping it in the wheel trivial
   rather than a question about canonical locations.

## The contract: what moves, what must not

**Moves into the docstring** — everything a human decided:

- indicator/signal description prose
- `formula`, `interpretation`, `applications`, `abbreviation`, `reference`
- per-output `units`, `range`, `canonical_name`, `description`
- per-input `description`

**Stays derived, and must never be authored:**

| stays derived | why |
|---|---|
| `uses` and `instance-of` **edges** | derived by AST from what the code actually calls. Authored, they go stale the moment a call changes — silently — and the graph stops being exact, which is the only thing that makes it worth more than prose. |
| `source_module` | file location |
| `usage_example` | generated from the class attributes; authored, it drifts from the signature |
| param `type` / `default` / `min` / `max` | read from the real signature; authoring them lets the docstring contradict the code |
| `warmup_bars` | lifted from `min_periods` in `_compute` where unambiguous |

The rule: **authored facts go in the docstring; facts the code already states stay derived from the
code.** A docstring may not restate something the compiler or the AST can tell us.

## Format

Not a raw JSON blob. Dumping the node verbatim into `__doc__` would make `help()` unreadable, which
forfeits reason (3) above — the point is that a user reading the docstring gets the metadata.

Extend the existing sectioned format the parser already handles (`Args:`, `Returns:`, `Type:`,
`Requires:`). Sketch, to be settled in phase 1:

```
Average Directional Movement Index (ADX)

    <description prose, unchanged>

    Formula:
        +DI = 100 * EMA(+DM) / ATR
        -DI = 100 * EMA(-DM) / ATR
        DX  = 100 * |+DI - -DI| / (+DI + -DI)
        ADX = EMA(DX, n periods, typically 14)

    Outputs:
        adx (series, dimensionless, 0..100) "ADX":
            Wilder's trend-STRENGTH index -- non-directional by design...
            WARMUP CAVEAT: the first 27 bars are filled with literal 0.0 rather than NaN...
        adx_pos (series, dimensionless, 0..100) "+DI":
            ...

    Interpretation:
        - ADX > 25: strong trend
        - ADX < 20: weak trend / ranging

    Reference: https://chartschool.stockcharts.com/...
```

Requirements on the format: round-trips losslessly, readable in `help()`, and unambiguous enough
that the parser needs no heuristics. Unbounded ranges are written `-inf..inf` — they are `[-inf,
inf]` in the graph today, never null.

## Migration

The backfill is mechanical and runs **from the graph into the source**, which is what makes it safe:
the graph is complete for the fields being moved, so the target is known.

1. **Generator** reads the committed graph and rewrites each indicator/signal docstring in place.
   One-time; kept afterwards only as a formatter if that proves useful.
2. **Parser** extended to read the new sections.
3. **Builder** loses `_carry` (line 1361), loses the `knowledge-base/*.md` lift, and loses the
   precedence chain at line ~351 ("knowledge base -> previously authored -> docstring") — there is
   one source after this.

### Verification — the reason this is safe

```
rebuild with carry-forward disabled  ->  diff against today's committed graph  ->  must be identical
```

A hard pass/fail, not a judgement call. Any field that fails to round-trip shows up as a diff. Add it
as a test so the property is permanent: **the graph rebuilt from a clean tree equals the committed
graph.**

## Scale

- 22 source files (`mangrove_kb/indicators/*.py`, `mangrove_kb/signals/*.py`)
- ~1,260 authored values, of which 355 outputs × 4 fields = 1,420 output-level fields
- builder is 1,511 lines; expect it to shrink substantially
- **known gaps to fill or accept while in there:** 224 null `abbreviation`, 56 null `reference`

## Explicitly out of scope

- **`knowledge-base/*.md` is not deleted.** It stops being a *builder input*, but it is an
  independent published corpus with its own table of contents, served by the document tools. Retiring
  it is a separate decision.
- The `.claude/skills/author-*-properties` skills stay. New indicators still need authoring; only the
  target changes, from the JSON to the docstring. They need updating, not deleting.
- Edges, and everything else in the derived column above.

## Phases

| # | phase | done when |
|---|---|---|
| 1 | settle the docstring format on 2–3 real indicators, both directions | round-trips losslessly by hand |
| 2 | extend the parser to read it | parses the phase-1 examples |
| 3 | run the generator across all 22 files | every authored value is in a docstring |
| 4 | rebuild with carry-forward off, diff | byte-identical to the committed graph |
| 5 | delete `_carry`, the KB lift, the precedence chain | builder reads source only |
| 6 | pin it | test asserts clean-tree rebuild == committed graph |

Phase 4 is the gate. If it does not come out identical, the format is lossy and phase 1 was wrong.

## Risks

- **Lossy format** — caught by phase 4, which is why phase 4 exists.
- **Docstring bloat.** ADX's output descriptions are long. Mitigated by the sectioned format;
  accepted otherwise, since the alternative is the values living somewhere the user cannot see.
- **Collision with in-flight authoring.** The generator rewrites files another session may be
  editing. This needs coordinating, not just scheduling.
- **`help()` regression** — verify a rendered docstring by eye in phase 1, not at the end.
