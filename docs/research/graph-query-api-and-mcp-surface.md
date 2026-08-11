# Graph query API and MCP tool surface — prior art

Grounding for the `mangrove_kb` graph layer: a Python query library, a skill, and an MCP server over
the signal/indicator knowledge graph. Surveyed 2026-08-09 across four axes — production practice,
academic literature, standards, and our own prior art.

**Graph at time of survey:** 301 nodes, 732 edges. Primitives `Object 1 / Concept 7 / Procedure 288 /
Property 4 / Schema 1`. Relations `instance-of 286 / has-role 216 / uses 214 / kind-of 10 /
part-of 4 / supersedes 2`.

Two shape facts drive everything below:

- **216 of 301 nodes carry two containment parents** — every signal is `instance-of Signal` *and*
  `has-role trigger|filter`. The cross-cutting axis is 72% of the graph, not an edge case.
- **Hubs are large relative to the graph**: `concept:signal` degree 218, `property:role-filter` 114,
  `property:role-trigger` 104. Any unbounded neighbour call returns most of the graph.

---

## 1. Corrections to our own documentation (found by this survey)

These are stated first because they invalidate claims we currently ship.

### 1.1 We are not following "the Biolink pattern"

`jarvis/src/jarvis/graph/model/ontology.py` — vendored into `tools/mangrove-kg`, and the stated
foundation of this ontology — claims:

> Relationships form a **hierarchy** (the Biolink pattern): every relation inherits from the generic
> root `associated-with`; under it sit six categories (structural, causal, descriptive, associative,
> temporal, meta)

Verified against `biolink/biolink-model` v4.4.3 (`biolink-model.yaml`, parsed; corroborated by a
second independent fetch):

| our claim | Biolink actually |
|---|---|
| root is `associated with` | root is **`related to`** — "a relationship that is asserted between two named things"; carries `broad_mappings: owl:topObjectProperty` |
| `associated with` is generic | it is a **narrow leaf-ish predicate** under `related to at instance level`: "indicates a non-causal association between two entities… established through statistical analysis" |
| six mid-level categories | **two**: `related to at concept level` and `related to at instance level` (a TBox/ABox split) |

**Disposition.** The *model* is fine; the *attribution* is wrong. Six semantic categories that let a
consumer ask for "all causal edges" is more useful for a single curated graph than Biolink's
federation-driven TBox/ABox split. Keep the categories, stop crediting Biolink for them, and either
rename the root to `related-to` or publish `broad_mappings: owl:topObjectProperty` on it — which is
exactly what Biolink does for its own root.

### 1.2 We draw three lines where every standard draws one

We hold `is-a`, `kind-of` **and** `instance-of` as distinct structural leaves. RDFS, OWL, OBO, SKOS
and Wikidata all draw exactly one distinction in this region: instance→class (`rdf:type`) versus
class→class (`rdfs:subClassOf`). `is-a` and `kind-of` are two names for the same predicate, and no
surveyed vocabulary uses the string "kind of".

### 1.3 Audit of `jarvis/docs/memory/research/01-graph-memory-llm-agents.md`

That file was written by an agent in an environment that fabricates convincing paper pages, so every
citation was re-verified against dblp / ACL Anthology / official proceedings.

**Result: no fabrications. All 8 entries real.** Two entries flagged as suspect on date grounds
(MAGMA, GAAMA, both 2026) both check out — MAGMA is peer-reviewed at **ACL 2026** (pp. 36848–36865,
`aclanthology.org/2026.acl-long.1709`) and is the strongest-verified entry in the file.

Three accuracy defects to fix before building on it:

1. **Zep** — credits only "Preston Rasmussen"; actual authors Rasmussen, Paliychuk, Beauvais et al.
2. **GAAMA** — "Swarna Kpaul" is a mangled name; actual authors Swarna Kamal Paul, Shubhendu Sharma,
   Nitin Sareen. Preprint-only (`corr/abs-2603-27910`) — demote from the peer-reviewed set.
3. **Mem0** → now **ECAI 2025** (DOI 10.3233/FAIA251160); **Peng survey** → now **ACM TOIS 2026**
   (DOI 10.1145/3777378). Both have graduated from preprint; upgrade the citations.

Also: half that file (MemGPT, GraphRAG, Zep, GAAMA) is preprint-only but presented at equal weight.
A public package's rationale must mark which claims rest on peer review.

---

## 2. Verified references

### 2.1 Academic literature

Every entry independently corroborated against a non-arXiv signal. A control test (three invented
titles) returned zero dblp hits, confirming dblp discriminates in this environment.

