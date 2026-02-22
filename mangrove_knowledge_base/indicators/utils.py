"""Utility functions for technical indicators."""
import numpy as np
import pandas as pd


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Calculate Welles Wilder's True Range.

    Captures volatility including gaps by taking max of:
    1. Current range (high - low)
    2. Gap from prev close to current high: abs(high - prev_close)
    3. Gap from prev close to current low: abs(low - prev_close)

    Examples:
    ---------
    Normal day (no gap):
        Close=$100, Next: Low=$98, High=$105
        tr1 = 7, tr2 = 5, tr3 = 2 -> True Range = 7

    Gap up:
        Close=$100, Next: Low=$109, High=$115
        tr1 = 6 (misses gap!), tr2 = 15, tr3 = 9 -> True Range = 15

    Gap down:
        Close=$100, Next: Low=$82, High=$88
        tr1 = 6 (misses gap!), tr2 = 12, tr3 = 18 -> True Range = 18

    References:
        J. Welles Wilder Jr.
        Used by ATR, Ultimate Oscillator, Vortex, etc.
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)


def get_min_max(series1: pd.Series, series2: pd.Series, function: str = "min") -> pd.Series:
    """Element-wise min/max between two series."""
    arr1 = np.array(series1)
    arr2 = np.array(series2)

    if function == "min":
        output = np.amin([arr1, arr2], axis=0)
    elif function == "max":
        output = np.amax([arr1, arr2], axis=0)
    else:
        raise ValueError('function must be "min" or "max"')

    return pd.Series(output, index=series1.index)
