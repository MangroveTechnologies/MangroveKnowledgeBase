<h1 align="center">MangroveKnowledgeBase</h1>

<p align="center"><strong>A trading-signal library that ships a knowledge graph of itself.</strong></p>

<p align="center">
  <a href="https://pypi.org/project/mangrove-kb/"><img src="https://img.shields.io/pypi/v/mangrove-kb.svg?color=42a7c6&logo=pypi&logoColor=white" alt="PyPI version"></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-ff9e18.svg" alt="License: PolyForm Noncommercial 1.0.0">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/graph%20%2B%20indices-in%20the%20wheel-2ec27e.svg" alt="Graph and both search indices ship in the wheel">
  <img src="https://img.shields.io/badge/graph-714%20nodes%20%C2%B7%202342%20edges-42a7c6.svg" alt="Graph: 714 nodes, 2342 edges">
  <img src="https://img.shields.io/badge/agent-skill%20%2B%20guide-9b5cff.svg" alt="Agent skill + guide">
</p>

<p align="center">
  <a href="https://discord.gg/Yycbw6P93B"><img src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white&style=for-the-badge" alt="Discord"></a>
  <a href="https://pepy.tech/projects/mangrove-kb"><img src="https://static.pepy.tech/badge/mangrove-kb" alt="PyPI Downloads"></a>
</p>

**249 trading signal functions** (119 TRIGGER, 130 FILTER) and **80 technical indicator classes**,
every one with a machine-readable docstring — formula, inputs, parameters with ranges and defaults,
typed outputs with units, and warmup.

How it is built, stored and searched is drawn in [`docs/architecture/`](docs/architecture/README.md) — provenance, the node and
edge schema, the search corpus, `find()`, `ask()`, both search indices and how they are
fused, and the three traversals that are easy to confuse.

And a **knowledge graph** — 714 nodes and 2342 edges, with two halves on one schema. One is compiled
from the source above: what each computation is, what it measures, what it reads, and what part it
plays. That half is exact, because it is read from the code rather than extracted from prose. The
other is the trading knowledge base — market structure, instruments, risk, chart patterns,
quantitative method — ingested from its eight chapters as nodes and edges beside them.

The join is what makes either half worth querying: `procedure:atr-based-stop` is a rule the risk
chapter states, and it `uses` an indicator the code defines, so one query crosses from *why* to
*what it computes*.

The point is the second thing. A library of 249 functions is only useful if you can find the right
one, and `grep` cannot answer *"which indicators produce a bounded oscillator"*, *"what reads RSI's
third output"*, or *"is there already a signal for this"*. The graph can, and the answers are facts
about the code as it is.

![The knowledge graph viewer, with the rsi_oversold signal selected](assets/graph-viewer.png)

