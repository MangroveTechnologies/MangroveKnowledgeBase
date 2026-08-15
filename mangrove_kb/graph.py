"""Query the signal/indicator knowledge graph.

The knowledge space is a curated graph over the library's own indicators and signals: what each
computation *is*, what it consumes and produces, which signals read which of its outputs, and what
part each signal plays in a strategy. It is generated from the source, so it is exact rather than
extracted -- there is no text-mining noise to rank around.

**Two classification axes, and they are not interchangeable.** Every signal is simultaneously an
``instance-of`` a type and a bearer of a ``has-role`` role (218 of 498 nodes carry both). These are
kept strictly apart throughout this module:

* ``instance-of`` / ``kind-of`` is the **rigid backbone** -- what a thing *is*. It is transitively
  closed, so asking for indicators of class ``momentum`` reaches members of its subclasses.
* ``has-role`` is an **anti-rigid index** -- what a thing is *being used as*, which is contextual
  rather than intrinsic. It is deliberately **never** closed and never treated as a supertype.

Flattening the two is the classic modelling error (Steimann, *Data & Knowledge Engineering* 2000;
Guarino & Welty, *OntoClean*, CACM 2002): roles are anti-rigid and cannot form a backbone taxonomy.
Concretely, ``filter`` is not a kind of signal -- it is a part some signals play -- so a role must
never be returned where a type is expected, and role membership must never be inherited. That is why
:meth:`KnowledgeGraph.find` takes ``kind`` and ``role`` as *separate* parameters and intersects them,
rather than offering one "category" argument that silently means either.

Design notes are recorded in ``docs/research/graph-query-api-and-mcp-surface.md``.

Usage::

    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    kg.stats()["relations"]                          # what vocabulary exists at all
    kg.find(kind="momentum", role="trigger")         # both axes at once
    kg.get("procedure:indicator-rsi")["outputs"]     # typed outputs with units and range
    kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in")   # who reads it

A signal's class is not a property it declares -- it is derived from the graph: ``signal --uses-->
indicator --instance-of--> class``. :meth:`KnowledgeGraph.in_class` walks that, so ``kind`` reaches
signals and indicators alike.
"""
from __future__ import annotations

import functools
import json
import os
import re
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

__all__ = ["KnowledgeGraph", "Node", "Edge", "Result", "GraphError", "NodeNotFound"]


# --- the relation vocabulary ---------------------------------------------------------------------
# Mirrors the upper ontology the builder writes against. Held here so the library has no dependency
# on the builder, and so a consumer can enumerate legal values instead of guessing relation names --
# guessing is the dominant tool-use failure mode (Patil et al., Gorilla, NeurIPS 2024).
#
# `exact` mappings are semantic assertions: our relation and the standard term mean the same thing,
# and a consumer may substitute one for the other. `close` is a near match that is NOT substitutable.
# Getting that distinction wrong is worse than publishing no mapping at all.
RELATIONS: dict[str, dict[str, Any]] = {
    "instance-of": {"category": "structural",  "transitive": False, "exact": "rdf:type"},
    "kind-of":     {"category": "structural",  "transitive": True,  "exact": "rdfs:subClassOf"},
    "part-of":     {"category": "structural",  "transitive": True,  "exact": "BFO:0000050"},
    "has-role":    {"category": "descriptive", "transitive": False, "exact": "RO:0000087"},
    # An indicator MEASURES its class; a signal is CONCERNED WITH it. `dcterms:subject` because
    # momentum is the signal's subject, not its type -- a signal emits a boolean and measures
    # nothing. Descriptive, so it stays out of BACKBONE and nothing is inherited along it.
    "about":       {"category": "descriptive", "transitive": False, "exact": "dcterms:subject"},
    "uses":        {"category": "associative", "transitive": False, "close": "prov:used"},
    "supersedes":  {"category": "meta",        "transitive": False, "exact": "dcterms:replaces"},
}

#: The rigid backbone: the only relations along which class membership may be inherited.
BACKBONE: tuple[str, ...] = ("instance-of", "kind-of")

#: Anti-rigid. Never closed, never inherited, never returned as a type. See the module docstring.
ROLE_RELATION = "has-role"

#: The character axis. The classes a computation can be classified into are exactly the immediate
#: subclasses of this node -- what a computation MEASURES, which is orthogonal to what KIND of thing
#: it is. Named here rather than inferred because every alternative was a guess: deriving the class
#: list from "everything the backbone points at" swept in the entity types (`concept:indicator`,
#: `concept:signal`) and the role axis, so `stats()` advertised `find(kind=...)` arguments that
#: return every indicator, every signal, or the two role values -- filters that read as a query and
#: act as a no-op.
CLASS_AXIS_ROOT = "concept:technical-analysis"

CATEGORIES: tuple[str, ...] = ("structural", "descriptive", "associative", "meta")

