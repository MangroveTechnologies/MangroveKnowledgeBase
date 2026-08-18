"""Search the graph with a model that learned English somewhere else.

:mod:`mangrove_kb.semantic` is latent semantic analysis over this graph's own text, so it knows what
*this corpus* puts near what: it reaches a node about a breakout being read as a loss from a question
about breakouts failing. What it cannot do is bridge a paraphrase the corpus never states. Asked
*"what are the odds I wipe out the account"* it does not reach ``concept:risk-of-ruin``, whose
summary is *"the probability of losing a specified percentage of capital"* -- the same sentence in
different words, sharing none of them. Nothing in 714 documents puts "odds" beside "probability"
often enough for co-occurrence to learn it; a model trained on the open web already knows.

The two fail differently, which is the point. Measured on twenty-five questions phrased the way a
trader asks them, LSA answers 13, this answers 15, and the union of their top five holds 18 -- so
they are combined rather than chosen between. :meth:`KnowledgeGraph.ask` fuses them by reciprocal
rank; see the note there for why fusion and not interleaving.

Every row is keyed by a node id, as in the LSA index: a hit lands on a node and the edges explain
from there. There is no passage store and no second copy of the text.

    from mangrove_kb.dense import DenseIndex

    DenseIndex.load().similar("how much can I borrow against what I have")

The vectors are a build artifact -- ``ontology/build_dense_index.py`` writes them from the committed
graph and stamps that graph's checksum, so a stale index is detectable rather than quietly answering
about a graph that has changed. Encoding a *query* needs the model itself, which is why
``sentence-transformers`` is a hard dependency; the model downloads once on first use and is cached
by ``huggingface_hub`` thereafter.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np

__all__ = ["DenseIndex", "DenseIndexNotFound"]

_ENV_VAR = "MANGROVE_KB_DENSE_INDEX"
_PACKAGED = Path(__file__).resolve().parent / "data" / "dense-index.npz"


class DenseIndexNotFound(FileNotFoundError):
    """Raised with the command that builds one, because that is the next step."""


@dataclass
class DenseIndex:
    ids: np.ndarray                # (chunks,) node id owning each row -- a node has several
    vectors: np.ndarray            # (chunks, dim), L2-normalised
    graph_sha: str
    built_with: dict
    _model: Any = field(default=None, repr=False, compare=False)

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> "DenseIndex":
        candidates = [Path(path)] if path else [
            Path(p) for p in (os.environ.get(_ENV_VAR),) if p] + [_PACKAGED]
        for candidate in candidates:
            if candidate.is_file():
                with np.load(candidate, allow_pickle=False) as data:
                    return cls(ids=data["ids"],
                               # Stored at half precision -- 1.2 MB rather than 2.5 MB, and the
                               # rounding is four orders of magnitude below the gap between
                               # neighbouring cosines. Promoted once here, not per query.
                               vectors=data["vectors"].astype(np.float32),
                               graph_sha=str(data["graph_sha"]),
                               built_with=json.loads(str(data["built_with"])))
        raise DenseIndexNotFound(
            "no dense index found. Build one with:\n"
            "    python3 ontology/build_dense_index.py\n"
            f"(looked in: {', '.join(str(c) for c in candidates)})")

    def matches(self, graph_path: str | os.PathLike[str]) -> bool:
        """Whether this index was built from that graph file, byte for byte."""
        return self.graph_sha == hashlib.sha256(Path(graph_path).read_bytes()).hexdigest()

    @property
    def model(self):
        """The encoder, loaded on first query and kept.

        Deferred rather than loaded with the vectors: importing sentence-transformers costs seconds
        and pulls in torch, and a caller who only reads the graph should pay neither.
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer   # noqa: PLC0415
            except ImportError as exc:                                  # pragma: no cover
                raise ImportError(
                    "sentence-transformers is required to encode a question. It is an extra:\n"
                    "    pip install 'mangrove-kb[semantic]'\n"
                    "Reaching this means the index was handed out without it -- "
                    "`KnowledgeGraph.dense_index()` checks for the encoder and returns None, so "
                    "`ask()` should have fallen back to the word index rather than arriving "
                    "here.") from exc
            self._model = SentenceTransformer(self.built_with["model"])
        return self._model

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode([text], normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)[0]

    def similar(self, text: str, *, limit: int | None = 10,
                among: Sequence[str] | None = None) -> list[tuple[str, float]]:
        """Nodes closest in meaning, best first, as ``(node id, cosine similarity)``.

        A node is scored by its BEST chunk, not its average: a long node answers a question when one
        part of it does, and averaging buries that part under the rest of the node.

        ``among`` restricts the comparison to a set of ids, which is what makes this usable as a
        re-ranker over a pool the graph produced rather than only as a way in.
        """
        query = self.embed(text)
        scores = self.vectors @ query
        keep = set(among) if among is not None else None
        best: dict[str, float] = {}
        for nid, score in zip(self.ids.tolist(), scores.tolist()):
            if keep is not None and nid not in keep:
                continue
            if score > best.get(nid, -2.0):
                best[nid] = score
        ranked = sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:limit] if limit is not None else ranked
