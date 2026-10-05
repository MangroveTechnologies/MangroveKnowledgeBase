#!/usr/bin/env python3
"""Export the encoder as ONNX: the same vectors, without torch at runtime.

`mangrove_kb.dense.DenseIndex.model` embeds one short question per `ask()` call. Everything else
about that call is a precomputed `.npz` -- the node vectors `build_dense_index.py` writes -- so the
only runtime cost `sentence-transformers` buys is encoding that one string, and it buys it at the
price of `torch`: ~180 MB RSS and ~10 s to import and load, and 1.4 GB in the CPU wheel. This script
exports the same checkpoint to ONNX so the runtime path needs only `onnxruntime` and `tokenizers`.

    python3 ontology/build_onnx_encoder.py        # writes mangrove_kb/data/onnx-encoder/

Needs `optimum[onnxruntime]` and `onnx` to RUN -- a build dependency, deliberately undeclared in
any extra, same reasoning as `wiki-to-graph` in `pyproject.toml`'s `dev` extra: a tool almost nobody
runs should not add its weight to every contributor's install.

    pip install "optimum[onnxruntime]" onnx

**Two files are shipped, nothing else.** `tokenizers.Tokenizer.from_file` reads vocabulary, special
tokens and normalization straight out of `tokenizer.json`; the rest of what `save_pretrained` writes
(`config.json`, `vocab.txt`, `tokenizer_config.json`, `special_tokens_map.json`) is redundant with
it and is not bundled.

**fp32, not int8.** Dynamic int8 quantization shrinks the model from 86 MiB to 22 MiB, but the
embeddings it produces are no longer close enough to call the same vectors: compared against the
torch model over this graph's corpus plus the question set used to measure `ask()`, fp32 cosine
similarity is min 0.99999982 / mean 1.0 -- a lossless re-export -- while int8 is min 0.8796 / mean
0.9447, which is large enough to change which node a query seeds from. 86 MiB keeps the wheel under
PyPI's 100 MB-per-file limit with room to spare, so there is nothing quantization is worth buying
here. `--quantize` is kept as a flag because a future, larger model might need the trade; it is not
the default and is not what is committed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")   # export from the cache; this script fetches nothing

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "mangrove_kb" / "data" / "onnx-encoder"

#: Must match `build_dense_index.MODEL` -- this re-exports the same checkpoint the node vectors
#: were encoded with, not a different one.
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def export(model_name: str, out: Path, *, quantize: bool = False) -> dict:
    import shutil
    import tempfile

    from optimum.onnxruntime import ORTModelForFeatureExtraction
    from transformers import AutoTokenizer

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = ORTModelForFeatureExtraction.from_pretrained(model_name, export=True)
        model.save_pretrained(staged)
        tokenizer.save_pretrained(staged)

        out.mkdir(parents=True, exist_ok=True)
        model_path = staged / "model.onnx"
        if quantize:
            from onnxruntime.quantization import QuantType, quantize_dynamic

            quantize_dynamic(model_input=str(model_path), model_output=str(out / "model.onnx"),
                             weight_type=QuantType.QInt8)
        else:
            shutil.copyfile(model_path, out / "model.onnx")
        shutil.copyfile(staged / "tokenizer.json", out / "tokenizer.json")

    manifest = {"model": model_name, "quantized": quantize,
                "bytes": (out / "model.onnx").stat().st_size}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--quantize", action="store_true",
                    help="dynamic int8 quantization -- smaller, measurably worse (see module docstring)")
    args = ap.parse_args()
    manifest = export(args.model, args.out, quantize=args.quantize)
    print(f"// wrote {args.out}")
    print(f"// {manifest['bytes'] / 1024 / 1024:.1f} MiB, quantized={manifest['quantized']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
