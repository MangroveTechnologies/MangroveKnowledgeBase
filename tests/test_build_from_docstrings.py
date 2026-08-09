"""The new builder must reproduce the committed graph exactly.

`build_from_docstrings` reads authored values from the docstring alone -- no carry-forward from the
previous JSON, no `knowledge-base/*.md`. The proof that the move is lossless is that its output is
byte-identical to what the old builder produced, node for node.

Two nodes are converted so far (BollingerBands and bb_above_upper). Each additional conversion adds
its id to CONVERTED, and this test proves it before the next one starts.
"""
import json
from pathlib import Path

import pytest

from mangrove_kb import indicators
from mangrove_kb.signals.volatility import bb_above_upper
from ontology.build_from_docstrings import build_indicator, build_signal

GRAPH = Path(__file__).resolve().parent.parent / "ontology" / "signal-indicator-ontology.json"


@pytest.fixture(scope="module")
def committed():
    return {a["id"]: a for a in json.loads(GRAPH.read_text())["atoms"]}


def _diff(got, want, path=""):
    """Every differing leaf, with its path -- so a failure names the field, not just 'not equal'."""
    out = []
    if isinstance(got, dict) and isinstance(want, dict):
        for key in sorted(set(got) | set(want)):
            out += _diff(got.get(key), want.get(key), f"{path}.{key}" if path else key)
    elif got != want:
        out.append((path, got, want))
    return out


def test_indicator_node_is_reproduced_exactly(committed):
    want = committed["procedure:indicator-bollingerbands"]
    # `params` is resolved by the AST call-graph from the signals that wrap this indicator; that
    # resolution is unchanged and is not what this builder is responsible for.
    got = build_indicator(indicators.BollingerBands, params=want["props"]["params"])
    assert not (d := _diff(got, want)), "\n".join(
        f"{p}\n  new builder: {a!r}\n  committed  : {b!r}" for p, a, b in d)


def test_signal_node_is_reproduced_exactly(committed):
    want = committed["procedure:signal-bb-above-upper"]
    got = build_signal(bb_above_upper, params=want["props"]["params"],
                       source_module=want["props"]["source_module"],
                       warmup=want["props"]["warmup_bars"])
    assert not (d := _diff(got, want)), "\n".join(
        f"{p}\n  new builder: {a!r}\n  committed  : {b!r}" for p, a, b in d)


def test_it_reads_the_docstring_and_not_the_previous_graph(committed):
    """The point of the exercise. Change the docstring, the output must change with it.

    If this passes while the summary is edited, the builder is reading the old JSON somewhere and
    the carry-forward has not actually been escaped.
    """
    cls = indicators.BollingerBands
    original = cls.__doc__
    try:
        cls.__doc__ = original.replace(
            "Volatility bands placed above and below a moving average",
            "SENTINEL rewritten summary", 1)
        got = build_indicator(cls, params={})
        assert got["summary"].startswith("SENTINEL rewritten summary"), \
            "the builder ignored the docstring -- it is still reading a carried-forward value"
    finally:
        cls.__doc__ = original


def test_a_docstring_on_the_wrong_class_is_rejected():
    """The declared name is an assertion, not decoration."""
    cls = indicators.BollingerBands
    original = cls.__doc__
    try:
        cls.__doc__ = original.replace("Indicator: BollingerBands", "Indicator: KeltnerChannel", 1)
        with pytest.raises(ValueError, match="attached to the wrong class"):
            build_indicator(cls, params={})
    finally:
        cls.__doc__ = original


def test_kind_mismatch_is_rejected():
    """Declaring an indicator as a Signal must not build.

    Two guards can catch this and either is correct: the parser rejects the indicator-only sections
    a Signal may not carry, and `build_indicator` rejects the kind. `DocstringFormatError` subclasses
    `ValueError`, so this asserts the outcome rather than pinning which fires first -- pinning it
    would make the test fail if the guards are ever reordered, which is not a regression.
    """
    cls = indicators.BollingerBands
    original = cls.__doc__
    try:
        cls.__doc__ = original.replace("Indicator: BollingerBands", "Signal: BollingerBands", 1)
        with pytest.raises(ValueError):
            build_indicator(cls, params={})
    finally:
        cls.__doc__ = original
