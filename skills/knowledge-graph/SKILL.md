---
name: knowledge-graph
description: >-
  Query the mangrove-kb knowledge graph — every indicator and signal in the library, what each
  computes, what it consumes and produces, which signals read which of its outputs, and what part
  each plays in a strategy. Reach for this before grepping the source or guessing at names: "which
  indicators produce a bounded oscillator", "what reads RSI", "what would break if I change this
  output", "is there already a signal for X", "what does this signal actually need". Uses
  mangrove_kb.graph (stats · find · get · neighbors · subgraph · path).
---

# Ask the graph before you read the source

`mangrove_kb` ships a knowledge graph of itself: **302 nodes, 750 edges** covering 71 indicators and
216 signals. It is generated from the source, so it is exact — not extracted from prose, not
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
names, class names, role names, primitives — plus the graph's source path and version. Call it
first. The one reliable way to get a wrong answer from this graph is to invent a relation or class
name; `stats()` is how you avoid it.

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

`find(kind=...)` walks that for you. All 216 signals resolve. Four of them derive **two** classes —
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
| what is in here at all? | `stats()` — always first |
| what shapes can I even ask for? | `schema()` |
| is there already a signal/indicator for X? | `find("keyword")` |
| everything of a class, or in a role, or both | `find(kind=…, role=…)` |
| what does this thing compute — formula, params, outputs? | `get(id)` |
| what reads this indicator? | `neighbors(id, relation="uses", direction="in")` |
| what does this signal depend on? | `neighbors(id, relation="uses", direction="out")` |
| what breaks if I change this? | `neighbors(id, direction="in")`, then widen with `subgraph` |
| the neighbourhood around something | `subgraph(id, radius=1)` |
| how are these two related? | `path(a, b)` |

`neighbors` takes `category=` as well as `relation=`, so you can follow every `structural` edge
without naming each one — useful when you want "how is this classified" regardless of which
structural relation carries it.

## The typed detail is the point

`get()` returns what the code actually does, not a description of it:

```python
kg.get("procedure:indicator-rsi")["outputs"]
# {'rsi': {'type': 'series', 'units': 'dimensionless', 'range': [0, 100],
#          'canonical_name': 'Relative Strength Index', 'description': ...}}
```

Every node carries `formula`, `inputs`, `params`, `outputs`, `warmup_bars`, `reference`,
`usage_example`. Outputs carry `units` and `range` — so *"which indicators produce a bounded
output"* is answerable, and so is *"can I compare these two directly"*.

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
kg.find("divergence")                       # by name and description
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

**"How is this signal connected to that class?"**

```python
kg.path("procedure:signal-adosc-bearish", "concept:indicator-class-momentum")
# each step names the relation traversed, so the answer explains itself
```
