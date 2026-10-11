"""`mass_reversal_signal` is a TRIGGER, so it fires on one bar per reversal.

Corresponds to MangroveTechnologies/MangroveKnowledgeBase#150. The condition it
tests, a Mass Index spike above the upper threshold within the last ten bars
followed by a fall back below the lower one, stays satisfied for as long as the
spike sits inside that lookback, and longer if the index crosses back above
meanwhile. Reporting it on every such bar makes one reversal look like a state
that is true for a long stretch. Measured over 48 charts before the fix, it
averaged 4.99 true bars per run and reached 118.

Usage:
    pytest tests/test_mass_reversal_fires_on_the_edge.py -v
"""

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.indicators.trend_indicators import MassIndex
from mangrove_kb.signals.momentum import mass_reversal_signal

PARAMS = dict(window_fast=9, window_slow=25, threshold_high=27.0, threshold_low=26.5)


def _frame(n=400, seed=7):
    """A price series whose Mass Index crosses both thresholds repeatedly."""
    rng = np.random.default_rng(seed)
    base = 100 + np.cumsum(rng.normal(0, 1.0, n))
    # Widen and narrow the bar range in waves, which is what the Mass Index reads.
    width = 1.0 + 3.0 * (1 + np.sin(np.linspace(0, 12 * np.pi, n))) / 2
    high = base + width
    low = base - width
    return pd.DataFrame(
        {"open": base, "high": high, "low": low, "close": base,
         "volume": np.full(n, 1000.0)},
        index=pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC"),
    )


def _states(df):
    """The signal at every bar, as the sweep evaluates it."""
    return np.array([bool(mass_reversal_signal(df.iloc[: i + 1], **PARAMS))
                     for i in range(len(df))])


def _underlying_condition(df):
    """The condition the signal tests, without the edge, at every bar."""
    mi = MassIndex.compute(data={"high": df["high"], "low": df["low"]},
                           params={"window_fast": PARAMS["window_fast"],
                                   "window_slow": PARAMS["window_slow"]})["mass_index"]
    out = []
    for i in range(len(df)):
        last = mi.iloc[i]
        if pd.isna(last) or float(last) >= PARAMS["threshold_low"]:
            out.append(False)
            continue
        recent = mi.iloc[max(0, i - 9): i + 1]
        out.append(any(float(v) > PARAMS["threshold_high"]
                       for v in recent if not pd.isna(v)))
    return np.array(out)


@pytest.fixture(scope="module")
def series():
    df = _frame()
    state = _underlying_condition(df)
    if not state.any():
        pytest.skip("the synthetic series produced no bulge to test")
    return df, _states(df), state


def test_it_never_stays_true_for_two_bars_in_a_row(series):
    _, fired, _ = series
    assert not (fired[1:] & fired[:-1]).any(), (
        "a TRIGGER fires on one bar; consecutive true bars mean it reports a state"
    )


def test_it_fires_exactly_once_per_reversal(series):
    _, fired, state = series
    starts = state & ~np.concatenate(([False], state[:-1]))
    assert int(fired.sum()) == int(starts.sum())


def test_it_only_fires_where_the_condition_holds(series):
    _, fired, state = series
    assert bool((fired <= state).all())


def test_the_condition_itself_still_persists(series):
    """The control: the underlying state does last several bars.

    Without this, the three tests above would pass on a signal that never fires
    at all, which is the other way to make them true.
    """
    _, _, state = series
    longest = 0
    run = 0
    for v in state:
        run = run + 1 if v else 0
        longest = max(longest, run)
    assert longest > 1, "the fixture no longer exercises the defect"
