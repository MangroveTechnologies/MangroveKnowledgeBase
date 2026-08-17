"""The semantic index answers about the graph that is committed, not the one it was built from.

A stale index is the failure this file exists to prevent: it answers confidently about a graph that
has changed under it, and nothing in the answer says so. Merging a chapter without rebuilding the
index must fail here rather than in an agent's face.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mangrove_kb.graph import GraphError, KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "ontology" / "signal-indicator-ontology.json"

semantic = pytest.importorskip("mangrove_kb.semantic", reason="numpy is required to read the index")


@pytest.fixture(scope="module")
def index():
    try:
        return semantic.SemanticIndex.load()
    except semantic.IndexNotFound as missing:
        pytest.fail(str(missing))


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


def test_the_index_was_built_from_the_committed_graph(index):
    assert index.matches(GRAPH), (
        "the semantic index is stale -- the graph has changed since it was built. Rebuild it:\n"
        "    python3 ontology/build_semantic_index.py")


def test_it_indexes_every_node_and_nothing_else(index, kg):
    assert set(index.ids) == set(kg.nodes)
    assert len(index.vectors) == len(index.ids)
    assert index.vectors.shape[1] == index.built_with["components"]


def test_folding_a_query_matches_the_library_that_built_the_index(index):
    """`embed()` re-implements TF-IDF and the SVD projection over numpy so that scikit-learn is a
    BUILD dependency and never a query one. That is only safe while the two agree."""
    sklearn_text = pytest.importorskip("sklearn.feature_extraction.text")
    import numpy as np

    vectorizer = sklearn_text.TfidfVectorizer(sublinear_tf=True, token_pattern=r"[a-z0-9]{2,}",
                                              vocabulary=index.vocabulary)
    vectorizer.idf_ = index.idf
    for query in ("why do breakouts fail", "impermanent loss", "what settles two days later"):
        from mangrove_kb.graph import query_terms
        theirs = vectorizer.transform([" ".join(query_terms(query))])
        theirs = index.components @ np.asarray(theirs.todense()).ravel().astype(np.float32)
        theirs /= np.linalg.norm(theirs) or 1.0
        assert np.allclose(index.embed(query), theirs, atol=1e-5), query


def test_a_question_reaches_a_node_that_shares_no_word_with_it(index):
    """The whole justification. `liquidity-grab` says a failed breakout is read as a loss, and the
    word `fail` appears nowhere in it."""
    hits = [nid for nid, _ in index.similar("stops are hunted before price reverses", limit=5)]
    assert "concept:stop-hunt" in hits or "concept:liquidity-grab" in hits, hits


def test_ask_uses_the_index_when_it_matches_and_says_so_when_asked_for_it_without_one(kg):
    assert kg.semantic_index() is not None, "the committed index should load and match"
    semantic_first = [x["id"] for x in kg.ask("why do breakouts fail", limit=5)]
    words_only = [x["id"] for x in kg.ask("why do breakouts fail", semantic=False, limit=5)]
    assert semantic_first != words_only, "semantic seeding must actually change the answer"

    bare = KnowledgeGraph.load()
    # BOTH, because there are two now. Unsetting only the LSA one left the dense index seeding the
    # call, so this read as a fallback failure when it was really a fallback that had not happened.
    bare._semantic = bare._dense = None         # as if neither index shipped
    assert [x["id"] for x in bare.ask("why do breakouts fail", limit=5)] == words_only, \
        "without an index the call must fall back to the word search, not fail"
    with pytest.raises(GraphError, match="build_semantic_index"):
        bare.ask("why do breakouts fail", semantic=True)


def test_either_index_alone_still_answers(kg):
    """Neither index may become load-bearing for the other's presence.

    They are built by separate commands and a rebuild of one can land without the other, so each
    has to seed a search on its own -- degrading to a worse answer, never to an exception.
    """
    for missing in ("_semantic", "_dense"):
        one = KnowledgeGraph.load()
        setattr(one, missing, None)
        assert one.ask("how far away from my entry should the stop go", limit=5).total > 0, \
            f"ask() stopped working with {missing} absent"


def test_it_answers_the_measured_questions(kg):
    """The gate the layer had to pass to ship: the same twenty questions the word search scored
    seven on, and `ask` over words scored twelve on.

    Kept as a test rather than a note, because a change that quietly lowers it should fail rather
    than be discovered the next time someone measures.
    """
    cases = [
        ("how do I stop getting stopped out on obvious levels", "concept:stop-hunt"),
        ("is a high win rate safer", "fact:win-rate-is-not-risk"),
        ("which strategy works in a sideways market", "concept:ranging-market"),
        ("how do I hide a large order", "concept:iceberg-order"),
        ("what happens when my margin runs out", "concept:liquidation-engine"),
        ("what do I pay to hold a perpetual overnight", "property:perpetual-funding-rate"),
        ("why is my liquidity position worth less than holding", "property:impermanent-loss"),
        ("what is the fairest price today", "concept:point-of-control"),
        ("is there a gap price will come back to fill", "concept:fair-value-gap"),
        ("which timeframe should I trust", "concept:multi-timeframe-analysis"),
        ("what is the option worth if I exercise now", "property:intrinsic-and-time-value"),
        ("what settles two days later", "concept:equity-settlement"),
    ]
    answered = sum(want in [x["id"] for x in kg.ask(q, limit=5)] for q, want in cases)
    assert answered >= 11, f"semantic retrieval answered {answered} of {len(cases)}"