| Paper | Principle | API consequence | Verification | Conf. |
|---|---|---|---|---|
| Steimann, *On the representation of roles in object-oriented and conceptual modelling*, **Data & Knowledge Engineering** 2000 | **A role is not a subclass.** Roles are dynamic, multiple, orthogonal to identity; conflating role with type is the classic modelling error | Our two axes stay two axes. `kind`/`role` are separate parameters; closure applies to `kind-of`, **never** to `has-role`; a role must never surface as a supertype | dblp `journals/dke/Steimann00` | HIGH |
| Guarino & Welty, *Evaluating ontological decisions with OntoClean*, **CACM** 2002 | Roles are **anti-rigid** and must not form the backbone taxonomy; only rigid types do | `instance-of`/`kind-of` is the single rigid backbone used for inheritance; `has-role` is a cross-cutting index. Enforce in the API contract | dblp `journals/cacm/GuarinoW02` | HIGH |
| Peng et al., *Graph Retrieval-Augmented Generation: A Survey*, **ACM TOIS** 2026 | Retrieval granularity taxonomy: node / triple / path / subgraph, each a distinct precision-vs-context trade-off | Ship four distinct entry points, not one overloaded `query()` | DOI 10.1145/3777378 | HIGH |
| He et al., *G-Retriever*, **NeurIPS** 2024 | Subgraph retrieval as a **size-bounded optimization** — the returned subgraph is explicitly budgeted | Hard node/edge budget with explicit `truncated` / `omitted` reporting. Never silently clip | NeurIPS 37 proceedings | HIGH |
| Cuenca Grau et al., *Modular Reuse of Ontologies*, **JAIR** 2008 | **Locality-based modules** carry a logical guarantee: the module preserves entailments over its signature | Document what `subgraph` is *closed under*, rather than an arbitrary depth cut | DOI 10.1613/jair.2375 | HIGH |
| Luo et al., *Reasoning on Graphs*, **ICLR** 2024 | Plan relation paths **on the schema** first, then ground on instances | Schema introspection is a first-class tool, so agents plan without guessing edge names | dblp `conf/iclr/LuoLHP24` | HIGH |
| Jiang et al., *StructGPT*, **EMNLP** 2023 | Give the LLM a small set of specialized interfaces over the structure; it never sees raw storage | Justifies a fixed ~6–8 tool surface instead of a query language | dblp `conf/emnlp/JiangZDYZW23` | HIGH |
| Xiong et al., *Interactive-KBQA*, **ACL** 2024 | A deliberately **tiny** KB tool set drives multi-turn interaction better than an expressive one | Cap the surface; one graph operation per tool | `aclanthology.org/2024.acl-long.569` | HIGH |
| Kuric et al., *KG Exploration: Usability Evaluation of Query Builders for Laypeople*, **SEMANTiCS** 2019 | Maximum expressiveness **hurts** — the most SPARQL-complete builder scored worst, from information overload | Resist one god-tool with 12 optional parameters | DOI 10.1007/978-3-030-33220-4_24 | HIGH |
| Ferré, *Sparklis*, **Semantic Web Journal** 2017 | **Guided-navigation invariant**: every intermediate state is a valid query with a non-empty result — no dead ends | Enumerate legal values; on a miss return candidate corrections, never a bare empty list | dblp `journals/semweb/Ferre17` | HIGH |
| Patil et al., *Gorilla*, **NeurIPS** 2024 | **API hallucination is the dominant failure mode**; constraining to a documented API set fixes it | Enumerate valid relation/role/primitive names **in the JSON schema** so the model cannot invent `is_a` when we mean `kind-of` | dblp `conf/nips/PatilZ0G24` | HIGH |
| Qin et al., *ToolLLM*, **ICLR** 2024 | Large flat tool surfaces need retrieval *over tools*; small curated sets do not | Stay at ~6–8 tools so no tool-retrieval layer is ever needed | dblp `conf/iclr/QinLYZYLLCTQZHT24` | HIGH |
| Sun et al., *Think-on-Graph*, **ICLR** 2024 | LLM as an agent that **steps** the graph — small frontier per step, not one bulk dump | Return a compact frontier plus the legal next moves | dblp `conf/iclr/SunXTW0GNSG24` | HIGH |
| Gutiérrez et al., *HippoRAG*, **NeurIPS** 2024 | Single-shot Personalized PageRank matches iterative multi-hop retrieval at 10–30× lower cost | Offer one cheap ranked-relatedness call so "what relates to X" is not an agent loop | NeurIPS 37 proceedings | HIGH |
| Katifori et al., *Ontology visualization methods*, **ACM CSUR** 2007; Dudáš et al., **KER** 2018 | Navigating large ontologies needs **overview + focus/context**, never raw dumps | Global `stats` alongside local `neighbors`. Both, always | DOI 10.1145/1287620.1287621 | HIGH |
| Zhang et al., *Ontology summarization based on RDF sentence graph*, **WWW** 2007 | Salience-ranked summarization — return the *important* slice | When over budget, rank by a **declared** criterion and say which | dblp `conf/www/ZhangCQ07` | HIGH |
| Seifer et al., *Usage of graph query languages in OSS Java projects*, **SLE** 2019 | Real embedded queries use a small, simple fragment; mostly untyped strings, unchecked | Typed Python functions with enumerable parameters beat a string DSL | DOI 10.1145/3357766.3359541 | HIGH |
| Pan et al., *Unifying LLMs and Knowledge Graphs*, **IEEE TKDE** 2024 | KGs supply the verifiable, non-hallucinated substrate | Every response carries provenance (node id, relation traversed) so an agent cites rather than paraphrases | dblp `journals/tkde/PanLWCWW24` | HIGH |

