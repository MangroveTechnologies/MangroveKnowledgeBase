# Signal / Indicator Ontology

Status: **in progress.** The indicator class axis and the indicator node-property schema are
settled. Signals, metadata placement and composition are not.
Design discussion and provenance: MangroveTechnologies/MangroveAI#1012.

This is a **domain specialization of the ontology this tool already vendors**
(`vendor/jarvis_graph/ontology.py`). It introduces **no new primitives and no new relation types** --
every node's primitive is one of the existing nine, every edge is one of the existing 28 relations.

Terminology, since the two words were being used interchangeably: a **taxonomy** is the
classification scheme (the kinds and their subsumption); an **ontology** contains the taxonomy plus
the other entity types, relations, properties and constraints. Taxonomy is a subset of ontology.

Throughout, claims are marked **verified** (read or executed against the installed `mangrove_kb`),
**lifted** (present in the source today), or **authored** (written by us; does not exist yet).

## Entity types

| type | primitive | why |
|---|---|---|
| Indicator | `Procedure` | a computation; its identity *is* its method |
| Signal | `Procedure` | also a pure computation; the boolean output is a property of it, not a different kind of thing |
| Strategy | `Schema` | a structured template/policy composing signals -- the primitive's own example is a runbook |

The three are `part-of` a root node, `concept:signal-indicator-ontology`, and the role axis is
`part-of` Signal. Without those four edges the graph has four disconnected tops and nothing states
that they belong to one ontology -- a consumer walking containment from any one of them sees only
part of the model, and the part it misses is Role.

The root is in the graph source rather than added by a viewer. A renderer that invents it asserts a
fact about the ontology in display code, where nothing can query it and the next rebuild does not
know it exists.

## Class axis (indicators)

`Class` is the name of the axis, not a node. The classes are subcategories of Indicator. The whole
subgraph for one indicator is four nodes and three edges:

```
Procedure            (existing primitive)
    ^ is-a
Indicator
    ^ kind-of
volatility           (or any of the other six)
    ^ instance-of
BollingerBands
```

| relation | meaning in this ontology |
|---|---|
| `is-a` | category membership (graded) |
| `kind-of` | subcategory |
| `instance-of` | specific exemplar of a concept |

Class membership currently uses `instance-of`, which is **crisp**. If graded membership is wanted
later (an indicator strongly one class and weakly another), that bottom edge becomes `is-a`.

**Class is an edge, never a property.** It must not also appear as a field on the node, or there are
two representations of one fact.

### The seven classes -- 94 indicators

| class | n | definition |
|---|---|---|
| `pattern` | 27 | shape of one or a few bars (candlestick geometry) |
| `momentum` | 21 | rate of change -- how fast, and in which direction, the input is moving |
| `averaging` | 16 | emits a reference level in price units, produced by averaging over a window |
| `oscillator` | 12 | bounded output where absolute thresholds are meaningful |
| `volatility` | 8 | observed dispersion -- distance, width, or range |
| `flow` | 5 | running accumulation; level is arbitrary, direction carries the meaning |
| `unclassed` | 1 | not yet determined -- named so the gap stays visible |

`unclassed` holds `TTMSqueeze` alone. Of the original five: `EPMA`, `Ichimoku` and `HeikinAshi` are
`averaging` -- each emits reference levels in price units, which is what the class asks about the
output, whatever the indicator is used for. `Divergence` turned out not to be an indicator at all
(four boolean outputs, no measurement) and was replaced by `SwingDelta`; see below. `TTMSqueeze`
emits two booleans beside one number and is pinned with `MultiTFTrend`.

### Basis of division, and what it rejects

The class answers **what the output tells you about the input**. Two consequences, both deliberate
departures from the current file layout and from TA-Lib / pandas-ta:

- **There is no `trend` class.** Nothing measures trend. A moving average emits a reference level;
  ADX measures directional strength. "Trend" is an interpretation laid over those, and it is the
  word that attracted CCI, KST, TRIX and DPO into `trend_indicators.py` because traders *use* them
  for trend work. Classing by use case rather than by output is the error being removed.
- **There is no `volume` class.** OBV accumulates; PVO measures rate of change. Both consume volume.
  Volume is an **input**, not a measurement. Confirmation this is right: `flow` also covers the
  on-chain and ETF netflow measures, so the class holds across completely different inputs.

`momentum` absorbed directional strength (ADX, Aroon, Vortex, MultiTFTrend). Those are unsigned or
mixed-sign where the rest of momentum is signed; that distinction is left to the description rather
than the class, because consumers reason about derived signals and can read it.

### Removed from the indicator layer

