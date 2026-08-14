"""One retrieval surface over both halves of the graph.

The code-derived half (indicators, signals) and the doc-derived half (concepts, chapter formulas,
Facts, Judgments) must be reachable by the same calls. When they are not, a caller has to know which
half a thing lives in before it can ask for it -- which is the thing a graph is supposed to remove.

The specific failure these guard: `descendants()` walks the rigid backbone only, so a chain that
passes through a `part-of` edge stopped dead. "Everything from market foundations" returned almost
nothing, because an order type is PART of the subject rather than a KIND of it.
"""
from __future__ import annotations

import pytest

from mangrove_kb.graph import RELATIONS, KnowledgeGraph

SUBJECT = "concept:market-foundations"


@pytest.fixture(scope="module")
def kg() -> KnowledgeGraph:
    return KnowledgeGraph.load()


def test_containment_crosses_part_of(kg):
    """The chain is `order type --part-of--> subject` with the members `kind-of` the order type."""
    under = kg.under(SUBJECT)
    assert "concept:order-type" in under, "a direct part-of child is missing"
    assert "concept:market-order" in under, \
        "a grandchild reached through part-of then kind-of is missing -- the walk stopped at part-of"
    assert SUBJECT not in under, "a node is not under itself"

    backbone_only = set(kg.descendants(SUBJECT))
    assert under > backbone_only, \
        "containment must reach strictly more than classification, or it adds nothing"


def test_every_primitive_is_reachable_by_the_same_call(kg):
    """Concept, Procedure, Fact and Judgment all come back from one query."""
    got = {kg.get(i)["primitive"] for i in kg.under(SUBJECT)}
    assert {"Concept", "Procedure", "Fact", "Judgment"} <= got, got


def test_find_scopes_by_containment_and_intersects(kg):
    whole = {r["id"] for r in kg.find(under=SUBJECT, limit=None)}
    assert whole == kg.under(SUBJECT)

    procs = {r["id"] for r in kg.find(under=SUBJECT, primitive="Procedure", limit=None)}
    assert procs and procs < whole, "primitive= must narrow the scope, not replace it"

    scoped = {r["id"] for r in kg.find("spread", under=SUBJECT, limit=None)}
    everywhere = {r["id"] for r in kg.find("spread", limit=None)}
    assert scoped and scoped <= everywhere, "a scoped text search must be a subset of the open one"


def test_containment_is_derived_from_edges_not_from_a_property(kg):
    """`reference_chapter` is provenance, never the retrieval mechanism.

    Every node under a subject must be reachable by walking edges alone. If containment silently
    depended on the property, a node whose edges were wrong would still look correctly placed.
    """
    down = {r for r, spec in RELATIONS.items() if spec.get("transitive")} | {"instance-of", "about"}
    reached = kg.under(SUBJECT)
    for nid in reached:
        assert any(e.relation in down for e in kg.edges if e.src == nid), \
            f"{nid} is in scope but carries no containment edge -- it was matched some other way"


def test_a_path_explains_itself_at_every_hop(kg):
    """Every edge records why it holds; a route that drops it explains nothing."""
    hops = kg.path("property:quoted-spread", "object:mangrove-knowledge-space")
    assert hops and len(hops) > 2
    for step in hops[1:]:
        via = step["via"]
        assert via["relation"] in RELATIONS
        assert via.get("why", "").strip(), f"hop into {step['node']['id']} carries no reason"


def test_all_paths_carries_the_same_reasons(kg):
    routes = kg.all_paths("property:quoted-spread", SUBJECT, limit=None).items
    assert routes, "expected at least one route"
    for route in routes:
        for step in route[1:]:
            assert step["via"].get("why", "").strip(), step
