#!/usr/bin/env python3
"""Build the dense index: the graph as seen by a model that learned English elsewhere.

The companion to ``build_semantic_index.py``. That one is LSA over this corpus and knows what *this
text* puts near what; this one is a pretrained sentence encoder and knows what English puts near
what. Measured on the twenty-five questions in ``tests/test_the_graph_answers_questions.py``, LSA
answers 13, this answers 15, and fusing the two answers 18 -- so both are built and
:meth:`KnowledgeGraph.ask` combines them.

    python3 ontology/build_dense_index.py        # writes mangrove_kb/data/dense-index.npz

**Nodes are chunked; the LSA document is not usable here.** That builder repeats each search tier
by weight, which is the right way to tell a bag-of-words model what a node is mostly about. This
encoder truncates at 256 tokens, so the same document would spend its window on a triplicated name
and never reach the node's detail. Instead each node contributes several rows -- its name and
summary, then its detail in windows -- and a node is scored by its best row. That is also why the
row count exceeds the node count.

`sentence-transformers` is needed to BUILD the index and, unlike scikit-learn for the LSA one, also
to USE it: a query has to be encoded by the same model. It is a hard dependency for that reason.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from mangrove_kb.graph import KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "ontology" / "signal-indicator-ontology.json"
OUT = REPO / "mangrove_kb" / "data" / "dense-index.npz"

#: Small, fast, and the one the comparison was run against. Changing this invalidates every number
#: recorded in the test suite, so it is recorded in the artifact and asserted at load.
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#: Words per detail window. The encoder truncates at 256 word-pieces, which is roughly 180 words of
#: this corpus's prose; a window near that length fills the context without overflowing it.
CHUNK_WORDS = 180

#: Rows per node. A handful of long nodes would otherwise contribute dozens of windows and dominate
#: the index by sheer surface area.
MAX_CHUNKS = 8


def chunks_of(kg: KnowledgeGraph, nid: str) -> list[str]:
    """The rows one node contributes, each prefixed with its name.

    The prefix is not decoration: a detail window on its own reads as an anonymous paragraph, and
    the encoder places it by its topic rather than by its subject. Naming the node in every row is
    what keeps its windows near it.
    """
    node = kg.nodes[nid]
    hay = kg._haystacks[nid]
    rows = [f"{node.name}. {node.summary or ''}".strip()]
    detail = " ".join(tier for tier in hay[2:] if tier).split()
    for start in range(0, len(detail), CHUNK_WORDS):
        window = " ".join(detail[start:start + CHUNK_WORDS])
        if window:
            rows.append(f"{node.name}. {window}")
    return rows[:MAX_CHUNKS]


def build(graph_path: Path, out: Path, model_name: str = MODEL) -> dict:
    from sentence_transformers import SentenceTransformer

    kg = KnowledgeGraph.load(graph_path)
    ids, texts = [], []
    for nid in sorted(kg.nodes):
        for row in chunks_of(kg, nid):
            ids.append(nid)
            texts.append(row)

    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, batch_size=64, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False)

    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        # Unicode dtype, not object: an object array cannot be loaded without pickle, and a
        # published data file that requires pickle to read is a published deserialisation hazard.
        ids=np.array(ids, dtype="U"),
        # Half precision. The rounding is ~1e-3 of a cosine, four orders below the gap between
        # neighbouring results, and it halves a file that ships in the wheel.
        vectors=vectors.astype(np.float16),
        graph_sha=np.array(hashlib.sha256(graph_path.read_bytes()).hexdigest(), dtype="U"),
        built_with=np.array(json.dumps({"model": model_name, "chunk_words": CHUNK_WORDS,
                                        "max_chunks": MAX_CHUNKS,
                                        "dim": int(vectors.shape[1])}), dtype="U"),
    )
    return {"nodes": len(kg.nodes), "rows": len(ids), "dim": int(vectors.shape[1]),
            "bytes": out.stat().st_size}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", type=Path, default=GRAPH)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()
    stats = build(args.graph, args.out, args.model)
    print(f"// wrote {args.out}")
    print(f"// {stats['nodes']} nodes as {stats['rows']} rows, {stats['dim']} dimensions, "
          f"{stats['bytes'] / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
