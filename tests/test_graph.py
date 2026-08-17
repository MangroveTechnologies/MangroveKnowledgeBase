"""Tests for the knowledge-graph query layer.

These run against the real committed ontology rather than fixtures. A hand-written fixture would
pass while the shipped graph was broken, and the shape of the real graph -- disjoint axis
populations, hubs of degree 200+ -- is exactly what the API has to cope with.
"""
import re

import pytest

from mangrove_kb.graph import (BACKBONE, FUNCTION_WORDS, RELATIONS, ROLE_RELATION, SEARCH_TIERS,
                               GraphError, KnowledgeGraph, NodeNotFound, _flatten, _is_bounded)


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
    for cls in s["classes"]:
        assert kg.find(kind=cls, limit=1) is not None
    assert len(s["classes"]) == 7, (
        "classes is the CHARACTER vocabulary -- the divisions of technical analysis. "
        "It once returned every backbone target, which swept in concept:indicator (71 "
        "results), concept:signal (218), concept:technical-analysis (295 of 303) and "
        "property:role (the role values), advertising filters that act as no-ops. Six are "
        "measured by a computation; concept:chart-pattern is knowledge only -- multi-bar "
        "formations need swing points, which nothing in the library produces -- so it is "
        "deliberately memberless rather than missing.")
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
    momentum = kg.descendants("concept:momentum")
    assert momentum, "expected members in the momentum class"
    # every member reaches the class transitively over the backbone
    for m in momentum:
        assert "concept:momentum" in kg.ancestors(m)
    # bearers are exactly the direct has-role sources -- no closure
    direct = {e.src for e in kg.edges
              if e.relation == ROLE_RELATION and e.dst == "property:role-trigger"}
    assert set(kg.bearers("property:role-trigger")) == direct


def test_signals_are_about_their_class_and_indicators_are_instances(kg):
    """The two claims are different and carry different relations.

    An indicator MEASURES its character and is `instance-of` the class. A signal emits a boolean,
    measures nothing, and is `about` the class instead. `in_class` returns both, because "everything
    to do with momentum" is the useful question -- but the edges stay distinguishable, and that is
    what lets `path` explain a signal's class rather than merely assert it.

    Every `about` edge must still have the `uses` edge it was projected from behind it. The builder
    aborts otherwise; this checks the shipped graph, not the build.
    """
    momentum = kg.in_class("concept:momentum")
    signals = {m for m in momentum if m.startswith("procedure:signal-")}
    indicators = {m for m in momentum if m.startswith("procedure:indicator-")}
    assert signals and indicators, "the class must span both layers"

    about = {e.src for e in kg.edges if e.relation == "about" and e.dst == "concept:momentum"}
    assert about == signals, "signals reach the class by `about`, and only signals do"
    for i in indicators:
        assert "concept:momentum" in {e.dst for e in kg.edges
                                      if e.src == i and e.relation == "instance-of"}, \
            f"{i} must be an INSTANCE of the class it measures"

    for sig in signals:
        used = {n["id"] for n in kg.neighbors(sig, relation="uses", direction="out", limit=None)}
        assert used & set(kg.descendants("concept:momentum")), \
            f"{sig} is `about` momentum with no `uses` edge behind it"


def test_both_axes_in_one_call(kg):
    """The obvious question must work: momentum-class signals playing a trigger role."""
    r = kg.find(kind="momentum", role="trigger", limit=None)
    assert r.total > 0, "kind x role must not be empty -- class is derivable for signals"
    triggers = set(kg.bearers("property:role-trigger"))
    momentum = kg.in_class("concept:momentum")
    for row in r:
        assert row["id"] in triggers and row["id"] in momentum


def test_derivation_never_runs_over_roles(kg):
    """Class derivation follows `about` + the backbone. A role must never confer class membership.

    Scoped to the six CHARACTER classes, and they are selected by the edge that makes them one --
    `kind-of technical analysis` -- not by an id prefix. `concept:signal` is also a `concept:` and
    legitimately contains every trigger-bearing signal, so a prefix test here would assert the
    opposite of what it means.
    """
    classes = {n["id"] for n in kg.neighbors("concept:technical-analysis", relation="kind-of",
                                             direction="in", limit=None).items}
    assert len(classes) == 7, f"expected the seven character classes, got {sorted(classes)}"
    for role in kg.roles():
        bearers = set(kg.bearers(role))
        for cls in classes:
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
    p = kg.path("procedure:signal-rsi-oversold", "concept:oscillator")
    assert p is not None
    assert p[0]["node"]["id"] == "procedure:signal-rsi-oversold"
    assert p[-1]["node"]["id"] == "concept:oscillator"
    assert all("via" in step for step in p[1:])


def test_path_returns_none_rather_than_raising(kg):
    assert kg.path("procedure:indicator-rsi", "procedure:indicator-rsi") is not None
    assert kg.path("procedure:indicator-rsi", "property:role-trigger", max_depth=1) is None


