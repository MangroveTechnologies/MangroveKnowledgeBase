---
name: author-indicator-properties
description: Fill the authored (null) property fields on ONE indicator node in the signal/indicator ontology graph - the indicator description, per-input descriptions, and per-output units/range/description. Use when the builder emits nulls that cannot be lifted from source. Triggers on "author the properties for <Indicator>", "fill in the nulls for <Indicator>", "describe <Indicator>'s outputs".
---

# Author the null properties for one indicator

The builder (`ontology/build_signal_indicator_ontology.py`) lifts everything machine-derivable and
emits `null` for anything a human must write. This skill fills those nulls for **one indicator at a
time**.

> **Working a whole CLASS?** The per-class loop is: build -> review the nulls -> research the
> literature -> verify every claim by executing the indicator -> fill -> file anything the research
> turned up as a defect. This file is the innermost step of that loop. Design decisions are in
> `ontology/signal-indicator-ontology.md`; the research already done is in `ontology/research/`.

## `range` uses infinity, never null

An unbounded side is `Infinity` / `-Infinity`, not `null`:

    "range": [0, Infinity]          a price: non-negative, no ceiling
    "range": [-Infinity, Infinity]  a signed difference or position
    "range": [0, 100]               genuinely bounded
    "range": null                   NOT AUTHORED YET -- the only meaning a bare null carries

`null` inside a range said two different things at once -- "unbounded" and "nobody wrote this" --
and 62 outputs were carrying `[null, null]`, which looks authored and states nothing. Picking a side is per output, and `units` is NOT sufficient to decide it. `units: price` covers
both a LEVEL (an average, a band, VWAP -- non-negative, `[0, Infinity]`) and a DIFFERENCE of two
prices (`macd`, `mom`, `ao`, `dpo`, `squeeze_depth` -- signed, `[-Infinity, Infinity]`). A
difference of two prices is not a price: it crosses zero, and that crossing is usually the whole
point of the output.

Deciding it by `units` alone put a false `[0, Infinity]` on ten signed outputs, including two that
had already been authored correctly by hand. Measured afterwards on the fixture: `macd` is negative
on 582 bars, `squeeze_depth` on 1,047 of 1,294. **`[-Infinity, Infinity]` is the safe default** --
it never asserts a bound that is not there. Narrow it only where the quantity is provably
non-negative: a price level, an absolute magnitude (`|body|`, `range`, wick, ATR, true range), or a
ratio of two non-negative sizes.

The builder emits it from `inf` / `-inf` in a docstring `Range:` line. Note that parameters are
different: no parameter docstring declares `inf`, so a null `min`/`max` on a param means the source
states no bound, and asserting infinity there would invent a fact.

**Verify the range, do not reason about it.** `scripts/audit/audit_output_ranges.py` runs every
indicator over all seven fixtures and reports any observed value outside its declared range -- 929
checks. Run it after authoring a range. It would have caught all ten of the bad bounds above
immediately, and it reports anything it could not exercise as UNVERIFIED rather than counting it as
a pass.

**Serialisation caveat.** `json.dumps` writes bare `Infinity`, which Python accepts and a
JavaScript literal accepts (`Infinity` is a JS global) but the JSON spec does not. Every consumer
today is one of those two -- the builder, the harness, the tests and the renderer, which embeds the
graph as `const DATA = {...}` rather than parsing it. A strict third-party parser would need
`parse_constant`.


## The fields, in one place

Per output: `units`, `range`, `canonical_name`, `description`.
Per input: `description`.
Per node: `formula`, `interpretation`, `applications`, `abbreviation`.

**The node-level four are the ones that get forgotten.** The builder lifts some of them from the
knowledge-base markdown, so a node looks partly done when it is not -- coverage there is 41/94 for
`interpretation` and only 14/94 for `applications`. Fill them in the same pass as the outputs.

## Scope - read this before anything else

**ONE indicator. Nothing else.** Do not touch signals, strategies, classes, roles, composition, other
indicators, or the ontology model. If something adjacent looks wrong, note it in one line at the end
and keep going. Scope creep on this task has repeatedly wasted hours.

Do not restate the class scheme, re-derive the ontology, or summarise the corpus. No totals across
all 94 indicators unless explicitly asked.

## What is already populated - never author these

Lifted or derived by the builder. If you find yourself writing one of these, stop:

| field | source |
|---|---|
| `inputs` / `params` / `outputs` **keys** | `cls._data` / `cls._params` / `cls._outputs` |
| param `type` | docstring `params:` block |
| param `default` / `min` / `max` / `description` | the docstrings of signals that wrap this indicator |
| `reference` | first URL in the docstring |
| `warmup_bars` | unambiguous `min_periods` in `_compute` |
| `source_module` | file location |
| class | the `instance-of` edge, never a property |

## What you author

1. `description` - the indicator, one or two sentences
2. `inputs.<name>.description` - one short phrase per input
3. `outputs.<name>.units` - per output
4. `outputs.<name>.range` - per output
5. `outputs.<name>.description` - per output

