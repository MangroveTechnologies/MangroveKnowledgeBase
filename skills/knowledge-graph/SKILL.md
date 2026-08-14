---
name: knowledge-graph
description: >-
  Query the mangrove-kb knowledge graph — every indicator and signal in the library, what each
  computes, what it consumes and produces, which signals read which of its outputs, and what part
  each plays in a strategy. Reach for this before grepping the source or guessing at names: "which
  indicators produce a bounded oscillator", "what reads RSI", "what would break if I change this
  output", "is there already a signal for X", "what does this signal actually need". Uses
  mangrove_kb.graph (stats · find · get · outputs · neighbors · subgraph · path · all_paths).
---

# Ask the graph before you read the source

`mangrove_kb` ships a knowledge graph of itself: **361 nodes, 1111 edges** covering 71 indicators and
218 signals. It is generated from the source, so it is exact — not extracted from prose, not
approximate, no ranking model in the way. Every answer is a fact about the code as it is.

It answers things grep cannot: *what reads this indicator's third output*, *which signals produce a
bounded value*, *every way this signal connects to that class, and which of them is the reason*.

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()
```

This file is the reference for **which call**. [`GUIDE.md`](GUIDE.md), beside it, is the reference for
**what a whole job looks like** — thirteen tasks end to end, with real output and the trap in each,
from "the user said a name, not an id" through to running what you found.

## Contents

Read the section you need; each one links on to the others that bear on it.

| section | |
|---|---|
| [Start here](#start-here) | The four calls that answer most questions, and the order to make them in. |
| [The two axes](#the-two-axes-the-thing-to-understand) | Why `kind` and `role` are separate parameters, and why conflating them returns the wrong thing. |
| [Two halves, one retrieval surface](#two-halves-one-retrieval-surface) | The graph holds code-derived computations and knowledge-base concepts; one set of calls reaches both. |
| [Which call](#which-call) | A question-to-method table — the fastest way in when you know what you are asking. |
| [The typed detail is the point](#the-typed-detail-is-the-point) | What `get()` returns, which fields exist on which kind of node, and the data carried on edges. |
| [Rules of use](#rules-of-use) | Caps, truncation, guessed values, and the failure modes that make an answer look complete when it is not. |
| [Worked examples](#worked-examples) | An index into `GUIDE.md`, where each job is shown end to end. |

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

**See also:** [SKILL · which call](SKILL.md#which-call) · [§1 orient yourself](GUIDE.md#1-orient-yourself-in-a-library-you-have-never-seen)

## The two axes — the thing to understand

Every signal is classified two ways at once, and they mean different things.

| axis | relation | question it answers | inherited? |
|---|---|---|---|
| **class** | `instance-of` (indicators) · `about` (signals) | what character is this computation concerned with? | over `kind-of`, yes |
| **role** | `has-role` | what *part* does it play in a strategy? | **never** |

Classes are `averaging`, `flow`, `momentum`, `oscillator`, `pattern`, `volatility` — the six
characters a computation can measure. They are `kind-of` **technical analysis**, not `kind-of`
Indicator: they span indicators *and* signals. Roles are `trigger` and `filter`.

**A role is not a type.** `filter` is not a kind of signal — it is a part some signals play, and the
same computation could play another part in another strategy. So role is never inherited and never
appears as a class. Treat "is a momentum signal" and "is being used as a filter" as answers to
different questions, because the graph does.

**An indicator *measures* its class; a signal is *about* its class.** The two get different
relations, because they are different claims. `momentum` is defined as measuring rate of change —
ADOSC does that, `adosc_bearish` emits a boolean and does not, so it is `about` momentum rather than
an instance of it:

```
ADOSC          --instance-of--> momentum      it measures rate of change
adosc_bearish  --about-------->  momentum      it is concerned with it, because of what it reads
adosc_bearish  --uses--------->  ADOSC         ...and this is the reason
```

`find(kind=...)` returns both. All 218 signals carry an `about` edge, every one derived from a `uses`
edge the builder checks it against — so the claim is in the file and the reason is one hop away.
Four signals carry **two** — the RSI divergence signals read both an oscillator and a momentum
indicator, and are genuinely about both. Do not assume class is single-valued.

```python
kg.find(kind="momentum", role="trigger")     # momentum-class signals used as triggers
kg.find(kind="oscillator")                   # everything in the oscillator class
kg.find(role="filter")                       # signals playing the filter part
```

**See also:** [§4 compose from both axes](GUIDE.md#4-compose-a-strategy-from-both-axes) · [§8 why it is classified that way](GUIDE.md#8-explain-why-something-is-classified-the-way-it-is)

## Two halves, one retrieval surface

The graph holds two kinds of thing and they are queried identically.

**Read off the code** -- 71 indicators and 218 signals, exact, with typed inputs and outputs.
**Read off the knowledge base** -- the concepts a market is made of (orders, participants, venues,
liquidity, spread), the formulas the chapters state, and two nodes per subject holding what is
true of it (`Fact`) and what to do about it (`Judgment`).

`find(under=…)` is the call that spans them: it walks containment (`part-of` alongside `kind-of`
and `instance-of`) and is primitive-blind, so `find(under="market foundations")` returns Concepts,
Procedures, the Fact and the Judgment together. Intersect it with anything -- `primitive="Fact"`,
`role=`, a text query.

Two sub-kinds are worth knowing apart. A `procedure:indicator-*` is callable; a bare `procedure:*`
is a **formula** the knowledge base states and nothing implements.

The same split shows up between a node's content and its members. `concept:chart-pattern` answers
*what is a chart pattern* in full -- `find("head and shoulders")` returns it, and it names the
formations and what completes them. What it has no members: nothing implements them, because a
multi-bar formation needs swing points no computation here produces. Read the node for the
knowledge; `find(kind="chart-pattern")` is empty because there is no code, not because there is
nothing to know.

**See also:** [§14 pull what the knowledge base says](GUIDE.md#14-pull-what-the-knowledge-base-says-about-a-subject) · [§15 the reasoning behind advice](GUIDE.md#15-find-the-reasoning-behind-a-piece-of-advice)

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
| everything belonging to a subject, whatever kind | `find(under="market foundations")` |
| how are these two related? | `path(a, b)` — one shortest route |
| every way these two connect, and why | `all_paths(a, b)` — all routes, shortest first |
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

**See also:** [SKILL · worked examples](SKILL.md#worked-examples) · [SKILL · rules of use](SKILL.md#rules-of-use)

## The typed detail is the point

`get()` returns what the code actually does, not a description of it:

```python
kg.get("procedure:indicator-rsi")["outputs"]
# {'rsi': {'type': 'series', 'units': 'dimensionless', 'range': [0, 100],
#          'canonical_name': 'Relative Strength Index', 'description': ...}}
```

Every **signal and indicator** node carries `formula`, `inputs`, `params`, `outputs`,
`warmup_bars`, `reference`, `usage_example` -- they are lifted from the code. Doc-derived nodes
carry what their chapter states instead: a summary, an `explanation`, `applications`, `examples`,
and for a chapter formula a `formula` with typed `inputs` and `outputs` but no `warmup_bars` or
`usage_example`, because there is no implementation behind it. Read `get()` rather than assuming a
field is there. Outputs carry `units` and `range`, which is what makes *"can I compare these two
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

**See also:** [§5 what a signal needs](GUIDE.md#5-find-out-what-a-signal-needs-to-run) · [§6 comparability](GUIDE.md#6-decide-whether-two-outputs-are-comparable) · [§9 the value index](GUIDE.md#9-ask-about-the-values-not-the-nodes)

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

**See also:** [§2 truncation in practice](GUIDE.md#2-check-whether-something-already-exists-before-building-it) · [§10 enumerable vocabularies](GUIDE.md#10-filter-by-what-something-needs-and-whether-it-is-still-current)

## Worked examples

Each of these is a whole job -- the calls, the output, and the trap -- in
[`GUIDE.md`](GUIDE.md). They are not restated here; this file is the reference for *which call*.

| you want to | GUIDE |
|---|---|
| orient yourself in the library | §1 |
| check something does not already exist | §2 |
| work out what a change breaks | §3 |
| compose a strategy from both axes | §4 |
| find what a signal needs to run | §5 |
| decide whether two outputs are comparable | §6 |
| explain why something is classified as it is | §8 |
| ask about values rather than nodes | §9 |
| run what you found against real data | §12–13 |
| pull what the knowledge base says about a subject | §14 |
| find the reasoning behind a piece of advice | §15 |