def test_all_paths_returns_every_route_not_one(kg):
    """`path` picks one shortest route and says nothing about the rest; this returns them all.

    Both routes to a signal's class matter and they say different things: the `about` edge is the
    claim, the `uses` chain is the reason. `path` shows only the first.
    """
    r = kg.all_paths("procedure:signal-adosc-bearish", "concept:momentum", limit=None)
    routes = [[s["via"]["relation"] for s in p[1:]] for p in r.items]
    assert routes == [["about"], ["uses", "instance-of"]], \
        "expected the claim and the derivation, shortest first"
    assert r.truncated is False and r.total == 2


def test_all_paths_excludes_sibling_hops_by_default(kg):
    """Entering and leaving a node on two edges that both point AT it is a sibling, not a route.

    `adosc_bearish --instance-of--> Signal <--instance-of-- adosc_bullish` says "both are signals".
    On this graph that is not a minority: `concept:signal` has degree 218, and allowing it turns 2
    real routes into 9,785 at max_depth=5.
    """
    deep = kg.all_paths("procedure:signal-adosc-bearish", "concept:momentum",
                        max_depth=5, limit=None)
    assert deep.total == 2, "depth must not multiply the answer through a hub"

    loose = kg.all_paths("procedure:signal-adosc-bearish", "concept:momentum",
                         max_depth=5, sibling_hops=True, limit=None)
    assert loose.total > 1000, "the detours are real; the default is what suppresses them"

    # ...and when the shared parent IS the answer, asking for it works.
    both = kg.all_paths("procedure:signal-rsi-oversold", "procedure:signal-rsi-overbought",
                        max_depth=2, sibling_hops=True, limit=None)
    assert {p[1]["node"]["id"] for p in both.items} >= {"procedure:indicator-rsi"}, \
        "'they both read RSI' is a sibling hop and a legitimate answer"
    assert kg.all_paths("procedure:signal-rsi-oversold", "procedure:signal-rsi-overbought",
                        max_depth=2, limit=None).total == 0


