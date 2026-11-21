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
