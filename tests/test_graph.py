"""Tests for the knowledge-graph query layer.

These run against the real committed ontology rather than fixtures. A hand-written fixture would
pass while the shipped graph was broken, and the shape of the real graph -- disjoint axis
populations, hubs of degree 200+ -- is exactly what the API has to cope with.
"""
import pytest

from mangrove_kb.graph import (BACKBONE, RELATIONS, ROLE_RELATION, SEARCH_TIERS, GraphError,
                               KnowledgeGraph, NodeNotFound, _flatten, _is_bounded)


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
    """Rank first, then id. Ties must not depend on dict iteration order."""
    a = [r["id"] for r in kg.find("cross", limit=None)]
    assert a == [r["id"] for r in kg.find("cross", limit=None)]

    def tier(node_id):
        """Which SEARCH_TIERS band this id matched in -- recomputed independently of find()."""
        source = {"name": kg.nodes[node_id].name, "id": node_id,
                  "summary": kg.nodes[node_id].summary, **kg.nodes[node_id].props}
        for i, fields in enumerate(SEARCH_TIERS):
            if "cross" in " ".join(_flatten(source.get(f)) for f in fields).lower():
                return i
        raise AssertionError(f"{node_id} matched in find() but in no tier")

    assert a == sorted(a, key=lambda i: (tier(i), i))
    assert len(set(map(tier, a))) > 1, "expected this query to hit more than one tier"


# --- attribute queries ---------------------------------------------------------------------------

def test_search_reads_the_authored_detail_not_only_the_headline(kg):
    """The regression that motivated SEARCH_TIERS: a term explained only in prose was invisible.

    `find("mean reversion")` returned nothing while two nodes described exactly that, and
    `find("crossover")` returned 32 of the 62 nodes that mention it. The existence check is the
    search's headline use, so a false negative there is the worst failure it has.
    """
    for term in ("mean reversion", "crossover", "overbought"):
        found = {r["id"] for r in kg.find(term, limit=None)}
        mentioned = {n.id for n in kg.nodes.values()
                     if term in _flatten({"name": n.name, "id": n.id,
                                          "summary": n.summary, **n.props}).lower()}
        assert mentioned, f"expected {term!r} somewhere in the graph"
        assert found == mentioned, f"{term!r}: {len(mentioned - found)} nodes mention it but do not match"


def test_a_name_match_still_outranks_a_detail_match(kg):
    """Widening the corpus must not push the obvious answer below the buried one."""
    rows = kg.find("divergence", limit=None).items
    named = [i for i, r in enumerate(rows) if "divergence" in r["id"].lower()]
    assert named == list(range(len(named))), "name matches must occupy the top of the result"


def test_status_and_requires_are_enumerable_and_enforced(kg):
    s = kg.stats()
    assert set(s["statuses"]) == kg.statuses() and "deprecated" in s["statuses"]
    assert "volume" in s["input_columns"]

    deprecated = {r["id"] for r in kg.find(status="deprecated", limit=None)}
    assert deprecated == {n.id for n in kg.nodes.values() if n.status == "deprecated"}
    assert deprecated, "the graph is expected to carry deprecations"

    vol = {r["id"] for r in kg.find(requires="volume", limit=None)}
    assert vol == {n.id for n in kg.nodes.values() if "volume" in (n.props.get("inputs") or {})}

    # A guessed value must name the vocabulary rather than returning an empty result that reads
    # as "there are none".
    for call in (lambda: kg.find(status="retired"), lambda: kg.find(requires="vwap"),
                 lambda: kg.outputs(units="furlongs")):
        with pytest.raises(GraphError) as e:
            call()
        assert "known" in str(e.value) or "declared" in str(e.value)


def test_outputs_indexes_values_not_nodes(kg):
    """A row is one output. An indicator with three outputs contributes three rows."""
    macd = [r for r in kg.outputs(limit=None) if r["id"] == "procedure:indicator-macd"]
    assert {r["output"] for r in macd} == set(kg.get("procedure:indicator-macd")["outputs"])
    assert len(macd) > 1
    assert all(r["id"] and r["name"] for r in macd), "every row must name its producer"


def test_bounded_examines_the_endpoints_not_the_presence_of_a_range(kg):
    """Unbounded is written [-inf, inf], not null -- so `has a range` is the wrong test."""
    assert _is_bounded([0, 100]) is True
    assert _is_bounded([0, float("inf")]) is False
    assert _is_bounded([float("-inf"), float("inf")]) is False
    assert _is_bounded(None) is None

    bounded = kg.outputs(bounded=True, limit=None)
    assert bounded.total and all(r["bounded"] is True for r in bounded)
    assert all(float("inf") not in map(float, r["range"]) for r in bounded)

    unbounded = kg.outputs(bounded=False, limit=None)
    assert all(r["bounded"] is False for r in unbounded)
    # OBV declares a range and is still unbounded -- the case the naive test gets wrong.
    assert any(r["id"] == "procedure:indicator-obv" for r in unbounded)


def test_outputs_intersects_with_the_type_axis(kg):
    """The query the novelty claim rests on: bounded outputs of a given class."""
    rows = kg.outputs(bounded=True, kind="oscillator", limit=None)
    assert rows.total, "expected bounded oscillator outputs"
    in_class = kg.in_class("oscillator")
    assert all(r["id"] in in_class for r in rows)
    # ...and it is genuinely narrower than the same query without the axis.
    assert rows.total < kg.outputs(bounded=True, limit=None).total


def test_outputs_finds_a_producer_by_output_name(kg):
    """`resolve()` only knows node ids and names; an output name needed a hand scan of every node."""
    rows = kg.outputs("histogram", limit=None)
    assert {r["id"] for r in rows} == {"procedure:indicator-macd"}
    assert all("histogram" in r["output"] for r in rows)
