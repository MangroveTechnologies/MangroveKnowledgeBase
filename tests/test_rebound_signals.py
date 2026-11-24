"""Coverage for the new seeded measurements and causal rule boundaries."""
import numpy as np
import pandas as pd

from mangrove_kb import RuleRegistry
from mangrove_kb.indicators import SMASeededRSI, WeightedATR
import mangrove_kb.signals  # noqa: F401 -- register frame-based signals


def _ranges(widths):
    width = pd.Series(widths, dtype=float)
    return pd.DataFrame({"high": 100 + width / 2, "low": 100 - width / 2, "close": 100.0})


def test_seeded_rsi_uses_a_full_window_of_price_changes():
    close = pd.Series([100.0, 102.0, 101.0, 104.0, 103.0], index=pd.date_range("2026-01-01", periods=5))
    rsi = SMASeededRSI.compute({"close": close}, {"window": 3})["rsi"]
    assert rsi.index.equals(close.index)
    assert rsi.iloc[:3].isna().all()
    np.testing.assert_allclose(rsi.iloc[3:], [100 * 5 / 6, 100 * 2 / 3])


def test_weighted_atr_includes_the_gap_from_the_previous_close():
    bars = pd.DataFrame({"high": [102.0, 111.0, 112.0], "low": [98.0, 109.0, 110.0],
                         "close": [100.0, 110.0, 111.0]})
    atr = WeightedATR.compute(dict(bars), {"window": 2})["weighted_atr"]
    assert np.isnan(atr.iloc[0])
    np.testing.assert_allclose(atr.iloc[1:], [(4 + 2 * 11) / 3, (11 + 2 * 2) / 3])


def test_atr_expansion_compares_to_prior_bars_and_preserves_one_bar_memory():
    bars = _ranges([2] * 6 + [5, 2, 2])
    rule = {"name": "atr_change_expansion", "params": {"window": 2, "window_threshold": 3}}
    assert RuleRegistry.evaluate(rule, bars.iloc[:6]) is False
    assert RuleRegistry.evaluate(rule, bars.iloc[:7]) is True
    assert RuleRegistry.evaluate(rule, bars.iloc[:8]) is True
    assert RuleRegistry.evaluate(rule, bars) is False


def test_atr_elevation_allows_repeated_zeros_and_rejects_a_fading_score():
    bars = _ranges([2] * 8 + [20, 2, 2])
    rule = {"name": "atr_elevated_score_not_fading", "params": {"window": 2, "window_elevation": 4}}
    assert RuleRegistry.evaluate(rule, bars.iloc[:5]) is False
    assert RuleRegistry.evaluate(rule, bars.iloc[:6]) is True
    assert RuleRegistry.evaluate(rule, bars.iloc[:9]) is True
    assert RuleRegistry.evaluate(rule, bars.iloc[:10]) is False
    assert RuleRegistry.evaluate(rule, bars) is True


def _walk(seed, bars, volatility=0.004):
    """A random walk with open, high, low and close on a plain integer index."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, volatility, bars)))
    open_ = np.concatenate([[100.0], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, volatility / 2, bars)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, volatility / 2, bars)))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


def _answers(rule, bars, ends, start=0):
    """The rule's answer at each bar in `ends`, evaluated on the bars from `start` to that bar."""
    return [RuleRegistry.evaluate(rule, bars.iloc[start:end + 1]) for end in ends]


def test_rsi_rebound_fires_on_a_rebound_and_not_without_one():
    """A steady climb, a four-bar selloff, then a recovery. RSI(5) sits near 65 during the climb,
    falls to 9 in the selloff, and rises through the weakness threshold of 45 on the second
    recovery bar."""
    params = {"window": 5, "threshold": 45.0, "window_threshold": 20}
    rule = {"name": "rsi_rebound_confirmation", "params": params}
    steps = [1.0, -0.5] * 20 + [-3.0] * 4 + [2.0] + [3.0] * 7
    bars = pd.DataFrame({"close": 100.0 + np.cumsum([0.0] + steps)})
    rsi = SMASeededRSI.compute({"close": bars["close"]}, {"window": 5})["rsi"]
    fired = dict(zip(range(30, len(bars)), _answers(rule, bars, range(30, len(bars)))))

    # No weakness: RSI rises on every other bar of the climb and stays above the threshold.
    assert rsi.iloc[30:41].min() > 45 and rsi.iloc[39] > rsi.iloc[38]
    assert not any(fired[t] for t in range(30, 41))
    # Weakness without a rebound: RSI is below the threshold and still falling.
    assert rsi.iloc[41:45].max() < 45 and rsi.iloc[41:45].is_monotonic_decreasing
    assert not any(fired[t] for t in range(41, 45))
    # The first rise while RSI is still below the threshold.
    assert rsi.iloc[44] < rsi.iloc[45] < 45
    assert fired[45] is True
    # Two rising bars with RSI back above the threshold are one short of a confirmation.
    assert rsi.iloc[46] > 45
    assert fired[46] is False
    # The third rising bar confirms it: weakness within five bars and the large rise at bar 45.
    assert rsi.iloc[47] > 45
    assert fired[47] is True
    # After that, no large rise below the threshold remains within the last three bars.
    assert not any(fired[t] for t in range(48, len(bars)))


