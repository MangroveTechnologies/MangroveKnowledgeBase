# Declarations reference

Every declaration in `ontology/chapter_to_atoms.py`, what it does, and the defect it exists to
prevent. Nothing here is a preference: each entry was added because its absence produced a wrong
graph that looked right.

Declarations are of two kinds. **Per-chapter** ones live under `CHAPTERS[<chapter-id>]` and describe
one document. **Global** ones are keyed by node id or by term and hold across chapters.

---

## Per-chapter

### `taxonomy` — which `### Examples` blocks list kinds

```python
"taxonomy": {"Order Types", "Market Participants", "Trading Venues & Execution Models"},
```

An Examples block is either the section's real taxonomy, whose members become Concepts, or a worked
illustration, which becomes none. "Market Makers" is a kind of participant; "Slippage Example" is
arithmetic. **Nothing in the markup separates them**, so it is declared per section title.

Keyed by section **title**, never by section number. Numbers say where a thing sits in a file, and
keying on them made every declaration silently inert on the next chapter, whose sections are numbered
differently — a clean build with no taxonomies at all, invisible unless the absence is already known.

### `principle_concepts` — a Core Principle that is a definition, not a claim

```python
"principle_concepts": {"Price Discovery": "concept", "Order Flow": "concept"},
```

Some sections state their actual subject matter as principles: §1.1's five "principles" are the five
concepts the section is about, each with a definition attached, and §3.4 states stop hunts and
liquidity pools the same way. Filed as principles they sit inert in a list while the graph contains
no node for something the chapter defines.

### `formula_primitive` — what a stated formula IS

```python
"formula_primitive": {"Black-Scholes Call Price": "Procedure", "Put-Call Parity": "Fact"},
```

Default is `Property` — a quantity a thing has. Exceptions: `Procedure` for something run
(Black-Scholes, GARCH, a detection rule), `Fact` for an identity that holds (put-call parity, cost of
carry), `Concept` for a family rather than a calculation (the Greeks).

Reading every formula as a Procedure produced "spot return is a procedure" and a graph with zero
Properties. Reading them by section position produced the same error in a different order. The
primitive is a judgement about the formula, so it is declared.

### `formula_subject` — which subject a formula belongs to

```python
"formula_subject": {"Return Amplification": "concept:leverage",
                    "Impermanent Loss": "concept:automated-market-maker"},
```

A formula attaches to the section subject whose name appears in its label — head noun first, then any
other word. Two cases need declaring: a label naming its subject nowhere in itself
("Return Amplification" is about leverage), and a formula belonging to a taxonomy member rather than
the section subject (the AMM arithmetic under a section about crypto generally).

Without it, everything attaches to whichever subject came first: `simple slippage` was declared to be
about liquidity, and `low volatility regime` was made a kind of volatility rather than of regime.

### `rename` — the id a term should have

```python
"rename": {"Price Impact (AMM)": "property:amm-price-impact",
           "Trend, Range, Compression/Expansion": "concept:market-regime"},
```

Three uses:

1. **Fold onto an existing node.** A section that defines something the graph already holds gets that
   node's id, and folds into it: identity and edges kept, the chapter's content unioned in.
2. **Keep two things apart that share a name.** Chapter 1's price impact is Kyle lambda — how far a
   book moves per unit of order flow. Chapter 2's is the constant-product curve. Same words, different
   quantity; folding them on the strength of the name is the opposite of what folding is for.
3. **Fix an id a heading would produce.** `concept:trend-range-compression-expansion` names a heading,
   not a thing.

### `retitle` — the name a node displays

```python
"retitle": {"Trending Market Characteristics": "trending market"},
```

A heading is written to head a section, not to name a node. `rename` fixes the id; this fixes the
label a reader sees.

### `blocks_as_nodes` — a section with no scaffold

```python
"blocks_as_nodes": {"Core Market Wisdom": {"Win Rate Is Not Risk": "Fact",
                                           "The Trend Is Your Friend": "Judgment"}},
```

For a section that states several claims under headings of their own, with no `### Definition` and no
single subject. Each declared heading becomes a node whose summary is its `**Definition:**` line,
whose bullets become `explanation`, whose table becomes `comparison` and whose blockquote becomes
`caution` — the last of these being the part that matters most, since a warning is usually written as
a quote ("do NOT describe mean reversion as safer").

