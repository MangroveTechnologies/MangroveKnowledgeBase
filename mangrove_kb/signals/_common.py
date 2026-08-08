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