#: What :meth:`KnowledgeGraph.find` reads, best match first. A query is ranked by *where* it hit, so
#: the thing actually named for a term outranks the thing that merely mentions it.
#:
#: Tier 3 exists because searching only the headline fields produced false negatives on exactly the
#: question the search is for -- "is there already something for X". ``find("mean reversion")``
#: returned nothing while two nodes described it in prose, and ``find("crossover")`` returned 32 of
#: the 62 nodes that mention it. The authored detail is where a computation is actually explained.
#: A doc-derived node has no formula, params or outputs -- its ``explanation`` body is the same
#: thing for it, so it belongs in the same tier rather than a tier of its own.
SEARCH_TIERS: tuple[tuple[str, ...], ...] = (
    ("name", "id"),
    ("abbreviation",),
    ("summary",),
    ("formula", "reference", "interpretation", "applications",
     "inputs", "params", "outputs",           # slot NAMES and their descriptions
     "explanation",                           # the doc-derived body (see `reference_chapter`)
     # A chapter node's content IS these lists -- 39 principles, 50 practices, the worked examples.
     # Leaving them out made `find("mean reversion")` miss the node that states it, which is the
     # exact false negative SEARCH_TIERS was widened to prevent.
     "principles", "practices", "examples"),
)

#: A link is provenance, not content. Left in the corpus, ``find("com")`` returned 336 of 498 nodes
#: and ``find("http")`` 233, because every code-derived node cites a URL -- and one useless query
#: that returns most of the graph teaches a caller not to trust the search at all.
_URL = re.compile(r"https?://\S+|www\.\S+")

#: Two characters minimum. A single letter matches everything, which is not a search result.
MIN_QUERY = 2


def query_terms(query: str) -> list[str]:
    """A query as the terms it is made of, so word order stops mattering.

    ``"mean reversion"`` and ``"reversion mean"`` are the same question and used to return 11 nodes
    and none, because the query was matched as one literal string. Each term is matched
    independently and a node must carry all of them.
    """
    return [t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) >= MIN_QUERY]


@functools.lru_cache(maxsize=1024)
def _variants(term: str) -> tuple[str, ...]:
    """A term and the plural or singular of it, so ``zone`` and ``zones`` ask the same question.

    Deliberately crude -- an English stemmer would fold ``basis`` to ``basi`` and ``futures`` to
    ``future``, which are different words in this domain, so nothing is stripped from a term the
    graph would then fail to find. Both forms are tried; whichever exists is what matches.
    """
    if len(term) < 4:
        return (term,)
    if term.endswith("ies"):
        return (term, term[:-3] + "y")
    if term.endswith("es"):
        return (term, term[:-2], term[:-1])
    if term.endswith("s"):
        return (term, term[:-1])
    return (term, term + "s", term + "es")


def rank_of(hay: tuple[str, ...], terms: Sequence[str]) -> int | None:
    """Which tier a query matched in, or None if the node does not carry every term.

    The rank is the WORST tier among the terms: a node holding both words in its name outranks one
    that has one in its name and the other buried in a formula. Ties break on id, so a result is
    reproducible.
    """
    worst = 0
    for term in terms:
        hit = next((i for i, text in enumerate(hay)
                    if any(v in text for v in _variants(term))), None)
        if hit is None:
            return None
        worst = max(worst, hit)
    return worst


def haystacks(source: dict) -> tuple[str, ...]:
    """One lowercased string per search tier, for a node's fields.

    The last band is everything the tiers do not name. An allow-list had to grow every time a
    chapter introduced a prop -- a comparison table, a caution, a heading nobody anticipated -- and
    until it did, a term stated only there was invisible to the search that answers "do we have
    anything for X?".

    Defined once because two callers need identical ranking: the query layer, and the viewer's
    precomputed index. A second copy in the renderer would drift from this one silently.
    """
    ranked = {f for tier in SEARCH_TIERS for f in tier}
    tiers = [" ".join(_flatten(source.get(f)) for f in tier).lower() for tier in SEARCH_TIERS]
    tiers.append(" ".join(_flatten(v) for k, v in source.items() if k not in ranked).lower())
    return tuple(_URL.sub(" ", t) for t in tiers)


#: Where the graph is looked for, in order. An explicit path always wins; ``MANGROVE_KB_ONTOLOGY``
#: lets a caller point at a build output; then the copy shipped inside the package; then the
#: repository layout, so the library works from a source checkout with no install step.
_ENV_VAR = "MANGROVE_KB_ONTOLOGY"
_PACKAGED = Path(__file__).resolve().parent / "data" / "signal-indicator-ontology.json"
_IN_REPO = Path(__file__).resolve().parent.parent / "ontology" / "signal-indicator-ontology.json"

#: Default result caps. Small on purpose: a hub in this graph has degree 218, so an unbounded
#: neighbour call returns most of the graph and swamps whatever asked for it. Callers raise them
#: deliberately; every truncated result says so out loud rather than looking complete.
DEFAULT_LIMIT = 25
DEFAULT_FIND_LIMIT = 10
DEFAULT_SUBGRAPH_NODES = 50


class GraphError(Exception):
    """Base class for graph query errors."""


class NodeNotFound(GraphError):
    """Raised when an id does not resolve. Carries suggestions so the caller can recover.

    A bare failure is a dead end; the guided-navigation literature (Ferré, *Sparklis*, SWJ 2017)
    treats "every state offers a next move" as the property that makes exploration usable. So the
    message names candidates rather than only reporting the miss.
    """

    def __init__(self, ref: str, suggestions: Sequence[str] = ()):
        self.ref = ref
        self.suggestions = list(suggestions)
        hint = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else \
               " Call find() to search, or stats() for the vocabulary."
        super().__init__(f"no node matching {ref!r}.{hint}")


