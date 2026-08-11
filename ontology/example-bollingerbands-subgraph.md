# Example subgraph: BollingerBands

The complete subgraph for a single indicator, for review. Scope is the **indicator layer only** --
no signals, no strategies, no roles.

**4 nodes, 3 edges.** Everything else about BollingerBands is properties on its node.

Ontology it specializes: `vendor/jarvis_graph/ontology.py`. No new primitives, no new relations.
Full model: `signal-indicator-ontology.md`.

---

## Shape

```
Procedure            (existing primitive)
    ^ is-a
Indicator            (entity type)
    ^ kind-of
volatility           (class)
    ^ instance-of
BollingerBands       (the indicator)
```

## Edges (3)

| from | relation | to | why |
|---|---|---|---|
| `Indicator` | `is-a` | `Procedure` | entity type under an existing primitive |
| `volatility` | `kind-of` | `Indicator` | subcategory of Indicator |
| `BollingerBands` | `instance-of` | `volatility` | class membership |

All three are in the `structural` branch of the relation hierarchy. Class is expressed as an edge and
**never** duplicated as a node property.

## Nodes (4)

### 1. `Procedure`

The vendored primitive. Not defined here -- referenced. In the emitted graph the primitive travels in
each atom's `kind` field rather than as a separate node, matching how the main graph surface does it.

### 2. `Indicator`

```json
{
  "id": "concept:indicator",
  "title": "Indicator",
  "kind": "Procedure",
  "summary": "A computation over one or more input series producing one or more numeric output series."
}
```

### 3. `volatility`

```json
{
  "id": "concept:volatility",
  "title": "volatility",
  "kind": "Concept",
  "summary": "Measures observed dispersion -- distance, width, or range."
}
```

Members (8): `ATR`, `TrueRange`, `NATR`, `UlcerIndex`, `BollingerBands`, `KeltnerChannel`,
`DonchianChannel`, `STARCBands`.

### 4. `BollingerBands`

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

**The description lives in the atom's native `summary`, not in `props`.** It is one fact and gets one
home: `atoms.json` and the GraphStore carry `summary`, while `viz.data_from_rows` reads
`props["description"]`, so the renderer maps `summary -> props.description` at render time. Emitting
both would store it twice.

---

## Provenance, field by field

| field | source | status |
|---|---|---|
| `inputs` keys | `cls._data` | **lifted** -- declared in the class |
| `params` keys | `cls._params` | **lifted** |
| `outputs` keys | `cls._outputs` | **lifted** |
| param `type` | docstring `params:` block | **lifted** |
| output `type` | docstring `Returns:` block | **lifted** -- uniformly `series`; the 27 pattern indicators declare no `Returns:` block but return Series too |
| param `default` / `min` / `max` / `description` | the BollingerBands *signal* docstrings, via AST resolution | **lifted**, but misplaced: the values live on signals and are triplicated across the three |
| `warmup_bars` | `min_periods=window` in `_compute` | **derived** |
| `reference` | first docstring URL | **lifted** |
| `source_module` | file location | **lifted** |
| `summary` (the description) | -- | **authored.** This docstring has no prose -- it is one of the 11 that carry only a title line |
| every output `units`, `range`, `description` | reading `_compute` | **authored.** Nothing declares any of the three, anywhere |

## Decisions this example encodes

- **7 outputs became 5.** `hband_indicator` and `lband_indicator` are removed: they are
  `np.where(close > hband, 1.0, 0.0)`, a boolean decision over a numeric series the indicator already
  emits, which is a signal rather than an indicator output. Verified free to remove -- grepped across
  `mangrove_kb`, `MangroveAI/src` and `MangroveOracle/src`: produced and never read.
- **No `primary_output`.** Which output matters belongs to the consumer, not the indicator:
  `bb_squeeze` reads `wband`, `bb_upper_breakout` reads `hband`, `bb_lower_breakout` reads `lband`.
  Three consumers, three outputs, none privileged.
- **No `originator`** field, and **no `class`** field -- class is the `instance-of` edge.
- `outputs` and `params` are **dicts**; the keys carry the names, so a parallel list is redundant.

## Conventions this example fixes

**`range` is always a 2-tuple `[min, max]`.** `null` in a slot means unbounded on that side; never a
bare `null` for the unbounded-both-ways case. So:

| value | meaning |
|---|---|
| `[0, 100]` | bounded both ways -- absolute thresholds are meaningful |
| `[0, null]` | non-negative, unbounded above |
| `[null, null]` | unbounded both ways |

Applied above, each justified from `_compute`: `wband` is `[0, null]` because the rolling standard
deviation is non-negative, so `hband >= lband` and the width cannot go negative. `mavg`, `hband` and
`lband` are `[null, null]` -- price units, with no bound the indicator imposes. `pband` is
`[null, null]` because it is explicitly not clamped, so it exceeds 1 above the upper band and drops
below 0 under the lower one, even though it sits in 0..1 most of the time.

**`type` on inputs is carried**, not dropped.

**`warmup_bars` holds an expression** (`window - 1`), because warmup is a function of the parameters
rather than a constant.

## Remaining work, not an open question

This node is populated for BollingerBands only. Every indicator needs the same manual read of
`_compute` -- and that covers **descriptions as much as units and range**, since almost none exist:

| field | scale | source |
|---|---|---|
| indicator `description` | 88 lifted, **11 to author** | lifted from the docstring's leading prose; BollingerBands is one of the 11 with only a title line |
| output `description` + `units` + `range` | 163 outputs | **authored** -- nothing declares any of the three |
| param `type` | 164 params | lifted from the docstring `params:` block |
| param `description` + `default` + `min`/`max` | 164 params | **liftable** for the 92 indicators a signal wraps; **authored** for the other 7 |
| input `description` | 7 distinct names, reused 237 times | **authored** once each |
| `warmup_bars` | 34 derived, 65 null | derived from an unambiguous `min_periods` |

Until output `range` is populated the `oscillator` class -- *defined* by boundedness -- cannot be
checked against declared data.

The builder emits this shape with `null` for anything not yet authored. For this node that is the
`summary`, `inputs.close.description`, and `units` / `range` / `description` on every output.

## Where the authored values go

**Into the docstring.** One source of truth, and the format is the `Args:` convention the codebase
already uses for parameters:

```
window (int): MA period for center band. Range: 5-100. Default: 20.
```

Applied to `Returns:`, which today carries names and types only:

```
Returns:
    mavg (series, price): rolling mean of close over window -- the center band.
    wband (series, percent): band separation as a percent of the center band,
        (hband - lband) / mavg * 100. Range: 0-.
```

Name, type, units, description, and `Range:` where a bound exists -- the same shape as `Args:`, so no
new convention is invented and the same parser handles both.