**Indicators are measurements, never verdicts. Signals are verdicts.**

That is the whole criterion. An indicator states what it measured; deciding what the measurement
means is the signal layer's job.

`ATRTrailingStop`, `SuperTrend` and `PSAR` fail it and are excluded from this ontology and from the
graph. SuperTrend emits `direction` (+1 long / -1 short) and NaNs its bands according to that
verdict; PSAR emits `psar_up_indicator` / `psar_down_indicator`, which are flip flags;
ATRTrailingStop does both -- its stop level accumulates forward and it emits `direction` too. The
measurement underneath the ATR-based ones is ATR, which is already classed.

This generalises the boolean-output rule below: a boolean is a verdict with two values, and the
same argument applies to a ternary or any other flag.

**Two of the original five were on that list wrongly**, and the list turns out to have been built
from what things were CALLED rather than from what they do. Both were found by reading the
implementation; both were fixed by renaming and rewriting the prose, not by changing behaviour.

**`ChandelierExit` was on that list and should not have been.** It emits two price levels, both
defined on every bar, both plain functions of the window -- and its own docstring said it was not a
state machine. It was excluded for a property it does not have. It is now `ChandelierLevels`, class
`volatility`, living in `volatility_indicators.py` beside the ATR it is built on, with outputs
renamed `high_offset` / `low_offset` and its two signals renamed `cl_below_high_offset` /
`cl_above_low_offset` (old names aliased). Note the two offsets are anchored to OPPOSITE extremes,
so they are not an upper and a lower band and do cross -- 27% of bars on the BTC fixture.

**`VolatilityStop` was on it too.** Its own docstring called it a "standard-deviation-based
volatility envelope" and said it "is not a state machine (no ratcheting)"; its outputs were already
named `vstop_hband` / `vstop_lband`; and `hband >= lband` holds on 100% of bars, so unlike the
Chandelier offsets it is a genuine band pair. Only the word "Stop" was positional. It is now
`VolatilityEnvelope`, class `volatility`, with signals `ve_above_upper` / `ve_below_lower`.

**`Divergence` was not an indicator.** All four of its outputs were `dtype=bool` -- it stated that
a divergence had occurred rather than measuring anything. What it measures underneath is two
changes: how far price moved between its last two confirmed swings, and how far a companion
indicator moved between the two that pair with them. That is now `SwingDelta`, class `momentum`,
and the four sign comparisons moved into the four signals that read it. Proven equivalent: the sign
predicates reproduce the old booleans bar-for-bar on all 1,294 fixture bars, and the rewritten
signals disagree with the old implementation on zero of 1,254 expanding-window evaluations.
`Divergence` itself is kept, deprecated and unchanged, for anything already calling it.

**Known violation, pending a decision:** `MultiTFTrend` emits `higher_tf_trend`, a ternary
-1 / 0 / +1 state, and is currently classed `momentum` with two signals that read the verdict
directly. `TTMSqueeze` is the same shape -- `squeeze_on` and `squeeze_fired` are booleans beside a
real-valued `momentum` -- and is held in `unclassed` for the same reason. `SwingDelta` is the
template for fixing both. By the rule above it does not belong in the indicator layer as it stands; the measurement
is the normalised higher-timeframe slope, and the sign should be the signal's decision. Left in
place deliberately rather than silently, so the rule and the data are not quietly inconsistent.

---

## Node properties (indicators)

**Outputs, inputs and parameters are properties of the indicator node, not nodes themselves.** They
have no identity apart from the indicator -- nothing references `wband` without BollingerBands.

### Where each property comes from

| property | source | note |
|---|---|---|
| `inputs` keys | `cls._data` | **verified.** Lift from the class attribute, NOT from the docstring |
| `params` keys | `cls._params` | **verified.** Same |
| `outputs` keys | `cls._outputs` | **verified.** Same |
| param `default` / `min` / `max` / `description` | signal docstring `Args:` prose | **lifted** but misplaced -- see coverage below |
| `warmup_bars` | `min_periods` in `_compute` | **verified** by reading |
| `reference` | docstring URL | **lifted**, 39 of 99 have one |
| indicator `description` | -- | **must be authored.** Most docstrings open with the indicator's own name and say nothing |
| output `units` / `description` | -- | **must be authored.** Nothing declares either, anywhere |

The structural three (`inputs`, `params`, `outputs`) come from the class attributes rather than the
docstring on purpose. The docstring `Args:`/`Returns:` blocks currently duplicate them, and parsing
prose back would make it a second source of truth for something the code already declares. The right
direction is to **generate** those docstring sections from the attributes.

### Coverage, measured across all 99

