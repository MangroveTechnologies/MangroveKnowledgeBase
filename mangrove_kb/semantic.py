"""Search the graph by meaning, not by wording.

`KnowledgeGraph.find` matches the words a query uses. This matches what it is *about*: a question
and a node are compared as directions in a 128-dimensional space built from how terms co-occur
across the graph, so *"why do breakouts fail"* reaches the node that says a breakout is read as a
loss, which shares no word with the question.

**It returns node ids and nothing else.** There is no passage store, no chunking and no second copy
of the text: every row of the index is keyed by a node, so a hit lands in the graph and the edges
explain from there. Conventional retrieval returns a passage with no identity; that is the failure
mode this design refuses.

The index is a build artifact -- `ontology/build_semantic_index.py` writes it from the committed
graph, and it carries that graph's checksum so a stale one is detectable rather than silently
answering an older question. Building needs scikit-learn; using needs numpy, which the package
already requires.

    from mangrove_kb.semantic import SemanticIndex

    idx = SemanticIndex.load()
    idx.similar("why do breakouts fail")     # [(node id, score), ...]

Reached through the graph as `kg.ask(question, semantic=True)`, which uses these as the seeds it
walks out from.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .graph import query_terms

__all__ = ["SemanticIndex", "IndexNotFound"]

_ENV_VAR = "MANGROVE_KB_SEMANTIC_INDEX"
_PACKAGED = Path(__file__).resolve().parent / "data" / "semantic-index.npz"
_IN_REPO = Path(__file__).resolve().parent.parent / "mangrove_kb" / "data" / "semantic-index.npz"


class IndexNotFound(FileNotFoundError):
    """Raised with the command that builds one, because that is the next step."""


@dataclass(frozen=True)
class SemanticIndex:
    ids: list[str]
    vectors: np.ndarray            # (nodes, components), L2-normalised
    vocabulary: dict[str, int]     # term -> column in the term-document matrix
    idf: np.ndarray                # (terms,)
    components: np.ndarray         # (components, terms) -- the projection a query folds through
    graph_sha: str
    built_with: dict

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> "SemanticIndex":
        candidates = [Path(path)] if path else [
            Path(p) for p in (os.environ.get(_ENV_VAR),) if p] + [_PACKAGED, _IN_REPO]
        for candidate in candidates:
            if candidate.is_file():
                with np.load(candidate, allow_pickle=False) as data:
                    vocabulary = {t: i for i, t in enumerate(data["vocabulary"].tolist())}
                    return cls(ids=data["ids"].tolist(), vectors=data["vectors"],
                               vocabulary=vocabulary, idf=data["idf"],
                               components=data["components"],
                               graph_sha=str(data["graph_sha"]),
                               built_with=json.loads(str(data["built_with"])))
        raise IndexNotFound(
            "no semantic index found. Build one with:\n"
            "    python3 ontology/build_semantic_index.py\n"
            f"(looked in: {', '.join(str(c) for c in candidates)})")

    def matches(self, graph_path: str | os.PathLike[str]) -> bool:
        """Whether this index was built from that graph file, byte for byte.

        A stale index is worse than none: it answers confidently about a graph that has changed
        under it, and nothing in the answer says so.
        """
        return self.graph_sha == hashlib.sha256(Path(graph_path).read_bytes()).hexdigest()

    def embed(self, text: str) -> np.ndarray:
        """Fold a query into the space, exactly as the builder folded the documents.

        Re-implemented over numpy rather than kept as a scikit-learn object: the weighting is four
        lines, and requiring the training library at query time would make a search dependency of a
        build dependency.
        """
        counts: dict[int, int] = {}
        for term in query_terms(text):
            column = self.vocabulary.get(term)
            if column is not None:
                counts[column] = counts.get(column, 0) + 1
        row = np.zeros(len(self.idf), dtype=np.float32)
        for column, count in counts.items():
            row[column] = (1.0 + np.log(count)) * self.idf[column]   # sublinear tf, as built
        norm = np.linalg.norm(row)
        if norm:
            row /= norm
        folded = self.components @ row
        norm = np.linalg.norm(folded)
        return folded / norm if norm else folded

    def similar(self, text: str, *, limit: int | None = 10,
                among: Sequence[str] | None = None) -> list[tuple[str, float]]:
        """Nodes closest in meaning, best first, as ``(node id, cosine similarity)``.

        ``among`` restricts the comparison to a set of ids -- which is what makes this usable as a
        re-ranker over a pool the graph produced, rather than only as a way in.
        """
        query = self.embed(text)
        if not query.any():
            return []
        if among is None:
            rows, ids = self.vectors, self.ids
        else:
            keep = [i for i, nid in enumerate(self.ids) if nid in set(among)]
            if not keep:
                return []
            rows, ids = self.vectors[keep], [self.ids[i] for i in keep]
        scores = rows @ query
        order = np.argsort(-scores)
        if limit is not None:
            order = order[:limit]
        return [(ids[i], float(scores[i])) for i in order]
