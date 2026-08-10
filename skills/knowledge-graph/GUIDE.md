# Agent guide: using the knowledge graph

Ten tasks an agent actually gets asked to do with this library, and how to do each one with
`mangrove_kb.graph`. Every call here was executed against the committed graph; the outputs are real.

The skill (`SKILL.md`, beside this file) is the reference for *which call*. This is the
reference for *what a whole job looks like*, including the traps.

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()
```

---

## 1. Orient yourself in a library you have never seen

**Task:** "Have a look at mangrove-kb and tell me what's in it."

Do not start by listing files. Start with the graph's own summary:

```python
s = kg.stats()
s["nodes"], s["edges"]          # 301, 749
s["primitives"]                 # {'Procedure': 288, 'Concept': 6, 'Property': 4, ...}
s["relations"]                  # {'instance-of': 286, 'uses': 231, 'has-role': 216, ...}
s["kinds"]                      # the class vocabulary
s["roles"]                      # ['property:role-filter', 'property:role-trigger']
kg.schema()                     # the (subject, relation, object) shapes that actually occur
```

```
nodes, edges  301 749
primitives    {'Procedure': 289, 'Concept': 6, 'Property': 4, 'Object': 1, 'Schema': 1}
relations     {'instance-of': 287, 'uses': 231, 'has-role': 216, 'kind-of': 9,
               'part-of': 4, 'supersedes': 2}
kinds         ['concept:indicator', 'concept:indicator-class-averaging',
               'concept:indicator-class-flow', 'concept:indicator-class-momentum',
               'concept:indicator-class-oscillator', 'concept:indicator-class-pattern',
               'concept:indicator-class-volatility', 'concept:signal', 'property:role']
roles         ['property:role-filter', 'property:role-trigger']
schema        [{'subject': 'Concept',   'relation': 'kind-of',     'object': 'Procedure'},
               {'subject': 'Procedure', 'relation': 'has-role',    'object': 'Property'},
               {'subject': 'Procedure', 'relation': 'instance-of', 'object': 'Concept'},
               ... 10 shapes in total]
```

`schema()` is the one to read carefully. It tells you what questions are answerable *before* you ask
one and get an empty result you might misread as "there are none".

**Trap:** `stats()["kinds"]` returns full node ids (`concept:indicator-class-momentum`), but every
filter also accepts the short name (`"momentum"`). Both work; the ids are what you get back.

---

## 2. Check whether something already exists before building it

**Task:** "Add a signal that fires when RSI diverges from price."

The expensive failure is writing a duplicate. Two searches, cheap:

```python
kg.find("divergence")                    # by name, summary, abbreviation
kg.find(kind="oscillator", role="trigger")   # by what it is and how it is used
```

```
find("divergence") -> 37 matches, name matches first
  procedure:signal-rsi-bearish-divergence
  procedure:signal-rsi-bullish-divergence
  procedure:signal-rsi-hidden-bearish-divergence
  procedure:signal-rsi-hidden-bullish-divergence
  procedure:indicator-klingervolumeoscillator      <- from here down, matched in prose only
  procedure:indicator-kvo
  procedure:indicator-roc
  procedure:indicator-swingdelta
```

So yes, it exists — four of them. Do not write a fifth.

Results are ranked by *where* the query matched: name, then abbreviation, then summary, then the
authored detail (formula, interpretation, applications, and the names and descriptions of inputs,
params and outputs). The thing actually called "divergence" comes before things that merely mention
it, so the long tail costs you nothing — read down until the matches stop being about your term.

**Trap:** results are capped at 10 by default. `Result.truncated` and `Result.note` tell you when
there are more. Pass `limit=None` when the count itself is the answer — here the default would have
shown you 10 of 37.

---

## 3. Work out what a change breaks

**Task:** "I want to change RSI's output range. What depends on it?"

```python
readers = kg.neighbors("procedure:indicator-rsi", relation="uses",
                       direction="in", limit=None)
for r in readers:
    print(r["id"], r["inputs"])      # which output each reader actually reads
