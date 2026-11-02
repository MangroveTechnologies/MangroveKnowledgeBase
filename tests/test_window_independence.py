"""A signal's answer on a bar does not depend on how many earlier bars it was handed.

A strategy evaluates each rule on a rolling window ending at the current bar, and the window is as
long as the LONGEST warmup among all of the strategy's rules. So a signal whose answer moves with
the window's length changes when an unrelated rule is added to the strategy. MangroveAI's backtest
engine computes every indicator once over the whole series and serves each bar a slice of it
(`signal_hoist`), so anything an indicator computes is window-independent there. What it cannot
reach is state a signal builds itself over the window it is handed: `supertrend_long` deciding the
regime in a loop over the window measured 51 of 198 BTC daily bars different between a 16-bar
window and the whole history, and halved an RSI + SuperTrend strategy's trade count when a
never-firing 60-bar exit rule was added.

`test_whole_series_indicators_leave_nothing_window_dependent` is that engine, reduced to the part
that matters: indicators served from the whole series, each signal then evaluated on a window of
exactly its declared requirement, on a longer one, and on the whole prefix. They must agree.

`test_the_declared_warmup_covers_what_the_signal_reads` pins the Warmup lines that were too short
for the indicator the signal reads: at exactly Warmup + 1 bars, the output it reads is defined on
every bar it reads.
"""
import ast
import inspect
import math
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import mangrove_kb.signals  # noqa: F401  (registers every signal)
from mangrove_kb.docstring_parser import DocstringFormatError, parse_authored
from mangrove_kb.indicators import DEMA, HMA, STC, TEMA, MassIndex, StochRSI
from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.registry import RuleRegistry

DATA = Path(__file__).resolve().parent.parent / "data"
OHLCV = {"open", "high", "low", "close", "volume"}

#: The four RSI divergence signals hand `SwingDelta` an RSI series, not a raw column, so even the
#: engine computes that step over the window. Swing detection near the window's first bar can then
#: differ (1 bar of 775 on the ETH 4h fixture). Known and left as is; listed so a new case is not.
DERIVED_INPUT = {"rsi_bearish_divergence", "rsi_bullish_divergence",
                 "rsi_hidden_bearish_divergence", "rsi_hidden_bullish_divergence"}


def _bars():
    return pd.read_csv(DATA / "btc_2022-08-01_2026-02-15_1d.csv")[sorted(OHLCV)].astype(float)


def _defaults(fn):
    return {k: p.default for k, p in inspect.signature(fn).parameters.items()
            if p.default is not inspect.Parameter.empty}


def _warmup(fn, params=None):
    """The docstring's `Warmup:` at the given params (defaults fill the rest); the grammar the
    engines evaluate: names, numbers, + - * / //, max and min."""
    expr = parse_authored(fn.__doc__)["warmup"]
    env = {**_defaults(fn), **(params or {})}
    tree = ast.parse(expr, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
               ast.Name, ast.Constant, ast.Load, ast.Call, ast.UnaryOp, ast.USub)
    assert all(isinstance(node, allowed) for node in ast.walk(tree)), expr
    # Safe: the tree was just checked to hold only arithmetic over names and numbers, and the
    # expression is our own docstring, evaluated with no builtins beyond max and min.
    value = eval(compile(tree, "<warmup>", "eval"), {"__builtins__": {}, "max": max, "min": min}, env)
    return int(math.ceil(value))


@contextmanager
def _whole_series(full):
    """Serve every indicator call whose inputs are a window of `full` from one computation over
    the whole of `full`, sliced to that window -- what MangroveAI's backtest engine does."""
    original = IndicatorInterface.compute.__func__
    cache = {}

    def compute(cls, data, params):
        first = next(iter(data.values()))
        idx = first.index
        a, b = int(idx[0]), int(idx[-1])
        view = all(k in full and isinstance(v, pd.Series) and len(v) == b - a + 1
                   and v.iloc[-1] == full[k].iloc[b] for k, v in data.items())
        if not view:
            return original(cls, data, params)
        key = (cls.__name__, repr(sorted(params.items())), tuple(sorted(data)))
        if key not in cache:
            cache[key] = original(cls, {k: full[k] for k in data}, params)
        return {k: v.iloc[a:b + 1] if isinstance(v, pd.Series) else v for k, v in cache[key].items()}

    IndicatorInterface.compute = classmethod(compute)
    try:
        yield
    finally:
        IndicatorInterface.compute = classmethod(original)