**Excluded — surfaced but not corroborated:** "S-Path-RAG" (arXiv 2603.23512), "KGFR" (arXiv
2511.04093), a drpress.org survey, "KGMP", "GNN Enhanced Retrieval" (arXiv 2406.06572). All
arXiv-or-worse only, zero dblp records. Do not cite.

### 2.2 Standards

| Standard | Convention to conform to | URL | Conf. |
|---|---|---|---|
| **MCP 2026-07-28** (current; *not* 2025-06-18) | `tools/list`+`tools/call`; Tool = `name`,`title`,`description`,`inputSchema`,`outputSchema`,`annotations`,`_meta`; normative **Tool Names** §; mandatory `_meta`; `resultType`; result caching | modelcontextprotocol.io/specification/2026-07-28/server/tools | HIGH |
| MCP `ToolAnnotations` defaults | `readOnlyHint` **false**, `destructiveHint` **true**, `idempotentHint` false, `openWorldHint` **true** — silence mislabels a read-only server | schema/2026-07-28/schema.ts | HIGH |
| SPARQL 1.1 property paths | `InversePath ^`, `SequencePath /`, `AlternativePath |`, `ZeroOrMorePath *`, `OneOrMorePath +`, `ZeroOrOnePath ?` | w3.org/TR/sparql11-query/#propertypaths | HIGH |
| ISO/IEC 39075:2024 (GQL) | Pattern sub-language is **GPML**; Ed. 1.0, 2024-04-12 | iso.org/standard/76120.html · webstore.iec.ch/en/publication/94107 | HIGH (metadata) / clause text paywalled |
| RDFS 1.1 | `rdf:type`; `rdfs:subClassOf` (**transitive**); `rdfs:subPropertyOf` | w3.org/TR/rdf-schema/ | HIGH |
| SKOS | `skos:broader` is **not** transitive; `skos:broaderTransitive` is — the split exists because conflating them breaks closure | w3.org/TR/skos-reference/ | HIGH |
| OBO RO / BFO | `RO:0000087` **has role**; `BFO:0000050` **part of** | ebi.ac.uk/ols4/api (exercised live) | HIGH |
| DCMI Terms | `dcterms:replaces` — definition literally reads "supplants, displaces, or **supersedes**" | dublincore.org/specifications/dublin-core/dcmi-terms/ | HIGH |
| W3C PROV-O | `prov:used`, `prov:wasDerivedFrom` | w3.org/TR/prov-o/ | HIGH |
| Biolink v4.4.3 | snake_case CURIE predicates; `canonical_predicate: true` + `inverse:` naming; `exact_mappings` | github.com/biolink/biolink-model | HIGH |
| TRAPI | `GET /meta_knowledge_graph` — machine-readable set of (category, predicate, category) triples the server can answer | github.com/NCATSTranslator/ReasonerAPI | HIGH |
| EBI OLS4 / BioPortal | Converged endpoints: `search`, `parents`, `children`, `ancestors`, `descendants` | ebi.ac.uk/ols4/api · data.bioontology.org/documentation | HIGH / MEDIUM-HIGH |

**Relation name mapping** (the cheapest interoperability win — no edge changes required):

| ours | canonical | verdict |
|---|---|---|
| `instance-of` | `rdf:type` | semantics conform exactly |
| `kind-of` | `rdfs:subClassOf` / OBO `is_a` / `skos:broader` / Wikidata P279 | **diverges — nothing is called "kind of"** |
| `has-role` | `RO:0000087` **has role** | conforms exactly, label included |
| `part-of` | `BFO:0000050` | conforms exactly |
| `uses` | `prov:used` (nearest) | no standard predicate named `uses`; no collision either |
| `supersedes` | `dcterms:replaces` | semantics conform exactly |
| root `associated-with` | Biolink root `related to`; `owl:topObjectProperty` | **name collision** — see §1.1 |

