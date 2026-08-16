# How the knowledge graph is built, stored and searched

Seven diagrams. The first three are about **what exists and where it comes from**; the next three
about **how a question becomes an answer**; the last about **three walks that are easy to confuse**.

No counts appear in a diagram label. A number in a box goes stale silently and no test can read
prose out of a diagram — the counts that are quoted anywhere are pinned by
`tests/test_documented_counts.py` instead.

| | diagram | answers |
|---|---|---|
| 1 | [Provenance and build](#1-provenance-and-build) | Where does a node come from, and which stage may overwrite what? |
| 2 | [What a node and an edge are](#2-what-a-node-and-an-edge-are) | What is stored, and what does each relation mean? |
| 3 | [One corpus, three readers](#3-one-corpus-three-readers) | What text is searched, and who else reads it? |
| 4 | [find() — matching words](#4-find--matching-words) | Why did that query return that? |
| 5 | [ask() — answering a question](#5-ask--answering-a-question) | What is a hop, and where does selection happen? |
| 6 | [The semantic index](#6-the-semantic-index) | How is meaning represented, and why is it not a second store? |
| 7 | [Three walks](#7-three-walks-that-are-easy-to-confuse) | What do `descendants`, `in_class` and `under` each return? |

---

## 1. Provenance and build

Three independent sources feed one record. They run **in order**, each taking the previous output as
its input, and the order is not arbitrary: the code builder is authoritative and nothing downstream
may overwrite what it wrote, so it runs first and everything after it merges.

```mermaid
flowchart LR
  subgraph sources[Sources]
    src[library source<br/>indicators · signals]
    wiki[ontology/wiki/*.md<br/>hand-authored anchors]
    raw[ontology/raw/*.md<br/>knowledge-base chapters]
    decl[CHAPTERS declarations<br/>in chapter_to_atoms.py]
  end

  subgraph builders[Builders · run in this order]
    b1[build_signal_indicator_ontology.py<br/><i>authoritative</i>]
    w2g[wiki-to-graph<br/>pinned to a commit]
    b2[wiki_to_atoms.py]
    b3[chapter_to_atoms.py<br/>one run per chapter]
    b4[build_semantic_index.py]
  end

  record[(signal-indicator-ontology.json<br/>atoms · relations · meta)]
  index[(mangrove_kb/data/<br/>semantic-index.npz)]

  src --> b1 --> record
  wiki --> w2g --> b2 --> record
  raw --> b3
  decl --> b3
  b3 --> record
  record --> b4 --> index

  record --> wheel[[wheel: data/ + skills/]]
  index --> wheel
  record --> viewer[[viewer: one static HTML file]]

  b4 -. embeds the record's sha256 .-> index
```

The dotted line is the guard: the index stores the checksum of the record it was built from, and a
mismatch makes it ignored rather than trusted. A chapter merged without rebuilding the index fails
`tests/test_semantic.py`.

## 2. What a node and an edge are

Everything is an atom with a primitive and a bag of authored properties; every relation carries the
reason it holds. The `why` is not decoration — it is filterable, and several traversals depend on it.

```mermaid
classDiagram
  class Node {
    id : primitive:slug
    name
    primitive : Concept|Procedure|Property|Fact|Judgment|Object|Schema
    summary
    status : draft|ratified|deprecated
    epistemic : observed|inferred|hypothesized|assumed
    props : formula, inputs, outputs, explanation,
    props : applications, principles, practices, examples,
    props : reference_chapter, source_wording, chapter_variants
    brief() : id, name, primitive, summary
    full() : brief + status + epistemic + props
  }
  class Edge {
    src
    dst
    relation
    why : why this edge holds
    props : e.g. which outputs a `uses` edge reads
  }
  Node "1" --> "many" Edge : src
  Edge "many" --> "1" Node : dst
```

The relation vocabulary, and the property that decides how each may be walked:

```mermaid
flowchart TB
  subgraph structural[structural · the rigid backbone]
    io[instance-of<br/>not transitive]
    ko[kind-of<br/>transitive]
    po[part-of<br/>transitive]
  end
  subgraph descriptive[descriptive · never inherited]
    hr[has-role<br/>anti-rigid]
    ab[about]
  end
  subgraph other[associative and meta]
    us[uses]
    su[supersedes]
  end

  io -->|"membership may be inherited"| BACKBONE([BACKBONE])
  ko --> BACKBONE
  po -->|"containment, not classification"| CONTAINMENT([under])
  ko --> CONTAINMENT
  hr -->|"what a thing is USED AS,<br/>never what it IS"| NEVER([never a supertype])
```

`has-role` is kept out of the backbone deliberately: `filter` is a part some signals play, not a kind
of signal, and returning a role where a type is expected is the classic modelling error
(Guarino & Welty, *OntoClean*). `part-of` is structural but **not** classification — which is why
`under()` exists beside `descendants()`; see [diagram 7](#7-three-walks-that-are-easy-to-confuse).

## 3. One corpus, three readers

Every searchable string is built once, by `haystacks()`, into five bands. Three different consumers
read it, and when they disagree the search answers differently depending on where you asked.

```mermaid
flowchart TB
  node[node fields<br/>name · id · summary · props]
  node --> t0[tier 0 · name, id]
  node --> t1[tier 1 · abbreviation]
  node --> t2[tier 2 · summary]
  node --> t3["tier 3 · formula, interpretation, applications,<br/>inputs, params, outputs, explanation,<br/>principles, practices, examples"]
  node --> t4["tier 4 · every other prop<br/>(a chapter may introduce one)"]

  t0 & t1 & t2 & t3 & t4 --> strip[strip URLs<br/>a link is provenance, not content]
  strip --> hay[["haystacks() · 5 lowercased bands<br/>tier order IS rank order"]]

  hay --> find["find() · ranks by which band matched"]
  hay --> lsa["build_semantic_index.py<br/>bands weighted 3·2·2·1·1"]
  hay --> idx["viewer IDX · exported into the page"]
  idx --> js["page rank() in JavaScript"]

  find -.->|"asserted equal by<br/>tests/test_viz.py, running node"| js
```

The dotted line is the second guard: the viewer's own JavaScript is executed in a JS engine during
the test run and its ordering compared against `find()`. A Python transcription of the algorithm
would have agreed with itself while the browser disagreed.

## 4. `find()` — matching words

The path a query takes. Two rules here surprise people, and both exist because of a measured defect:
a term most of the graph carries is dropped, and a query that matches nothing in full falls back to
its best partial match rather than returning nothing.

```mermaid
flowchart TB
  q([query string]) --> tok[split on non-alphanumeric<br/>keep terms ≥ 2 chars]
  tok --> fw{"all function words?"}
  fw -->|no| drop[drop function words<br/>why · do · what · is]
  fw -->|yes| keep[keep them<br/>a query of them still asks]
  drop --> pool
  keep --> pool

  pool[["candidate pool<br/>filters first: under=, kind=, role=,<br/>primitive=, status=, requires="]]
  pool --> hits[per node: which tier each term hits<br/>plural and singular both tried]
  hits --> df{"term carried by more than<br/>STOP_SHARE of the GRAPH?"}
  df -->|yes| dropterm[drop it from scoring<br/>measured over the whole graph,<br/>never the filtered pool]
  df -->|no| score
  dropterm --> score

  score{"does any node<br/>carry every term?"}
  score -->|yes| all[keep only those]
  score -->|no| best[keep those carrying<br/>the most terms]
  all --> rank
  best --> rank

  rank[sort by: terms missing,<br/>then worst tier hit,<br/>then id] --> cap[["cap at limit;<br/>Result says total and truncated"]]
```

## 5. `ask()` — answering a question

Seed, expand, re-rank. Seeding takes the nearest by meaning **and** anything carrying the question's
own words, because the two disagree often enough to lose an answer either way round. The expansion
takes **every** neighbour — there is no picking during the walk — and selection happens afterwards,
over the whole pool, because judging relevance before seeing the candidates is guessing.

```mermaid
flowchart TB
  q([question]) --> sem{"semantic index<br/>present and matching?"}
  sem -->|yes| seeds1["SemanticIndex.similar()<br/>nearest by meaning"]
  sem -->|yes| seeds3["find()<br/>carries the words"]
  sem -->|no| seeds2["find()<br/>nearest by words"]
  seeds1 --> frontier
  seeds3 --> frontier
  seeds2 --> frontier

  frontier[["seeds"]] --> bfs["breadth-first, undirected:<br/>every edge in or out"]
  bfs --> filt{"relations= / why=<br/>allow this edge?"}
  filt -->|no| skipped[not traversed]
  filt -->|yes| add[add node · keep the SHORTEST route<br/>and the edge that took it]
  add --> more{"hops remaining?"}
  more -->|yes| bfs
  more -->|no| rerank

  rerank{"seeded by meaning?"}
  rerank -->|yes| rs["rank pool by similarity<br/>to the question"]
  rerank -->|no| rl["rank pool by words<br/>missing, tier, then distance"]
  rs --> out
  rl --> out
  out[["each result carries `reached`:<br/>seed · hops · relation · that edge's why"]]
```

Measured, right node in the top five of twenty questions: words alone 8, words + 1 hop 10,
words + 2 hops 12, meaning + 1 hop 16. More hops is not strictly better — each round adds nodes that
compete on the same score, so a correct answer can be diluted down the list.

## 6. The semantic index

Latent semantic analysis over the graph's own text. Terms that occur in the same contexts end up in
the same direction, which is how a question about a breakout that *fails* reaches a node that says it
is read as a *loss* — sharing no word with the question.

```mermaid
flowchart TB
  subgraph build[Build · scikit-learn, once per graph change]
    docs["one document per node<br/>bands weighted 3·2·2·1·1"] --> tfidf["TF-IDF<br/>nodes × terms"]
    tfidf --> svd["truncated SVD · arpack, fixed seed<br/>so the artifact is reviewable as a diff"]
    svd --> vec[["vectors · nodes × components<br/>L2-normalised"]]
    svd --> comp[["components · components × terms"]]
    tfidf --> idf[["idf · terms"]]
  end

  subgraph query[Query · numpy only]
    qq([question]) --> qt["query_terms()<br/>the same tokenising find() uses"]
    qt --> weight["sublinear tf × idf, L2-normalised"]
    weight --> fold["fold through components<br/>→ a vector in the same space"]
    fold --> cos["cosine against every node<br/>one matrix multiply"]
    cos --> ids[["ranked NODE IDS"]]
  end

  comp --> fold
  idf --> weight
  vec --> cos
  ids --> back[["back into the graph:<br/>ask() walks edges from here"]]
```

**Why this is not a disjoint layer.** Every row is keyed by a node id; there is no passage store and
no chunking, so a hit is always a node and the edges still do the explaining. It is built from the
same text `find()` searches, and it carries the record's checksum so it cannot silently answer about
an older graph. A pretrained sentence model was measured against it and scored lower on this corpus —
it knows English better and this vocabulary not at all.

## 7. Three walks that are easy to confuse

Same fragment of the graph, three questions, three different answers.

```mermaid
flowchart BT
  sig[procedure:signal-rsi-oversold]
  ind[procedure:indicator-rsi]
  osc[concept:oscillator]
  ta[concept:technical-analysis]
  role[property:role-filter]
  space[object:mangrove-knowledge-space]

  sig -->|instance-of| sigtype[concept:signal]
  sig -->|uses| ind
  sig -->|about| osc
  sig -->|has-role| role
  ind -->|instance-of| osc
  osc -->|kind-of| ta
  ta -->|part-of| space
```

| call | walks | on `concept:oscillator` |
|---|---|---|
| `descendants()` | `instance-of` + `kind-of`, transitively — **classification only** | the indicators that measure it |
| `in_class()` | that, plus a one-hop `about` projection | those, plus the signals concerned with them |
| `under()` | every transitive structural relation **including `part-of`**, plus `instance-of` and the same `about` projection | everything contained by a subject, whatever primitive |

`descendants()` on a subject area returns nothing, because a chapter's terms are `part-of` it and not
`kind-of` it. That is exactly the bug `under()` was added to fix: "everything from market foundations"
returned almost nothing while the graph held over a hundred nodes for it.

**A role is never walked as a type.** `has-role` appears in no closure above — asking for oscillators
must never return the things merely *used as* filters.

---

## Keeping these honest

- Diagrams carry no counts; the numbers live in prose that `tests/test_documented_counts.py` pins.
- The build order in diagram 1 is enforced by `tests/test_doc_derived_atoms.py` (the record must be
  the merged output, not the code build alone) and `tests/test_rebuild_pipeline_is_runnable.py`.
- Diagram 3's dotted line is `tests/test_viz.py`, which runs the page's own JavaScript.
- Diagram 6's checksum is `tests/test_semantic.py`.