```

```
8 readers
  procedure:signal-rsi-bearish-divergence  {'rsi': {'type': 'series'}}
  procedure:signal-rsi-bullish-divergence  {'rsi': {'type': 'series'}}
  procedure:signal-rsi-cross-down          {'rsi': {'type': 'series'}}
  procedure:signal-rsi-cross-up            {'rsi': {'type': 'series'}}
  ...
```

All eight read the same single output, so a change to `rsi` touches all of them and a change to
anything else touches none.

The `inputs` on the edge is the point: a reader that only takes `rsi` is unaffected by a change to a
second output, and the graph tells you which is which without opening a file.

Widen to the neighbourhood when you need the shape rather than the list:

```python
kg.subgraph("procedure:indicator-rsi", radius=1)
```

---

## 4. Compose a strategy from both axes

**Task:** "Build a strategy with a momentum trigger and a volatility filter."

This is the query the two axes exist for:

```python
triggers = kg.find(kind="momentum",   role="trigger", limit=None)
filters  = kg.find(kind="volatility", role="filter",  limit=None)
```

```
momentum triggers   25      volatility filters  16
  procedure:signal-adosc-cross-down       procedure:signal-atr-high-volatility
  procedure:signal-adosc-cross-up         procedure:signal-bb-above-upper
  procedure:signal-ao-zero-cross          procedure:signal-bb-below-lower
```

`kind` is what the computation *is*; `role` is the part it *plays*. They are independent — a signal
can be momentum-class and used as either a trigger or a filter.

**Trap:** a signal can derive **two** classes. The RSI divergence signals read both an oscillator and
a momentum indicator, so they appear under both. Do not assume the sets are disjoint.

---

## 5. Find out what a signal needs to run

**Task:** "Can I use `rsi_oversold` on 50 bars of 1-minute data?"

```python
sig = kg.get("procedure:signal-rsi-oversold")
sig["params"]        # every knob, with its range and default
sig["warmup_bars"]   # an EXPRESSION in those params -- e.g. 'window'
sig["inputs"]        # which OHLCV columns it needs
kg.neighbors(sig["id"], relation="uses", direction="out")   # the indicators beneath it
```

```
params       {'window':    {'type': 'int',   'default': 14,   'min': 2,   'max': 100},
              'threshold': {'type': 'float', 'default': 30.0, 'min': 0.0, 'max': 50.0}}
warmup_bars  'window'
inputs       ['close']
uses         ['procedure:indicator-rsi']
```

So with the default `window=14` it needs 14 bars, and 50 is plenty. With `window=100` it is not.

**Trap:** `warmup_bars` is a formula, not a number — `window * 3 - 1`, and worse. To answer "is 50
bars enough", substitute the params you intend to use. Comparing the string numerically is
meaningless.

---

## 6. Decide whether two outputs are comparable

**Task:** "Can I put RSI and ADX on the same axis?"

```python
for ind in ("procedure:indicator-rsi", "procedure:indicator-adx"):
    for name, spec in kg.get(ind)["outputs"].items():
        print(ind, name, spec["units"], spec["range"])
```

```
rsi      rsi       units=dimensionless  range=[0, 100]
adx      adx       units=dimensionless  range=[0, 100]
adx      adx_pos   units=dimensionless  range=[0, 100]
adx      adx_neg   units=dimensionless  range=[0, 100]
obv      obv       units=dimensionless  range=[-inf, inf]     <- NOT comparable with the above
```

RSI and ADX share units and bounds, so they belong on one axis. OBV shares the units but is
unbounded, so it does not.

Same units and a shared bounded range means comparable; anything unbounded does not belong on a
shared scale with anything bounded.

**Trap:** unbounded is written `[-inf, inf]`, not `null`. A naive "does it have a range" check passes
for unbounded outputs. Test the endpoints for infinity — or let `outputs(bounded=…)` do it, which is
the next use case.

## 7. Check whether something is deprecated, and what replaced it

**Task:** "Should I use `hanging_man_trigger`?"

```python
kg.get("procedure:signal-hanging-man-trigger")["status"]     # 'deprecated'
kg.neighbors("procedure:signal-hanging-man-trigger",
             relation="supersedes", direction="in")          # what replaced it, and why
