"""multi_tf_trend_* answer the same for a time-indexed frame and for one carrying a ``timestamp``
column, which is the shape a backtest engine's rolling window has."""
import numpy as np
import pandas as pd
import pytest

from mangrove_kb.registry import RuleRegistry


@pytest.fixture
def hourly():
    ts = pd.date_range("2024-01-01", periods=24 * 7 * 40, freq="1h", tz="UTC")
    close = 100 + np.cumsum(np.sin(np.arange(len(ts)) / 300.0) + 0.05)
    return pd.DataFrame({"timestamp": ts, "open": close, "high": close + 1, "low": close - 1,
                         "close": close, "volume": 1.0})


@pytest.mark.parametrize("name", ["multi_tf_trend_bullish", "multi_tf_trend_bearish"])
def test_a_timestamp_column_answers_like_a_time_index(hourly, name):
    fn = RuleRegistry._registry[name]
    answers = []
    for end in range(24 * 7 * 14, len(hourly), 97):
        window = hourly.iloc[:end]
        indexed = fn(window.set_index("timestamp"), higher_tf="1W", window=10)
        assert fn(window.reset_index(drop=True), higher_tf="1W", window=10) == indexed
        answers.append(indexed)
    assert any(answers), "the fixture never produces a firing, so it would not catch a constant False"