```
docstring Args:/Returns: disagreeing with declared attributes      0        (duplicated but consistent)
INDICATORS with an Args: block                                    75        of which per-param prose:   0
SIGNALS    with an Args: block                                   243        of which per-param prose: 243
indicator Returns: blocks describing what an output means           0        (names and types only)
declarations of Range / Default / Bounds / Min / Max / Units        0
```

Two conclusions. First, human-readable parameter text exists at **full coverage on the signal side
and zero on the indicator side** -- so `param_spec` is not missing, it is misplaced (and triplicated:
`window`'s range and default appear in all three BollingerBands signal docstrings, reachable only
through them). Second, **nothing anywhere states an output's units, range or meaning**, which means
the `oscillator` class -- defined by boundedness -- currently cannot be verified against declared
data. It rests on reading implementations.

### Worked example: BollingerBands

The complete node. Four nodes and three edges in the graph (above); everything else is here.

```json
{
  "id": "procedure:indicator-bollingerbands",
  "title": "BollingerBands",
  "kind": "Procedure",
  "summary": "Rolling mean of close with symmetric bands placed window_dev rolling standard deviations above and below it. The band separation widens as realized volatility rises and contracts as it falls.",
  "epistemic": "ratified",
  "status": "ratified",
  "props": {
    "source_module": "volatility_indicators",
    "reference": "https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands",
    "warmup_bars": "window - 1",

    "inputs": {
      "close": {"type": "series", "description": "closing price"}
    },

    "params": {
      "window":     {"type": "int", "default": 20, "min": 5, "max": 100,
                     "description": "MA period for center band"},
      "window_dev": {"type": "int", "default": 2,  "min": 1, "max": 5,
                     "description": "Standard deviation multiplier"}
    },

    "outputs": {
      "mavg":  {"type": "series", "units": "price",   "range": [null, null],
                "description": "rolling mean of close over window -- the center band"},
      "hband": {"type": "series", "units": "price",   "range": [null, null],
                "description": "mavg + window_dev * rolling stdev -- the upper band"},
      "lband": {"type": "series", "units": "price",   "range": [null, null],
                "description": "mavg - window_dev * rolling stdev -- the lower band"},
      "wband": {"type": "series", "units": "percent", "range": [0, null],
                "description": "band separation as a percent of the center band, (hband - lband) / mavg * 100. Non-negative because the rolling stdev cannot be negative. Scale-free, so comparable across assets and price levels"},
      "pband": {"type": "series", "units": "ratio",   "range": [null, null],
                "description": "position of close between the bands, (close - lband) / (hband - lband). 0 at the lower band, 1 at the upper, but NOT clamped -- exceeds 1 above hband and drops below 0 under lband. NaN when the bands coincide"}
    }
  }
}
```

Notes on the example:

- `outputs` and `params` are **dicts, not lists plus a parallel spec** -- the keys carry the names,
  so a separate list is redundant.
- There is **no `primary_output`**. Which output matters is a property of the consumer, not the
  indicator: `bb_squeeze` reads `wband`, `bb_upper_breakout` reads `hband`, `bb_lower_breakout` reads
  `lband`. Three consumers of one indicator, three different outputs, none privileged.
- There is **no `originator`** field.
- There is **no `class`** field -- that is the `instance-of` edge.
- `hband_indicator` and `lband_indicator` are absent because they are leaving the indicator (below),
  taking BollingerBands from 7 outputs to 5.
- The indicator `description` and all five output `description`s and `units` are **authored**. None
  of it exists in the source today.

### Schema conventions

**`null` means "not yet authored" -- everywhere, with no exceptions.** The nulls are the worklist, so
a field that is *deliberately* not applicable must never be null; it would be indistinguishable from
one nobody has filled in yet. A boolean flag output therefore carries `units: "boolean"` and
`range: [0, 1]` rather than nulls. The builder **aborts** if any output has a `description` but a
null `units` or `range`, which is the signature of prose authored without the machine-readable
fields.

**`range` is always a 2-tuple `[min, max]`.** `null` in a slot means unbounded on that side; never a
bare `null` for the unbounded-both-ways case. This is the same invariant one level down: a bare
`null` reads as unauthored, a 2-tuple as authored, and only inside the tuple does `null` mean
unbounded.

| value | meaning |
|---|---|
| `[0, 100]` | bounded both ways -- absolute thresholds are meaningful |
| `[0, null]` | non-negative, unbounded above |
| `[null, null]` | unbounded both ways |

**`type` is carried on inputs, params and outputs.** **`warmup_bars` holds an expression**
(`window - 1`), because warmup is a function of the parameters rather than a constant.

