"""The question encoder, as ONNX rather than torch.

`mangrove_kb.dense.DenseIndex` precomputes every node's vector at build time; the only encoding
left at runtime is one short question per `ask()` call. `sentence-transformers` can do that, but it
pulls `torch` to do it -- ~180 MB RSS and ~10 s to import and load a model that then runs one
50-ms forward pass per call. This is the same checkpoint (`ontology/build_onnx_encoder.py` exports
it), read by `onnxruntime` with `tokenizers` doing the tokenizing, so neither `torch` nor
`sentence-transformers` need to be installed.

Mean pooling over the token embeddings, masked by `attention_mask` and then L2-normalised, is what
`sentence-transformers` does for this model (`1_Pooling/config.json` names `pooling_mode_mean_tokens`
and `config_sentence_transformers.json` adds a final `Normalize` module) -- re-implemented here over
the raw ONNX output rather than carried as a second dependency on the library that already does it.

``encode()`` matches the slice of ``SentenceTransformer.encode()`` that :meth:`DenseIndex.embed`
calls, so swapping the encoder needs no change on that side: ``normalize_embeddings``,
``convert_to_numpy`` and ``show_progress_bar`` are accepted and the last two are no-ops, since this
always returns a normalised numpy array and never prints one.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

__all__ = ["OnnxEncoder"]


class OnnxEncoder:
    def __init__(self, model_dir: str | Path, *, max_length: int = 256):
        import onnxruntime as ort           # noqa: PLC0415 -- the point of this module
        from tokenizers import Tokenizer    # noqa: PLC0415

        model_dir = Path(model_dir)
        self._tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        # BERT's [PAD] is id 0 in this vocabulary; padding and truncation are set here because the
        # ONNX graph is fixed-shape over a batch -- every row in one call must have the same length.
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self._tokenizer.enable_truncation(max_length=max_length)
        self._session = ort.InferenceSession(str(model_dir / "model.onnx"),
                                             providers=["CPUExecutionProvider"])

    def encode(self, texts: Sequence[str], *, normalize_embeddings: bool = True,
               convert_to_numpy: bool = True, show_progress_bar: bool = False) -> np.ndarray:
        encodings = self._tokenizer.encode_batch(list(texts))
        ids = np.array([e.ids for e in encodings], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)
        (token_embeddings,) = self._session.run(
            None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": type_ids})
        mask_f = mask[..., None].astype(np.float32)
        pooled = (token_embeddings * mask_f).sum(axis=1) / np.clip(mask_f.sum(axis=1), 1e-9, None)
        if normalize_embeddings:
            norm = np.linalg.norm(pooled, axis=1, keepdims=True)
            pooled = pooled / np.clip(norm, 1e-12, None)
        return pooled.astype(np.float32)
