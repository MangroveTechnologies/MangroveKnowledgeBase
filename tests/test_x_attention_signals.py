"""X attention signals: fire at their declared warmup with default params, fail closed on flat or missing counts."""

import ast
import inspect

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.docstring_parser import parse_authored, parse_signal_docstring
from mangrove_kb.graph import KnowledgeGraph
from mangrove_kb.indicators import SocialZScore
from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import social

SIGNALS = {
    "x_post_count_spike": social.x_post_count_spike,
    "x_attention_elevated": social.x_attention_elevated,
    "x_attention_price_divergence": social.x_attention_price_divergence,
}
TYPES = {"x_post_count_spike": "TRIGGER", "x_attention_elevated": "FILTER", "x_attention_price_divergence": "TRIGGER"}
ZSCORE_SIGNALS = ["x_post_count_spike", "x_attention_price_divergence"]
#: `Warmup:` at the default params: bars discarded before the first bar a signal can decide on.
WARMUP_AT_DEFAULTS = {"x_post_count_spike": 48, "x_attention_elevated": 77, "x_attention_price_divergence": 72}


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


def _defaults(fn):
    return {k: p.default for k, p in inspect.signature(fn).parameters.items()
            if p.default is not inspect.Parameter.empty}


def _warmup_bars(fn):
    """The docstring's `Warmup:` expression, evaluated at the signal's default params."""
    expr = parse_authored(fn.__doc__)["warmup"]
    tree = ast.parse(expr, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Name, ast.Constant, ast.Load)
    assert all(isinstance(node, allowed) for node in ast.walk(tree)), expr
    return int(eval(compile(tree, "<warmup>", "eval"), {"__builtins__": {}}, _defaults(fn)))


def _frame(counts, close=None, column="XPostCount"):
    n = len(counts)
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"close": close if close is not None else np.full(n, 100.0),
                         column: np.asarray(counts, dtype=float)}, index=idx)


def _varied(n, seed=0):
    """Integer counts drawn from 8..12, so the baseline has spread."""
    return list(np.random.default_rng(seed).integers(8, 13, n))


def _falling(n):
    """Close flat at 100, then down 10% over the last 25 bars (24-bar ROC = -10%)."""
    close = np.full(n, 100.0)
    close[-25:] = np.linspace(100.0, 90.0, 25)
    return close


def _firing(name, bars):
    """A frame of exactly `bars` rows whose last bar meets the signal's default thresholds."""
    if name == "x_post_count_spike":
        return _frame(_varied(bars - 1) + [500])
    if name == "x_attention_elevated":
        return _frame([10] * (bars - 6) + [20] * 6)
    return _frame(_varied(bars - 1) + [500], close=_falling(bars))


def test_registered_with_types_and_input():
    assert set(SIGNALS) <= RuleRegistry.names()
    for name, fn in SIGNALS.items():
        meta = parse_signal_docstring(fn)
        assert meta["type"] == TYPES[name]
        assert "XPostCount" in meta["requires"]


@pytest.mark.parametrize("name", SIGNALS)
def test_warmup_expression_parses_and_matches_the_graph(name, kg):
    fn = SIGNALS[name]
    assert kg.get(name)["warmup_bars"] == parse_authored(fn.__doc__)["warmup"]
    assert _warmup_bars(fn) == WARMUP_AT_DEFAULTS[name]


@pytest.mark.parametrize("name", SIGNALS)
def test_fires_on_the_first_bar_after_warmup_and_not_before(name):
    fn = SIGNALS[name]
    bars = _warmup_bars(fn)
    assert fn(_firing(name, bars + 1)) is True
    assert fn(_firing(name, bars)) is False


@pytest.mark.parametrize("name", SIGNALS)
def test_flat_counts_never_fire(name):
    fn = SIGNALS[name]
    assert fn(_frame([50] * 200, close=_falling(200))) is False


@pytest.mark.parametrize("name", ZSCORE_SIGNALS)
def test_a_spike_on_a_flat_baseline_is_undefined(name):
    fn = SIGNALS[name]
    bars = _warmup_bars(fn) + 1
    assert fn(_frame([50] * (bars - 1) + [5000], close=_falling(bars))) is False
    assert fn(_frame(_varied(bars - 1) + [5000], close=_falling(bars))) is True


@pytest.mark.parametrize("name", SIGNALS)
def test_reads_xpostcount_only(name):
    fn = SIGNALS[name]
    df = _firing(name, _warmup_bars(fn) + 1)
    assert fn(df) is True
    assert RuleRegistry.evaluate({"name": name}, df) is True
    assert fn(df.rename(columns={"XPostCount": "x_post_count"})) is False
    assert fn(df.drop(columns="XPostCount")) is False


@pytest.mark.parametrize("name", SIGNALS)
def test_a_gap_inside_the_window_fails_closed(name):
    fn = SIGNALS[name]
    df = _firing(name, _warmup_bars(fn) + 1)
    df.iloc[len(df) // 2, df.columns.get_loc("XPostCount")] = np.nan
    assert fn(df) is False


def test_zscore_baseline_flat_within_tolerance_is_undefined():
    v = pd.Series(np.log1p([1000.0] * 72 + [10000.0]))
    noisy = v.copy()
    noisy.iloc[3] += 1e-15
    for series in (v, noisy):
        assert pd.isna(SocialZScore.compute(data={"value": series}, params={"window": 72})["zscore"].iloc[-1])
    distinct = v.copy()
    distinct.iloc[3] = np.log1p(1001.0)
    z = SocialZScore.compute(data={"value": distinct}, params={"window": 72})["zscore"].iloc[-1]
    assert np.isfinite(z) and z > 3
