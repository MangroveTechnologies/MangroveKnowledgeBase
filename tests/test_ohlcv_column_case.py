"""OHLCV column case is canonically lowercase, and capitalised frames still work.

The library used to contradict itself: indicators took lowercase dict keys (`ATR._data` is
`['high', 'low', 'close']`, `ATR.compute` reads `data['high']`) while signals read `df["High"]` off
the frame. The knowledge graph could only publish one of those, published lowercase, and so told
every consumer to build a frame that raised `KeyError: 'High'` on 211 of 218 signals.

Found by installing the wheel and using it as a new consumer would -- not by any test in this suite,
because every test here built its frames the way the code already wanted them.
"""
import inspect

import pandas as pd
import pytest

from mangrove_kb import RuleRegistry, sample_ohlcv
from mangrove_kb.graph import KnowledgeGraph
from mangrove_kb.registry import OHLCV, _canonical_columns


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


@pytest.fixture(scope="module")
def frames():
    """The same bars, spelled three ways."""
    lower = sample_ohlcv()
    return {
        "lowercase": lower,
        "capitalised": lower.rename(columns=str.title),
        "mixed": lower.rename(columns={"high": "High", "volume": "VOLUME"}),
    }


def _runnable(kg):
    """Every graph signal that resolves to a registered function, with arguments it will accept.

    A handful of signals take a parameter the signature leaves required and the graph gives no
    default for -- `ema_crossover(window_fast, window_slow)`. The graph's declared `min` stands in,
    since the value is irrelevant here: the question is which column names the frame must use.
    """
    for node in kg.nodes.values():
        if not node.id.startswith("procedure:signal-"):
            continue
        fn = RuleRegistry._registry.get(node.name)
        if fn is None:
            continue
        declared = node.props.get("params") or {}
        kwargs = {k: v["default"] for k, v in declared.items() if v.get("default") is not None}
        required = [p for p in list(inspect.signature(fn).parameters.values())[1:]
                    if p.default is inspect.Parameter.empty
                    and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                    and p.name not in kwargs]
        if any(declared.get(p.name, {}).get("min") is None for p in required):
            continue                       # cannot construct a call; not what this test is about
        kwargs.update({p.name: declared[p.name]["min"] for p in required})
        yield node, fn, kwargs


def test_sample_data_is_lowercase():
    assert list(sample_ohlcv().columns) == list(OHLCV)


def test_the_graph_states_the_case_the_code_requires(kg, frames):
    """The regression itself: build the frame the graph asks for, and every signal must run."""
    lower = frames["lowercase"]
    failures = []
    for node, fn, params in _runnable(kg):
        declared = set(node.props.get("inputs") or {})
        if not declared <= set(lower.columns):
            continue                       # on-chain signals need series this frame does not carry
        try:
            fn(lower, **params)
        except Exception as e:             # noqa: BLE001 -- collect them all, report the count
            failures.append(f"{node.name}: {type(e).__name__}: {e}")
    assert not failures, (f"{len(failures)} signals reject the columns the graph declares, e.g.\n  "
                          + "\n  ".join(failures[:5]))


def test_capitalised_and_mixed_frames_give_identical_answers(kg, frames):
    """Accepting capitalised input is a rename at the boundary, not a second code path."""
    ran = 0
    for node, fn, params in _runnable(kg):
        if not set(node.props.get("inputs") or {}) <= set(frames["lowercase"].columns):
            continue
        want = fn(frames["lowercase"], **params)
        for label in ("capitalised", "mixed"):
            got = fn(frames[label], **params)
            if isinstance(want, pd.Series):
                assert got.equals(want), f"{node.name} differs on a {label} frame"
            else:
                assert got == want, f"{node.name}: {label} gave {got!r}, lowercase gave {want!r}"
        ran += 1
    assert ran > 200, f"expected the whole library exercised, only ran {ran}"


def test_only_ohlcv_columns_are_touched():
    """Lowercasing the whole frame would silently rewrite a caller's own columns.

    SwingDelta reads a companion indicator column; `MyIndicator` quietly becoming `myindicator`
    would be a data bug introduced by a convenience.
    """
    df = pd.DataFrame({"Close": [1.0], "MyIndicator": [2.0], "WhaleNetInflow": [3.0]})
    out = _canonical_columns(df)
    assert list(out.columns) == ["close", "MyIndicator", "WhaleNetInflow"]


def test_a_frame_holding_both_spellings_is_left_alone():
    """Renaming `Close` onto an existing `close` would drop a column. Ambiguity is not ours to resolve."""
    df = pd.DataFrame({"Close": [1.0], "close": [2.0]})
    out = _canonical_columns(df)
    assert list(out.columns) == ["Close", "close"]


def test_the_declared_input_vocabulary_is_lowercase_ohlcv(kg):
    """`find(requires=...)` filters on this; a capitalised entry would make it miss."""
    declared = {c for n in kg.nodes.values() for c in (n.props.get("inputs") or {})}
    price = {c for c in declared if c.lower() in OHLCV}
    assert price == set(OHLCV) - {"open"} | {"open"}, sorted(price)
    assert all(c.islower() for c in price), sorted(c for c in price if not c.islower())
