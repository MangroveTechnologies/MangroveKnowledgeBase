---
name: knowledge-graph
description: >-
  Query the mangrove-kb knowledge graph — every indicator and signal in the library, what each
  computes, what it consumes and produces, which signals read which of its outputs, and what part
  each plays in a strategy. Reach for this before grepping the source or guessing at names: "which
  indicators produce a bounded oscillator", "what reads RSI", "what would break if I change this
  output", "is there already a signal for X", "what does this signal actually need". Uses
  mangrove_kb.graph (stats · find · get · outputs · neighbors · subgraph · path).
---

# Ask the graph before you read the source

`mangrove_kb` ships a knowledge graph of itself: **303 nodes, 755 edges** covering 71 indicators and
218 signals. It is generated from the source, so it is exact — not extracted from prose, not
approximate, no ranking model in the way. Every answer is a fact about the code as it is.

It answers things grep cannot: *what reads this indicator's third output*, *which signals produce a
bounded value*, *what is the shortest connection between this signal and that class*.

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()
```

## Start here

```python
kg.stats()
```

Returns the counts, the **complete vocabulary** every other call accepts as a filter — relation
names, class names, role names, primitives, statuses, input columns, output units — plus the graph's
source path and version. Call it first. The one reliable way to get a wrong answer from this graph is
to invent a relation or class name; `stats()` is how you avoid it. Filters that take a vocabulary
raise and name the legal values rather than returning an empty result you would read as "there are
none".

`kg.schema()` goes further: the list of `(subject, relation, object)` shapes that **actually occur**,
so you can plan a traversal against what exists rather than discovering emptiness one query at a
time.

## The two axes — the thing to understand

Every signal is classified two ways at once, and they mean different things.

| axis | relation | question it answers | inherited? |
|---|---|---|---|
| **class** | `instance-of` / `kind-of`, and via `uses` | what *kind* of computation is this? | yes, transitively |
| **role** | `has-role` | what *part* does it play in a strategy? | **never** |

Classes are `averaging`, `flow`, `momentum`, `oscillator`, `pattern`, `volatility`. Roles are
`trigger` and `filter`.

**A role is not a type.** `filter` is not a kind of signal — it is a part some signals play, and the
same computation could play another part in another strategy. So role is never inherited and never
appears as a class. Treat "is a momentum signal" and "is being used as a filter" as answers to
different questions, because the graph does.

**A signal's class is derived, not declared.** A signal does not carry a class of its own; it takes
the character of what it computes over:

```
adosc_bearish --uses--> ADOSC --instance-of--> momentum --kind-of--> Indicator
```

`find(kind=...)` walks that for you. All 218 signals resolve. Four of them derive **two** classes —
the RSI divergence signals read both an oscillator and a momentum indicator, and genuinely belong to
both. Do not assume class is single-valued.

```python
kg.find(kind="momentum", role="trigger")     # momentum-class signals used as triggers
kg.find(kind="oscillator")                   # everything in the oscillator class
kg.find(role="filter")                       # signals playing the filter part
```

## Which call

| question | call |
|---|---|
| the user gave me a name, not an id | `resolve("rsi_oversold")`, or `get()` which resolves too |
| what is in here at all? | `stats()` — always first |
| what shapes can I even ask for? | `schema()` |
| is there already a signal/indicator for X? | `find("keyword")` |
| everything of a class, or in a role, or both | `find(kind=…, role=…)` |
| what needs a volume column? what is retired? | `find(requires=…)`, `find(status=…)` |
| what does this thing compute — formula, params, outputs? | `get(id)` |
| which values are bounded / in these units? | `outputs(bounded=True, units=…)` |
| what produces an output called X? | `outputs("X")` |
| what reads this indicator? | `neighbors(id, relation="uses", direction="in")` |
| what does this signal depend on? | `neighbors(id, relation="uses", direction="out")` |
| what breaks if I change this? | `neighbors(id, direction="in")`, then widen with `subgraph` |
| the neighbourhood around something | `subgraph(id, radius=1)` |
| how are these two related? | `path(a, b)` |
| now actually run what I found | `RuleRegistry.evaluate({"name": node["name"], ...}, df)` |

`neighbors` takes `category=` as well as `relation=`, so you can follow every `structural` edge
without naming each one — useful when you want "how is this classified" regardless of which
structural relation carries it.

`outputs()` is the one call that indexes **values rather than nodes**: a row is a single output, so
an indicator with three outputs contributes three rows, and every row names its producer. It answers
the questions `get()` can only answer one node at a time — *which computations emit a percentage*,
*which are bounded and therefore belong on a shared axis*, *what produces the thing called
`histogram`* (which `get()` and `resolve()` cannot answer at all, since `histogram` is nobody's node
name). It intersects with the type axis: `outputs(bounded=True, kind="oscillator")`.

## The typed detail is the point

`get()` returns what the code actually does, not a description of it:

```python
kg.get("procedure:indicator-rsi")["outputs"]
# {'rsi': {'type': 'series', 'units': 'dimensionless', 'range': [0, 100],
#          'canonical_name': 'Relative Strength Index', 'description': ...}}
```

Every node carries `formula`, `inputs`, `params`, `outputs`, `warmup_bars`, `reference`,
`usage_example`. Outputs carry `units` and `range`, which is what makes *"can I compare these two
directly"* a question with an exact answer — reach for `outputs()` when you want it across the whole
library rather than for one node.

All of that authored text is searchable, not just the name and the summary. `find("mean reversion")`
finds the two indicators that explain themselves that way without ever using it as a name.

And the edges carry data too. A `uses` edge records **which specific output** the signal reads:

```python
kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in")
# [{'id': 'procedure:signal-rsi-oversold', ..., 'inputs': {'rsi': {'type': 'series'}}}, ...]
```

That is a fact about the connection, not about either end — which matters for signals that read two
indicators.

## Rules of use

- **Results are capped, and say so.** Defaults are small on purpose: `concept:signal` has degree
  218, so an unbounded call returns most of the graph. A truncated result carries
  `truncated: True` and a note — *"showing 10 of 47"*. **Read it.** A short list is not evidence
  that there are only ten; pass `limit=None` when you need the total.
- **A miss offers candidates, not a dead end.** `NodeNotFound` carries suggestions. If you get one,
  the next move is in the message.
- **Search reads the detail, so widen the query before concluding absence.** A term that appears only
  in a formula or an output description still matches — it just ranks below the things named for it.
  If `find` still returns nothing, that is close to real evidence; try a shorter stem first.
- **Units say what a computation measures, so the vocabulary is heterogeneous by design.** A
  percentage change, a price, a quotient and an index number are different things and are labelled
  differently; one output's unit is *deferred* — SwingDelta's deltas carry whatever unit its
  companion indicator has. `outputs(units=…)` is an exact match, so read `stats()["units"]` and
  filter on what is there.
- **`subgraph` states what it guarantees.** It returns every node within `radius` *and every edge
  between them* — not a truncated walk. You can reason over the fragment without going back.
- **The graph is only as current as its build.** `stats()["source"]` names the file it read. If the
  ontology has been rebuilt since, reload. A negative result from a stale graph means nothing.
- **`source_module` is provenance, not the answer.** Nodes carry it, and it usually matches the
  derived class — but the *edges* are the assertion. Ask the graph, don't read the property.
- **`warmup_bars` is an expression, not a number.** It is written in the node's own parameters —
  `window * 3 - 1`, `window_slow + window_sign - 2` — because warmup depends on how you configure
  it. Comparing it numerically is a mistake; evaluate it against the params you intend to use.
- **The graph says what the code does, not whether it is a good idea.** A signal existing, or
  bearing the `trigger` role, says nothing about whether it works on your data. It is a map of the
  library, not a recommendation.

## Worked examples

**"Is there already something that does X?"**

```python
kg.find("divergence")                       # every authored field, ranked by where it hit
kg.find(kind="volatility", role="trigger")  # by what it is and how it is used
```

**"What breaks if I change RSI's output?"**

```python
readers = kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in", limit=None)
[r["id"] for r in readers]        # every signal that reads it — and `inputs` says which output
```

**"What does this signal actually need to run?"**

```python
sig = kg.get("procedure:signal-rsi-oversold")
sig["params"]                         # {'window': {...}, 'threshold': {...}} — its knobs, with ranges
sig["warmup_bars"]                    # 'window' — an EXPRESSION in those params, evaluate it yourself
kg.neighbors(sig["id"], relation="uses", direction="out")          # the indicators beneath it
```

**"Take what I found and run it."**

```python
from mangrove_kb import RuleRegistry, sample_ohlcv
from mangrove_kb.signals import momentum            # import the class module to register it

node = kg.get("procedure:signal-adosc-cross-down")
RuleRegistry.evaluate({"name": node["name"], "params": {"fast": 3, "slow": 10}}, sample_ohlcv())
```

A node's `name` **is** the registered signal name — that is the join between the graph and the code,
and it is what makes this a map of a runnable library rather than an encyclopedia.

**"How is this signal connected to that class?"**

```python
kg.path("procedure:signal-adosc-bearish", "concept:indicator-class-momentum")
# each step names the relation traversed, so the answer explains itself
```

**"What can I plot on one panel, and what can I run without a volume feed?"**

```python
kg.outputs(bounded=True, kind="oscillator", limit=None)   # 48 outputs, each with units and range
kg.outputs("histogram")                                   # who produces one — MACD, and only MACD

ids = lambda r: {x["id"] for x in r}                      # rows are dicts; key on the id
ids(kg.find(role="trigger", limit=None)) - ids(kg.find(requires="volume", role="trigger", limit=None))
kg.find(status="deprecated", limit=None)                  # 2 — exclude these from anything new
```