**The description lives in the atom's native `summary`, never also in `props`.** One fact, one home:
`atoms.json` and the GraphStore carry `summary`, while `viz.data_from_rows` reads
`props["description"]`, so the renderer maps `summary -> props.description` at render time.

### Remaining work: every indicator needs a manual review

The builder lifts everything machine-derivable and emits `null` for the rest, so the gap is visible in
the graph itself. What is left is a per-indicator read of `_compute`.

| field | scale | source |
|---|---|---|
| `summary` (the description) | **88 lifted, 11 to author** | **lifted** from the docstring's leading prose. The 11 with nothing but a title line: `SMA`, `EMA`, `WMA`, `Ichimoku`, `BollingerBands`, `DonchianChannel`, `UlcerIndex`, `NVI`, `DailyReturn`, `DailyLogReturn`, `CumulativeReturn` |
| output `units` + `range` + `description` | **163 outputs** | **authored.** Nothing in the source declares any of the three. This is the bulk of the work |
| param `type` | **164 params** | **lifted** from the docstring `params:` block -- the one structural fact absent from the class attributes, since `_params` holds names only |
| output `type` | **163 outputs** | **lifted** from the docstring `Returns:` block; uniformly `series`. The 27 pattern indicators declare no `Returns:` block but return Series too |
| param `description` + `default` + `min` / `max` | **128 of 154 lifted** | **lifted** from the docstrings of the signals that wrap the indicator, resolved by AST call-graph transitively through module helpers. The 26 that did not lift belong to indicators no signal exposes those params through -- the moving-average family (`WMA`, `DEMA`, `TEMA`, `TRIMA`, `SMMA`, `HMA`, `EPMA`), the multi-window oscillators (`Ichimoku`, `KST`, `UltimateOscillator`, `AwesomeOscillator`), plus `DonchianChannel.offset` and `VPT.smoothing_factor` |
| input `description` | **7 distinct series names** | **authored** once each -- `close` (88 uses), `high` (54), `low` (54), `open` (26), `volume` (13), `price` (1), `indicator` (1). Reused 237 times, so 7 definitions rather than 237 jobs |
| `warmup_bars` | **34 derived, 65 null** | **derived** from an unambiguous `min_periods` in `_compute`; null where there is none or more than one |

### Where the authored values go -- settled

**Into the node, in the graph.** The builder emits the node with `null` in every slot no source
states; those nulls are the worklist, and filling them is a manual read of `_compute` performed with
`.claude/skills/author-indicator-properties/SKILL.md`.

**They do NOT go into the `mangrove_kb` docstrings, and no new store is created to hold them.** The
KnowledgeBase docstrings are upstream of this graph: they carry signal metadata that
`docstring_parser.py` already parses, and writing ontology properties into them would put this
tool's output into another repo's source. Three separate mechanisms were proposed for these values
during the design -- a sidecar data module, the docstrings, and a post-build script -- and all three
were rejected. The node is the home; there is nothing to build.

The two input-vocabulary oddities are the same indicator: `Divergence`, `_data=['price','indicator']`
-- `price` where 88 others say `close`, and `indicator` because it consumes another indicator's
output. It is the relational case sitting in `unclassed`, so both ride along with that decision.

Until output `range` is populated the `oscillator` class -- *defined* by boundedness -- cannot be
checked against declared data and rests on implementation reading.

---

## Indicator-layer decisions taken

### Boolean outputs leave the indicator layer

Our ontology has Indicator emitting numeric series and Signal emitting a boolean predicate.
Determined **by execution**, at least **23 indicator outputs are boolean-valued**: 18 of the 27
pattern indicators, MARibbon's three (`ribbon_bullish` / `ribbon_bearish` / `ribbon_tangled`,
`dtype=bool`), and BollingerBands' two. KeltnerChannel, Divergence and TTMSqueeze did not exercise on
synthetic parameters, so the count is higher -- KC declares the same two flag outputs as BB.

**BollingerBands and KeltnerChannel drop `hband_indicator` and `lband_indicator`.** They are
`np.where(close > hband, 1.0, 0.0)` -- a decision *over* a numeric series the indicator already
emits. Verified free to remove: grepped across `mangrove_kb`, `MangroveAI/src` and
`MangroveOracle/src`, both are **produced and never read**. MARibbon is the same shape.

### Two duplicate pattern indicators are removed

`HangingMan._compute` is `Hammer._compute` with the output key renamed; `ShootingStar._compute` is
`InvertedHammer._compute` renamed. Byte-identical computation. A hanging man genuinely *is* a hammer
-- what distinguishes them is the prior trend, which the code does not encode. Two names for one
measurement with the distinguishing input absent.