def _ohlcv_signals():
    out = []
    for name in sorted(RuleRegistry.names()):
        fn = RuleRegistry._registry[name]
        if getattr(fn, "runtime_disabled", False):
            continue
        try:
            authored = parse_authored(fn.__doc__)
        except DocstringFormatError:
            continue  # the deprecated atr_trailing_stop_* signals: no Warmup line to hold them to
        described = RuleRegistry.describe(name)
        requires = {str(c).lower() for c in described.get("requires") or []}
        # `bars_per(...)` is a warmup counted in another timeframe's bars (multi_tf_trend_*), which
        # needs the bar size; one fixture has one.
        warmup = authored.get("warmup") or ""
        if (described.get("executable", True) and requires and requires <= OHLCV and warmup
                and "bars_per(" not in warmup):
            out.append(name)
    return out


def test_whole_series_indicators_leave_nothing_window_dependent():
    signals = _ohlcv_signals()
    assert len(signals) > 200, "the signal list came back nearly empty; the filter is broken"
    bars = _bars()
    full = {k: bars[k] for k in bars.columns}
    differ = {}
    with _whole_series(full):
        for name in signals:
            if name in DERIVED_INPUT:
                continue
            fn = RuleRegistry._registry[name]
            need = _warmup(fn) + 1
            rule = {"name": name, "params": {}}
            for end in range(max(need + 60, 400), len(bars), 23):
                answers = {bool(RuleRegistry.evaluate(rule, bars.iloc[end - n + 1:end + 1]))
                           for n in (need, need + 60, end + 1)}
                if len(answers) > 1:
                    differ.setdefault(name, []).append(end)
    assert not differ, ("answer depends on the window length (signal: first bars): "
                        + "; ".join(f"{k}: {v[:3]}" for k, v in sorted(differ.items())))


#: (signal, params, what it reads, bars back it reads). Each `read` returns the output series the
#: signal reads, computed on the window. The params include each range's maximum, where an
#: under-declared formula is furthest off.
READS = [
    ("is_above_dema", {"window": 21}, lambda d, p: DEMA.compute({"close": d["close"]}, p)["dema"], 1),
    ("is_above_dema", {"window": 200}, lambda d, p: DEMA.compute({"close": d["close"]}, p)["dema"], 1),
    ("is_above_tema", {"window": 21}, lambda d, p: TEMA.compute({"close": d["close"]}, p)["tema"], 1),
    ("is_above_tema", {"window": 100}, lambda d, p: TEMA.compute({"close": d["close"]}, p)["tema"], 1),
    ("is_above_hma", {"window": 16}, lambda d, p: HMA.compute({"close": d["close"]}, p)["hma"], 1),
    ("is_above_hma", {"window": 200}, lambda d, p: HMA.compute({"close": d["close"]}, p)["hma"], 1),
    ("dema_cross_up", {"window_fast": 9, "window_slow": 21},
     lambda d, p: DEMA.compute({"close": d["close"]}, {"window": p["window_slow"]})["dema"], 2),
    ("tema_cross_up", {"window_fast": 9, "window_slow": 50},
     lambda d, p: TEMA.compute({"close": d["close"]}, {"window": p["window_slow"]})["tema"], 2),
    ("hma_cross_up", {"window_fast": 9, "window_slow": 25},
     lambda d, p: HMA.compute({"close": d["close"]}, {"window": p["window_slow"]})["hma"], 2),
    ("hma_cross_up", {"window_fast": 20, "window_slow": 200},
     lambda d, p: HMA.compute({"close": d["close"]}, {"window": p["window_slow"]})["hma"], 2),
    ("stochrsi_overbought", {"window": 14},
     lambda d, p: StochRSI.compute({"close": d["close"]}, {"window": p["window"], "smooth1": 3,
                                                           "smooth2": 3})["stochrsi"], 1),
    ("stochrsi_overbought", {"window": 50},
     lambda d, p: StochRSI.compute({"close": d["close"]}, {"window": p["window"], "smooth1": 3,
                                                           "smooth2": 3})["stochrsi"], 1),
    ("mass_reversal_signal", {},
     lambda d, p: MassIndex.compute({"high": d["high"], "low": d["low"]},
                                    {"window_fast": 9, "window_slow": 25})["mass_index"], 10),
]