A section with no Definition and an undeclared block raises rather than dropping it.

### `tables` — a markdown table whose rows are nodes

```python
"tables": {"Key Definitions": ("concept:volume-profile", "part-of", "Concept")},
```

`(target, relation, primitive)`; primitive defaults to `Procedure`. A table is as often a summary of
nodes that already exist as it is a source of new ones, so which one it is gets declared.

### `table_properties` — a table whose rows are properties of existing nodes

```python
"table_properties": {"Order Type Summary Table": ["execution_certainty", "price_certainty", "use_case"]},
```

Row label names a node this chapter already created; the remaining columns become its properties.
Raises if a row names no node, so a reworded table fails loudly.

### `edges` — a relationship the chapter states and never draws

```python
"edges": [("concept:iceberg-order", "about", "concept:information-leakage",
           "displays partial size to reduce it")],
```

`(src, relation, dst, why)`. Both endpoints must already exist or the build raises. Use for:

- a quantity computed from another quantity (annualized basis from basis),
- a rule and the thing it detects (structure-break detection and break of structure),
- a chapter term and the library computation it names (ATR% and `procedure:indicator-atr`),
- cross-chapter links, which are the edges that make the graph worth having,
- **closing degree-1 nodes**: a node reachable only by its own `kind-of` can be found by walking down
  from its parent and by no other question.

Every `why` is mandatory and is the reason the edge holds, not a restatement of it.

### `wired` — a stated line and the node it concerns

```python
"wired": {"Use iceberg orders for large positions": "concept:iceberg-order"},
```

A principle or practice lives in its list until it earns an edge; then it **moves** — out of the
list, onto an `about` edge from that node to the list node, as the edge's `why`. Never in both
places, so the copies cannot drift, and what remains in a list is exactly what is not yet connected.

Keyed by a distinctive fragment rather than the whole sentence; a key matching no line raises, so a
reworded source fails loudly instead of silently drawing no edge. The edge runs **from** the concept
**to** the list: a reader arrives at a concept and asks what is known about it, and outgoing edges are
the answer.

---

## Global

### `AUTHORED` — the prose a node ships with

```python
'concept:iceberg-order': (
    'A large order that displays only part of its size at a time, ...',
    'Showing full size is itself information: ... It exists to reduce [[Information Leakage]].'),
```

`(summary, explanation)` keyed by node id. Merged, never substituted: an existing summary that
differs materially is kept as `source_wording`; one that is a worked illustration moves to
`examples`; one that says the same thing in other words collapses. The explanation has no counterpart
in the source — chapters state what a thing is and rarely why it matters.

### `DEFINITION` — a definition for a term the chapter only illustrates

Where a section explains each member through a worked example only, so `market-order` would read "Buy
100 shares at the best available price" — true of one order, and not what a market order is. The
example is kept as `examples`; this is the summary beside it. `AUTHORED` supersedes it when both
exist.

### `MERGE_INTO` — a term the graph holds under a different id

```python
MERGE_INTO = {"procedure:on-balance-volume": "procedure:indicator-obv"}
```

For a collision the slug cannot see: the chapter says "On-Balance Volume", the library registers
`OBV`. Terms that collide on the id itself need no entry — `--ontology` catches those.

### `NOT_A_KIND` — a block inside a taxonomy that is not a member

```python
NOT_A_KIND = {"Regime Shift Triggers", "Zone Quality Factors", "Covered Call"}
```

Blocks that read like members and are not: causes of a thing, attributes of a thing, a position built
from a thing. Their text is kept on the subject rather than discarded.

### `IRREGULAR` — words the singulariser must not touch

```python
IRREGULAR = {"basis": "basis", "greeks": "greeks", "futures": "futures", "status": "status"}
```

A category node is singular — one `market maker`, not `market makers` — because chapters title their
sections in the plural. Stripping the `s` blindly invented `basi`, `greek`, `future` and `statu`.

### `FORMULA_IO` — typed inputs and outputs for a stated formula

The formula is in the text; what it consumes and emits is not, and without it nothing connects a
spread to the bid and ask it reads. Same shape as the code-derived indicators use. `range` uses
`None` for an open end.

### `RECONCILED` — an existing definition already deconflicted by hand

Suppresses `chapter_variants` for a node whose wording has been decided. Recording a settled question
as a conflict reports finished work as outstanding.
