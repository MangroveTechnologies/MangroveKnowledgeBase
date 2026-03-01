"""Candle geometry utility functions for pattern detection.

Provides vectorized helper functions for computing candle body, wick,
and range measurements used by pattern indicator classes.

All functions operate on pd.Series and return pd.Series, enabling
fully vectorized pattern detection across entire DataFrames.
"""

import numpy as np
import pandas as pd


def candle_body(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Absolute body size: |Close - Open|."""
    return (close_s - open_s).abs()


def candle_range(high_s: pd.Series, low_s: pd.Series) -> pd.Series:
    """Full candle range: High - Low."""
    return high_s - low_s


def upper_wick(open_s: pd.Series, high_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Upper wick length: High - max(Open, Close)."""
    return high_s - pd.concat([open_s, close_s], axis=1).max(axis=1)


def lower_wick(open_s: pd.Series, low_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Lower wick length: min(Open, Close) - Low."""
    return pd.concat([open_s, close_s], axis=1).min(axis=1) - low_s


def is_bullish(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Boolean series: True where Close > Open."""
    return close_s > open_s


def is_bearish(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Boolean series: True where Close < Open."""
    return close_s < open_s


def body_ratio(open_s: pd.Series, high_s: pd.Series,
               low_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Body as fraction of range: body / range.

    Returns 0.0 where range is 0 (flat candles).
    """
    body = candle_body(open_s, close_s)
    rng = candle_range(high_s, low_s)
    return body / rng.replace(0, np.nan).fillna(np.inf)
