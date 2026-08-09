"""Tests for the knowledge-graph query layer.

These run against the real committed ontology rather than fixtures. A hand-written fixture would
pass while the shipped graph was broken, and the shape of the real graph -- disjoint axis
populations, hubs of degree 200+ -- is exactly what the API has to cope with.
"""
import pytest

from mangrove_kb.graph import (BACKBONE, RELATIONS, ROLE_RELATION, GraphError, KnowledgeGraph,
                               NodeNotFound)


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


# --- loading and orientation ---------------------------------------------------------------------

def test_loads_the_committed_graph(kg):
    s = kg.stats()
    assert s["nodes"] > 250 and s["edges"] > 600
    assert s["source"].endswith("signal-indicator-ontology.json")


def test_stats_enumerates_every_filter_value(kg):
    """Orientation must list what the other calls will accept, or callers guess names."""
    s = kg.stats()
    for role in s["roles"]:
        assert kg.find(role=role, limit=1) is not None
    for kind in s["kinds"]:
        assert kg.find(kind=kind, limit=1) is not None
    assert set(s["relations"]) <= set(RELATIONS), "graph uses a relation the library cannot classify"


def test_single_root(kg):
    assert kg.stats()["roots"] == ["object:mangrove-knowledge-space"]


def test_schema_reports_only_triples_that_occur(kg):
    triples = {(t["subject"], t["relation"], t["object"]) for t in kg.schema()}
    assert ("Procedure", "has-role", "Property") in triples
    assert ("Procedure", "uses", "Procedure") in triples
    for _, rel, _ in triples:
        assert rel in RELATIONS


# --- the load-bearing constraint: roles are not types --------------------------------------------

def test_roles_are_never_inherited(kg):
    """A role is anti-rigid: it must never appear as an ancestor, for any node in the graph.

    This is the constraint the whole two-axis design rests on (Steimann 2000; OntoClean 2002).
    If a role ever leaks into the backbone closure, `find(kind=...)` starts returning things that
    merely *play a part* as though they *were* a type, and the distinction is silently gone.
    """
    roles = kg.roles()
    for nid in kg.nodes:
        assert not (set(kg.ancestors(nid)) & roles), f"{nid} inherited a role as a type"


def test_backbone_closure_is_transitive_but_roles_are_one_hop(kg):
    momentum = kg.descendants("concept:indicator-class-momentum")
    assert momentum, "expected members in the momentum class"
    # every member reaches the class transitively over the backbone
    for m in momentum:
        assert "concept:indicator-class-momentum" in kg.ancestors(m)
    # bearers are exactly the direct has-role sources -- no closure
    direct = {e.src for e in kg.edges
              if e.relation == ROLE_RELATION and e.dst == "property:role-trigger"}
    assert set(kg.bearers("property:role-trigger")) == direct


def test_the_two_axes_sit_on_disjoint_populations(kg):
    """Classes are borne by indicators, roles by signals. Pins the fact that motivates `uses_kind`."""
    assert all(b.startswith("procedure:signal-") for b in kg.bearers("property:role-trigger"))
    assert all(d.startswith("procedure:indicator-")
               for d in kg.descendants("concept:indicator-class-momentum"))
    assert kg.find(kind="concept:indicator-class-momentum",
                   role="property:role-trigger", limit=None).total == 0


def test_uses_kind_joins_the_axes(kg):
    joined = kg.find(role="trigger", uses_kind="momentum", limit=None)
    assert joined.total > 0
    momentum = set(kg.descendants("concept:indicator-class-momentum"))
    triggers = set(kg.bearers("property:role-trigger"))
    for row in joined:
        assert row["id"] in triggers
        used = {n["id"] for n in kg.neighbors(row["id"], relation="uses", direction="out",
                                              limit=None)}
        assert used & momentum, f"{row['id']} does not use a momentum indicator"


# --- bounded results -----------------------------------------------------------------------------

def test_truncation_is_audible_never_silent(kg):
    """A short list must not be mistakable for a complete one."""
    hub = "concept:signal"
    r = kg.neighbors(hub, limit=5)
    assert len(r) == 5 and r.truncated and r.total > 5
    assert "of" in r.note and str(r.total) in r.note
    assert kg.neighbors(hub, limit=None).truncated is False


def test_subgraph_honours_its_closure_guarantee(kg):
    """Every edge between returned nodes is present -- not a truncated walk."""
    sg = kg.subgraph("procedure:indicator-rsi", radius=1)
    ids = {n["id"] for n in sg["nodes"]}
    expected = {(e.src, e.dst, e.relation) for e in kg.edges if e.src in ids and e.dst in ids}
    assert {(e["src"], e["dst"], e["relation"]) for e in sg["edges"]} == expected
    assert sg["truncated"] is False


def test_subgraph_reports_when_it_stops_early(kg):
    sg = kg.subgraph("concept:signal", radius=2, max_nodes=20)
    assert sg["truncated"] is True and "max_nodes" in sg["note"]
    assert len(sg["nodes"]) <= 20


# --- resolution and errors -----------------------------------------------------------------------

def test_resolve_accepts_id_name_and_fragment(kg):
    assert kg.resolve("procedure:indicator-rsi") == "procedure:indicator-rsi"
    assert kg.resolve("RSI") == "procedure:indicator-rsi"


def test_unknown_node_suggests_candidates(kg):
    with pytest.raises(NodeNotFound) as e:
        kg.resolve("cross")
    assert e.value.suggestions, "a miss must offer a next move, not a dead end"


def test_bad_arguments_name_the_legal_values(kg):
    for call in (lambda: kg.neighbors("RSI", direction="sideways"),
                 lambda: kg.neighbors("RSI", relation="invented"),
                 lambda: kg.neighbors("RSI", category="invented")):
        with pytest.raises(GraphError) as e:
            call()
        assert "'" in str(e.value), "the error must name what is legal"


# --- traversal -----------------------------------------------------------------------------------

def test_path_is_undirected_and_reports_the_relation(kg):
    p = kg.path("procedure:signal-rsi-oversold", "concept:indicator-class-oscillator")
    assert p is not None
    assert p[0]["node"]["id"] == "procedure:signal-rsi-oversold"
    assert p[-1]["node"]["id"] == "concept:indicator-class-oscillator"
    assert all("via" in step for step in p[1:])


def test_path_returns_none_rather_than_raising(kg):
    assert kg.path("procedure:indicator-rsi", "procedure:indicator-rsi") is not None
    assert kg.path("procedure:indicator-rsi", "property:role-trigger", max_depth=1) is None


def test_uses_edges_carry_which_output_is_read(kg):
    rows = list(kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in", limit=None))
    assert rows, "expected signals reading RSI"
    assert any(r.get("inputs") for r in rows), "the `uses` edge must record which output is read"


def test_results_are_deterministic(kg):
    assert [r["id"] for r in kg.find("cross", limit=10)] == \
           [r["id"] for r in kg.find("cross", limit=10)]


def test_relation_mappings_distinguish_exact_from_close(kg):
    """`exact` asserts substitutability; `close` does not. Conflating them misleads consumers."""
    assert RELATIONS["has-role"]["exact"] == "RO:0000087"
    assert RELATIONS["part-of"]["exact"] == "BFO:0000050"
    assert "exact" not in RELATIONS["uses"] and RELATIONS["uses"]["close"] == "prov:used"
    assert all(r in RELATIONS for r in BACKBONE)
