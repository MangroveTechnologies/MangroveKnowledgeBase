#!/usr/bin/env python3
"""Build the semantic index: what the graph means, rather than which words it uses.

The word search answers "do we already have one of these" well and answers "why does Y happen"
badly, because the node that answers a question rarely contains the question's words. Measured on
the twenty-five questions in `tests/test_the_graph_answers_questions.py`, phrased the way a trader
asks them, the word search puts the right node in the top five 5 times out of 25.

This is latent semantic analysis over the graph's own text (Deerwester et al., *JASIS* 1990): a
term-document matrix, TF-IDF weighted, reduced by truncated SVD. Terms that occur in the same
contexts end up close, which is how a question about a breakout that *fails* reaches a node that
says it is read as a *loss*. On those questions it scores 13.

**It is one of two indices, and `ask` fuses them** -- see `ontology/build_dense_index.py` for the
other, a pretrained sentence encoder. What this one knows is what *this corpus* puts together, which
is where the meaning of "basis" or "delta" is decided; what it cannot know is a paraphrase the
corpus never states, and *"what are the odds I wipe out the account"* does not reach
`concept:risk-of-ruin` however it is weighted. The encoder scores 15 alone and the fused pair scores
18, because they fail on different questions.

That comparison is only as good as the questions. An earlier run of it had this index at 16/20 and
the encoder at 12/20, on a set written by an agent that had just read the chapters and therefore
used the corpus's own vocabulary -- the one condition under which co-occurrence beats general English
by construction. Re-measured on questions written to avoid node wording, the order reverses. Any
future comparison here is worth only what its question set is worth.

The output is a projection of the graph, not a second copy of it: every row is keyed by node id, so
a hit lands on a node and the edges do the explaining from there.

    python3 ontology/build_semantic_index.py            # writes mangrove_kb/data/semantic-index.npz

`scikit-learn` is needed to BUILD the index and never to use one -- the query side folds a question
through the saved projection with numpy alone. (The dense index differs here: encoding a query needs
its model, which is why that one carries a runtime dependency and this one does not.)
`tests/test_semantic.py` checks the committed index against the committed graph, so a chapter merged
without rebuilding it fails CI rather than answering yesterday's questions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from mangrove_kb.graph import FUNCTION_WORDS, KnowledgeGraph, haystacks

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "ontology" / "signal-indicator-ontology.json"
OUT = REPO / "mangrove_kb" / "data" / "semantic-index.npz"

#: Dimensions kept. Measured: 64 scores 14/20, 128 scores 16/20, 256 scores 15/20 -- past the middle
#: the extra components carry the corpus's noise rather than its meaning.
COMPONENTS = 128

#: How much each search tier is repeated in the document. A node's name and summary say what it IS;
#: the detail says what it is like. Weighting them keeps a node ABOUT a subject above one that
#: merely mentions it -- the same claim `SEARCH_TIERS` makes for the word search.
TIER_WEIGHTS = (3, 2, 2, 1, 1)


def documents(kg: KnowledgeGraph) -> tuple[list[str], list[str]]:
    ids = sorted(kg.nodes)
    docs = []
    for nid in ids:
        n = kg.nodes[nid]
        # The same corpus `find` reads, edge reasons included: a wired statement is text about the
        # node it hangs off, and leaving it out indexed the graph as it was before it was wired.
        hay = kg._haystacks[nid]
        docs.append(" ".join(" ".join([text] * weight)
                             for text, weight in zip(hay, TIER_WEIGHTS) if text))
    return ids, docs


def build(graph_path: Path, out: Path, components: int = COMPONENTS) -> dict:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    kg = KnowledgeGraph.load(graph_path)
    ids, docs = documents(kg)

    vec = TfidfVectorizer(stop_words=sorted(FUNCTION_WORDS), sublinear_tf=True,
                          token_pattern=r"[a-z0-9]{2,}")
    matrix = vec.fit_transform(docs)
    # `arpack` rather than the randomised default: the index is a committed artifact reviewed as a
    # diff, and a build that returns different numbers each run cannot be reviewed at all.
    svd = TruncatedSVD(n_components=components, algorithm="arpack", random_state=0)
    vectors = svd.fit_transform(matrix).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12

    vocabulary = vec.get_feature_names_out()
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        # Unicode dtype, not object: an object array cannot be loaded without pickle, and a
        # published data file that requires pickle to read is a published deserialisation hazard.
        ids=np.array(ids, dtype="U"),
        vectors=vectors,
        vocabulary=np.array(vocabulary, dtype="U"),
        idf=vec.idf_.astype(np.float32),
        components=svd.components_.astype(np.float32),
        graph_sha=np.array(hashlib.sha256(graph_path.read_bytes()).hexdigest(), dtype="U"),
        built_with=np.array(json.dumps({"components": components, "sublinear_tf": True,
                                        "weights": list(TIER_WEIGHTS)}), dtype="U"),
    )
    return {"nodes": len(ids), "terms": len(vocabulary), "components": components,
            "explained_variance": float(svd.explained_variance_ratio_.sum()),
            "bytes": out.stat().st_size}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", type=Path, default=GRAPH)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--components", type=int, default=COMPONENTS)
    args = ap.parse_args()
    stats = build(args.graph, args.out, args.components)
    print(f"// wrote {args.out}")
    print(f"// {stats['nodes']} nodes, {stats['terms']} terms, {stats['components']} components, "
          f"{stats['explained_variance']:.2f} variance, {stats['bytes'] / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
