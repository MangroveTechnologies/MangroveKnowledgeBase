"""The SuperTrend and PSAR signals decide exactly what the deprecated verdict indicators decided.

`SuperTrend` emits a `direction` verdict and `PSAR` emits its level beside two flip flags; the
ontology excludes both because an indicator states what it measured and deciding what that means
is the signal layer's job. `SuperTrendBands` and `ParabolicSAR` emit the measurements only, and
the seven signals that read them now make the decision themselves. This proves the split changed
nothing a consumer can observe:

1. The measurement is the one the verdict was drawn from. The regime the signals reconstruct from
   `SuperTrendBands` equals `SuperTrend.direction` on every bar, and `ParabolicSAR.psar` equals
   `PSAR.psar` on every bar the recursion defines, across all seven fixtures.
2. Each signal, evaluated the way a strategy evaluates it -- on a window ending at each bar --
   returns the same boolean as the verdict indicator's own output read the way the old signal
   read it. Sliding windows over every fixture, asset and timeframe.

The deprecated classes are the reference because they ARE the old implementation: each old
signal was a two-line comparison over one of their outputs, restated verbatim in `OLD` below.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.indicators import PSAR, ParabolicSAR, SuperTrend, SuperTrendBands
from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals.volatility import _supertrend_regime

DATA = Path(__file__).resolve().parent.parent / "data"
FIXTURES = sorted(p.name for p in DATA.glob("*.csv"))

ST_PARAMS = {"window": 10, "multiplier": 3.0}
PSAR_PARAMS = {"step": 0.02, "max_step": 0.2}

#: Sliding-window evaluation: `WINDOW` bars ending at each of the last `OFFSETS` bars of a fixture.
#: A strategy evaluates a signal on the bars it has so far, so each window is one real evaluation.
WINDOW, OFFSETS = 256, 60


def _old_supertrend(sub):
    return SuperTrend.compute(
        {"high": sub["high"], "low": sub["low"], "close": sub["close"]}, ST_PARAMS)["direction"]


def _old_psar(sub):
    return PSAR.compute(
        {"high": sub["high"], "low": sub["low"], "close": sub["close"]}, PSAR_PARAMS)["psar"]


#: The old signals, as they read the verdict indicators. Each is the old function body minus the
#: indicator call, so a divergence here is a divergence from what shipped.
OLD = {
    "supertrend_long": lambda sub: bool(_old_supertrend(sub).iloc[-1] == 1),
    "supertrend_short": lambda sub: bool(_old_supertrend(sub).iloc[-1] == -1),
    "supertrend_flip_up": lambda sub: (lambda d: bool(d.iloc[-2] == -1 and d.iloc[-1] == 1))(_old_supertrend(sub)),
    "supertrend_flip_down": lambda sub: (lambda d: bool(d.iloc[-2] == 1 and d.iloc[-1] == -1))(_old_supertrend(sub)),
    "psar_bullish": lambda sub: bool(_old_psar(sub).iloc[-1] < sub["close"].iloc[-1]),
    "psar_bearish": lambda sub: bool(_old_psar(sub).iloc[-1] > sub["close"].iloc[-1]),
    "psar_reversal": lambda sub: (lambda p, c: bool(p.iloc[-2] > c.iloc[-2] and p.iloc[-1] < c.iloc[-1]))(
        _old_psar(sub), sub["close"]),
}
NEW_PARAMS = {n: dict(ST_PARAMS) for n in OLD if n.startswith("supertrend")}
NEW_PARAMS.update({n: dict(PSAR_PARAMS) for n in OLD if n.startswith("psar")})


@pytest.fixture(scope="module", params=FIXTURES)
def bars(request):
    df = pd.read_csv(DATA / request.param)
    df.columns = [c.lower() for c in df.columns]
    assert len(df) > WINDOW + OFFSETS, request.param
    return df


def test_the_seven_fixtures_span_assets_and_timeframes():
    assert len(FIXTURES) == 7
    timeframes = {name.rsplit("_", 1)[-1].removesuffix(".csv") for name in FIXTURES}
    assert len(timeframes) >= 5, timeframes


def test_supertrend_regime_equals_the_deprecated_direction_on_every_bar(bars):
    old = _old_supertrend(bars).to_numpy()
    new = _supertrend_regime(bars, **ST_PARAMS).to_numpy()
    assert len(new) == len(bars)
    assert np.array_equal(np.isnan(old), np.isnan(new)), "warmup differs"
    defined = ~np.isnan(old)
    assert defined.sum() == len(bars) - ST_PARAMS["window"]
    assert np.array_equal(old[defined], new[defined])


def test_parabolic_sar_level_equals_the_deprecated_level_on_every_defined_bar(bars):
    data = {"high": bars["high"], "low": bars["low"], "close": bars["close"]}
    old = PSAR.compute(data, PSAR_PARAMS)["psar"].to_numpy()
    new = ParabolicSAR.compute(data, PSAR_PARAMS)["psar"].to_numpy()
    # PSAR carries close[0] and close[1] in its first two slots as the recursion's seed rather
    # than as a computed level; ParabolicSAR leaves them undefined. From bar 2 the level is the
    # same float on every bar.
    assert np.isnan(new[:2]).all() and np.isfinite(new[2:]).all()
    assert np.array_equal(old[2:], new[2:])


def test_supertrend_bands_are_the_bands_supertrend_ratchets(bars):
    """The level SuperTrend publishes is one of these two bands, held in the regime's favour: never
    below the basic lower band while long, never above the basic upper band while short, and equal
    to the basic band on the bar the regime changes, where nothing has been held yet. So the ratchet
    and the regime are what the signals add; the bands are what the indicator measures."""
    data = {"high": bars["high"], "low": bars["low"], "close": bars["close"]}
    bands = SuperTrendBands.compute(data, ST_PARAMS)
    upper, lower = bands["upper_band"], bands["lower_band"]
    assert np.isnan(upper.to_numpy()[: ST_PARAMS["window"] - 1]).all()
    assert (upper >= lower).loc[upper.notna()].all()
    old = SuperTrend.compute(data, ST_PARAMS)
    level, direction = old["supertrend"], old["direction"]
    assert (level >= lower).loc[direction == 1].all()
    assert (level <= upper).loc[direction == -1].all()
    flipped = (direction != direction.shift(1)) & direction.notna() & direction.shift(1).notna()
    assert flipped.sum() > 0
    assert ((level == lower) | (level == upper)).loc[flipped].all()


@pytest.mark.parametrize("name", sorted(OLD))
def test_signal_agrees_with_the_verdict_indicator_on_sliding_windows(bars, name):
    n = len(bars)
    disagreements = []
    fired = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for k in range(OFFSETS):
            sub = bars.iloc[n - WINDOW - k: n - k]
            expected = OLD[name](sub)
            got = RuleRegistry.evaluate({"name": name, "params": NEW_PARAMS[name]}, sub)
            assert got in (True, False)
            fired += got
            if got != expected:
                disagreements.append((k, got, expected))
    assert disagreements == [], f"{name}: {len(disagreements)} of {OFFSETS} windows differ"


def test_the_regime_signals_fire_on_the_fixtures():
    """Agreement is vacuous if neither side ever fires; the filters fire on roughly half of all
    bars and each trigger fires at least once across the corpus."""
    counts = {n: 0 for n in OLD}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for fixture in FIXTURES:
            df = pd.read_csv(DATA / fixture)
            df.columns = [c.lower() for c in df.columns]
            regime = _supertrend_regime(df, **ST_PARAMS)
            counts["supertrend_long"] += int((regime == 1).sum())
            counts["supertrend_short"] += int((regime == -1).sum())
            counts["supertrend_flip_up"] += int(((regime.shift(1) == -1) & (regime == 1)).sum())
            counts["supertrend_flip_down"] += int(((regime.shift(1) == 1) & (regime == -1)).sum())
            level = ParabolicSAR.compute(
                {"high": df["high"], "low": df["low"], "close": df["close"]}, PSAR_PARAMS)["psar"]
            below, above = level < df["close"], level > df["close"]
            counts["psar_bullish"] += int(below.sum())
            counts["psar_bearish"] += int(above.sum())
            counts["psar_reversal"] += int((above.shift(1, fill_value=False) & below).sum())
    assert all(v > 0 for v in counts.values()), counts
    assert counts["supertrend_flip_up"] > 100 and counts["psar_reversal"] > 100, counts
