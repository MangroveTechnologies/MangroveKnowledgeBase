"""The dense index answers about the graph that is committed, and with the model it was built with.

Same purpose as `test_semantic.py` and one extra failure mode. A stale index answers confidently
about a graph that has changed under it; a MISMATCHED MODEL is worse, because the vectors load, the
shapes agree, the cosines are plausible numbers and every answer is quietly wrong -- the query and
the nodes were placed in two different spaces. So the model name is recorded in the artifact and
checked here against the builder's.

Encoding a query needs the model, which is a real download the first time. Tests that only inspect
the artifact do not load it; the two that do are marked so they can be deselected offline.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from mangrove_kb.graph import KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "ontology" / "signal-indicator-ontology.json"

dense = pytest.importorskip("mangrove_kb.dense", reason="numpy is required to read the index")

#: Whether SOME encoder is installed -- the bundled ONNX export (`semantic`) or the torch fallback
#: (`semantic-torch`). The dense vectors ship in the wheel either way, but embedding a QUESTION
#: needs one of the two, so a plain install skips these rather than failing on an ImportError that
#: says nothing about the graph. CI installs `[dev]`, which carries both, so they run there.
HAS_ENCODER = dense.encoder_available()
needs_encoder = pytest.mark.skipif(not HAS_ENCODER,
                                   reason="needs an encoder: pip install 'mangrove-kb[semantic]'")

HAS_ONNX = (importlib.util.find_spec("onnxruntime") is not None
           and importlib.util.find_spec("tokenizers") is not None)
needs_onnx = pytest.mark.skipif(not HAS_ONNX,
                                reason="needs the onnx extra: pip install 'mangrove-kb[semantic]'")

HAS_TORCH_ENCODER = importlib.util.find_spec("sentence_transformers") is not None
needs_torch_encoder = pytest.mark.skipif(
    not HAS_TORCH_ENCODER,
    reason="needs the torch fallback: pip install 'mangrove-kb[semantic-torch]'")



@pytest.fixture(scope="module")
def index():
    try:
        return dense.DenseIndex.load()
    except dense.DenseIndexNotFound as missing:
        pytest.fail(str(missing))


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


def test_the_index_was_built_from_the_committed_graph(index):
    assert index.matches(GRAPH), (
        "the dense index is stale -- the graph has changed since it was built. Rebuild it:\n"
        "    python3 ontology/build_dense_index.py")


def test_it_was_built_with_the_model_the_builder_names(index):
    """A different encoder is undetectable at read time and wrong at every query."""
    import sys

    sys.path.insert(0, str(REPO / "ontology"))
    from build_dense_index import MODEL

    assert index.built_with["model"] == MODEL, (
        f"index built with {index.built_with['model']!r}, builder now names {MODEL!r} -- "
        f"rebuild, or queries land in a different space than the nodes")


def test_every_node_has_at_least_one_row(index, kg):
    """A node absent from the index is unreachable by meaning and nothing else would say so."""
    covered = set(index.ids.tolist())
    assert covered == set(kg.nodes), (
        f"{len(set(kg.nodes) - covered)} nodes have no row, "
        f"{len(covered - set(kg.nodes))} rows name no node")


def test_rows_are_normalised_and_shaped(index):
    import numpy as np

    assert index.vectors.shape[0] == len(index.ids)
    assert index.vectors.shape[1] == index.built_with["dim"]
    norms = np.linalg.norm(index.vectors, axis=1)
    # float16 storage, so exact unit length is not available; this is well inside that rounding.
    assert np.allclose(norms, 1.0, atol=1e-3), f"rows are not unit vectors: {norms.min()}..{norms.max()}"


def test_no_node_is_split_into_more_rows_than_the_builder_allows(index):
    import collections
    import sys

    sys.path.insert(0, str(REPO / "ontology"))
    from build_dense_index import MAX_CHUNKS

    worst = collections.Counter(index.ids.tolist()).most_common(1)[0]
    assert worst[1] <= MAX_CHUNKS, f"{worst[0]} contributes {worst[1]} rows, cap is {MAX_CHUNKS}"


@needs_encoder
def test_it_reaches_a_paraphrase_lsa_cannot(index):
    """The reason this index exists, as a single case.

    `risk of ruin` is defined as "the probability of losing a specified percentage of capital". The
    question says "odds" and "wipe out the account" and shares no content word with it; LSA does not
    rank it anywhere, because nothing in 714 documents puts those phrasings together.

    Not marked `model`: the default encoder is the bundled ONNX export, and loading it needs no
    network. That marker is reserved for what actually needs one -- see the torch-fallback tests
    below.
    """
    hits = [nid for nid, _ in index.similar("what are the odds I wipe out the account", limit=5)]
    assert "concept:risk-of-ruin" in hits, hits


@needs_encoder
def test_a_node_is_scored_by_its_best_row_not_its_average(index):
    """Chunking is only worth its complexity if one good passage can carry a long node."""
    scores = dict(index.similar("three peaks and the middle one is the highest", limit=None))
    assert scores["concept:head-and-shoulders"] > 0.4


def test_ask_degrades_rather_than_raising_when_the_encoder_is_absent(kg, monkeypatch):
    """Neither encoder extra is guaranteed installed, so a bare install must degrade, not raise.

    The vectors are a numpy `.npz` and load without an encoder. So `DenseIndex.load()` succeeded,
    the graph reported a dense index, and `ask()` then raised `ImportError` from inside the query --
    a missing OPTIONAL dependency breaking the call rather than lowering its quality. `ask()` has to
    keep answering on the LSA index alone. Both `onnxruntime`/`tokenizers` (the default path) and
    `sentence-transformers` (the fallback) are blinded, because blinding only one used to leave the
    other able to carry the call -- this has to simulate neither extra being installed at all.
    """
    import importlib.util

    from mangrove_kb.graph import KnowledgeGraph

    real = importlib.util.find_spec
    blinded = {"sentence_transformers", "onnxruntime", "tokenizers"}

    def blind(name, *a, **k):
        return None if name in blinded else real(name, *a, **k)

    monkeypatch.setattr(importlib.util, "find_spec", blind)
    bare = KnowledgeGraph.load()
    assert bare.dense_index() is None, "the encoder is absent; the index must not report present"
    assert bare.semantic_index() is not None, "the LSA index needs no encoder and must survive"

    answered = bare.ask("how far away from my entry should the stop go", limit=5)
    assert answered.total > 0, "ask() stopped answering without the optional extra"


# --- the ONNX encoder: the default path, no torch -------------------------------------------------

@needs_onnx
def test_the_default_path_needs_no_torch(index):
    """`DenseIndex.model` must not import torch when the bundled ONNX export can serve the query."""
    import sys

    for name in ("torch", "sentence_transformers"):
        sys.modules.pop(name, None)
    from mangrove_kb.onnx_encoder import OnnxEncoder

    assert isinstance(index.model, OnnxEncoder)
    assert "torch" not in sys.modules, "loading the onnx encoder imported torch"
    assert "sentence_transformers" not in sys.modules


@needs_onnx
def test_the_onnx_encoder_returns_unit_vectors(index):
    import numpy as np

    vec = index.embed("how far away from my entry should the stop go")
    assert vec.shape == (index.built_with["dim"],)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-4


@pytest.mark.model
@needs_onnx
@needs_torch_encoder
def test_the_onnx_encoder_matches_the_torch_encoder_it_replaced():
    """The parity gate, as a fast spot check -- not the full corpus-plus-question-set sweep that
    `ontology/build_onnx_encoder.py`'s docstring reports (min 0.99999982, mean 1.0 there); this is
    enough to catch a regression without re-encoding the whole graph on every test run."""
    import numpy as np
    from sentence_transformers import SentenceTransformer

    from mangrove_kb.onnx_encoder import OnnxEncoder
    from mangrove_kb.dense import _ONNX_DIR

    texts = ["how far away from my entry should the stop go",
             "what are the odds I wipe out the account",
             "three peaks and the middle one is the highest"]
    onnx_vecs = OnnxEncoder(_ONNX_DIR).encode(texts, normalize_embeddings=True)
    torch_vecs = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2").encode(
        texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    sims = np.sum(onnx_vecs * torch_vecs, axis=1)
    assert sims.min() > 0.999, sims.tolist()


@pytest.mark.model
def test_the_torch_fallback_is_only_reached_without_the_onnx_files(monkeypatch):
    """`_load_encoder` tries ONNX first; this proves the fallback branch is live rather than dead
    code, by hiding the bundled export and checking the torch path is the one that answers."""
    if not HAS_TORCH_ENCODER:
        pytest.skip("needs the torch fallback: pip install 'mangrove-kb[semantic-torch]'")
    import mangrove_kb.dense as dense_mod

    monkeypatch.setattr(dense_mod, "_ONNX_DIR", dense_mod._ONNX_DIR.parent / "does-not-exist")
    fresh = dense.DenseIndex.load()
    from sentence_transformers import SentenceTransformer

    assert isinstance(fresh.model, SentenceTransformer)
