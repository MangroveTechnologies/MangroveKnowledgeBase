"""Build ontology nodes from the docstring, with no carry-forward and no knowledge-base lift.

The replacement for `build_signal_indicator_ontology.py`, written alongside it rather than into it
so the old builder keeps working untouched until this one reproduces its output exactly.

The difference is the whole point of the exercise: this builder reads **one** source for every
authored value -- the docstring of the object itself -- and derives everything else from the code.
It never reads the previous graph, and it never reads `knowledge-base/*.md`. Delete the JSON and it
rebuilds; the old builder cannot, because ~1,270 of its values come from the file it is writing.

Authored, read from the docstring by `parse_authored`:
    summary, formula, abbreviation, reference, interpretation, applications,
    per-input description, per-output units / range / canonical_name / description

Derived, read from the code and never authored:
    source_module   the class's module
    inputs/params/outputs KEYS   the `_data` / `_params` / `_outputs` class attributes
    usage_example   generated from those attributes
    warmup_bars     `min_periods` in `_compute`, only when unambiguous

Usage:
    python3 ontology/build_from_docstrings.py BollingerBands
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mangrove_kb.docstring_parser import parse_authored  # noqa: E402


def usage_example(cls) -> str:
    """A copy-pasteable `compute()` call, generated from the class attributes.

    Generated rather than parsed, for the same reason the old builder generates it: the version in
    the knowledge-base markdown is itself generated from these attributes, so reading it back would
    make a derived artifact the source.
    """
    data = ", ".join(f"'{d}': df['{d.title()}']" for d in cls._data)
    params = ", ".join(f"'{p}': value" for p in cls._params)
    return f"{cls.__name__}.compute(data={{{data}}}, params={{{params}}})"


def warmup_bars(cls) -> str | None:
    """`min_periods` from `_compute`, and only when it is unambiguous.

    A GUESS, not a reading: it assumes the rolling result is published on the bar it was computed
    for. A `.shift(` breaks that assumption and makes the guess wrong by exactly the shift, so the
    guess is withheld. Same rule as the old builder -- DonchianChannel is the case that exposed it.
    """
    src = inspect.getsource(cls)
    found = sorted({m for m in re.findall(r"min_periods\s*=\s*([A-Za-z_]\w*|\d+)", src)})
    if ".shift(" in src:
        return None
    return f"{found[0]} - 1" if len(found) == 1 else None


def build_indicator(cls, *, params: dict) -> dict:
    """One indicator atom, exactly as the graph stores it.

    `params` (types, defaults, min/max) still comes from the caller: it is resolved from the
    docstrings of the SIGNALS that wrap this indicator, by AST call-graph, and that resolution is
    unchanged and not this function's business.
    """
    authored = parse_authored(inspect.getdoc(cls))
    if authored["kind"] != "Indicator":
        raise ValueError(f"{cls.__name__}: docstring declares {authored['kind']}, not Indicator")
    if authored["name"] != cls.__name__:
        raise ValueError(
            f"docstring on {cls.__name__} declares '{authored['name']}' -- attached to the wrong class?")

    inputs = {k: {"type": "series", "description": authored["inputs"][k]} for k in cls._data}
    outputs = {}
    for key in cls._outputs:
        spec = authored["outputs"][key]
        outputs[key] = {"type": "series", "units": spec["units"], "range": spec["range"],
                        "canonical_name": spec["canonical_name"],
                        "description": spec["description"]}

    return {
        "id": f"procedure:indicator-{cls.__name__.lower()}",
        "title": cls.__name__,
        "kind": "Procedure",
        "summary": authored["summary"],
        "epistemic": "observed",
        "status": "ratified",
        "props": {
            "source_module": cls.__module__.rsplit(".", 1)[-1],
            "reference": authored.get("reference"),
            "warmup_bars": warmup_bars(cls),
            "abbreviation": authored.get("abbreviation"),
            "usage_example": usage_example(cls),
            "formula": authored.get("formula"),
            "interpretation": authored.get("interpretation"),
            "applications": authored.get("applications"),
            "inputs": inputs,
            "params": params,
            "outputs": outputs,
        },
    }


def signal_usage_example(name: str, params: dict) -> str:
    """The registered call, generated from the name and the resolved parameter keys."""
    inner = ", ".join(f"'{p}': value" for p in params)
    return f"RuleRegistry.evaluate({{'name': '{name}', 'params': {{{inner}}}}}, df)"


def build_signal(func, *, params: dict, source_module: str, warmup: str | None,
                 status: str = "ratified") -> dict:
    """One signal atom.

    `params`, `warmup` and the `uses` edges all come from the AST call-graph, not from here. A
    signal's warmup is a property of the indicator it reads -- a state signal inherits it unchanged,
    a crossing costs exactly one bar more -- so it cannot be known from this docstring alone, and
    authoring it here would let the docstring contradict the code."""
    authored = parse_authored(inspect.getdoc(func))
    if authored["kind"] != "Signal":
        raise ValueError(f"{func.__name__}: docstring declares {authored['kind']}, not Signal")

    outputs = {k: {"type": "bool", "units": v["units"], "range": v["range"],
                   "canonical_name": v["canonical_name"], "description": v["description"]}
               for k, v in authored["outputs"].items()}
    return {
        "id": f"procedure:signal-{authored['name'].replace('_', '-')}",
        "title": authored["name"],
        "kind": "Procedure",
        "summary": authored["summary"],
        "epistemic": "observed",
        "status": status,
        "props": {
            "source_module": source_module,
            "reference": authored.get("reference"),
            "warmup_bars": warmup,
            "abbreviation": authored.get("abbreviation"),
            "usage_example": signal_usage_example(authored["name"], params),
            "formula": authored.get("formula"),
            "inputs": {k: {"type": "series", "description": v}
                       for k, v in authored.get("inputs", {}).items()},
            "params": params,
            "outputs": outputs,
        },
    }


if __name__ == "__main__":
    import json
    from mangrove_kb import indicators
    name = sys.argv[1] if len(sys.argv) > 1 else "BollingerBands"
    cls = getattr(indicators, name)
    print(json.dumps(build_indicator(cls, params={}), indent=1))