@dataclass(frozen=True)
class Node:
    """One node, with its authored properties."""

    id: str
    name: str
    primitive: str
    summary: str = ""
    status: str | None = None
    epistemic: str | None = None
    props: dict[str, Any] = field(default_factory=dict)

    def brief(self) -> dict[str, Any]:
        """The concise projection: enough to decide whether to fetch the whole node.

        Returned by every search and traversal. Full properties -- formula, inputs, params, outputs
        -- come only from an explicit :meth:`KnowledgeGraph.get`, because they are large and are
        rarely what a caller scanning results needs.
        """
        return {"id": self.id, "name": self.name, "primitive": self.primitive,
                "summary": self.summary}

    def full(self) -> dict[str, Any]:
        return {**self.brief(), "status": self.status, "epistemic": self.epistemic, **self.props}


@dataclass(frozen=True)
class Edge:
    """One relation. ``props`` carries facts about the relationship itself.

    ``uses`` edges carry ``inputs`` -- *which* of the indicator's outputs the signal reads. That is a
    fact about the connection, not about either endpoint, and storing it on a node would put it in
    the wrong place and lose it for signals that read two indicators.
    """

    src: str
    dst: str
    relation: str
    why: str = ""
    props: dict[str, Any] = field(default_factory=dict)

    @property
    def category(self) -> str | None:
        spec = RELATIONS.get(self.relation)
        return spec["category"] if spec else None

    def as_dict(self) -> dict[str, Any]:
        return {"src": self.src, "dst": self.dst, "relation": self.relation,
                "category": self.category, "why": self.why, **self.props}


@dataclass(frozen=True)
class Result:
    """A bounded result set that states its own truncation.

    ``total`` is the number of matches found, ``items`` the number returned. When they differ,
    ``truncated`` is True and ``note`` says how to see the rest. Silent truncation is worse than a
    large result: a caller -- human or model -- reads a short list as "that is all there is".
    """

    items: list[dict[str, Any]]
    total: int
    truncated: bool = False
    note: str = ""

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"items": self.items, "total": self.total,
                               "returned": len(self.items), "truncated": self.truncated}
        if self.note:
            out["note"] = self.note
        return out