When executed, this takes the graph from 94 indicators to 92. The committed graph still has 94; the
removal has been decided, not performed.

### Candle geometry becomes an indicator

`indicators/pattern_utils.py` already computes `candle_body`, `candle_range`, `upper_wick`,
`lower_wick`, `body_ratio` -- module-level functions rather than an `IndicatorInterface` subclass.
17 of the 27 pattern indicators call it. Promote it to a `CandleGeometry` indicator emitting numeric
outputs only, replacing `is_bullish`/`is_bearish` with a **signed** body (`close - open`) so the new
indicator does not reintroduce the boolean-output problem above.

The 8 multi-bar relational patterns (Engulfing, Harami, PiercingLine, DarkCloudCover,
ThreeInsideUp/Down, InsideBar, OutsideBar) are `.shift(1)` comparisons of raw OHLC with no derived
numeric measurement underneath. They ride on nothing, and inventing an indicator for them would be
manufacturing a layer.

Consequent rule: not "every signal rides on an indicator" but **"a signal is a predicate over
series, which may be indicator outputs or raw OHLC."** `Requires:` already declares which.

---

## Role axis (signals)

```
Property             (existing primitive)
    ^ is-a
Role                 -- part-of Signal
    ^ kind-of
trigger | filter | arm
```

Role is `part-of` **Signal**, not a peer of it under the root: every `has-role` edge in the graph
starts at a signal and none at an indicator, so it is an axis of Signal specifically. `part-of`
rather than `kind-of` because a role is not a kind of signal.

Role is **contextual**, class is **intrinsic** -- which is why they attach to different branches of
the relation hierarchy: class via `structural` (`kind-of`, `instance-of`), role via `descriptive`
(`has-role`). An indicator *is* a volatility indicator; a signal *plays* the trigger role inside a
strategy.

`confirmation` was considered and dropped: it describes why a signal is in a strategy, not how its
boolean behaves, so it mixes two bases into one enum.

## Naming decisions

- The axis word is **`Class`** -- not `category` (live in four MangroveAI API response bodies, and
  associated with the mixed-basis library convention) and not `type` (4,359 occurrences across
  MangroveAI and Oracle for the *wrong* concept, including persisted strategy `rules` JSON, Oracle's
  backtest contract, and SIEVE feature extraction).
- `Type:` in KB docstrings is **deprecated, not repurposed**. Its TRIGGER/FILTER values migrate to
  `Role:` unchanged, so the migration is a rename with identical values.

## Not yet covered

1. **Signal class** -- whether it is inherited from the indicator. Evidenced: AST call-graph
   resolution shows 212 of 223 price signals resolve to exactly one indicator, 0 unresolved. The 11
   exceptions are 7 pattern aggregates and 4 RSI divergences.
2. Whether signals share these same seven classes.
3. The 25 non-price signals -- `onchain` (10), `defi_pro` (10), social (5, MangroveAI-local). They
   have no indicator layer, so inheritance cannot reach them.
4. How role is determined -- declared, or derived from the signal's predicate form.
5. Relations beyond the three structural ones: `derived-from` (signal to indicator, with the output
   name as an edge property), `part-of` (signal to strategy), `requires` (input series),
   `has-state` (enabled/disabled). Proposed, not ratified.
6. Where the metadata physically lives (a `Class:` docstring tag) and the `Type:` to `Role:` migration.
7. Strategy has no structure yet beyond its primitive.
8. Constraints -- nothing yet about what makes a composition legal, which is the part of an ontology
   that does the enforcing.
9. **Lookback tolerance** -- every signal decides on the final bar, which makes conjunctions of rare
   events brittle. A `last N bars` tolerance is the same measurement with a looser time bound; it is
   not a role change. Filed on #1012.

## Building

```
python ontology/build_signal_indicator_ontology.py > ontology/signal-indicator-ontology.json
```

`ontology/signal-indicator-ontology.json` is the ontology of record and **is committed**. Authored
values live in the nodes, so the builder carries every authored value forward from the existing file
and a rebuild is a fixed point -- running it twice produces identical output. A lift wins where a
source supplies one; wherever a run produces `null` and the previous build had a value, the previous
value is kept.

The builder reads this repository's `mangrove_kb` package for ground truth and **aborts** rather than
emit a graph if any assigned indicator does not exist, any present indicator is neither assigned nor
explicitly removed, or any indicator appears in two classes. The class assignments are data in that
script, so they are reviewable and diffable.

Rendering the graph to an interactive page is deliberately not part of this repository. The viewer
is a separate, differently-licensed component; it consumes the JSON emitted here.
