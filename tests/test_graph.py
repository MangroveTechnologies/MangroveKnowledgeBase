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


def test_class_is_derived_through_uses_not_declared(kg):
    """A signal's class comes from the indicator it uses -- the graph states it, nothing is buried.

    Regression for a real mistake: this was first read as "signals have no class", because they
    carry no DIRECT class edge. They carry it one hop out, via `uses`, and 209 of 216 resolve.
    """
    momentum = kg.in_class("concept:indicator-class-momentum")
    assert any(m.startswith("procedure:signal-") for m in momentum), \
        "signals must reach their class through the indicator they use"
    assert any(m.startswith("procedure:indicator-") for m in momentum), \
        "indicators must reach their class directly"
    for sig in (m for m in momentum if m.startswith("procedure:signal-")):
        used = {n["id"] for n in kg.neighbors(sig, relation="uses", direction="out", limit=None)}
        assert used & set(kg.descendants("concept:indicator-class-momentum"))


def test_both_axes_in_one_call(kg):
    """The obvious question must work: momentum-class signals playing a trigger role."""
    r = kg.find(kind="momentum", role="trigger", limit=None)
    assert r.total > 0, "kind x role must not be empty -- class is derivable for signals"
    triggers = set(kg.bearers("property:role-trigger"))
    momentum = kg.in_class("concept:indicator-class-momentum")
    for row in r:
        assert row["id"] in triggers and row["id"] in momentum


def test_derivation_never_runs_over_roles(kg):
    """Class derivation follows uses + the backbone. A role must never confer class membership."""
    for role in kg.roles():
        bearers = set(kg.bearers(role))
        for cls in kg.stats()["kinds"]:
            if cls.startswith("concept:indicator-class-"):
                members = kg.in_class(cls)
                assert not (members >= bearers), \
                    f"{cls} swallowed every bearer of {role} -- roles are leaking into class"


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


def test_find_ranks_name_matches_above_prose_matches(kg):
    """A caller reads the first few results and stops. Burying the exact match is a wrong answer.

    Regression: `find("divergence")` used to return five indicators that merely mention divergence
    in their summary AHEAD of the four signals actually named for it, because results were sorted by
    id alone.
    """
    rows = kg.find("divergence", limit=None).items
    named = [i for i, r in enumerate(rows) if "divergence" in r["id"].lower()]
    prose = [i for i, r in enumerate(rows) if "divergence" not in r["id"].lower()]
    assert named and prose, "expected both kinds of match for this query"
    assert max(named) < min(prose), "name matches must all rank above prose-only matches"


def test_find_stays_deterministic_within_a_rank(kg):
    a = [r["id"] for r in kg.find("cross", limit=None)]
    assert a == [r["id"] for r in kg.find("cross", limit=None)]
    assert a == sorted(a, key=lambda i: (0 if "cross" in i else 1, i))