### 2.3 Production practice

| Project | Surface | Design choice worth taking | Conf. |
|---|---|---|---|
| `modelcontextprotocol/servers` **memory** | `search_nodes`, `open_nodes`, `read_graph` + 6 writes | Read path is **search → open-by-name → whole graph**; entities addressed by **name**, not opaque id; graph also exposed as a **resource** (`memory://knowledge-graph`) | HIGH |
| **neo4j/mcp** (official) | `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures` | `get-schema` is the mandatory orientation tool; read/write split into separate tools | HIGH |
| **neo4j-contrib/gds-agent** | GDS tools **+ a paired `SKILL.md`** | **Direct precedent for our (2)+(3):** server and skill ship from one repo, consumed by Claude Code plugin, Gemini extension and release zip. Hard caps as env vars (500 rows / 100k chars / 200 per cell) | HIGH |
| **memgraph/ai-toolkit** | `run_cypher_query`, `get_node_schema`, `get_relationship_schema`, `get_enum_schema`, `search_schema` | Schema **decomposed** into several tools plus a `search_schema`, so the agent finds the relevant slice | HIGH |
| **getzep/graphiti** | 13 tools incl. `search_nodes`, `search_memory_facts` | Nodes and edges get **separate** search tools; embeddings stripped at the serialiser; empty results are typed (`message='No relevant nodes found'`), never a bare `[]` | HIGH |
| **mem0ai/mem0** | `search_memories`/`get_memories` ↔ `Memory.search`/`get_all` | **Library methods and MCP tools are 1:1**; the MCP layer holds no logic | HIGH |
| NetworkX 3.6.1 / igraph 1.0.0 / rustworkx 0.18.1 | `ego_graph(radius=)`, `neighborhood(order=, mode=)`, `neighbors_undirected` | Bounded traversal is **`radius`/`order`, never `depth`**; direction is `mode="in"/"out"/"all"`; ego retrieval returns an **induced subgraph**, not a node list | HIGH |
| Anthropic, *Writing tools for agents* | guidance | "More tools don't always lead to better outcomes"; prefix namespacing; natural-language ids over UUIDs; errors must name the fix | HIGH (single-source figures) |

### 2.4 Our own prior art

