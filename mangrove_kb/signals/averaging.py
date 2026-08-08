"""Averaging signals.

Signals whose class is `averaging` -- the class of the indicator each one reads. The file name is the
class, so a signal's location and its position in the ontology graph agree. Registered names are
unchanged; only the file moved.
"""

import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators import (
    KAMA,
    VWAP,
    VWMA,
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


@RuleRegistry.register("is_above_vwma")
def is_above_vwma(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if the current price is above the Volume-Weighted Moving Average (VWMA).

    VWMA weights each bar's close by its volume, emphasizing high-participation
    bars. Useful as a filter that incorporates conviction from volume.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): VWMA window in bars. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > VWMA, False otherwise.
    """
    if len(df) < window:
        return False
    closes = df["Close"]
    volume = df["Volume"]
    result = VWMA.compute(data={'close': closes, 'volume': volume}, params={'window': window})
    vwma = result['vwma']
    if vwma.empty or pd.isna(vwma.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > vwma.iloc[-1])


@RuleRegistry.register("vwap_above")
def vwap_above(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if price is above VWAP (bullish bias).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): VWAP period. Range: 5-50. Default: 14.

    Returns:
        bool: True if Close > VWAP, False otherwise.
    """
    if len(df) < window:
        return False

    result = VWAP.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window})
    vwap = result['vwap']

    if pd.isna(vwap.iloc[-1]):
        return False

    return float(df["Close"].iloc[-1]) > float(vwap.iloc[-1])


@RuleRegistry.register("vwap_below")
def vwap_below(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if price is below VWAP (bearish bias).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): VWAP period. Range: 5-50. Default: 14.

    Returns:
        bool: True if Close < VWAP, False otherwise.
    """
    if len(df) < window:
        return False

    result = VWAP.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window})
    vwap = result['vwap']

    if pd.isna(vwap.iloc[-1]):
        return False

    return float(df["Close"].iloc[-1]) < float(vwap.iloc[-1])


@RuleRegistry.register("vwma_cross_down")
def vwma_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect a bearish VWMA crossover (fast VWMA crosses below slow VWMA).

    Volume-weighted version of the classic SMA death cross.

    Type: TRIGGER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast VWMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow VWMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bearish VWMA crossover detected on the current bar.
    """
    if len(df) < window_slow + 1:
        return False
    data = {'close': df["Close"], 'volume': df["Volume"]}
    fast = VWMA.compute(data=data, params={'window': window_fast})['vwma']
    slow = VWMA.compute(data=data, params={'window': window_slow})['vwma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


@RuleRegistry.register("vwma_cross_up")
def vwma_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect a bullish VWMA crossover (fast VWMA crosses above slow VWMA).

    Volume-weighted version of the classic SMA golden cross. High-volume bars
    carry more weight, so the signal is less susceptible to low-volume noise.

    Type: TRIGGER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast VWMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow VWMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bullish VWMA crossover detected on the current bar.
    """
    if len(df) < window_slow + 1:
        return False
    data = {'close': df["Close"], 'volume': df["Volume"]}
    fast = VWMA.compute(data=data, params={'window': window_fast})['vwma']
    slow = VWMA.compute(data=data, params={'window': window_slow})['vwma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)
