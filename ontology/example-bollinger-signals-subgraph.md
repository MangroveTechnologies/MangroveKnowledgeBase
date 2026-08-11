# Example subgraph: the Bollinger signals

The complete subgraph for the five signals built on `BollingerBands`, for review. Scope is the
**signal layer only** -- the indicator subgraph is `example-bollingerbands-subgraph.md` and is not
restated here.

**5 new nodes, 15 new edges.** Every scaffold node they attach to already exists in the committed
graph, and **no new relation vocabulary is introduced** -- every relation used is already defined in
`vendor/jarvis_graph/ontology.py`.

This is the signal counterpart of the indicator worked example, and exists for the same reason: to
settle the node shape on one concrete set before generating 247 of them.

Full model: `signal-indicator-ontology.md`.

---

## Why these five

They cover the variety that a single signal would hide:

- **both roles** -- 3 TRIGGER, 2 FILTER
- **three different indicator outputs consumed** -- `hband`, `lband`, `wband`
- **an extra parameter on one of them** -- `bb_squeeze` takes `threshold`, the others do not
- **two signals that are identical on every structural field** -- `bb_above_upper` and
  `bb_upper_breakout` have the same inputs, the same params and the same output, and differ only by
  role. On the 1,294-bar BTC daily fixture they fire on 104 and 46 bars respectively.

Two of the five (`bb_above_upper`, `bb_below_lower`) were `hband_indicator` / `lband_indicator`
outputs on the indicator until they were moved into the signal layer, so this set also exercises the
case where a signal carries content that used to be an indicator output.

---

## Shape

```
Procedure            (existing primitive)
    ^ is-a
Signal               (entity type -- already in the graph)
    ^ instance-of
bb_upper_breakout    (the signal)
    |
    | uses                       has-role
    v                               v
BollingerBands                   trigger
(the indicator)                  (role value)
```

A signal sits under `Signal` the way an indicator sits under a class. Its **class is not stored**: it
is reached by following `uses` to `BollingerBands` and then that indicator's `instance-of` edge to
`volatility`. This is the same rule the indicator layer already follows -- class is an edge, never
duplicated as a property -- applied one level out.

## Edges (15)

Each of the five signals carries the same three:

| relation | to | category | why |
|---|---|---|---|
| `instance-of` | `Signal` | structural | entity type |
| `uses` | `BollingerBands` | associative | the indicator it invokes |
| `has-role` | `trigger` / `filter` | descriptive | role |

Roles: `bb_upper_breakout`, `bb_lower_breakout`, `bb_squeeze` -> `trigger`;
`bb_above_upper`, `bb_below_lower` -> `filter`.

`Signal is-a Procedure`, `trigger|filter|arm kind-of Role` and
`BollingerBands instance-of volatility` are all already in the committed graph.

### On `uses` rather than `derived-from`

The vendored ontology glosses `uses` as *"runtime invocation/orchestration (skill->tool,
procedure->tool)"*, which is exactly what happens: a signal is a `Procedure` and it calls
`BollingerBands.compute()` when evaluated.

Two alternatives were considered and rejected:

- **`derived-from`** (`associative`, acyclic) is glossed *"genealogy / provenance"*. That is
  provenance of knowledge -- where a claim came from -- not dataflow between two procedures at
  runtime. Its acyclicity is the one thing it has over `uses`, and it buys nothing here: signals do
  not invoke signals and indicators do not invoke signals, so no cycle is reachable.
