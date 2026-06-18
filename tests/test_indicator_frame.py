"""Tests for the uniform tabular accessor IndicatorInterface.compute_frame().

Context: a contract-audit bug report claimed 14 indicators "violate the unified
data pipeline contract" by returning raw dicts instead of pandas tabular
objects. In fact ALL indicators return ``dict[str, pd.Series]`` -- that is the
documented contract (the 14 flagged were simply the no-param indicators, the
only ones the reporter's harness could execute with empty params). These tests
pin down that uniform contract and exercise ``compute_frame()``, the additive,
non-breaking tabular surface for feature stacking.
"""
import numpy as np
import pandas as pd

import mangrove_kb.indicators as ind
from mangrove_kb.indicators.indicator_interface import IndicatorInterface

# The 14 no-param indicators the audit harness flagged.
NO_PARAM_INDICATORS = [
    "ADI", "BOP", "CumulativeReturn", "DailyLogReturn", "DailyReturn",
    "Engulfing", "Harami", "HeikinAshi", "InsideBar", "OBV", "OutsideBar",
    "ThreeInsideDown", "ThreeInsideUp", "TrueRange",
]


def _ohlcv(n=120):
    np.random.seed(0)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = pd.Series(100 + np.cumsum(np.random.randn(n)), index=idx)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    open_ = close.shift(1).bfill()
    volume = pd.Series(np.random.randint(1000, 5000, n).astype(float), index=idx)
    return idx, {"open": open_, "high": high, "low": low, "close": close, "volume": volume}


def test_all_no_param_indicators_share_dict_contract():
    """compute() returns dict[str, pd.Series] for every flagged indicator."""
    idx, full = _ohlcv()
    for name in NO_PARAM_INDICATORS:
        cls = getattr(ind, name)
        data = {k: full[k] for k in cls._data}
        result = cls.compute(data=data, params={})
        assert isinstance(result, dict), f"{name} did not return a dict"
        for key, series in result.items():
            assert isinstance(series, pd.Series), f"{name}[{key}] is not a Series"
            assert series.index.equals(idx), f"{name}[{key}] lost the input index"


def test_compute_frame_returns_dataframe_with_output_columns():
    """compute_frame() yields a DataFrame whose columns are the output names."""
    idx, full = _ohlcv()
    for name in NO_PARAM_INDICATORS:
        cls = getattr(ind, name)
        data = {k: full[k] for k in cls._data}
        frame = cls.compute_frame(data=data, params={})
        assert isinstance(frame, pd.DataFrame), f"{name}.compute_frame() is not a DataFrame"
        assert list(frame.columns) == list(cls._outputs), f"{name} columns != _outputs"
        assert frame.index.equals(idx), f"{name} frame lost the input index"


def test_compute_frame_works_for_param_indicators():
    """The accessor is uniform: param-taking indicators also yield DataFrames."""
    idx, full = _ohlcv()
    frame = ind.RSI.compute_frame(data={"close": full["close"]}, params={"window": 14})
    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == ["rsi"]
    macd = ind.MACD.compute_frame(
        data={"close": full["close"]},
        params={"window_fast": 12, "window_slow": 26, "window_sign": 9},
    )
    assert list(macd.columns) == ["macd", "signal", "histogram"]
    assert macd.index.equals(idx)


def test_frames_outer_join_into_feature_matrix():
    """The reporter's use case: stack many indicators into one matrix."""
    idx, full = _ohlcv()
    features = pd.concat(
        [
            ind.RSI.compute_frame({"close": full["close"]}, {"window": 14}),
            ind.OBV.compute_frame({"close": full["close"], "volume": full["volume"]}, {}),
            ind.TrueRange.compute_frame(
                {"high": full["high"], "low": full["low"], "close": full["close"]}, {}
            ),
            ind.MACD.compute_frame(
                {"close": full["close"]},
                {"window_fast": 12, "window_slow": 26, "window_sign": 9},
            ),
        ],
        axis=1,
    )
    assert isinstance(features, pd.DataFrame)
    # No row explosion: concat aligned on the shared index, one row per bar.
    assert len(features) == len(idx)
    assert features.index.equals(idx)
    assert set(["rsi", "obv", "true_range", "macd", "signal", "histogram"]).issubset(features.columns)


def test_compute_frame_available_on_base_interface():
    assert hasattr(IndicatorInterface, "compute_frame")