*The bundled viewer (`python -m mangrove_kb.viz`): click any node to read what it computes and walk
its edges. [What each part does](#the-viewer).*

## Contents

- [Install](#install)
- [Quick start](#quick-start)
  - [1 · Ask the graph before you read the source](#1--ask-the-graph-before-you-read-the-source)
  - [2 · Work out what a change breaks](#2--work-out-what-a-change-breaks)
  - [3 · Ask about the values, not the nodes](#3--ask-about-the-values-not-the-nodes)
  - [4 · Explain an answer](#4--explain-an-answer)
  - [5 · Run what you found](#5--run-what-you-found)
  - [6 · View it in a browser](#6--view-it-in-a-browser)
- [Skill & graph tools](#skill--graph-tools)
  - [The tools](#the-tools)
- [The model in 30 seconds](#the-model-in-30-seconds)
- [The viewer](#the-viewer)
  - [The inspector — what a node actually carries](#the-inspector--what-a-node-actually-carries)
  - [Following an edge](#following-an-edge)
  - [The Action panel — trim the graph to the question](#the-action-panel--trim-the-graph-to-the-question)
  - [The rail — two-level filters](#the-rail--two-level-filters)
  - [Search — ranked, and it tells you why](#search--ranked-and-it-tells-you-why)
  - [3D](#3d)
- [What is in the graph, and what is not](#what-is-in-the-graph-and-what-is-not)
- [Repository structure](#repository-structure)
- [Development](#development)
- [License](#license)
- [Contributing](#contributing)
- [Links](#links)

---
## Install

```bash
pip install mangrove-kb
```

Python 3.10+. The graph, both search indices, the agent skill and the viewer all ship **inside the
wheel**, so `KnowledgeGraph.load()` needs no network and no configuration.

`ask()` works out of the box on the LSA index. Its second index — a pretrained encoder, worth 13/25
to 18/25 — is an **extra**, because `sentence-transformers` pulls torch and pip's default torch wheel
bundles the whole CUDA stack: `mangrove-kb` is 373 MB installed, `mangrove-kb[semantic]` is 5,276 MB,
and 3.4 GB of that is GPU support this never uses.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu   # 1,402 MB instead of 5,276
pip install "mangrove-kb[semantic]"
```

CPU or GPU is chosen there and cannot be declared by the package — there is no `torch-cpu` on PyPI,
and the `+cpu` wheels carry the same version from a different index. Without the extra, `ask()`
answers on one index rather than two; nothing raises.

---

## Quick start

### 1 · Ask the graph before you read the source

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()

kg.stats()                                   # counts + every value a filter will accept
kg.find("divergence")                        # search name, abbreviation, summary, authored detail
kg.find(kind="momentum", role="trigger")     # by what it measures AND the part it plays
kg.get("rsi_oversold")                       # formula, params, typed outputs, warmup

kg.ask("how far away from my entry should the stop go")   # a QUESTION, not a term
```

`find()` matches the words you use. `ask()` matches what you *mean* — it seeds from two indices, one
built from this corpus and one from a pretrained sentence model, fuses them by reciprocal rank, and
walks a hop along the edges. Every row carries `reached`: which seed it came from, how far, along
which relation, and that edge's own reason. Measured on twenty-five questions phrased the way a
trader asks them, `find()` answers 5 and `ask()` answers 18.

`stats()` first, always. It returns the **complete vocabulary** every other call accepts — relations,
classes, roles, statuses, input columns, output units — so you never have to guess a name. Filters
that take a vocabulary raise and list the legal values rather than returning an empty result you
would read as *"there are none"*.

### 2 · Work out what a change breaks

```python
kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in", limit=None)
# every signal that reads RSI -- and each edge says WHICH output it reads
```

### 3 · Ask about the values, not the nodes

```python
kg.outputs(bounded=True, kind="oscillator", limit=None)   # 48 outputs, each with units and range
kg.outputs("histogram")                                   # who produces one -- MACD, and only MACD
```

`outputs()` indexes **values rather than nodes**: one row per output, each naming its producer. It
answers *"what can I plot on one panel"* — which `get()` can only answer one node at a time, and
which `resolve()` cannot answer at all, since `histogram` is nobody's node name.

### 4 · Explain an answer

```python
kg.all_paths("adosc_bearish", "momentum")
# adosc_bearish --about--> momentum                                  the claim
# adosc_bearish --uses--> indicator-adosc --instance-of--> momentum  the reason
```

### 5 · Run what you found

```python
from mangrove_kb import RuleRegistry, sample_ohlcv
from mangrove_kb.signals import momentum          # import the class module to register it

node = kg.get("procedure:signal-adosc-cross-down")
RuleRegistry.evaluate({"name": node["name"], "params": {"fast": 3, "slow": 10}}, sample_ohlcv())
```

A node's `name` **is** the registered signal name. That join is what makes this a map of a runnable
library rather than an encyclopedia.

### 6 · View it in a browser

```bash
python -m mangrove_kb.viz > graph.html
```

One self-contained file — no CDN, no build step, no network.

---

## Skill & graph tools

Two documents ship **inside the wheel**, so an agent that installs the package has them without
fetching anything:

| | what it is |
|---|---|
| [`SKILL.md`](skills/knowledge-graph/SKILL.md) | the reference for **which call** — the two axes, the rules of use, and a question→call table |
| [`GUIDE.md`](skills/knowledge-graph/GUIDE.md) | the reference for **what a whole job looks like** — sixteen tasks end to end, with real output and the trap in each |

Both are executable documentation: every example in them is re-run by the test suite against the
committed graph, so an example that drifts fails the build rather than misleading a reader.

### The tools

`mangrove_kb.graph.KnowledgeGraph` is the whole query surface:

| question | call |
|---|---|
| what is in here at all? | `stats()` — **always first**; returns every value the other calls accept as a filter |
| what shapes can I even ask for? | `schema()` — the 12 `(subject, relation, object)` triples that actually occur |
| the user gave me a name, not an id | `resolve("rsi_oversold")`, or `get()`, which resolves too |
| is there already a signal for X? | `find("keyword")` — ranked by *where* it matched |
| a question in ordinary words, not a term | `ask("how far should the stop go")` — meaning over two indices, then a hop |
| everything of a class, or in a role, or both | `find(kind=…, role=…)` |
| what needs volume? what is retired? | `find(requires=…)`, `find(status=…)` |
| everything under a subject, whatever kind | `find(under="risk management")` — Concepts, Procedures, Facts and Judgments together |
| what is *claimed*, and what to *do* about it | `find(primitive="Fact")`, `find(primitive="Judgment")` |
| what does this compute — formula, params, outputs? | `get(id)` |
| which values are bounded / in these units? | `outputs(bounded=True, units=…)` |
| what produces an output called X? | `outputs("X")` |
| what reads this indicator? what does this read? | `neighbors(id, relation="uses", direction="in"\|"out")` |
| the neighbourhood around something | `subgraph(id, radius=1)` |
| how are these two related? | `path(a, b)` — one shortest route |
| every way they connect, and why | `all_paths(a, b)` — all routes, shortest first |
| now actually run what I found | `RuleRegistry.evaluate({"name": node["name"], …}, df)` |

**Every bounded return states its own truncation.** A `Result` carries `total`, `truncated` and a
`note` — a short list is never mistakable for a complete one, and `limit=None` gets everything.
Filters that take a vocabulary raise and name the legal values rather than returning an empty result
you would read as *"there are none"*.

---

## The model in 30 seconds

Every computation is classified on **two independent axes**, and they answer different questions.

| axis | relation | question | inherited? |
|---|---|---|---|
| **class** | `instance-of` (indicators) · `about` (signals) | what character is this concerned with? | over `kind-of`, yes |
| **role** | `has-role` | what part does it play in a strategy? | **never** |

The six classes — `averaging`, `flow`, `momentum`, `oscillator`, `pattern`, `volatility` — are
divisions of **technical analysis** by what a computation measures. They are `kind-of` technical
analysis, **not** `kind-of` Indicator, because they span both layers.

**An indicator *measures* its class; a signal is *about* its class.** Different claims, so different
relations:

```
ADOSC          --instance-of--> momentum      it measures rate of change
adosc_bearish  --about-------->  momentum      it is concerned with it...
adosc_bearish  --uses--------->  ADOSC         ...because of what it reads
```

Momentum is defined as measuring rate of change. A signal emits a boolean and measures nothing, so
it is not an instance — and keeping the two edges distinct is what lets the graph *explain* a
classification instead of merely asserting it.

**A role is not a type.** `filter` is not a kind of signal; it is a part some signals play, and the
same computation could play another part in another strategy. So role is never inherited and never
appears as a class. (Grounded in Steimann, *DKE* 2000, and Guarino & Welty's OntoClean, *CACM* 2002.)

Seven relations in total: `instance-of`, `kind-of`, `part-of`, `about`, `has-role`, `uses`,
`supersedes`. `kg.schema()` lists the 12 `(subject, relation, object)` shapes that actually occur, so
you can plan a traversal against what exists rather than discovering emptiness one query at a time.

---

## The viewer

`python -m mangrove_kb.viz > graph.html` writes one self-contained page — no server, no build step,
no network — with the whole graph in 2D and 3D, filterable, searchable, and every node's authored
detail one click away.

| Pane | Where | What it holds |
| --- | --- | --- |
| Rail | left | filters, by kind of node and kind of edge |
| Map | middle | 714 nodes, 2342 edges |
| Panel | right | everything the library records about whatever you clicked |

### The inspector — what a node actually carries

<img src="assets/viewer-inspector.png" alt="The inspector showing BollingerBands: folded sections, then Inputs, Parameters and Outputs as tables" width="330" align="right">

Click any node or edge to pin its detail. Everything authored is here — description, `formula`,
`reference`, `usage_example` — and **inputs, parameters and outputs come as tables**, each with its
type, default, units and range, rather than a wall of JSON.

Sections **fold**, and the choice sticks: fold `Edges` once and it stays folded on the next node.
`Provenance & extras` holds the module and a call you can copy.

Ranges are read carefully, because three different facts used to render identically:

| Shown | Means |
| --- | --- |
| `0 … 100` | bounded both ways |
| `≥ 0` | floored, no ceiling |
| `unbounded` | `[-inf, inf]` — stated, not missing |
| `true/false` | boolean, not a `[0,1]` interval |
| `not authored` | nobody has written the range down |

**Two traps.** `warmup_bars` is an *expression* in the node's own parameters (`window * 3 - 1`), so
evaluate it against the parameters you intend to use. And units are heterogeneous by design: a
percentage, a price and an index number are different things and are labelled differently.

<br clear="right">

Every heading carries a **?** that says what that section holds, and so does every edge type — point
at it, tab to it, or tap it:

<p align="center">
  <img src="assets/viewer-tooltip.png" alt="The ? beside the uses row, with its explanation shown to the left of the panel" width="85%">
</p>

### Following an edge

Every name under `Edges` is a link: click it and the panel moves there, with a **back** button to
return. Edges are grouped incoming and outgoing, and each type asserts something different:

| Edge | Claim |
| --- | --- |
| `instance-of` | this indicator measures that family — RSI measures momentum |
| `about` | this signal is concerned with that family without measuring it |
| `uses` | this reads that one, and carries which of its outputs flow in |
| `has-role` | the part it plays in a strategy: trigger or filter |
| `part-of` | a component of the other |
| `kind-of` | a subtype of the other |

`instance-of` and `about` are the pair to keep straight. An indicator produces the quantity, so it is
an instance of the family; a signal emits a boolean, so it is *about* the family instead — and the
`uses` edge beside it is the reason.

### The Action panel — trim the graph to the question

<p align="center">
  <img src="assets/viewer-action.png" alt="The Action section with neighbors and ancestors both selected, and a bar over the map reading 'showing 17 of 714'" width="100%">
</p>

714 nodes at once is a picture, not an answer. **show only** keeps part of the graph around the
selected node, and the choices combine — `neighbors` + `ancestors` gives you both:

| | Keeps |
| --- | --- |
| everything | no trim |
| neighbors | one hop, in or out |
| descendants | everything built on this node |
| ancestors | everything this node is built from |

The count on each choice says how many nodes you would be left with **before** you click, and a
choice that would leave a single node is disabled. **show or hide** does the same one edge type at a
time, and its number is exact: hide `uses` on RSI and the eight signals that read it go, and nothing
else does.

The two compose — an edge type set to hide is dropped from the lineage walk as well, so the counts
above change to match. A bar over the map says how much is in view and how to get back; `Esc` clears
it, and clearing returns the view you had rather than refitting the whole graph.

Hiding a hub can leave a few nodes floating with nothing visibly joining them. That is honest: the
thing that connected them is the thing you hid.

### The rail — two-level filters

<img src="assets/viewer-facets.png" alt="The filter rail: Procedure splits into signal, formula and indicator; Concept into entity type, class and domain; and the knowledge half as Fact and Judgment" width="260" align="right">

Nodes group by **ontology primitive**, edges by **relation category**, and each splits into the
derived kind beneath it — so `signal` and `indicator` are separable inside `Procedure`, and `about`
is separable from `has-role` inside `descriptive`.

Sub-kinds are **shades of their parent's hue**, never new colours: every dot in that group is a
procedure, and the darker teal is the 71 indicators among them.

Parent and child are **AND-ed**. Unticking `Procedure` hides every procedure whatever the children
say, and the children grey out to show why — so the canvas can never empty for a reason that is not
visible in the rail.

**Density** spreads or tightens the layout. **Labels** switches between always / never / on hover /
on zoom — at 714 nodes, off is often clearer than on.

<br clear="right">

### Search — ranked, and it tells you why

<img src="assets/viewer-search.png" alt="Search results for 'divergence', badged NAME and SUMMARY by which field matched" width="420" align="right">

Search reads **every authored field**, not just names — formula, interpretation, applications, and
the names and descriptions of inputs, params and outputs.

Results rank by *where* the query hit, and the badge says which: `NAME` first, then `ABBREV`,
`SUMMARY`, `DETAIL`. So the thing actually called "divergence" comes before the things that merely
mention it, and the long tail costs you nothing.

This is the **same ranking `kg.find()` uses** — `SEARCH_TIERS` is exported from Python into the page
rather than reimplemented in JS, and a test asserts the two agree on real queries.

<br clear="right">

### 3D

<p align="center">
  <img src="assets/viewer-3d.png" alt="The same graph in 3D" width="80%">
</p>

The same graph, same filters, same inspector — drag to rotate, scroll to zoom, right-drag to pan. In
either view, **double-click a node to hide or show what hangs off it**, which is how you make a hub
with 218 signals attached readable.

A **green ring** marks the selected node; a **yellow ring** marks a deprecated one — it still runs,
it just has a canonical replacement. Nothing else is ringed: 308 of 714 nodes are `ratified`, so
marking that would be decoration rather than information.

Light, dark and follow-the-system are top right, and the choice is remembered.

---

## What is in the graph, and what is not

**The knowledge half.** All eight knowledge-base chapters are in the graph as nodes and edges, not
as documents: 202 Concepts (what a market is made of), 397 Procedures (of which the bare
`procedure:*` ones are formulas a chapter states and nothing implements), 74 Properties, and — the
two worth knowing about — **23 Facts and 16 Judgments**. A `Fact` holds what is *true* of a subject,
a `Judgment` what to *do* about it. They are separate primitives because they answer to different
standards: a Fact is settled by measurement, a Judgment by argument.

```python
kg.find(under="risk management", limit=None)            # 74 nodes, every primitive
kg.find(under="risk management", primitive="Judgment")  # 5 -- what to actually do
kg.neighbors("concept:market-impact", relation="about", direction="in")
# fact:square-root-market-impact-rule · procedure:almgren-chriss-market-impact-model
```

A statement lives in exactly one place. Until it concerns a particular node it sits in a Fact or
Judgment; once it earns an `about` edge it moves onto that edge as its `why` — so the reason an
answer is an answer travels with the connection, not in a list somewhere else.

**The library half.** Of **249 registered signals**, **218 are modelled** in the graph, along with
71 of the 80 indicator classes. That gap is deliberate:

- **Signals with no indicator beneath them** — a signal reading raw price with no measurement in
  between has no class to derive, and would sit in the graph as an unclassifiable node.
- **Stateful policy rules** — SuperTrend, PSAR, ChandelierExit, ATRTrailingStop, VolatilityStop.
  Their outputs are *verdicts*, not measurements: they carry a position forward and emit a direction.
  An indicator measures; these decide. They are excluded rather than mislabelled.
- **Private signal families** — on-chain and social signals ship in the package but are out of scope
  for the public ontology.

The graph is regenerated from a clean tree on every build, and a test rebuilds it into an empty path
and diffs against the committed file — so it cannot drift from the code it describes.

**Renames are never breaking.** A signal's registered name is the contract; a superseded duplicate
keeps working and carries a `supersedes` edge to its canonical replacement plus a deprecation
warning.

---

## Repository structure

```
MangroveKnowledgeBase/
├── mangrove_kb/                  ← the pip package
│   ├── graph.py                  ← the query library (stats · find · get · outputs ·
│   │                                neighbors · subgraph · path · all_paths)
│   ├── registry.py               ← RuleRegistry: evaluate a signal by name
│   ├── docstring_parser.py       ← docstring → structured metadata
│   ├── signals/                  ← 249 signal functions
│   ├── indicators/               ← 80 indicator classes
│   ├── viz/                      ← the self-contained graph viewer
│   ├── data/                     ← the graph, bundled at build time
│   └── skills/knowledge-graph/   ← SKILL.md + GUIDE.md, bundled at build time
├── ontology/
│   ├── build_signal_indicator_ontology.py   ← the ONLY thing that writes the graph
│   └── signal-indicator-ontology.json       ← the ontology of record
├── skills/knowledge-graph/       ← the agent skill and its guide (source of truth)
├── knowledge-base/               ← 11 trading-education documents
├── notebooks/                    ← signal explorer + validation
├── data/                         ← 7 sample OHLCV datasets
└── tests/                        ← the suite
```

The graph is **derived**. Authored values live in docstrings; everything else is read from the code.
Never edit `signal-indicator-ontology.json` by hand — change the docstring or the builder and rebuild:

```bash
python ontology/build_signal_indicator_ontology.py
```

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
flake8 mangrove_kb/ --max-line-length=120
```

---

## License

Free for noncommercial use under the [PolyForm Noncommercial License 1.0.0](LICENSE) — personal
study, hobby projects, research, teaching, and use by charitable, educational, public-research and
government organizations.

**Commercial use requires a paid license.** Using mangrove-kb in a product or service you sell, or
internally in a for-profit business, needs one — contact **support@mangrove.ai**.

Releases published before this change remain under the MIT license they shipped with.

---

## Contributing

Mangrove is named after the mangrove tree — an ecosystem where everything is interconnected,
resilient, and thriving. We think trading knowledge works the same way: the best strategies and the
most reliable tools don't come from hoarding information behind paywalls, they come from a community
that shares openly. If you want to contribute, join the discord and reach out to the team directly.

## Links

[GitHub Issues](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues).

Part of the [Mangrove](https://github.com/MangroveTechnologies) ecosystem —
[**join us on Discord**](https://discord.gg/Yycbw6P93B).

The [Mangrove](https://mangrove.io) app - try today for free, no subscription or payment required.

**If you find this useful, please star the repo** — it helps others discover it and keeps the project
growing.

- [PyPI](https://pypi.org/project/mangrove-kb/) · [GitHub](https://github.com/MangroveTechnologies/MangroveKnowledgeBase) · [Docs](https://mangrove.io/docs) · [Mangrove](https://mangrove.ai)