@pytest.mark.parametrize("name, params, read, back", READS,
                         ids=[f"{r[0]}-{'-'.join(map(str, r[1].values())) or 'defaults'}" for r in READS])
def test_the_declared_warmup_covers_what_the_signal_reads(name, params, read, back):
    bars = _bars()
    fn = RuleRegistry._registry[name]
    need = _warmup(fn, params) + 1
    for end in range(need + 5, len(bars), 97):
        window = bars.iloc[end - need + 1:end + 1]
        series = read(window, params)
        assert not series.iloc[-back:].isna().any(), (
            f"{name}{params}: Warmup gives {need} bars; the output it reads is NaN on its last {back}")


def test_stc_warmup_is_the_indicators_definition():
    """STC's signals read `stc`, defined from bar window_slow + 2 * cycle + smooth1 + smooth2 - 5 of a
    series. On a window that starts inside a one-way move it can stay NaN longer -- the stochastic of
    a flat range is 0/0 -- so this is pinned on the whole series, where only the definition counts."""
    close = _bars()["close"]
    for params in ({"window_slow": 50, "window_fast": 23, "cycle": 10, "smooth1": 3, "smooth2": 3},
                   {"window_slow": 80, "window_fast": 30, "cycle": 20, "smooth1": 5, "smooth2": 2}):
        stc = STC.compute({"close": close}, params)["stc"]
        assert stc.first_valid_index() <= _warmup(RuleRegistry._registry["stc_overbought"], params)


def test_supertrend_reads_the_whole_series_regime():
    """The four SuperTrend signals read `SuperTrendTrail`, so a window that is a slice of the whole
    series answers exactly as the whole series does, at any length."""
    bars = _bars()
    full = {k: bars[k] for k in bars.columns}
    from mangrove_kb.indicators import SuperTrendTrail
    regime = SuperTrendTrail.compute({"high": bars["high"], "low": bars["low"], "close": bars["close"]},
                                     {"window": 10, "multiplier": 3.0})["regime"]
    with _whole_series(full):
        for end in range(300, len(bars), 7):
            for n in (12, 16, 63, 300):
                window = bars.iloc[end - n + 1:end + 1]
                assert RuleRegistry.evaluate({"name": "supertrend_long"}, window) == (regime.iloc[end] == 1)
                assert RuleRegistry.evaluate({"name": "supertrend_short"}, window) == (regime.iloc[end] == -1)


def test_supertrend_warmup_picks_up_the_regime():
    """`Warmup: max(60, window)` gives a trail started late enough bars to find the current regime:
    on BTC daily bars at the defaults it disagrees with the whole-series trail on under 3% of days
    (13 of 894 measured; at the old 17 bars it was 355). Only the live path, which has no whole
    series, reads a late-started trail."""
    from mangrove_kb.indicators import SuperTrendTrail
    bars = _bars()
    params = {"window": 10, "multiplier": 3.0}
    need = _warmup(RuleRegistry._registry["supertrend_long"], params) + 1
    data = {k: bars[k] for k in ("high", "low", "close")}
    whole = SuperTrendTrail.compute(data, params)["regime"]
    ends = range(400, len(bars))
    late = [SuperTrendTrail.compute({k: v.iloc[e - need + 1:e + 1] for k, v in data.items()},
                                    params)["regime"].iloc[-1] for e in ends]
    differ = sum(a != whole.iloc[e] for a, e in zip(late, ends))
    assert differ / len(ends) < 0.03, f"{differ} of {len(ends)} days"
