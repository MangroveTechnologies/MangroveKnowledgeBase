"""Query the signal/indicator knowledge graph.

The knowledge space is a curated graph over the library's own indicators and signals: what each
computation *is*, what it consumes and produces, which signals read which of its outputs, and what
part each signal plays in a strategy. It is generated from the source, so it is exact rather than
extracted -- there is no text-mining noise to rank around.

**Two classification axes, and they are not interchangeable.** Every signal is simultaneously an
``instance-of`` a type and a bearer of a ``has-role`` role (216 of 301 nodes carry both). These are
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

import json
import os
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
    "uses":        {"category": "associative", "transitive": False, "close": "prov:used"},
    "supersedes":  {"category": "meta",        "transitive": False, "exact": "dcterms:replaces"},
}

#: The rigid backbone: the only relations along which class membership may be inherited.
BACKBONE: tuple[str, ...] = ("instance-of", "kind-of")

#: Anti-rigid. Never closed, never inherited, never returned as a type. See the module docstring.
ROLE_RELATION = "has-role"

CATEGORIES: tuple[str, ...] = ("structural", "descriptive", "associative", "meta")

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
            "kinds": sorted(self.kinds()),
            "roots": sorted(n for n in self.nodes if not self._out.get(n)),
            "mappings": {r: {k: v for k, v in spec.items() if k in ("exact", "close")}
                         for r, spec in RELATIONS.items()},
        }

    def roles(self) -> set[str]:
        """Every role actually borne by something. Enumerable so ``find(role=...)`` cannot miss."""
        return {e.dst for e in self.edges if e.relation == ROLE_RELATION}

    def kinds(self) -> set[str]:
        """Every class something is an instance or subclass of."""
        return {e.dst for e in self.edges if e.relation in BACKBONE}

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

    def bearers(self, role: str) -> list[str]:
        """Nodes that bear this role. **One hop, never transitive** -- roles are not inherited."""
        rid = self.resolve(role)
        return [e.src for e in self._in.get(rid, []) if e.relation == ROLE_RELATION]

    # --- search ----------------------------------------------------------------------------------

    def in_class(self, cls: str) -> set[str]:
        """Everything in a class -- **including what derives its class through what it uses**.

        A class reaches its members two ways, and both are edges in the graph:

        * directly, over the rigid backbone -- an indicator ``instance-of`` its class;
        * through the computation it is built on -- a signal ``uses`` an indicator that is
          ``instance-of`` the class. ``adosc_bearish --uses--> ADOSC --instance-of--> momentum``.

        The second is not a workaround for a missing edge; it is how a signal's class is *stated* in
        this model. A signal does not declare a class of its own -- it inherits the character of
        the computation it reads, and the graph already says so. All 216 signals resolve this way. (The node property ``source_module`` happens to carry the same string, but it is
        provenance, not the assertion -- the graph is the source of truth.)

        Roles are still excluded here: derivation runs over ``uses`` and the backbone, never over
        ``has-role``, so nothing is ever classified by the part it plays.
        """
        cid = self.resolve(cls)
        direct = set(self.descendants(cid)) | {cid}
        via_uses = {e.src for e in self.edges if e.relation == "uses" and e.dst in direct}
        return (direct | via_uses) - {cid}

    def find(self, query: str = "", *, kind: str | None = None, role: str | None = None,
             primitive: str | None = None, limit: int | None = DEFAULT_FIND_LIMIT) -> Result:
        """Search by text, and/or filter by class and by role.

        ``kind`` and ``role`` are separate parameters on purpose, and they intersect. ``kind`` is
        resolved by :meth:`in_class`, so it reaches indicators by their own ``instance-of`` edge and
        signals through the indicator they ``use``. ``role`` is matched on the direct ``has-role``
        edge and is **never** inherited or derived -- a role is what something is being used as, and
        must never be reachable as though it were a type::

            kg.find(kind="momentum", role="trigger")   # momentum-class signals used as triggers
            kg.find(kind="oscillator")                 # everything in the oscillator class
            kg.find(role="filter")                     # signals playing the filter part
        """
        pool: set[str] | None = None
        if kind is not None:
            pool = self.in_class(kind)
        if role is not None:
            rid = self.resolve(role)
            borne = set(self.bearers(rid))
            pool = borne if pool is None else (pool & borne)

        q = query.lower().strip()
        rows: list[dict[str, Any]] = []
        for n in self.nodes.values():
            if pool is not None and n.id not in pool:
                continue
            if primitive and n.primitive != primitive:
                continue
            if q and not (q in n.id.lower() or q in n.name.lower() or q in n.summary.lower()
                          or q in str(n.props.get("abbreviation", "")).lower()):
                continue
            rows.append(n.brief())
        rows.sort(key=lambda r: r["id"])          # deterministic: a public API must be stable
        return _cap(rows, limit, "matches")

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
                                  "from": e.src, "to": e.dst}})
            cur = parent
        chain.append({"node": self.nodes[a].brief()})
        return list(reversed(chain))