```

```
status         'deprecated'
replaced by    procedure:signal-hammer-trigger
why            'computes the same thing under the canonical name'
```

The `why` on the edge carries the reason — here, *"computes the same thing under the canonical
name"*. That is the difference between "renamed" and "replaced because it was wrong", and you should
report which.

**Trap:** `status` is on the node, not the edge, and only 2 of 301 nodes are deprecated. Check it
explicitly; nothing else surfaces it.

---

## 8. Explain why something is classified the way it is

**Task:** "Why does `adosc_bearish` come back when I ask for momentum signals?"

```python
kg.path("procedure:signal-adosc-bearish", "concept:indicator-class-momentum")
```

```
procedure:signal-adosc-bearish
procedure:indicator-adosc          [uses]
concept:indicator-class-momentum   [instance-of]
```

Each step names the relation traversed, so the answer explains itself:
`signal-adosc-bearish --uses--> indicator-adosc --instance-of--> momentum`.

This is the call to reach for whenever a result surprises you. The class was not declared on the
signal; it was derived, and `path` shows the derivation.

**Trap:** `path` returns the **shortest** connection, which is not always the *meaningful* one —
everything connects through the root eventually. Constrain it with `relations=` when you want a
specific kind of explanation.

---

## 9. Ask about the values, not the nodes

**Task:** "Give me every bounded oscillator output I could put on a shared 0-100 panel."

`get()` answers this one node at a time, which means knowing the nodes first. `outputs()` indexes the
values themselves, so you can ask by what they *are*:

```python
kg.outputs(bounded=True, kind="oscillator", limit=None)
```

```
48 outputs
  bop          bop        ratio          [-1, 1]
  cmf          cmf        ratio          [-1, 1]
  cmo          cmo        dimensionless  [-100, 100]
  mfi          mfi        dimensionless  [0, 100]
  rsi          rsi        dimensionless  [0, 100]
  stc          stc        dimensionless  [0, 100]
```

A row is an **output**, not a node — MACD contributes three — because comparability is a property of
one output, not of its producer. Every row names its producer, so `get()` and `neighbors()` are the
obvious next call.

It also runs the reverse lookup, which `resolve()` cannot: `resolve("histogram")` raises, because
`histogram` is nobody's node name.

```python
kg.outputs("histogram", limit=None)
# procedure:indicator-macd  histogram  price  [-inf, inf]
#   'macd minus signal. Crosses zero exactly when macd crosses it'
```

The other filters are `units=` (`kg.stats()["units"]` enumerates them; `percent` matches 26) and
`bounded=False` for the unbounded tail.

**Trap:** `units=` is an exact match against a deliberately heterogeneous vocabulary — a unit is a
statement about what a computation measures, so a percentage change, a price, a quotient and an
index number are labelled differently on purpose. SwingDelta goes further: its deltas are labelled
`indicator units` because they carry whatever unit the companion indicator it reads has, which is
not knowable until you supply one. Read `stats()["units"]` and filter on what is there.

---

## 10. Filter by what something needs, and whether it is still current

**Task:** "Give me trigger signals I can run on a feed with no volume column — and nothing retired."

```python
kg.find(requires="volume", role="trigger", limit=None)   # the ones to EXCLUDE
kg.find(status="deprecated", limit=None)                 # everything superseded, in one call
```

```
volume triggers   8    adosc-cross-down, adosc-cross-up, kvo-bearish-cross, kvo-bullish-cross,
                       pvo-bearish-cross, ...
deprecated        2    procedure:signal-hanging-man-trigger
                       procedure:signal-shooting-star-trigger
```

Both vocabularies are enumerable — `stats()["input_columns"]` is `close, high, indicator, low, open,
price, volume`, and `stats()["statuses"]` is `deprecated, ratified`. Use case 7 checks deprecation on
a node you already suspect; this is the sweep that finds the ones you did not.

**Trap:** a guessed value raises rather than returning an empty result. `find(requires="vwap")` is a
`GraphError` naming the seven real columns, not a quiet zero you would read as "nothing needs it".

---

---

## What this guide does not tell you

The graph describes what the library *does*, never whether it is a good idea. A signal existing, or
carrying the `trigger` role, says nothing about whether it works on your data, your timeframe, or
your instrument. Backtest before you believe anything.