## Method

**Read `_compute`. Not the name, not the docstring, not your prior knowledge of the indicator.**

```python
import inspect
from mangrove_kb.indicators.<module>_indicators import <Indicator>
print(inspect.getdoc(<Indicator>))
print(inspect.getsource(<Indicator>._compute))
```

The docstring is frequently absent or degenerate - 11 of 99 contain nothing but the indicator's own
name, and none describe an output. Where prose exists it usually just expands the acronym. Derive
meaning from the arithmetic.

If bounds are not obvious from the arithmetic, **run it** rather than guess:

```python
out = <Indicator>.compute({...synthetic OHLCV...}, {...default params...})
for k, s in out.items():
    v = s.dropna(); print(k, v.dtype, v.min(), v.max())
```

## Rules for each field

### `description`
State what the output measures and how it is constructed. **Must not merely restate the name** - "Bollinger
Bands" is not a description. Do not add attribution ("developed by...") unless the source says so;
never stamp an originator from your own knowledge.

### `inputs.<name>.description`
One phrase. There are only 7 distinct input names across the whole library - `close`, `high`, `low`,
`open`, `volume`, `price`, `indicator` - so reuse the same wording each time rather than inventing
variants.

### `outputs.<name>.units`
One of: `price` | `percent` | `ratio` | `dimensionless` | `count` | `boolean`

Never `null`. If an output is a flag rather than a measurement, that is `boolean`, not absence.

Per output, not per indicator. One indicator commonly mixes several - BollingerBands emits `price`
(mavg/hband/lband), `percent` (wband) and `ratio` (pband).

### `outputs.<name>.range`
**Always a 2-tuple `[min, max]`.** `null` in a slot means unbounded on that side. Never a bare `null`.

| value | meaning |
|---|---|
| `[0, 100]` | bounded both ways - absolute thresholds are meaningful |
| `[0, null]` | non-negative, unbounded above |
| `[null, null]` | unbounded both ways |

**Justify every bound from the computation.** `wband` is `[0, null]` because the rolling standard
deviation is non-negative, so `hband >= lband` and the width cannot go negative. A bound you cannot
justify from the arithmetic is a guess - use `null` instead.

Watch for the trap: a value that *usually* sits in a range is not bounded. `pband` is `(close - lband)
/ (hband - lband)`, normally 0..1, but **unclamped** - so `[null, null]`, and the description says so.
Getting this wrong matters because the `oscillator` class is defined by boundedness.

### `outputs.<name>.description`
What the series means, including the formula in plain terms where it clarifies. Call out anything a
consumer would get wrong - unclamped values, normalisation, one-sidedness (UlcerIndex only sees
downside), sign conventions (Williams %R runs 0 to -100).

## Where the values go

**Into the node being built, in the graph.** That is the whole answer.

**Do not create anything to hold them.** No sidecar data file, no authored-properties module, no
post-processing script, no new format. Do not edit the indicator source or its docstrings in
`mangrove_kb` - that is upstream of the graph and is not this skill's business.

**A skill is not a program.** Invoking this file loads instructions into context; YOU then read
`_compute` and write the values yourself. There is no code to write and nothing to automate. If you
find yourself reaching for the Write tool while running this skill, stop - that is the tell that you
have drifted from doing the task into building infrastructure for it.

The values are already durable, so do not invent somewhere for them to live. They go in the nodes;
`ontology/signal-indicator-ontology.json` is committed to the repository; and the builder carries
every authored value forward on rebuild, which is verified by the fact that running it twice is a
fixed point. If a rebuild ever drops an authored value, that is a bug in the carry-forward to be
fixed there - not a reason to introduce a sidecar file, a data module, or a new format.

## Verify before reporting

1. Apply the authored values to the node in `ontology/signal-indicator-ontology.json`
2. Rebuild in place and confirm nothing was lost:
   `python3 ontology/build_signal_indicator_ontology.py > /tmp/check.json` then diff it against the
   committed file. The builder carries authored values forward, so a rebuild must be a fixed point -
   any authored value that comes back `null` is a bug in the carry-forward, not a reason to re-author
3. Print the node and confirm every field you authored is populated and nothing lifted was overwritten
4. Show the **full JSON of the single node**, typed into the reply as a fenced block - the user cannot
   expand collapsed tool output

## `null` means one thing: not yet authored

This is an invariant, not a preference. **Nothing that is deliberately not-applicable may be left
`null`** - a null that means "n/a" is indistinguishable from a null that means "nobody has done this
yet", and the nulls ARE the worklist.

So a boolean flag output gets real values rather than nulls: `units: "boolean"` and `range: [0, 1]`,
justified because `np.where(cond, 1.0, 0.0)` emits only those two values. The builder aborts if an
output carries a `description` but a null `units` or `range`, so this cannot be skipped silently.

## Do not

- Guess a bound to avoid writing `null`.
- Author anything for an indicator in the `unclassed` class without asking - those are parked.
- Report corpus-wide totals when asked about one node.
