"""Averaging signals.

Signals whose class is `averaging` -- the class of the indicator each one reads. The file name is the
class, so a signal's location and its position in the ontology graph agree. Registered names are
unchanged; only the file moved.
"""

import logging

import numpy as np
import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators import (
    KAMA,
)

logger = logging.getLogger(__name__)


@RuleRegistry.register("kama_cross_up")
def kama_cross_up(df: pd.DataFrame, window: int = 10, pow1: int = 2, pow2: int = 30) -> bool:
    """
    Check if price crosses above KAMA (bullish signal).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Efficiency ratio period. Range: 5-30. Default: 10.
        pow1 (int): Fast smoothing constant. Range: 1-10. Default: 2.
        pow2 (int): Slow smoothing constant. Range: 10-50. Default: 30.

    Returns:
        bool: True if price crosses above KAMA, False otherwise.
    """
    if len(df) < window + max(pow1, pow2):
        return False

    result = KAMA.compute(
        data={'close': df["Close"]},
        params={'window': window, 'pow1': pow1, 'pow2': pow2}
    )
    kama = result['kama']

    if len(kama) < 2 or pd.isna(kama.iloc[-1]) or pd.isna(kama.iloc[-2]):
        return False

    close = df["Close"]
    prev_below = float(close.iloc[-2]) <= float(kama.iloc[-2])
    curr_above = float(close.iloc[-1]) > float(kama.iloc[-1])

    return prev_below and curr_above


@RuleRegistry.register("kama_cross_down")
def kama_cross_down(df: pd.DataFrame, window: int = 10, pow1: int = 2, pow2: int = 30) -> bool:
    """
    Check if price crosses below KAMA (bearish signal).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Efficiency ratio period. Range: 5-30. Default: 10.
        pow1 (int): Fast smoothing constant. Range: 1-10. Default: 2.
        pow2 (int): Slow smoothing constant. Range: 10-50. Default: 30.

    Returns:
        bool: True if price crosses below KAMA, False otherwise.
    """
    if len(df) < window + max(pow1, pow2):
        return False

    result = KAMA.compute(
        data={'close': df["Close"]},
        params={'window': window, 'pow1': pow1, 'pow2': pow2}
    )
    kama = result['kama']

    if len(kama) < 2 or pd.isna(kama.iloc[-1]) or pd.isna(kama.iloc[-2]):
        return False

    close = df["Close"]
    prev_above = float(close.iloc[-2]) >= float(kama.iloc[-2])
    curr_below = float(close.iloc[-1]) < float(kama.iloc[-1])

    return prev_above and curr_below