def _flatten(value: Any) -> str:
    """Every string inside an authored property, whatever shape it was authored in.

    ``interpretation`` and ``applications`` are a list on 64 nodes and a plain string on 7; the slot
    dicts nest a description under each name. Searching has to see through both without caring.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{k} {_flatten(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def _is_bounded(rng: Sequence[Any] | None) -> bool | None:
    """Whether an output's range has two finite endpoints. ``None`` when it declares no range.

    Unbounded is written ``[-inf, inf]``, not ``null`` -- so "does it have a range" is True for
    unbounded outputs and is the wrong test. The endpoints have to be examined.
    """
    if not rng or len(rng) != 2:
        return None
    try:
        lo, hi = float(rng[0]), float(rng[1])
    except (TypeError, ValueError):
        return None
    return not (lo in (float("-inf"), float("inf")) or hi in (float("-inf"), float("inf")))


def _cap(rows: list[dict[str, Any]], limit: int | None, what: str) -> Result:
    total = len(rows)
    if limit is None or total <= limit:
        return Result(rows, total)
    return Result(rows[:limit], total, True,
                  f"showing {limit} of {total} {what}; raise limit or narrow the query")


class KnowledgeGraph:
    """An in-memory view of the signal/indicator knowledge space.

    Load once and reuse -- the constructor builds the adjacency indexes. The graph is a few hundred
    nodes, so everything here is exact traversal rather than approximate retrieval; no ranking model
    is involved and results are deterministic.
    """

    def __init__(self, atoms: Iterable[dict[str, Any]], relations: Iterable[dict[str, Any]],
                 *, source: str | None = None, version: str | None = None):
        self.source = source
        self.version = version
        self.nodes: dict[str, Node] = {}
        for a in atoms:
            self.nodes[a["id"]] = Node(
                id=a["id"], name=a.get("title") or a["id"], primitive=a.get("kind") or "Atom",
                summary=a.get("summary") or "", status=a.get("status"),
                epistemic=a.get("epistemic"), props=dict(a.get("props") or {}))

        self.edges: list[Edge] = []
        self._out: dict[str, list[Edge]] = {}
        self._in: dict[str, list[Edge]] = {}
        for r in relations:
            src, dst = r.get("from_id"), r.get("to_id")
            if src not in self.nodes or dst not in self.nodes:
                continue                       # an edge to a node outside the set is not a fact here
            props = {k: v for k, v in r.items()
                     if k not in ("from", "to", "rel", "from_id", "to_id", "why")}
            e = Edge(src=src, dst=dst, relation=r["rel"], why=r.get("why") or "", props=props)
            self.edges.append(e)
            self._out.setdefault(src, []).append(e)
            self._in.setdefault(dst, []).append(e)

        # One lowercased haystack per node per tier, built once. The graph is a few hundred nodes,
        # so this is cheaper than re-flattening the nested slot dicts on every search.
        self._haystacks: dict[str, tuple[str, ...]] = {}
        for n in self.nodes.values():
            self._haystacks[n.id] = haystacks(
                {"name": n.name, "id": n.id, "summary": n.summary, **n.props})

    # --- loading ---------------------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> "KnowledgeGraph":
        """Load the graph. Resolution order: explicit path, ``MANGROVE_KB_ONTOLOGY``, packaged, repo."""
        candidates = [Path(path)] if path else [
            *( [Path(os.environ[_ENV_VAR])] if os.environ.get(_ENV_VAR) else [] ),
            _PACKAGED, _IN_REPO,
        ]
        for c in candidates:
            if c.is_file():
                data = json.loads(c.read_text())
                return cls(data.get("atoms", []), data.get("relations", []),
                           source=str(c), version=data.get("version") or data.get("generated"))
        raise GraphError(
            "could not locate the ontology graph. Tried: "
            + ", ".join(str(c) for c in candidates)
            + f". Set {_ENV_VAR} to a signal-indicator-ontology.json.")

    # --- orientation -----------------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """What this graph contains -- **call this first**.

        Returns the counts, the full relation and role vocabulary, the primitives in use, and the
        roots. Every value that another method will accept as a filter appears here, so a caller can
        enumerate legal arguments instead of guessing at names.
        """
        return {
            "source": self.source,
            "version": self.version,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "primitives": dict(Counter(n.primitive for n in self.nodes.values()).most_common()),
            "relations": dict(Counter(e.relation for e in self.edges).most_common()),
            "categories": {c: sum(1 for e in self.edges if e.category == c) for c in CATEGORIES},
            "roles": sorted(self.roles()),
            "classes": sorted(self.classes()),
            "statuses": sorted(self.statuses()),
            "input_columns": sorted(self.input_columns()),
            "units": sorted(self.units()),
            "roots": sorted(n for n in self.nodes if not self._out.get(n)),
            "mappings": {r: {k: v for k, v in spec.items() if k in ("exact", "close")}
                         for r, spec in RELATIONS.items()},
        }

    def roles(self) -> set[str]:
        """Every role actually borne by something. Enumerable so ``find(role=...)`` cannot miss."""
        return {e.dst for e in self.edges if e.relation == ROLE_RELATION}

    def classes(self) -> set[str]:
        """The character classes -- the vocabulary ``find(kind=...)`` is *for*.

        The six divisions of technical analysis: what a computation measures. An indicator is
        ``instance-of`` one; a signal is ``about`` one.

        This deliberately does **not** return every node the backbone points at. That set also holds
        ``concept:indicator`` (71 results), ``concept:signal`` (218), ``concept:technical-analysis``
        (299 of 498 nodes) and ``property:role`` (2 -- the role values), and advertising those as the
        class vocabulary invites a filter that looks like a query and returns almost everything.
        They remain legal ``kind=`` arguments, and :meth:`find` documents them; they are just not
        classes.
        """
        return {e.src for e in self.edges
                if e.relation == "kind-of" and e.dst == CLASS_AXIS_ROOT}

    def statuses(self) -> set[str]:
        """Every status a node actually carries. Enumerable so ``find(status=...)`` cannot miss."""
        return {n.status for n in self.nodes.values() if n.status}

    def input_columns(self) -> set[str]:
        """Every input column something declares -- the vocabulary ``find(requires=...)`` accepts."""
        return {c for n in self.nodes.values() for c in (n.props.get("inputs") or {})}

    def units(self) -> set[str]:
        """Every unit an output is measured in -- the vocabulary ``outputs(units=...)`` accepts."""
        return {str(o.get("units")) for n in self.nodes.values()
                for o in (n.props.get("outputs") or {}).values() if o.get("units")}

    def schema(self) -> list[dict[str, str]]:
        """Which (primitive, relation, primitive) triples actually occur.

        The machine-readable answer to "what can I ask?", so a caller plans a traversal against
        shapes that exist rather than discovering emptiness one query at a time (Luo et al.,
        *Reasoning on Graphs*, ICLR 2024). Modelled on TRAPI's ``meta_knowledge_graph``.
        """
        seen = {(self.nodes[e.src].primitive, e.relation, self.nodes[e.dst].primitive)
                for e in self.edges}
        return [{"subject": s, "relation": r, "object": o} for s, r, o in sorted(seen)]

    # --- resolution ------------------------------------------------------------------------------

    def resolve(self, ref: str) -> str:
        """Resolve an id, a name, or an unambiguous fragment to an exact node id."""
        if ref in self.nodes:
            return ref
        low = ref.lower().strip()
        for n in self.nodes.values():
            if n.name.lower() == low:
                return n.id
        hits = [n.id for n in self.nodes.values()
                if low in n.id.lower() or low in n.name.lower()]
        if len(hits) == 1:
            return hits[0]
        raise NodeNotFound(ref, sorted(hits)[:5])

    def get(self, ref: str) -> dict[str, Any]:
        """One node in full: every authored property, plus its relation counts by direction."""
        nid = self.resolve(ref)
        n = self.nodes[nid]
        return {**n.full(),
                "edges": {"out": dict(Counter(e.relation for e in self._out.get(nid, []))),
                          "in": dict(Counter(e.relation for e in self._in.get(nid, [])))}}

    # --- the two axes ----------------------------------------------------------------------------

    def ancestors(self, ref: str) -> list[str]:
        """Classes this node belongs to, transitively, over the **rigid backbone only**.

        Follows ``instance-of`` then ``kind-of`` upward. Roles are excluded by construction: a role
        is not a supertype, so it can never appear here.
        """
        nid = self.resolve(ref)
        out: list[str] = []
        seen = {nid}
        q = deque([nid])
        while q:
            cur = q.popleft()
            for e in self._out.get(cur, []):
                if e.relation in BACKBONE and e.dst not in seen:
                    seen.add(e.dst)
                    out.append(e.dst)
                    q.append(e.dst)
        return out

    def descendants(self, ref: str) -> list[str]:
        """Everything under this class, transitively, over the rigid backbone only."""
        nid = self.resolve(ref)
        out: list[str] = []
        seen = {nid}
        q = deque([nid])
        while q:
            cur = q.popleft()
            for e in self._in.get(cur, []):
                if e.relation in BACKBONE and e.src not in seen:
                    seen.add(e.src)
                    out.append(e.src)
                    q.append(e.src)
        return out

    def under(self, ref: str) -> set[str]:
        """Everything beneath this node, whatever primitive it is -- the containment question.

        :meth:`descendants` answers *what is a kind of this*, over the rigid backbone. That is the
        wrong question for "give me everything from market foundations": an order type is not a
        KIND of market foundations, it is PART of it, and `part-of` is not on the backbone -- so the
        walk stopped at the first composition edge and returned almost nothing.

        This follows every transitive structural relation (`part-of` alongside `kind-of`, both
        declared transitive in :data:`RELATIONS`) plus `instance-of` for the leaf members, and then
        the same one-hop `about` projection :meth:`in_class` uses, so a computation concerned with
        something in scope comes along with it.

        The point is that it is primitive-blind. A Fact, a Concept, an indicator and a chapter
        formula are all reached by this one call, because the graph already records which chapter
        each belongs to -- as edges. Nothing needs a `reference_chapter` filter to be found.
        """
        nid = self.resolve(ref)
        down = {r for r, spec in RELATIONS.items() if spec.get("transitive")} | {"instance-of"}
        seen = {nid}
        q = deque([nid])
        while q:
            cur = q.popleft()
            for e in self._in.get(cur, []):
                if e.relation in down and e.src not in seen:
                    seen.add(e.src)
                    q.append(e.src)
        via_about = {e.src for e in self.edges if e.relation == "about" and e.dst in seen}
        return (seen | via_about) - {nid}

    def bearers(self, role: str) -> list[str]:
        """Nodes that bear this role. **One hop, never transitive** -- roles are not inherited."""
        rid = self.resolve(role)
        return [e.src for e in self._in.get(rid, []) if e.relation == ROLE_RELATION]

    # --- search ----------------------------------------------------------------------------------

    def in_class(self, cls: str) -> set[str]:
        """Everything in a class -- **including what derives its class through what it uses**.

        A class reaches its members two ways, and the two say different things:

        * an indicator is ``instance-of`` its class -- it *measures* that character;
        * a signal is ``about`` its class -- it is *concerned with* that character, because of the
          indicator it reads. ``adosc_bearish --about--> momentum``.

        The second is deliberately not ``instance-of``. ``momentum`` is defined as measuring rate of
        change; a signal emits a boolean and measures nothing, so it is not an instance of the class
        and the graph does not say it is. It is still returned here, because "everything to do with
        momentum" is the question this method exists to answer -- but the edge naming the two claims
        keeps them distinguishable, which is what lets :meth:`path` explain a signal's class instead
        of merely asserting it.

        The ``about`` edges are a projection of ``uses`` plus the class table, emitted by the builder
        in the same pass and checked there against the ``uses`` edge behind each one.
        All 218 signals resolve this way, every one reading a classified indicator. (The node
        property ``source_module`` carries the same string, but it is provenance, not the assertion
        -- the graph is the source of truth.)

        Roles are excluded: membership runs over the backbone and ``about``, never over
        ``has-role``, so nothing is ever classified by the part it plays.
        """
        cid = self.resolve(cls)
        direct = set(self.descendants(cid)) | {cid}
        via_about = {e.src for e in self.edges if e.relation == "about" and e.dst in direct}
        return (direct | via_about) - {cid}

    def find(self, query: str = "", *, kind: str | None = None, role: str | None = None,
             primitive: str | None = None, status: str | None = None,
             requires: str | None = None, under: str | None = None,
             limit: int | None = DEFAULT_FIND_LIMIT) -> Result:
        """Search by text, and/or filter by class, role, status and required input.

        ``kind`` and ``role`` are separate parameters on purpose, and they intersect. ``kind`` is
        resolved by :meth:`in_class`, so it reaches indicators by their own ``instance-of`` edge and
        signals through the indicator they ``use``. ``role`` is matched on the direct ``has-role``
        edge and is **never** inherited or derived -- a role is what something is being used as, and
        must never be reachable as though it were a type::

            kg.find(kind="momentum", role="trigger")   # momentum-class signals used as triggers
            kg.find(kind="oscillator")                 # everything in the oscillator class
            kg.find(role="filter")                     # signals playing the filter part

        ``under`` scopes to everything beneath a node by containment -- and it is primitive-blind,
        so one call reaches the Concepts, the Facts, the advice and the formulas of a subject
        alike::

            kg.find(under="market foundations")            # the whole subject, every kind of node
            kg.find(under="market foundations", primitive="Procedure")   # just its computations
            kg.find("spread", under="market foundations")  # text search, scoped to the subject

        ``status`` and ``requires`` are flat node predicates with small enumerable vocabularies --
        both are listed by :meth:`stats`, so neither can be guessed wrong::

            kg.find(status="deprecated")               # everything superseded, in one call
            kg.find(requires="volume", role="trigger") # triggers that need a volume column

        The text search reads every authored field, ranked by where it hit -- see
        :data:`SEARCH_TIERS`. A name match outranks an abbreviation, which outranks the summary,
        which outranks a mention buried in a formula or an output description. So widening the
        search does not push the obvious answer down the page; it only stops the non-obvious one
        from being invisible.
        """
        pool: set[str] | None = None
        if under is not None:
            pool = self.under(under)
        if kind is not None:
            got = self.in_class(kind)
            pool = got if pool is None else (pool & got)
        if role is not None:
            rid = self.resolve(role)
            borne = set(self.bearers(rid))
            pool = borne if pool is None else (pool & borne)
        if status is not None and status not in (known := self.statuses()):
            raise GraphError(f"unknown status {status!r}; known: {', '.join(sorted(known))}")
        if requires is not None and requires not in (cols := self.input_columns()):
            raise GraphError(f"nothing declares the input {requires!r}; "
                             f"declared: {', '.join(sorted(cols))}")

        terms = query_terms(query)
        if query.strip() and not terms:
            raise GraphError(
                f"a query needs {MIN_QUERY} characters to mean anything; {query.strip()!r} would "
                "match most of the graph. Use find(kind=...), find(under=...) or resolve() instead.")
        rows: list[tuple[int, str, dict[str, Any]]] = []
        for n in self.nodes.values():
            if pool is not None and n.id not in pool:
                continue
            if primitive and n.primitive != primitive:
                continue
            if status is not None and n.status != status:
                continue
            if requires is not None and requires not in (n.props.get("inputs") or {}):
                continue
            rank = 0
            if terms:
                # WHERE a query matched decides rank. Sorting purely by id buried the four signals
                # actually NAMED "divergence" beneath five that merely mention it in prose -- and a
                # caller reading the first few results concludes the thing does not exist. The tier
                # index IS the rank; id breaks ties so results stay deterministic, which a public
                # API needs.
                hit = rank_of(self._haystacks[n.id], terms)
                if hit is None:
                    continue
                rank = hit
            rows.append((rank, n.id, n.brief()))
        rows.sort(key=lambda r: (r[0], r[1]))
        return _cap([r[2] for r in rows], limit, "matches")

    def outputs(self, name: str = "", *, units: str | None = None, bounded: bool | None = None,
                kind: str | None = None, limit: int | None = DEFAULT_LIMIT) -> Result:
        """The output index: every value the library produces, filterable by what it *is*.

        The other operations answer questions about a node's place in the graph. This one answers
        questions about the values themselves -- *what produces an output called* ``histogram``,
        *which computations emit a percentage*, *which are bounded and therefore comparable on one
        axis*. Those were previously reachable only by fetching all 498 nodes and looping, which is
        why they were not being asked.

        A row is an **output**, not a node: an indicator with three outputs contributes three rows,
        because "is this comparable with that" is a question about one output and not about its
        producer. Each row names its producer so a caller can go on to :meth:`get` or
        :meth:`neighbors`.

        ``bounded=True`` selects outputs with two finite endpoints. Unbounded is written
        ``[-inf, inf]`` rather than ``null``, so the naive "has a range" test passes for unbounded
        outputs and gives the wrong answer -- this filter examines the endpoints instead::

            kg.outputs(units="percent")                      # everything on a 0-100 scale
            kg.outputs(bounded=True, kind="oscillator")      # comparable oscillator outputs
            kg.outputs("histogram")                          # who produces one, and what it means
        """
        if units is not None and units not in (known := self.units()):
            raise GraphError(f"unknown units {units!r}; known: {', '.join(sorted(known))}")
        pool = self.in_class(kind) if kind is not None else None

        needle = name.lower().strip()
        rows: list[dict[str, Any]] = []
        for n in self.nodes.values():
            if pool is not None and n.id not in pool:
                continue
            for out_name, spec in (n.props.get("outputs") or {}).items():
                if needle and needle not in out_name.lower():
                    continue
                if units is not None and spec.get("units") != units:
                    continue
                is_bounded = _is_bounded(spec.get("range"))
                if bounded is not None and is_bounded is not bounded:
                    continue
                rows.append({"output": out_name, "id": n.id, "name": n.name,
                             "type": spec.get("type"), "units": spec.get("units"),
                             "range": spec.get("range"), "bounded": is_bounded,
                             "canonical_name": spec.get("canonical_name"),
                             "description": spec.get("description")})
        rows.sort(key=lambda r: (r["id"], r["output"]))
        return _cap(rows, limit, "outputs")

    # --- traversal -------------------------------------------------------------------------------

    def neighbors(self, ref: str, *, direction: str = "both", relation: str | None = None,
                  category: str | None = None, limit: int | None = DEFAULT_LIMIT) -> Result:
        """One hop. ``direction`` is ``"in"``, ``"out"`` or ``"both"``.

        Filter by an exact ``relation`` or by a whole ``category`` -- the latter lets a caller follow
        every structural edge without naming each one, which is what makes a poly-hierarchy
        navigable. ``direction`` follows the ``mode="in"/"out"/"all"`` convention of igraph and
        NetworkX rather than a boolean, because a boolean is unguessable.
        """
        nid = self.resolve(ref)
        if direction not in ("in", "out", "both"):
            raise GraphError(f"direction must be 'in', 'out' or 'both', not {direction!r}")
        if relation and relation not in RELATIONS:
            raise GraphError(f"unknown relation {relation!r}; known: {', '.join(RELATIONS)}")
        if category and category not in CATEGORIES:
            raise GraphError(f"unknown category {category!r}; known: {', '.join(CATEGORIES)}")

        rows: list[dict[str, Any]] = []
        for e, out in [(e, True) for e in self._out.get(nid, [])] + \
                      [(e, False) for e in self._in.get(nid, [])]:
            if direction == "out" and not out:
                continue
            if direction == "in" and out:
                continue
            if relation and e.relation != relation:
                continue
            if category and e.category != category:
                continue
            other = e.dst if out else e.src
            rows.append({**self.nodes[other].brief(),
                         "relation": e.relation, "category": e.category,
                         "direction": "out" if out else "in", "why": e.why, **e.props})
        rows.sort(key=lambda r: (r["relation"], r["id"]))
        return _cap(rows, limit, "neighbours")

    def subgraph(self, ref: str, *, radius: int = 1, relations: Sequence[str] | None = None,
                 max_nodes: int = DEFAULT_SUBGRAPH_NODES) -> dict[str, Any]:
        """The neighbourhood around a node, as an induced subgraph.

        **Closure guarantee**: the result contains every node within ``radius`` hops of ``ref`` over
        the permitted relations, treating edges as undirected, *and* every edge of the graph whose
        endpoints are both in that set. It is not a truncated walk -- a returned node's neighbours
        within the radius are all present, so a caller can reason over the fragment without going
        back for more. Stating the guarantee, rather than an arbitrary depth cut, is what makes an
        extracted module usable (Cuenca Grau et al., JAIR 2008).

        ``radius`` -- not "depth" -- matches ``networkx.ego_graph`` and igraph's ``neighborhood``.
        If the frontier exceeds ``max_nodes`` the expansion stops and says so.
        """
        nid = self.resolve(ref)
        if radius < 0:
            raise GraphError("radius must be >= 0")
        allowed = set(relations) if relations else None
        if allowed and (bad := allowed - set(RELATIONS)):
            raise GraphError(f"unknown relation(s): {', '.join(sorted(bad))}")

        seen = {nid}
        frontier = [nid]
        truncated = False
        for _ in range(radius):
            nxt: list[str] = []
            for cur in frontier:
                for e in self._out.get(cur, []) + self._in.get(cur, []):
                    if allowed and e.relation not in allowed:
                        continue
                    other = e.dst if e.src == cur else e.src
                    if other in seen:
                        continue
                    if len(seen) >= max_nodes:
                        truncated = True
                        break
                    seen.add(other)
                    nxt.append(other)
                if truncated:
                    break
            if truncated:
                break
            frontier = nxt
        induced = [e for e in self.edges if e.src in seen and e.dst in seen
                   and (not allowed or e.relation in allowed)]
        return {
            "center": nid,
            "radius": radius,
            "nodes": [self.nodes[i].brief() for i in sorted(seen)],
            "edges": [e.as_dict() for e in induced],
            "truncated": truncated,
            "closure": "all nodes within radius over the permitted relations, plus every edge "
                       "between them",
            **({"note": f"stopped at max_nodes={max_nodes}; raise it or reduce radius"}
               if truncated else {}),
        }

    def path(self, from_ref: str, to_ref: str, *, max_depth: int = 6,
             relations: Sequence[str] | None = None) -> list[dict[str, Any]] | None:
        """The shortest connecting path, as alternating nodes and the relation traversed.

        Edges are followed in either direction: "how are these two related" is not a question about
        edge orientation. Returns ``None`` when nothing connects them within ``max_depth`` -- which
        is a real answer about this graph, not a failure.

        Each hop carries the edge's own ``why``. Every relation in this graph records why it holds
        -- the merge refuses an edge without one -- and a route that named the relations but dropped
        the reasons was the one call whose whole job is explanation discarding the explanation.

        **Shortest is rarely the explanatory route.** It returns ONE path and says nothing about the
        others, so adding an edge silently changes the answer -- which is exactly what happened when
        signals gained a direct ``about`` edge to their class and this method stopped showing the
        ``uses`` derivation behind it. Constrain with ``relations=`` to ask for an explanation in
        particular terms, or use :meth:`all_paths` to see every route rather than one.
        """
        a, b = self.resolve(from_ref), self.resolve(to_ref)
        if a == b:
            return [{"node": self.nodes[a].brief()}]
        allowed = set(relations) if relations else None
        prev: dict[str, tuple[str, Edge]] = {}
        seen = {a}
        q = deque([(a, 0)])
        while q:
            cur, d = q.popleft()
            if d >= max_depth:
                continue
            for e in self._out.get(cur, []) + self._in.get(cur, []):
                if allowed and e.relation not in allowed:
                    continue
                other = e.dst if e.src == cur else e.src
                if other in seen:
                    continue
                seen.add(other)
                prev[other] = (cur, e)
                if other == b:
                    q.clear()
                    break
                q.append((other, d + 1))
        if b not in prev:
            return None
        chain: list[dict[str, Any]] = []
        cur = b
        while cur != a:
            parent, e = prev[cur]
            chain.append({"node": self.nodes[cur].brief(),
                          "via": {"relation": e.relation, "category": e.category,
                                  "why": e.why, "from": e.src, "to": e.dst}})
            cur = parent
        chain.append({"node": self.nodes[a].brief()})
        return list(reversed(chain))

    def all_paths(self, from_ref: str, to_ref: str, *, max_depth: int = 4,
                  relations: Sequence[str] | None = None,
                  sibling_hops: bool = False,
                  limit: int | None = DEFAULT_LIMIT,
                  max_steps: int = 200_000) -> Result:
        """Every simple route between two nodes, shortest first -- not one arbitrary one.

        ``sibling_hops`` controls the routes that pass *through a shared parent* -- entering and
        leaving a node on two edges that both point AT it::

            adosc_bearish --instance-of--> Signal <--instance-of-- adosc_bullish --about--> momentum

        That says "they are both signals", which is true and explains nothing. Excluded by default,
        because on this graph it is not a minority of the answers: between ``adosc_bearish`` and
        ``momentum`` there are 2 real routes and, at ``max_depth=5``, 9,638 of 9,785 paths are these
        detours through ``concept:signal`` (degree 218). Pass ``sibling_hops=True`` when the shared
        parent IS the answer -- *"how are these two related?" "they both read RSI"* is the same shape
        and genuinely informative.

        Three bounds, kept separate because they mean different things and a single "cap" hides
        which one you hit:

        ``max_depth``  how LONG a path may be. Default 4, not :meth:`path`'s 6: the count of simple
                       paths grows combinatorially with length, and past four hops the extra routes
                       are almost all detours through a hub rather than explanations.
        ``limit``      how MANY paths come back. The house convention -- ``total`` and ``truncated``
                       report the rest.
        ``max_steps``  how HARD to search before giving up. This graph has hubs of degree 218
                       (``concept:signal`` touches every signal), and enumerating simple paths
                       across one is combinatorial, so an unbounded search does not return.

        **The two truncated states are not the same claim, and the note says which one you got.**
        If the search finished, ``total`` is exact and the note reads *"showing 10 of 47"*. If
        ``max_steps`` tripped, the search did NOT finish, ``total`` is only what was found so far,
        and the note says so. Reporting "10 of 47" after an incomplete search would be the precise
        failure :class:`Result` exists to prevent -- a number that reads as complete and is not.
        """
        a, b = self.resolve(from_ref), self.resolve(to_ref)
        if a == b:
            return Result([[{"node": self.nodes[a].brief()}]], 1)
        allowed = set(relations) if relations else None

        found: list[list[dict[str, Any]]] = []
        steps = 0
        exhausted = True

        def walk(cur: str, depth: int, on_path: set[str], acc: list[dict[str, Any]],
                 arrived_on: Edge | None = None) -> None:
            nonlocal steps, exhausted
            if not exhausted or depth >= max_depth:
                return
            for e in self._out.get(cur, []) + self._in.get(cur, []):
                if not exhausted:
                    return
                if allowed and e.relation not in allowed:
                    continue
                other = e.dst if e.src == cur else e.src
                if other in on_path:
                    continue
                # Both edges point at `cur`: we came up an arrow and are about to go back down a
                # different one. That is a sibling, not a connection. See the docstring.
                if (not sibling_hops and arrived_on is not None
                        and arrived_on.dst == cur and e.dst == cur):
                    continue
                steps += 1
                if steps > max_steps:
                    exhausted = False
                    return
                step = {"node": self.nodes[other].brief(),
                        "via": {"relation": e.relation, "category": e.category,
                                "why": e.why, "from": e.src, "to": e.dst}}
                if other == b:
                    found.append(acc + [step])
                    continue          # a simple path ends at the target; do not walk through it
                walk(other, depth + 1, on_path | {other}, acc + [step], e)

        walk(a, 0, {a}, [{"node": self.nodes[a].brief()}])
        found.sort(key=len)           # shortest first: the explanation is usually the short one

        #: Both incomplete notes carry this verbatim, so a caller can test for the state rather than
        #: parse two different sentences. An exhausted search never contains it.
        incomplete = (f"the search stopped after {max_steps} steps, so there may be more; "
                      f"lower max_depth or constrain relations= to search a smaller space")
        total = len(found)
        if limit is None or total <= limit:
            return Result(found, total, not exhausted,
                          "" if exhausted else f"{total} paths found, but {incomplete}")
        note = (f"showing {limit} of {total} paths; raise limit or narrow the query" if exhausted
                else f"showing {limit} of {total} paths found so far -- {incomplete}")
        return Result(found[:limit], total, True, note)
