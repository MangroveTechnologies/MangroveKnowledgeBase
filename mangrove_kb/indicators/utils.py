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
    high_arr = high.to_numpy(dtype=np.float64, copy=False)
    low_arr = low.to_numpy(dtype=np.float64, copy=False)
    prev_close = close.shift(1).to_numpy(dtype=np.float64, copy=False)
    tr1 = high_arr - low_arr
    tr2 = np.abs(high_arr - prev_close)
    tr3 = np.abs(low_arr - prev_close)
    # np.fmax ignores NaN (matches pandas DataFrame.max(skipna=True)); at index
    # 0, tr2/tr3 are NaN because prev_close is NaN -- the original fell back to
    # tr1 there, so we must do the same.
    tr = np.fmax(tr1, np.fmax(tr2, tr3))
    return pd.Series(tr, index=high.index)


def typical_price(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Typical price: (high + low + close) / 3.

    Used by CCI, MFI, VWAP, and the original-formula KeltnerChannel.
    """
    return (high + low + close) / 3.0


def get_min_max(series1: pd.Series, series2: pd.Series, function: str = "min") -> pd.Series:
    """Element-wise min/max between two series."""
    arr1 = series1.to_numpy(copy=False)
    arr2 = series2.to_numpy(copy=False)

    if function == "min":
        output = np.minimum(arr1, arr2)
    elif function == "max":
        output = np.maximum(arr1, arr2)
    else:
        raise ValueError('function must be "min" or "max"')

    return pd.Series(output, index=series1.index)
