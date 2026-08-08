"""Predicates shared by signals in more than one class.

Splitting the signal files onto the ontology class put `bop_cross_up` (an `oscillator` signal) and
`mom_cross_up` (a `momentum` one) in different files while they still share one zero-crossing test.
A helper used by two classes belongs to neither, so it lives here rather than being imported across
class files or copied into both.
"""
import pandas as pd


def zero_cross(series: pd.Series, direction: str) -> bool:
    """Whether `series` crossed the zero line on the last bar, in `direction` ("up" or "down").

    A crossing reads two consecutive bars, so it is False on the first bar and wherever either is
    undefined. The comparison is `prev <= 0 < curr` rather than `prev < 0 < curr`: a series sitting
    exactly at zero and then rising has crossed.
    """
    if len(series) < 2:
        return False
    prev, curr = series.iloc[-2], series.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    if direction == "up":
        return bool(prev <= 0 < curr)
    return bool(prev >= 0 > curr)


def _ma_is_above(df: pd.DataFrame, indicator_cls, output_key: str, window: int) -> bool:
    """Helper: check if current close is above the given MA."""
    closes = df["Close"]
    if len(closes) < window:
        return False
    result = indicator_cls.compute(data={'close': closes}, params={'window': window})
    ma = result[output_key]
    if ma.empty or pd.isna(ma.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > ma.iloc[-1])

def _ma_crossover(
    df: pd.DataFrame,
    indicator_cls,
    output_key: str,
    window_fast: int,
    window_slow: int,
    direction: str,
) -> bool:
    """Helper: detect fast/slow MA crossover in the given direction."""
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    fast = indicator_cls.compute(data={'close': closes}, params={'window': window_fast})[output_key]
    slow = indicator_cls.compute(data={'close': closes}, params={'window': window_slow})[output_key]
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    if direction == "bullish":
        return bool(prev_fast <= prev_slow and curr_fast > curr_slow)
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)