- **`mangrove-skills-plugin/skills/kg-search/SKILL.md`** — the template: *what the graph folds
  together → node vocabulary → a question→tool table → rules of use*. Its "rules of use" section
  (staleness stamp, `draft` ≠ fact, verified ≠ enabled ≠ prod, "the graph is evidence, not
  authority") is the transferable pattern.
- **Every mangrove-kg response opens with `[graph generation N, built Xh ago]`** so a negative result
  cannot be mistaken for truth from a stale build. Adopt as an ontology-version stamp.
- **`tools/mangrove-kg/src/mcp_server.py`** — 8 discrete tools; `Graph` class with
  `find/neighbors/walk/path/impact/brief`. Note the **anti-pattern to avoid**: `kg_stats`,
  `kg_endpoint` and `kg_feature` compute inline **in the dispatcher**, not in `Graph`. Fine for one
  consumer; wrong for a public package where the library must work standalone.
- **`jarvis/src/jarvis/graph/surfaces/tool.py`** — `GraphSearchTool` uses **one tool with an `op`
  parameter**, contradicting the mangrove-kg design. Its `relation` **and** `category` parameters,
  hierarchy-expanded, are the right control for a poly-hierarchy and should be adopted.

---

## 3. Principles — the minimum to be defensible

1. **Curated typed tools, not a query language.** (Seifer SLE 2019; StructGPT; Interactive-KBQA)
2. **Four granularities as separate entry points** — node, edge, path, subgraph. (Peng TOIS 2026)
3. **The two axes stay orthogonal.** `kind` and `role` are separate parameters; closure applies to
   `kind-of` and **never** to `has-role`; a role is never returned as a supertype. (Steimann 2000;
   OntoClean 2002) — *the single most load-bearing constraint for this graph.*
4. **Every traversal budgeted, truncation audible**, with a declared ranking criterion.
   (G-Retriever; Zhang WWW 2007)
5. **Documented closure guarantee** on subgraph extraction. (Cuenca Grau JAIR 2008)
6. **Schema introspection is a first-class tool.** (RoG; StructGPT; and every production server has
   a `get-schema` analogue)
7. **No dead ends** — enumerate legal values, return candidates on a miss. (Sparklis; Kuric)
8. **Small signatures over one god-tool.** (Kuric SEMANTiCS 2019)
9. **Overview and focus both present.** (Katifori CSUR 2007; Dudáš KER 2018)
10. **Enumerate valid names in the JSON schema** to kill relation-name hallucination. (Gorilla)
11. **Provenance on every result.** (Pan TKDE 2024)
12. **Library is the source of truth; the MCP layer holds no logic.** (mem0; Memgraph; and our own
    dispatcher-logic anti-pattern)

---

## 4. Adopt / defer

**Adopt now**

- Discrete tools at orient → search → fetch → expand granularity. No `op` enum: no surveyed graph
  MCP server uses one.
- `radius` not `depth`; `direction: "in"|"out"|"both"`; `relation` **and** `category` filters.
- `stats()` as the orientation tool, documented "call this first".
- Bounded returns with explicit truncation notices; small defaults.
- MCP annotations set explicitly (`readOnlyHint: true`, `openWorldHint: false`) — defaults mislabel us.
- Errors as `isError: true` with actionable text naming the fix.
- `exact_mappings` to `RO:0000087`, `BFO:0000050`, `rdf:type`, `rdfs:subClassOf`, `dcterms:replaces`,
  `prov:used`.
- Ontology-version stamp on every response.
- Skill shipped in the same repo as the server (gds-agent precedent).
- Whole graph as an MCP **resource** as well as tools — at 301 nodes it is one readable artifact.

**Defer, deliberately**

- Pagination cursors — nothing can overflow yet; keep the `nextCursor` shape in reserve so adding it
  is not breaking.
- GQL/SPARQL engines — borrow the vocabulary, not the implementation.
- Ranked relatedness (PPR-style) — one cheap call would help, but degree-weighted is unvalidated at
  this scale; file as an epic.
- Renaming `kind-of` → `subclass-of` and collapsing `is-a`/`kind-of` — correct, but it changes the
  ontology and belongs with the graph owners, not this PR.
- `annotator`/`recommender` style endpoints — biomedical text-mining workloads we do not have.

---

## 5. Novelty — how ours differs and why it is better

The agent-memory and GraphRAG literature builds knowledge graphs **bottom-up by LLM extraction**
from unstructured text, then retrieves over whatever structure emerged. Our graph is the inverse: it
is **authored**, typed by a foundational upper ontology, and derived deterministically from
executable source — every indicator node carries its formula, typed inputs, parameters and outputs
with units and ranges, and every `uses` edge records *which specific output* a downstream signal
reads. Retrieval over it is therefore exact rather than approximate: there is no extraction noise to
rank around, and provenance is the code itself.

The distinctive constraint is that our classification is genuinely **two-axis and mostly
poly-hierarchical** — 216 of 301 nodes are simultaneously an instance of a type and a bearer of a
role. Steimann (DKE 2000) and Guarino & Welty's OntoClean (CACM 2002) establish why this must not be
flattened: roles are anti-rigid and cannot form a backbone taxonomy. Steimann further shows there is
**no consensus formalism for roles**, and OWL has no native role construct — so a query API that
keeps the rigid backbone (`instance-of`/`kind-of`, transitively closed) strictly separate from the
anti-rigid role index (`has-role`, never closed, never subsuming), and lets a caller intersect them
in a single call, is a defensible engineering contribution rather than an application of settled
practice. No system in the surveyed KGQA/GraphRAG line applies a formal ontology layer to constrain
the graph at all; that gap survived an independent search.

The practical payoff is a public package where an agent can ask *"which momentum indicators produce
a bounded oscillator output, and which trigger-role signals read it"* — a question that requires the
type axis, the role axis, and typed output metadata simultaneously, and that neither a document
search nor a generic entity-graph API can express.

---

## 6. Open problems (from the literature, not ours to solve)

- **Granularity selection is unsolved** — no principled rule for choosing node vs path vs subgraph
  per query (Peng TOIS 2026). Make it the caller's explicit choice.
- **Iterative vs single-shot retrieval is unsettled** — HippoRAG's one-shot PPR matches iterative
  methods cheaply; Think-on-Graph and Interactive-KBQA favour iteration. Offer both.
- **Ontology summarization has no agreed quality metric** (Zhang 2007; Dudáš 2018). Any salience
  ranking we pick is unvalidated.
- **Benchmarks are Freebase/Wikidata-scale.** Nothing evaluates retrieval over a ~300-node curated
  ontology. Borrowed results may not transfer to our regime.
