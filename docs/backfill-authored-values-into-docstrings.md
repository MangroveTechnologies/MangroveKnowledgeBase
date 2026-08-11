# Scope: backfill authored values into docstrings, make the build deterministic

**Status:** COMPLETE (p1-p6). **Owner:** unassigned. **Blocks:** nothing. **Unblocks:** shipping
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

**The docstrings and the code become the single source of truth. The graph becomes a derived
artifact.**

Every authored fact lives in the docstring of the thing it describes; every derived fact is read from
the code. Nothing falls outside those two, and the JSON is regenerable from a clean tree at any time.

Concretely, so that:

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

## Format — settled in phase 1, proven lossless on Bollinger Bands

Not a raw JSON blob. Dumping the node verbatim into `__doc__` would make `help()` unreadable, which
forfeits the reason for moving the values there at all. The sections below extend the format the
parser already handles (`Args:`, `Returns:`, `Type:`, `Requires:`).

```
Bollinger Bands

    Volatility bands placed above and below a moving average, with width determined by standard
    deviation.

    <any further prose, unchanged -- design rationale, caveats>

    Abbreviation: BB
    Reference: https://chartschool.stockcharts.com/...

    Formula:
        Middle Band = SMA(Close, 20)
        Upper Band = SMA + (2 * Standard Deviation)

        Bandwidth = (Upper - Lower) / Middle * 100

    Inputs:
        close: closing price

    Outputs:
        mavg [price, 0..inf]:
            rolling mean of close over window -- the center band
        wband [percent, 0..inf] "BandWidth":
            band separation as a percent of the center band, (hband - lband) / mavg * 100.
            Non-negative because the rolling stdev cannot be negative
        pband [ratio, -inf..inf] "%B":
            position of close between the bands. NOT clamped -- exceeds 1 above hband

    Interpretation:
        - Price at upper band: Potentially overbought / strong trend

    Applications:
        - Mean reversion trades at bands in ranges

    Args:      <unchanged -- types come from the signature>
    Returns:   <unchanged>
```

Rules:

* **Output line** is `name [units, lo..hi]` plus an optional `"canonical name"`, then an indented
  description that may wrap freely. Unbounded is `-inf`/`inf`, never null.
* **Summary** is the first prose paragraph. Everything after it, up to the first section header, is
  free prose and is preserved untouched.
* **A section that has no content is omitted**, not written empty.

### Three things phase 1 turned up

1. **Indicator and signal docstrings have different shapes, and it cannot be guessed.** An indicator
   CLASS docstring opens with a name line (`Bollinger Bands`); a signal FUNCTION docstring opens with
   the summary itself. Parsing on a heuristic silently mis-read the signal's summary as
   `"Type: FILTER Requires: Close"`. The builder knows which kind of object it is holding, so it
   passes `has_title` explicitly. **No heuristic.**
2. **Signals carry no `interpretation` or `applications` keys at all** -- absent, not null. The format
   must not require them, and the round-trip check must compare absent-to-absent rather than treating
   a missing section as an empty one.
3. **`canonical_name` is the literal string `"none"`** when an output has no canonical name, not
   `null`. The `"..."` on the output line is simply omitted in that case and parses back to `"none"`.

### Proof

Both shapes round-trip exactly against the committed graph -- every authored field, no exceptions:

```
LOSSLESS   indicator BollingerBands     (summary, formula, abbreviation, reference,
                                         interpretation, applications, input descriptions,
                                         5 outputs x units/range/canonical_name/description)
LOSSLESS   signal bb_above_upper        (summary, formula, reference, absent abbreviation,
                                         absent interpretation/applications, input descriptions,
                                         1 output x 4 fields)
```

`help()` stays readable: 64 lines, only two over 100 characters, one of which is the reference URL
and cannot wrap.

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

- **`knowledge-base/*.md` stops being a source of truth entirely.** Its values -- `formula`,
  `interpretation`, `applications`, `abbreviation` -- move into docstrings with everything else, and
  the builder stops reading it. The *files* are not deleted, because they are also an independent
  published corpus with their own table of contents, served by the document tools. But after this
  they feed nothing: no value in the graph comes from them. Retiring the files is a separate
  decision.
- The `.claude/skills/author-*-properties` skills stay. New indicators still need authoring; only the
  target changes, from the JSON to the docstring. They need updating, not deleting.
- Edges, and everything else in the derived column above.

## Phases

| # | phase | done when |
|---|---|---|
| 1 | ~~settle the docstring format on 2–3 real indicators, both directions~~ | **DONE** — lossless on BollingerBands + bb_above_upper |
| 2 | ~~extend the parser to read it~~ | **DONE** — `parse_authored`, format enforced |
| 3 | ~~run the generator across all 22 files~~ | **DONE** — 289 docstrings across 12 files |
| 4 | ~~rebuild with carry-forward off, diff~~ | **DONE** — atoms + relations identical |
| 5 | ~~delete `_carry`, the KB lift, the precedence chain~~ | **DONE** — one builder, one JSON, 122 lines removed |
| 6 | ~~pin it~~ | **DONE** — `tests/test_build_is_deterministic.py` |

Phase 4 is the gate. If it does not come out identical, the format is lossy and phase 1 was wrong.

## Risks

- **Lossy format** — caught by phase 4, which is why phase 4 exists.
- **Docstring bloat.** ADX's output descriptions are long. Mitigated by the sectioned format;
  accepted otherwise, since the alternative is the values living somewhere the user cannot see.
- **Collision with in-flight authoring.** The generator rewrites files another session may be
  editing. This needs coordinating, not just scheduling.
- **`help()` regression** — verify a rendered docstring by eye in phase 1, not at the end.


---

## Outcome

Four fields were AUTHORED that this scope classified as derived. Each was found by a diff, not by
reading:

- **`warmup_bars`** — 53 indicators disagreed with any `min_periods` guess.
- **param `description`** — for all 126 indicator params.
- **param `default` / `min` / `max`** — for the params of indicators no signal wraps, which had
  survived only by carry-forward.
- **the `DEPRECATED:` marker** — line-anchored, so re-wrapping the summary silently lost one
  `supersedes` edge.

The pattern: anything that survived only in the JSON looked derived, because nothing in the source
disagreed with it. The diff is what distinguished them.

`ontology/signal-indicator-ontology.md` and both `.claude/skills/author-*-properties` skills were
updated — they instructed authoring into the JSON, which the next build now overwrites.