def test_rsi_rebound_recovers_after_a_missing_close():
    """One missing close leaves RSI undefined until `window` price changes follow it. The signal
    answers again from the next bar, and once the missing bar has left the baseline it answers
    exactly as it does on the bars that follow the missing one."""
    params = {"window": 14, "threshold": 45.0, "window_threshold": 300}
    rule = {"name": "rsi_rebound_confirmation", "params": params}
    missing = 500
    bars = _walk(3, 1500)
    bars.loc[missing, "close"] = np.nan

    rsi = SMASeededRSI.compute({"close": bars["close"]}, {"window": 14})["rsi"]
    undefined = rsi.iloc[100:].isna()
    assert list(undefined[undefined].index) == list(range(missing, missing + 15))

    silent = range(missing, missing + 16)       # no RSI change is defined on these bars
    assert not any(_answers(rule, bars, silent))
    in_baseline = range(missing + 16, missing + 300)
    assert any(_answers(rule, bars, in_baseline)), "silent while the missing bar is in the baseline"

    clear = range(missing + 14 + 300 + 4, len(bars), 3)
    whole = _answers(rule, bars, clear)
    after_the_gap = _answers(rule, bars, clear, start=missing + 1)
    assert whole == after_the_gap
    assert any(whole) and not all(whole)


def test_atr_expansion_recovers_after_a_stretch_with_no_range():
    """Fifteen bars with no range take the weighted ATR to zero. Growth from zero is undefined
    while ATR stays there and infinite on the bar where trading resumes."""
    params = {"window": 5, "window_threshold": 100}
    rule = {"name": "atr_change_expansion", "params": params}
    clean = _walk(5, 700)
    flat = clean.copy()
    flat.loc[300:314, ["open", "high", "low", "close"]] = float(clean.loc[299, "close"])

    atr = WeightedATR.compute({k: flat[k] for k in ("high", "low", "close")}, {"window": 5})["weighted_atr"]
    assert (atr.iloc[304:315] == 0).all() and atr.iloc[315] > 0

    assert not any(_answers(rule, flat, range(306, 315)))   # ATR is zero on this bar and the last
    assert _answers(rule, flat, [315, 316]) == [True, True]  # the resumption, then one bar of memory
    assert any(_answers(rule, flat, range(317, 415))), "silent while the stretch is in the baseline"

    clear = range(425, len(flat))
    assert _answers(rule, flat, clear) == _answers(rule, clean, clear)
    assert any(_answers(rule, clean, clear))


def test_atr_expansion_needs_half_a_baseline_of_finite_growth():
    """Growth is undefined on 15 of the 20 bars before trading resumes at bar 320, so no baseline
    exists to compare the resumption with. From bar 332 at least 10 of the 20 bars before each of
    the two bars the rule reads are finite, and it answers."""
    params = {"window": 5, "window_threshold": 20}
    rule = {"name": "atr_change_expansion", "params": params}
    flat = _walk(5, 700)
    flat.loc[300:319, ["open", "high", "low", "close"]] = float(flat.loc[299, "close"])

    atr = WeightedATR.compute({k: flat[k] for k in ("high", "low", "close")}, {"window": 5})["weighted_atr"]
    growth = atr.pct_change(fill_method=None)
    assert growth.iloc[305:320].isna().all() and np.isinf(growth.iloc[320])
    assert np.isfinite(growth.iloc[300:305]).all() and np.isfinite(growth.iloc[321:340]).all()

    assert not any(_answers(rule, flat, range(320, 332)))
    assert any(_answers(rule, flat, range(332, 420)))


def test_atr_expansion_recovers_after_a_missing_bar():
    params = {"window": 5, "window_threshold": 100}
    rule = {"name": "atr_change_expansion", "params": params}
    clean = _walk(5, 700)
    gap = clean.copy()
    gap.loc[300, ["open", "high", "low", "close"]] = np.nan

    assert not any(_answers(rule, gap, range(301, 306)))    # no growth is defined on these bars
    assert any(_answers(rule, gap, range(307, 400))), "silent while the missing bar is in the baseline"
    clear = range(300 + 5 + 100 + 3, len(gap))
    assert _answers(rule, gap, clear) == _answers(rule, clean, clear)


def test_atr_elevation_recovers_after_a_missing_bar_and_a_stretch_with_no_range():
    params = {"window": 5, "window_elevation": 20}
    rule = {"name": "atr_elevated_score_not_fading", "params": params}
    clean = _walk(5, 700)
    gap = clean.copy()
    gap.loc[300, ["open", "high", "low", "close"]] = np.nan
    flat = clean.copy()
    flat.loc[300:339, ["open", "high", "low", "close"]] = float(clean.loc[299, "close"])

    # The missing bar is inside the ATR window or the elevation window on these bars.
    assert not any(_answers(rule, gap, range(300, 300 + 5 + 20 - 1)))
    clear = range(300 + 5 + 20, len(gap))
    assert _answers(rule, gap, clear) == _answers(rule, clean, clear)

    # With no range, ATR and its cutoff are both zero, so the score is zero on consecutive bars.
    assert all(_answers(rule, flat, range(330, 340)))
    clear = range(340 + 5 + 20, len(flat))
    assert _answers(rule, flat, clear) == _answers(rule, clean, clear)
    assert not all(_answers(rule, clean, clear))