- **`requires`** (`causal`, acyclic) is the KST surmise relation, about prerequisite ordering in a
  learner's knowledge state. The ontology comment explicitly says `uses` is *"NOT a prerequisite
  (that's the KST `requires`) -- deliberately associative so it stays OUT of the surmise lattice."*
  Putting every signal->indicator pair into the surmise lattice would distort it.

An earlier draft of this document asserted `derived-from`, and called it both *new* and *structural*.
It is neither: it already exists, and it is associative. Recorded because the mistake is easy to
repeat.

---

## Field mapping: all 17 fields of an indicator node

Read against a real indicator node rather than from memory -- 6 top-level fields and 11 props. Every
one is accounted for; the point of the exercise is that none is silently dropped.

| field | signal answer | lifted or authored |
|---|---|---|
| `id` | `procedure:signal-<name>` | generated |
| `title` | the registered name | **lifted** -- `RuleRegistry.names()` |
| `kind` | `Procedure` | fixed -- same primitive as an indicator |
| `summary` | docstring prose above the sections | **lifted** |
| `epistemic` | `ratified` | fixed -- as every indicator node |
| `status` | `ratified` | fixed |
| `source_module` | `volatility` | **lifted** -- file |
| `reference` | -- | **authored** (null) |
| `warmup_bars` | `window + 1` / `window` | **lifted** -- the `len(df) < ...` guard |
| `abbreviation` | -- | null. See *Conventions* |
| `usage_example` | generated `RuleRegistry.evaluate(...)` call | generated |
| `formula` | the predicate | **authored** (null) -- see *Decisions* |
| `interpretation` | -- | not a field. Reached through `uses` |
| `applications` | -- | not a field. Reached through `uses` |
| `inputs` | raw series, e.g. `close` | **lifted** -- `Requires:` |
| `params` | type, description, min, max, default | **lifted** -- `Args:` block |
| `outputs` | one boolean | **lifted** -- return annotation + `Returns:` |

One prop is added that indicators have no equivalent for:

| field | signal answer | lifted or authored |
|---|---|---|
| `consumes` | `{"BollingerBands": ["hband"]}` | **lifted** -- AST |

**16 of 18 rows need no human.** Only `reference` and `formula` are authored; `abbreviation` is a
convention question rather than content.

---

## Nodes (5)

### 1. `bb_upper_breakout`

```json
{
  "id": "procedure:signal-bb-upper-breakout",
  "title": "bb_upper_breakout",
  "kind": "Procedure",
  "summary": "Detect price breaking above the upper Bollinger Band. Fires on the bar where price crosses above the upper band, not while price remains above it. Crypto assets frequently test bands during high volatility; use with volume confirmation.",
  "epistemic": "ratified",
  "status": "ratified",
  "props": {
    "source_module": "volatility",
    "reference": null,
    "warmup_bars": "window + 1",
    "abbreviation": null,
    "usage_example": "RuleRegistry.evaluate({'name': 'bb_upper_breakout', 'params': {'window': value, 'window_dev': value}}, df)",
    "formula": null,
    "consumes": {
      "BollingerBands": ["hband"]
    },
    "inputs": {
      "close": {
        "type": "series",
        "description": "closing price"
      }
    },
    "params": {
      "window": {
        "type": "int",
        "default": 20,
        "min": 5,
        "max": 100,
        "description": "MA period for center band"
      },
      "window_dev": {
        "type": "int",
        "default": 2,
        "min": 1,
        "max": 5,
        "description": "Standard deviation multiplier"
      }
    },
    "outputs": {
      "fired": {
        "type": "bool",
        "units": "boolean",
        "range": [0, 1],
        "canonical_name": "none",
        "description": "True on the bar where close crosses above upper band"
      }
    }
  }
}
```

### 2. `bb_lower_breakout`

Identical in shape; `consumes` is `{"BollingerBands": ["lband"]}`, `warmup_bars` is `window + 1`,
role is `trigger`, and the output description is "True on the bar where close crosses below lower
band".

### 3. `bb_squeeze`

The one with a third parameter, and the one that consumes a different output:

```json
{
  "id": "procedure:signal-bb-squeeze",
  "title": "bb_squeeze",
  "kind": "Procedure",
  "summary": "Detect Bollinger Band squeeze onset (low volatility, potential breakout). Fires on the bar where band width drops below the threshold, not while it remains below.",
  "epistemic": "ratified",
  "status": "ratified",
  "props": {
    "source_module": "volatility",
    "reference": null,
    "warmup_bars": "window + 1",
    "abbreviation": null,
    "usage_example": "RuleRegistry.evaluate({'name': 'bb_squeeze', 'params': {'window': value, 'window_dev': value, 'threshold': value}}, df)",
    "formula": null,
    "consumes": {
      "BollingerBands": ["wband"]
    },
    "inputs": {
      "close": {"type": "series", "description": "closing price"}
    },
    "params": {
      "window":     {"type": "int",   "default": 20,  "min": 5, "max": 100, "description": "MA period for center band"},
      "window_dev": {"type": "int",   "default": 2,   "min": 1, "max": 5,   "description": "Standard deviation multiplier"},
      "threshold":  {"type": "float", "default": 5.0, "min": 1, "max": 20,  "description": "Band width percentage threshold"}
    },
    "outputs": {
      "fired": {
        "type": "bool",
        "units": "boolean",
        "range": [0, 1],
        "canonical_name": "none",
        "description": "True on the bar where band width crosses below threshold"
      }
    }
  }
}
```

Note the asymmetry between `inputs` and `consumes`. `bb_squeeze` never touches `close` directly --
it compares one indicator output against a constant -- but it declares `Requires: Close` because the
frame it is handed must carry that column for `BollingerBands` to run. `inputs` is what the signal
needs in the DataFrame; `consumes` is what it actually reads.

### 4. `bb_above_upper`

```json
{
  "id": "procedure:signal-bb-above-upper",
  "title": "bb_above_upper",
  "kind": "Procedure",
  "summary": "Check if price is currently above the upper Bollinger Band. A state, not an event: true for every bar close sits above the band, unlike bb_upper_breakout which fires only on the bar that crosses it.",
  "epistemic": "ratified",
  "status": "ratified",
  "props": {
    "source_module": "volatility",
    "reference": null,
    "warmup_bars": "window",
    "abbreviation": null,
    "usage_example": "RuleRegistry.evaluate({'name': 'bb_above_upper', 'params': {'window': value, 'window_dev': value}}, df)",
    "formula": null,
    "consumes": {"BollingerBands": ["hband"]},
    "inputs": {
      "close": {"type": "series", "description": "closing price"}
    },
    "params": {
      "window":     {"type": "int", "default": 20, "min": 5, "max": 100, "description": "MA period for center band"},
      "window_dev": {"type": "int", "default": 2,  "min": 1, "max": 5,   "description": "Standard deviation multiplier"}
    },
    "outputs": {
      "fired": {
        "type": "bool",
        "units": "boolean",
        "range": [0, 1],
        "canonical_name": "none",
        "description": "True if close > upper band on the current bar"
      }
    }
  }
}
```

### 5. `bb_below_lower`

Mirror of 4: `consumes` `{"BollingerBands": ["lband"]}`, `warmup_bars` `window`, role `filter`.

---

## Decisions this example encodes

- **No new relation vocabulary.** `instance-of`, `uses` and `has-role` are all already defined in
  the vendored ontology. See the note above on why `uses` beats `derived-from` and `requires`.

- **Class is not a field on a signal.** It is reached by `uses` then the indicator's `instance-of`.
  `bb_squeeze` is a volatility signal because `BollingerBands` is a volatility indicator, and nothing
  restates that. Measured over the whole corpus, 186 of 247 signals resolve their class this way with
  no ambiguity.

- **`interpretation` and `applications` are not signal fields either.** Same reasoning, same edge. It
  also avoids authoring 247 x 2 prose fields that would duplicate the indicator's.

- **`inputs` means the same thing at both layers: raw input series.** An indicator's `inputs` are
  `close` / `high` / `volume`; a signal's are the columns it declares in `Requires:`. Keeping one
  meaning is what makes the two layers comparable. An earlier draft put `BollingerBands.hband` in
  `inputs`, which put two different key vocabularies -- raw series names and dotted node-output
  references -- in one dict, and in `bb_upper_breakout` mixed both in the same object.

- **`consumes` carries which indicator outputs are read.** `{"BollingerBands": ["wband"]}`. This is
  the other half of a decision already taken: the indicator worked example rejected a
  `primary_output` field because "which output matters belongs to the consumer, not the indicator" --
  the signal *is* that consumer. The `uses` edge says which indicator; `consumes` says which of its
  outputs, which an edge cannot carry because outputs are properties rather than nodes. The indicator
  name is repeated in both so that `consumes` stays unambiguous for the 9 signals that read two
  indicators.

- **`outputs` has one entry, keyed `fired`.** A signal returns a bare `bool`, not a dict, so there is
  no name to lift. `fired` is the one invented key in the schema; it is named rather than left
  anonymous so the output can carry the same `type`/`units`/`range`/`description` sub-schema every
  indicator output has, and so the `Returns:` prose has somewhere to live.

- **`formula` is authored, not lifted.** The return expression is mechanically extractable --
  `prev_close <= prev_upper and curr_close > curr_upper` -- but it is in local-variable terms and
  means nothing without the bindings. Lifting it would put a string in the node that reads like a
  specification and is not one. Left null; authoring it means translating to domain terms
  (`close > hband`), not inventing.

- **`warmup_bars` is the `len(df) <` guard, and the guard is correct here.** Verified: `hband` first
  has a value at 20 bars, and a crossing needs two consecutive values, so 21. The guards say exactly
  `window` and `window + 1`. Verified on these five only -- whether every one of the 247 guards is
  the true warmup is unproven, and a wrong guard would put a wrong number in a node.

- **Role is lifted from `Type:` as it stands.** All 247 signals carry a `Type:` line and it maps
  cleanly onto the existing `trigger` / `filter` values. `arm` has no members.

- **Direction is deliberately absent.** Whether a signal firing argues bullish or bearish is carried
  in the name for some signals, in the docstring body for others, and is genuinely absent for the
  rest. Not uniform, not liftable, so it is its own pass rather than a field guessed at here.

---

## Conventions this example fixes

**`abbreviation` is `null`.** Signals do not have abbreviations. Strictly the invariant says a
deliberately-inapplicable field should carry a real value, because `null` means "not yet authored"
and the nulls are the worklist -- but the indicator layer already uses `null` in exactly this way,
and consistency with what is committed beats correcting one field in isolation. If that convention
changes it changes for both layers at once.

**`range` on the boolean output is `[0, 1]`, matching the indicator layer.** The removed
`hband_indicator` output carried `units: "boolean"`, `range: [0, 1]`, and the signal that replaced it
says the same thing about the same quantity.

**A signal's `id` is `procedure:signal-<name>` with underscores hyphenated**, matching
`procedure:indicator-<lowercased-class>`.

---

## What this example does not settle

- The 18 moving-average signals (`is_above_dema`, `tema_cross_up`, ...) pass the indicator class as a
  function argument, so the `uses` edge cannot be resolved by reading the call site. They need the
  resolver taught about that shape before they can be emitted.
- 39 signals have no classed indicator to inherit from: 15 built on the five stateful policy rules
  the ontology excludes, 20 reading non-price series with no indicator at all, and 4 comparing raw
  OHLC directly.
- `arm` has no members. It exists as a role value with nothing pointing at it.
- Whether the `len(df) <` guard is the true warmup for all 247 signals, or only for these five.