def test_all_paths_distinguishes_its_two_truncated_states(kg):
    """"Showing 10 of 47" is a claim that 47 exist. After an early stop you cannot make it."""
    complete = kg.all_paths("procedure:signal-adosc-bearish", "concept:momentum",
                            max_depth=4, sibling_hops=True, limit=3)
    assert complete.truncated and "showing 3 of 219" in complete.note
    assert "stopped" not in complete.note, "a finished search must not hedge"

    # The step bound is not decorative: the same query one hop deeper trips the default.
    deep = kg.all_paths("procedure:signal-adosc-bearish", "concept:momentum",
                        max_depth=5, sibling_hops=True, limit=None)
    assert deep.truncated and "stopped after 200000 steps" in deep.note, \
        "an unbounded walk across a degree-218 hub must stop and say so, not run"

    stopped = kg.all_paths("procedure:signal-adosc-bearish", "concept:momentum",
                           max_depth=4, sibling_hops=True, limit=3, max_steps=200)
    assert stopped.truncated and "stopped after 200 steps" in stopped.note
    assert "there may be more" in stopped.note, \
        "an unfinished search must say its total is a floor -- and both incomplete\n         notes must carry the same marker, so a caller tests instead of parsing prose"
    assert stopped.total < complete.total, "it stopped early, so it found fewer"


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
        """The band this id matched in, rebuilt from the node's own fields rather than read out of
        find(). Uses the library's corpus builder and matcher -- a second copy of the tokenising,
        the plural folding and the URL stripping would be testing a different search."""
        from mangrove_kb.graph import haystacks, query_terms, rank_of
        n = kg.nodes[node_id]
        hay = haystacks({"name": n.name, "id": node_id, "summary": n.summary, **n.props})
        rank = rank_of(hay, query_terms("cross"))
        assert rank is not None, f"{node_id} matched in find() but in no tier"
        return rank

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
        # Normalised the way the search reads text, not by raw substring: chapter 4 states a rule
        # as `mean_reversion_signal(price)`, which mentions mean reversion in every sense that
        # matters and contains no space. A cruder check here reports the match as a false positive.
        def plain(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", " ", text.lower())
        mentioned = {n.id for n in kg.nodes.values()
                     if plain(term) in plain(_flatten({"name": n.name, "id": n.id,
                                                       "summary": n.summary, **n.props}))}
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


# --- asking a question, rather than matching its words -------------------------------------------

def test_a_query_falls_back_to_its_best_subset_only_when_nothing_carries_all_of_it(kg):
    """A sentence is a query too, and returning nothing leaves an agent with nowhere to walk from.

    The fallback must not loosen a query that already works: `mean reversion` has nodes carrying
    both words, so nodes carrying one of them stay out.
    """
    both = kg.find("mean reversion", limit=None)
    assert both.total == 24, "a query that fully matches must not be widened"
    for row in both.items:
        hay = " ".join(kg._haystacks[row["id"]])
        assert "mean" in hay and "reversion" in hay

    question = kg.find("why do breakouts fail", limit=None)
    assert question.total, "a question that carries no full match must still seed a traversal"
    for row in question.items:
        hay = " ".join(kg._haystacks[row["id"]])
        assert "breakout" in hay and "fail" in hay, "the fallback kept a node matching neither term"


def test_a_term_most_of_the_graph_carries_is_dropped_from_scoring(kg):
    """`signal` is in 282 of 498 nodes: it says nothing about which one is meant.

    Derived from this corpus rather than an English stop-word list -- "the" never appears in a node
    name, while "signal", "price" and "trading" are stop words here and nowhere else.
    """
    assert kg._document_frequency("signal") > 0.4 * len(kg.nodes)
    assert [r["id"] for r in kg.find("signal divergence", limit=None)] == \
           [r["id"] for r in kg.find("divergence", limit=None)]


def test_frequency_is_measured_over_the_graph_not_the_filtered_pool(kg):
    """Otherwise `find(q)` and `find(q, under=...)` answer with different vocabularies, and the
    scoped result stops being a subset of the open one -- which is what `under=` promises."""
    scoped = {r["id"] for r in kg.find("volume profile", under="price action", limit=None)}
    everywhere = {r["id"] for r in kg.find("volume profile", limit=None)}
    assert scoped and scoped <= everywhere


def test_ask_returns_the_seed_and_what_it_reaches_with_the_reason(kg):
    r = kg.ask("what quantifies liquidity", hops=1, limit=None)
    assert r.items, "a question that seeds should reach something"
    ids = [x["id"] for x in r.items]
    assert len(ids) == len(set(ids)), "a node reached twice must appear once"
    for item in r.items:
        reached = item["reached"]
        assert reached["seed"] in ids and reached["hops"] in (0, 1)
        if reached["hops"]:
            assert reached["why"].strip(), "an edge is only an answer if it says why it holds"
            assert reached["relation"] in RELATIONS
    assert ids == [x["id"] for x in kg.ask("what quantifies liquidity", hops=1, limit=None).items]


def test_ask_reaches_what_search_alone_cannot(kg):
    """The whole point: the words of a question rarely appear in the node that answers it."""
    words = {r["id"] for r in kg.find("stops beyond obvious levels", limit=None)}
    reached = {x["id"] for x in kg.ask("stops beyond obvious levels", hops=1, limit=None)}
    assert reached > words, "expanding over edges must reach more than the text match did"


def test_ask_says_nothing_rather_than_guessing(kg):
    assert kg.ask("zzzzqqq", limit=None).total == 0


def test_every_walk_can_filter_on_the_reason_not_only_the_relation(kg):
    """An edge is not only its relation: six `about` edges reach liquidity and they say two
    different things, and the difference is written in the `why` and nowhere else."""
    quantifies = {e["id"] for e in kg.neighbors("concept:liquidity", why="quantifies", limit=None)}
    principles = {e["id"] for e in kg.neighbors("concept:liquidity", why="principle", limit=None)}
    everything = {e["id"] for e in kg.neighbors("concept:liquidity", relation="about", limit=None)}
    assert quantifies and principles
    assert not (quantifies & principles), "the two readings of `about` must not overlap"
    assert (quantifies | principles) <= everything

    narrow = kg.subgraph("concept:liquidity", radius=1, why="quantifies")
    wide = kg.subgraph("concept:liquidity", radius=1)
    assert len(narrow["nodes"]) < len(wide["nodes"])
    assert all("quantif" in e["why"] for e in narrow["edges"]), \
        "an induced edge must satisfy the same filter as a traversed one"

    hops = kg.path("concept:liquidity", "concept:stop-hunt", why="principle")
    assert hops and all("principle" in h["via"]["why"] for h in hops[1:])
    assert kg.path("concept:liquidity", "concept:stop-hunt", why="quantifies") is None, \
        "a filter that excludes every route must say so, not fall back to another one"


def test_a_concept_lifted_from_core_principles_reaches_its_subject(kg):
    """`part-of` the chapter is scope; `about` the subject is what the chapter actually claims.

    Without the second edge a stop hunt was part of price action in general, and the route from
    liquidity to the sweep that empties it ran up to the chapter node and back down.
    """
    for nid in ("concept:liquidity-pool", "concept:stop-hunt", "concept:liquidity-grab"):
        out = {e["id"]: e["relation"] for e in kg.neighbors(nid, direction="out", limit=None)}
        assert out.get("concept:liquidity") == "about", f"{nid} does not reach its subject"
        assert out.get("concept:price-action") == "part-of", f"{nid} lost its chapter scope"
    assert len(kg.path("concept:liquidity", "concept:liquidity-grab")) == 2


def test_function_words_are_dropped_but_a_query_of_them_still_asks(kg):
    """Frequency cannot catch them: `why` is in 26 nodes of 498 because our own prose says
    "which is why", so it scored as though it discriminated and ranked two nodes that merely say
    it above the one that answers the question."""
    from mangrove_kb.graph import query_terms

    assert query_terms("why do breakouts fail") == ["breakouts", "fail"]
    assert query_terms("what") == ["what"], "a query of nothing but function words still asks"
    assert "up" not in FUNCTION_WORDS and "down" not in FUNCTION_WORDS, \
        "a direction is domain vocabulary here, not a function word"
    assert kg.find("why do breakouts fail", limit=None).total
