"""Trend-based trading signals.

This module contains signal functions based on trend indicators including:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- MACD (Moving Average Convergence Divergence)
- ADX (Average Directional Index)
- Aroon
- WMA (Weighted Moving Average)
- TRIX
- Mass Index
- Ichimoku
- KST (Know Sure Thing)
- DPO (Detrended Price Oscillator)
- CCI (Commodity Channel Index)
- Vortex
- PSAR (Parabolic SAR)
- STC (Schaff Trend Cycle)
"""

import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry

# Import trend indicator classes
from mangrove_kb.indicators import (
    Aroon,
    MACD,
    EMA,
    SMA,
    WMA,
    TRIX,
    MassIndex,
    Ichimoku,
    KST,
    DPO,
    CCI,
    ADX,
    Vortex,
    PSAR,
    STC,
)

logger = logging.getLogger(__name__)


@RuleRegistry.register("is_above_sma")
def is_above_sma(df: pd.DataFrame, window: int) -> bool:
    """
    Check if the current price is above the Simple Moving Average.

    Uses SMA indicator to calculate the SMA for the given window and returns True
    if the most recent close price is strictly greater than the SMA value.
    Returns False if insufficient data is available. Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): SMA window in bars. Range: 1-200.

    Returns:
        bool: True if close > SMA, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window:
        return False

    result = SMA.compute(data={'close': closes}, params={'window': window})
    sma = result['sma']

    if sma.empty or pd.isna(sma.iloc[-1]):
        return False

    return closes.iloc[-1] > sma.iloc[-1]


@RuleRegistry.register("sma_crossover")
def sma_crossover(df: pd.DataFrame, window_fast: int, window_slow: int, direction: str = "bullish") -> bool:
    """
    Detect an SMA crossover signal with configurable direction (bullish or bearish).

    Uses SMA indicator to calculate window_fast and window_slow SMAs. Returns True when a crossover
    is detected in the specified direction.

    Bullish crossover (golden cross): window_fast SMA crosses above window_slow SMA
    Bearish crossover (death cross): window_fast SMA crosses below window_slow SMA

    The crossover detection compares the previous and current bars:
    - Bullish: prev window_fast <= prev window_slow AND current window_fast > current window_slow
    - Bearish: prev window_fast >= prev window_slow AND current window_fast < current window_slow

    Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window in bars. Range: 1-200.
        window_slow (int): Slow SMA window in bars. Range: 1-200.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if crossover detected in the specified direction, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow:
        return False

    # Calculate SMAs
    fast_result = SMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_sma = fast_result['sma']
    slow_result = SMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_sma = slow_result['sma']

    # Check if we have enough data for the crossover (need 2 bars to detect crossing)
    if len(fast_sma) < 2 or len(slow_sma) < 2:
        return False

    # Get current and previous values
    current_fast = fast_sma.iloc[-1]
    current_slow = slow_sma.iloc[-1]
    prev_fast = fast_sma.iloc[-2]
    prev_slow = slow_sma.iloc[-2]

    # Check for NaN values
    if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
        return False

    if direction.lower() == "bullish":
        return prev_fast <= prev_slow and current_fast > current_slow
    elif direction.lower() == "bearish":
        # Bearish crossover: window_fast was above or equal to window_slow, now window_fast is below window_slow
        return prev_fast >= prev_slow and current_fast < current_slow
    else:
        logger.warning(f"Unknown direction '{direction}', expected 'bullish' or 'bearish'")
        return False


@RuleRegistry.register("sma_cross_up")
def sma_cross_up(df: pd.DataFrame, window_fast: int, window_slow: int) -> bool:
    """
    Detect a bullish SMA crossover as an entry signal.

    Returns True when the window_fast SMA crosses above the window_slow SMA (golden cross).
    This is a momentum-driven entry signal, indicating a transition from
    bearish to bullish momentum. Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Note: This is a backwards-compatible wrapper around sma_crossover.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window in bars. Range: 1-200.
        window_slow (int): Slow SMA window in bars. Range: 1-200.

    Returns:
        bool: True if bullish crossover detected in the current bar, False otherwise.
    """
    return sma_crossover(df, window_fast=window_fast, window_slow=window_slow, direction="bullish")


@RuleRegistry.register("sma_cross_down")
def sma_cross_down(df: pd.DataFrame, window_fast: int, window_slow: int) -> bool:
    """
    Detect a bearish SMA crossover as an exit signal.

    Returns True when the window_fast SMA crosses below the window_slow SMA (death cross).
    This is a momentum-driven exit signal, indicating a transition from
    bullish to bearish momentum. Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Note: This is a backwards-compatible wrapper around sma_crossover.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window in bars. Range: 1-200.
        window_slow (int): Slow SMA window in bars. Range: 1-200.

    Returns:
        bool: True if bearish crossover detected in the current bar, False otherwise.
    """
    return sma_crossover(df, window_fast=window_fast, window_slow=window_slow, direction="bearish")



# =============================================================================
# MACD-Based Signals
# =============================================================================

@RuleRegistry.register("macd_bullish_cross")
def macd_bullish_cross(
    df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9
) -> bool:
    """
    Detect MACD bullish crossover (MACD line crosses above signal line).

    A bullish MACD crossover occurs when the MACD line crosses above
    the signal line, indicating potential upward momentum. Crypto's high volatility may produce frequent signals; use with trend confirmation.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-50. Default: 12.
        window_slow (int): Slow EMA window. Range: 10-100. Default: 26.
        window_sign (int): Signal line EMA window. Range: 2-50. Default: 9.

    Returns:
        bool: True if bullish crossover detected, False otherwise.
    """
    closes = df["Close"]
    min_periods = window_slow + window_sign
    if len(closes) < min_periods:
        return False

    result = MACD.compute(
        data={'close': closes},
        params={'window_fast': window_fast, 'window_slow': window_slow, 'window_sign': window_sign}
    )
    macd_line = result['macd']
    signal_line = result['signal']

    if len(macd_line) < 2:
        return False

    # Check for crossover: MACD was below/equal to signal, now above
    prev_macd = macd_line.iloc[-2]
    prev_signal = signal_line.iloc[-2]
    curr_macd = macd_line.iloc[-1]
    curr_signal = signal_line.iloc[-1]

    if pd.isna(prev_macd) or pd.isna(curr_macd) or pd.isna(prev_signal) or pd.isna(curr_signal):
        return False

    return bool(prev_macd <= prev_signal and curr_macd > curr_signal)


@RuleRegistry.register("macd_bearish_cross")
def macd_bearish_cross(
    df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9
) -> bool:
    """
    Detect MACD bearish crossover (MACD line crosses below signal line).

    A bearish MACD crossover occurs when the MACD line crosses below
    the signal line, indicating potential downward momentum. Crypto's high volatility may produce frequent signals; use with trend confirmation.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-50. Default: 12.
        window_slow (int): Slow EMA window. Range: 10-100. Default: 26.
        window_sign (int): Signal line EMA window. Range: 2-50. Default: 9.

    Returns:
        bool: True if bearish crossover detected, False otherwise.
    """
    closes = df["Close"]
    min_periods = window_slow + window_sign
    if len(closes) < min_periods:
        return False

    result = MACD.compute(
        data={'close': closes},
        params={'window_fast': window_fast, 'window_slow': window_slow, 'window_sign': window_sign}
    )
    macd_line = result['macd']
    signal_line = result['signal']

    if len(macd_line) < 2:
        return False

    # Check for crossover: MACD was above/equal to signal, now below
    prev_macd = macd_line.iloc[-2]
    prev_signal = signal_line.iloc[-2]
    curr_macd = macd_line.iloc[-1]
    curr_signal = signal_line.iloc[-1]

    if pd.isna(prev_macd) or pd.isna(curr_macd) or pd.isna(prev_signal) or pd.isna(curr_signal):
        return False

    return bool(prev_macd >= prev_signal and curr_macd < curr_signal)


@RuleRegistry.register("macd_positive")
def macd_positive(
    df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9
) -> bool:
    """
    Check if MACD histogram is positive (bullish momentum). Crypto's high volatility may produce frequent signals; use with trend confirmation.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-50. Default: 12.
        window_slow (int): Slow EMA window. Range: 10-100. Default: 26.
        window_sign (int): Signal line EMA window. Range: 2-50. Default: 9.

    Returns:
        bool: True if MACD histogram > 0, False otherwise.
    """
    closes = df["Close"]
    min_periods = window_slow + window_sign
    if len(closes) < min_periods:
        return False

    result = MACD.compute(
        data={'close': closes},
        params={'window_fast': window_fast, 'window_slow': window_slow, 'window_sign': window_sign}
    )
    macd_diff = result['histogram']

    if pd.isna(macd_diff.iloc[-1]):
        return False

    return float(macd_diff.iloc[-1]) > 0



# =============================================================================
# EMA-Based Signals
# =============================================================================

@RuleRegistry.register("ema_cross_up")
def ema_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect bullish EMA crossover (fast EMA crosses above slow EMA). Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow EMA window. Range: 5-200. Default: 21.

    Returns:
        bool: True if bullish crossover detected, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False

    fast_result = EMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_ema = fast_result['ema']
    slow_result = EMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_ema = slow_result['ema']

    if len(fast_ema) < 2:
        return False

    prev_fast = fast_ema.iloc[-2]
    prev_slow = slow_ema.iloc[-2]
    curr_fast = fast_ema.iloc[-1]
    curr_slow = slow_ema.iloc[-1]

    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False

    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)


@RuleRegistry.register("ema_cross_down")
def ema_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect bearish EMA crossover (fast EMA crosses below slow EMA). Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow EMA window. Range: 5-200. Default: 21.

    Returns:
        bool: True if bearish crossover detected, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False

    fast_result = EMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_ema = fast_result['ema']
    slow_result = EMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_ema = slow_result['ema']

    if len(fast_ema) < 2:
        return False

    prev_fast = fast_ema.iloc[-2]
    prev_slow = slow_ema.iloc[-2]
    curr_fast = fast_ema.iloc[-1]
    curr_slow = slow_ema.iloc[-1]

    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False

    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


@RuleRegistry.register("ema_crossover")
def ema_crossover(df: pd.DataFrame, window_fast: int, window_slow: int, direction: str = "bullish") -> bool:
    """
    Detect an EMA crossover signal with configurable direction (bullish or bearish).

    Uses EMA indicator to calculate window_fast and window_slow EMAs. Returns True when a crossover
    is detected in the specified direction.

    Bullish crossover: window_fast EMA crosses above window_slow EMA
    Bearish crossover: window_fast EMA crosses below window_slow EMA

    The crossover detection compares the previous and current bars:
    - Bullish: prev window_fast <= prev window_slow AND current window_fast > current window_slow
    - Bearish: prev window_fast >= prev window_slow AND current window_fast < current window_slow

    Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window in bars. Range: 1-200.
        window_slow (int): Slow EMA window in bars. Range: 1-200.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if crossover detected in the specified direction, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False

    fast_result = EMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_ema = fast_result['ema']
    slow_result = EMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_ema = slow_result['ema']

    if len(fast_ema) < 2:
        return False

    prev_fast = fast_ema.iloc[-2]
    prev_slow = slow_ema.iloc[-2]
    curr_fast = fast_ema.iloc[-1]
    curr_slow = slow_ema.iloc[-1]

    # Check for NaN values
    if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow):
        return False

    if direction.lower() == "bullish":
        # Bullish crossover: window_fast was below or equal to window_slow, now window_fast is above window_slow
        return prev_fast <= prev_slow and curr_fast > curr_slow
    elif direction.lower() == "bearish":
        # Bearish crossover: window_fast was above or equal to window_slow, now window_fast is below window_slow
        return prev_fast >= prev_slow and curr_fast < curr_slow
    else:
        logger.warning(f"Unknown direction '{direction}', expected 'bullish' or 'bearish'")
        return False


@RuleRegistry.register("price_above_ema")
def price_above_ema(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if price is above the EMA. Common periods: 9/21 (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA window. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > EMA, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window:
        return False

    result = EMA.compute(data={'close': closes}, params={'window': window})
    ema = result['ema']

    if pd.isna(ema.iloc[-1]):
        return False

    return float(closes.iloc[-1]) > float(ema.iloc[-1])



# =============================================================================
# ADX/Trend Strength Signals
# =============================================================================

@RuleRegistry.register("adx_strong_trend")
def adx_strong_trend(df: pd.DataFrame, window: int = 14, threshold: float = 25.0) -> bool:
    """
    Check if ADX indicates a strong trend.

    ADX values above 25 typically indicate a strong trend (either up or down).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ADX period. Range: 5-50. Default: 14.
        threshold (float): Trend strength threshold. Range: 15-50. Default: 25.0.

    Returns:
        bool: True if ADX > threshold, False otherwise.
    """
    if len(df) < window * 2:
        return False

    result = ADX.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    adx = result['adx']

    if pd.isna(adx.iloc[-1]):
        return False

    return float(adx.iloc[-1]) > threshold


@RuleRegistry.register("adx_bullish_di")
def adx_bullish_di(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if +DI is greater than -DI (bullish directional movement).

    When +DI > -DI, bulls have the upper hand.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ADX period. Range: 5-50. Default: 14.

    Returns:
        bool: True if +DI > -DI, False otherwise.
    """
    if len(df) < window * 2:
        return False

    result = ADX.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    di_pos = result['adx_pos']
    di_neg = result['adx_neg']

    if pd.isna(di_pos.iloc[-1]) or pd.isna(di_neg.iloc[-1]):
        return False

    return float(di_pos.iloc[-1]) > float(di_neg.iloc[-1])



# =============================================================================
# Aroon Signals
# =============================================================================

@RuleRegistry.register("aroon_up_trend")
def aroon_up_trend(df: pd.DataFrame, window: int = 25, threshold: float = 70.0) -> bool:
    """
    Check if Aroon Up indicates strong uptrend.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 10-50. Default: 25.
        threshold (float): Strong trend threshold. Range: 50-100. Default: 70.0.

    Returns:
        bool: True if Aroon Up > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = Aroon.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window': window}
    )
    aroon_up = result['aroon_up']

    if pd.isna(aroon_up.iloc[-1]):
        return False

    return float(aroon_up.iloc[-1]) > threshold


@RuleRegistry.register("aroon_down_trend")
def aroon_down_trend(df: pd.DataFrame, window: int = 25, threshold: float = 70.0) -> bool:
    """
    Check if Aroon Down indicates strong downtrend.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 10-50. Default: 25.
        threshold (float): Strong trend threshold. Range: 50-100. Default: 70.0.

    Returns:
        bool: True if Aroon Down > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = Aroon.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window': window}
    )
    aroon_down = result['aroon_down']

    if pd.isna(aroon_down.iloc[-1]):
        return False

    return float(aroon_down.iloc[-1]) > threshold


@RuleRegistry.register("aroon_crossover")
def aroon_crossover(df: pd.DataFrame, window: int = 25, direction: str = "bullish") -> bool:
    """
    Check if Aroon lines cross (trend change signal).

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 10-50. Default: 25.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if crossover detected, False otherwise.
    """
    if len(df) < window + 1:
        return False

    result = Aroon.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window': window}
    )
    aroon_up = result['aroon_up']
    aroon_down = result['aroon_down']

    if len(aroon_up) < 2:
        return False
    if (pd.isna(aroon_up.iloc[-1]) or pd.isna(aroon_down.iloc[-1])
            or pd.isna(aroon_up.iloc[-2]) or pd.isna(aroon_down.iloc[-2])):
        return False

    if direction.lower() == "bullish":
        prev_below = float(aroon_up.iloc[-2]) <= float(aroon_down.iloc[-2])
        curr_above = float(aroon_up.iloc[-1]) > float(aroon_down.iloc[-1])
        return prev_below and curr_above
    elif direction.lower() == "bearish":
        prev_above = float(aroon_up.iloc[-2]) >= float(aroon_down.iloc[-2])
        curr_below = float(aroon_up.iloc[-1]) < float(aroon_down.iloc[-1])
        return prev_above and curr_below

    return False


# =============================================================================
# WMA Signals
# =============================================================================

@RuleRegistry.register("wma_cross_up")
def wma_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Check if fast WMA crosses above slow WMA (bullish).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast WMA window. Range: 2-50. Default: 9.
        window_slow (int): Slow WMA window. Range: 10-100. Default: 21.

    Returns:
        bool: True if fast WMA crosses above slow WMA, False otherwise.
    """
    if len(df) < window_slow + 1:
        return False

    fast_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_fast})
    fast_wma = fast_result['wma']
    slow_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_slow})
    slow_wma = slow_result['wma']

    if len(fast_wma) < 2 or pd.isna(fast_wma.iloc[-1]) or pd.isna(slow_wma.iloc[-1]):
        return False

    prev_below = float(fast_wma.iloc[-2]) <= float(slow_wma.iloc[-2])
    curr_above = float(fast_wma.iloc[-1]) > float(slow_wma.iloc[-1])

    return prev_below and curr_above


@RuleRegistry.register("wma_cross_down")
def wma_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Check if fast WMA crosses below slow WMA (bearish).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast WMA window. Range: 2-50. Default: 9.
        window_slow (int): Slow WMA window. Range: 10-100. Default: 21.

    Returns:
        bool: True if fast WMA crosses below slow WMA, False otherwise.
    """
    if len(df) < window_slow + 1:
        return False

    fast_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_fast})
    fast_wma = fast_result['wma']
    slow_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_slow})
    slow_wma = slow_result['wma']

    if len(fast_wma) < 2 or pd.isna(fast_wma.iloc[-1]) or pd.isna(slow_wma.iloc[-1]):
        return False

    prev_above = float(fast_wma.iloc[-2]) >= float(slow_wma.iloc[-2])
    curr_below = float(fast_wma.iloc[-1]) < float(slow_wma.iloc[-1])

    return prev_above and curr_below


# =============================================================================
# TRIX Signals
# =============================================================================

@RuleRegistry.register("trix_bullish")
def trix_bullish(df: pd.DataFrame, window: int = 15, threshold: float = 0.0) -> bool:
    """
    Check if TRIX indicates bullish momentum.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TRIX period. Range: 5-30. Default: 15.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if TRIX > threshold, False otherwise.
    """
    if len(df) < window * 3:
        return False

    result = TRIX.compute(data={'close': df["Close"]}, params={'window': window})
    trix = result['trix']

    if pd.isna(trix.iloc[-1]):
        return False

    return float(trix.iloc[-1]) > threshold


@RuleRegistry.register("trix_bearish")
def trix_bearish(df: pd.DataFrame, window: int = 15, threshold: float = 0.0) -> bool:
    """
    Check if TRIX indicates bearish momentum.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TRIX period. Range: 5-30. Default: 15.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if TRIX < threshold, False otherwise.
    """
    if len(df) < window * 3:
        return False

    result = TRIX.compute(data={'close': df["Close"]}, params={'window': window})
    trix = result['trix']

    if pd.isna(trix.iloc[-1]):
        return False

    return float(trix.iloc[-1]) < threshold


# =============================================================================
# Mass Index Signals
# =============================================================================

@RuleRegistry.register("mass_reversal_signal")
def mass_reversal_signal(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 25, threshold_high: float = 27.0, threshold_low: float = 26.5) -> bool:
    """
    Check if Mass Index signals potential reversal (reversal bulge).

    A reversal bulge occurs when Mass Index rises above 27 then falls below 26.5.

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 5-15. Default: 9.
        window_slow (int): Sum period. Range: 15-40. Default: 25.
        threshold_high (float): Upper threshold. Range: 25-30. Default: 27.0.
        threshold_low (float): Lower threshold. Range: 24-27. Default: 26.5.

    Returns:
        bool: True if reversal bulge detected, False otherwise.
    """
    if len(df) < window_slow + window_fast:
        return False

    result = MassIndex.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window_fast': window_fast, 'window_slow': window_slow}
    )
    mi = result['mass_index']

    if len(mi) < 5 or pd.isna(mi.iloc[-1]):
        return False

    # Check for bulge: was above threshold_high recently, now below threshold_low
    recent = mi.iloc[-10:]
    was_above = any(float(v) > threshold_high for v in recent if not pd.isna(v))
    now_below = float(mi.iloc[-1]) < threshold_low

    return was_above and now_below


# =============================================================================
# Ichimoku Signals
# =============================================================================

@RuleRegistry.register("ichimoku_bullish")
def ichimoku_bullish(df: pd.DataFrame, window_tenkan: int = 9, window_kijun: int = 26, window_senkou: int = 52) -> bool:
    """
    Check if Ichimoku indicates bullish signal (price above cloud).

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_tenkan (int): Tenkan-sen (conversion line) window. Range: 5-20. Default: 9.
        window_kijun (int): Kijun-sen (base line) window. Range: 15-40. Default: 26.
        window_senkou (int): Senkou Span B (leading span B) window. Range: 30-70. Default: 52.

    Returns:
        bool: True if price above cloud, False otherwise.
    """
    if len(df) < window_senkou:
        return False

    result = Ichimoku.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_tenkan, 'window2': window_kijun, 'window3': window_senkou, 'visual': False}
    )
    span_a = result['span_a']
    span_b = result['span_b']

    if pd.isna(span_a.iloc[-1]) or pd.isna(span_b.iloc[-1]):
        return False

    cloud_top = max(float(span_a.iloc[-1]), float(span_b.iloc[-1]))
    close = float(df["Close"].iloc[-1])

    return close > cloud_top


@RuleRegistry.register("ichimoku_bearish")
def ichimoku_bearish(df: pd.DataFrame, window_tenkan: int = 9, window_kijun: int = 26, window_senkou: int = 52) -> bool:
    """
    Check if Ichimoku indicates bearish signal (price below cloud).

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_tenkan (int): Tenkan-sen (conversion line) window. Range: 5-20. Default: 9.
        window_kijun (int): Kijun-sen (base line) window. Range: 15-40. Default: 26.
        window_senkou (int): Senkou Span B (leading span B) window. Range: 30-70. Default: 52.

    Returns:
        bool: True if price below cloud, False otherwise.
    """
    if len(df) < window_senkou:
        return False

    result = Ichimoku.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_tenkan, 'window2': window_kijun, 'window3': window_senkou, 'visual': False}
    )
    span_a = result['span_a']
    span_b = result['span_b']

    if pd.isna(span_a.iloc[-1]) or pd.isna(span_b.iloc[-1]):
        return False

    cloud_bottom = min(float(span_a.iloc[-1]), float(span_b.iloc[-1]))
    close = float(df["Close"].iloc[-1])

    return close < cloud_bottom


@RuleRegistry.register("ichimoku_tk_cross")
def ichimoku_tk_cross(df: pd.DataFrame, window_tenkan: int = 9, window_kijun: int = 26, window_senkou: int = 52, direction: str = "bullish") -> bool:
    """
    Check if Tenkan-sen crosses Kijun-sen (TK cross).

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_tenkan (int): Tenkan-sen (conversion line) window. Range: 5-20. Default: 9.
        window_kijun (int): Kijun-sen (base line) window. Range: 15-40. Default: 26.
        window_senkou (int): Senkou Span B (leading span B) window. Range: 30-70. Default: 52.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if TK cross detected, False otherwise.
    """
    if len(df) < window_senkou + 1:
        return False

    result = Ichimoku.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_tenkan, 'window2': window_kijun, 'window3': window_senkou, 'visual': False}
    )
    tenkan = result['conversion_line']
    kijun = result['base_line']

    if len(tenkan) < 2 or pd.isna(tenkan.iloc[-1]) or pd.isna(kijun.iloc[-1]):
        return False

    if direction.lower() == "bullish":
        prev_below = float(tenkan.iloc[-2]) <= float(kijun.iloc[-2])
        curr_above = float(tenkan.iloc[-1]) > float(kijun.iloc[-1])
        return prev_below and curr_above
    elif direction.lower() == "bearish":
        prev_above = float(tenkan.iloc[-2]) >= float(kijun.iloc[-2])
        curr_below = float(tenkan.iloc[-1]) < float(kijun.iloc[-1])
        return prev_above and curr_below

    return False


# =============================================================================
# KST Signals
# =============================================================================

@RuleRegistry.register("kst_bullish_cross")
def kst_bullish_cross(df: pd.DataFrame, roc1: int = 10, roc2: int = 15, roc3: int = 20, roc4: int = 30, window_sma1: int = 10, window_sma2: int = 10, window_sma3: int = 10, window_sma4: int = 15, nsig: int = 9) -> bool:
    """
    Check if KST crosses above signal line (bullish).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        roc1 (int): ROC1 period. Range: 1-200. Default: 10.
        roc2 (int): ROC2 period. Range: 1-200. Default: 15.
        roc3 (int): ROC3 period. Range: 1-200. Default: 20.
        roc4 (int): ROC4 period. Range: 1-200. Default: 30.
        window_sma1 (int): SMA1 smoothing window for ROC1. Range: 2-200. Default: 10.
        window_sma2 (int): SMA2 smoothing window for ROC2. Range: 2-200. Default: 10.
        window_sma3 (int): SMA3 smoothing window for ROC3. Range: 2-200. Default: 10.
        window_sma4 (int): SMA4 smoothing window for ROC4. Range: 2-200. Default: 15.
        nsig (int): Signal line period. Range: 1-200. Default: 9.

    Returns:
        bool: True if KST crosses above signal, False otherwise.
    """
    if len(df) < roc4 + window_sma4 + nsig:
        return False

    result = KST.compute(
        data={"close": df["Close"]},
        params={
            "roc1": roc1,
            "roc2": roc2,
            "roc3": roc3,
            "roc4": roc4,
            "window1": window_sma1,
            "window2": window_sma2,
            "window3": window_sma3,
            "window4": window_sma4,
            "nsig": nsig,
        },
    )
    kst = result["kst"]
    signal = result["kst_signal"]

    if len(kst) < 2 or pd.isna(kst.iloc[-1]) or pd.isna(signal.iloc[-1]):
        return False

    prev_below = float(kst.iloc[-2]) <= float(signal.iloc[-2])
    curr_above = float(kst.iloc[-1]) > float(signal.iloc[-1])

    return prev_below and curr_above


@RuleRegistry.register("kst_bearish_cross")
def kst_bearish_cross(df: pd.DataFrame, roc1: int = 10, roc2: int = 15, roc3: int = 20, roc4: int = 30, window_sma1: int = 10, window_sma2: int = 10, window_sma3: int = 10, window_sma4: int = 15, nsig: int = 9) -> bool:
    """
    Check if KST crosses below signal line (bearish).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        roc1 (int): ROC1 period. Range: 1-200. Default: 10.
        roc2 (int): ROC2 period. Range: 1-200. Default: 15.
        roc3 (int): ROC3 period. Range: 1-200. Default: 20.
        roc4 (int): ROC4 period. Range: 1-200. Default: 30.
        window_sma1 (int): SMA1 smoothing window for ROC1. Range: 2-200. Default: 10.
        window_sma2 (int): SMA2 smoothing window for ROC2. Range: 2-200. Default: 10.
        window_sma3 (int): SMA3 smoothing window for ROC3. Range: 2-200. Default: 10.
        window_sma4 (int): SMA4 smoothing window for ROC4. Range: 2-200. Default: 15.
        nsig (int): Signal line period. Range: 1-200. Default: 9.

    Returns:
        bool: True if KST crosses below signal, False otherwise.
    """
    if len(df) < roc4 + window_sma4 + nsig:
        return False

    result = KST.compute(
        data={'close': df["Close"]},
        params={
            'roc1': roc1, 'roc2': roc2, 'roc3': roc3, 'roc4': roc4,
            'window1': window_sma1, 'window2': window_sma2, 'window3': window_sma3, 'window4': window_sma4,
            'nsig': nsig
        }
    )
    kst = result['kst']
    signal = result['kst_signal']

    if len(kst) < 2 or pd.isna(kst.iloc[-1]) or pd.isna(signal.iloc[-1]):
        return False

    prev_above = float(kst.iloc[-2]) >= float(signal.iloc[-2])
    curr_below = float(kst.iloc[-1]) < float(signal.iloc[-1])

    return prev_above and curr_below


# =============================================================================
# DPO Signals
# =============================================================================

@RuleRegistry.register("dpo_positive")
def dpo_positive(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if DPO is positive (price above detrended average).

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): DPO period. Range: 10-50. Default: 20.

    Returns:
        bool: True if DPO > 0, False otherwise.
    """
    if len(df) < window:
        return False

    result = DPO.compute(data={'close': df["Close"]}, params={'window': window})
    dpo = result['dpo']

    if pd.isna(dpo.iloc[-1]):
        return False

    return float(dpo.iloc[-1]) > 0


@RuleRegistry.register("dpo_negative")
def dpo_negative(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if DPO is negative (price below detrended average).

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): DPO period. Range: 10-50. Default: 20.

    Returns:
        bool: True if DPO < 0, False otherwise.
    """
    if len(df) < window:
        return False

    result = DPO.compute(data={'close': df["Close"]}, params={'window': window})
    dpo = result['dpo']

    if pd.isna(dpo.iloc[-1]):
        return False

    return float(dpo.iloc[-1]) < 0


# =============================================================================
# CCI Signals
# =============================================================================

@RuleRegistry.register("cci_overbought")
def cci_overbought(df: pd.DataFrame, window: int = 20, constant: float = 0.015, threshold: float = 100.0) -> bool:
    """
    Check if CCI indicates overbought condition.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CCI period. Range: 10-50. Default: 20.
        constant (float): CCI constant. Range: 0.001-0.1. Default: 0.015.
        threshold (float): Overbought threshold. Range: 50-200. Default: 100.0.

    Returns:
        bool: True if CCI > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = CCI.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'constant': constant}
    )
    cci = result['cci']

    if pd.isna(cci.iloc[-1]):
        return False

    return float(cci.iloc[-1]) > threshold


@RuleRegistry.register("cci_oversold")
def cci_oversold(df: pd.DataFrame, window: int = 20, constant: float = 0.015, threshold: float = -100.0) -> bool:
    """
    Check if CCI indicates oversold condition.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CCI period. Range: 10-50. Default: 20.
        constant (float): CCI constant. Range: 0.001-0.1. Default: 0.015.
        threshold (float): Oversold threshold. Range: -200--50. Default: -100.0.

    Returns:
        bool: True if CCI < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = CCI.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'constant': constant}
    )
    cci = result['cci']

    if pd.isna(cci.iloc[-1]):
        return False

    return float(cci.iloc[-1]) < threshold


# =============================================================================
# Vortex Indicator Signals
# =============================================================================

@RuleRegistry.register("vortex_bullish")
def vortex_bullish(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if Vortex Indicator shows bullish trend (+VI > -VI).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Vortex period. Range: 5-30. Default: 14.

    Returns:
        bool: True if +VI > -VI, False otherwise.
    """
    if len(df) < window:
        return False

    result = Vortex.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    vi_pos = result['vortex_pos']
    vi_neg = result['vortex_neg']

    if pd.isna(vi_pos.iloc[-1]) or pd.isna(vi_neg.iloc[-1]):
        return False

    return float(vi_pos.iloc[-1]) > float(vi_neg.iloc[-1])


@RuleRegistry.register("vortex_bearish")
def vortex_bearish(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if Vortex Indicator shows bearish trend (-VI > +VI).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Vortex period. Range: 5-30. Default: 14.

    Returns:
        bool: True if -VI > +VI, False otherwise.
    """
    if len(df) < window:
        return False

    result = Vortex.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    vi_pos = result['vortex_pos']
    vi_neg = result['vortex_neg']

    if pd.isna(vi_pos.iloc[-1]) or pd.isna(vi_neg.iloc[-1]):
        return False

    return float(vi_neg.iloc[-1]) > float(vi_pos.iloc[-1])


@RuleRegistry.register("vortex_crossover")
def vortex_crossover(df: pd.DataFrame, window: int = 14, direction: str = "bullish") -> bool:
    """
    Check if Vortex lines cross (trend change).

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Vortex period. Range: 5-30. Default: 14.
        direction (str): Crossover direction, 'bullish' (+VI crosses above -VI) or 'bearish'. Default: bullish.

    Returns:
        bool: True if crossover detected, False otherwise.
    """
    if len(df) < window + 1:
        return False

    result = Vortex.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    vi_pos = result['vortex_pos']
    vi_neg = result['vortex_neg']

    if len(vi_pos) < 2:
        return False
    if (pd.isna(vi_pos.iloc[-1]) or pd.isna(vi_neg.iloc[-1])
            or pd.isna(vi_pos.iloc[-2]) or pd.isna(vi_neg.iloc[-2])):
        return False

    if direction.lower() == "bullish":
        prev_below = float(vi_pos.iloc[-2]) <= float(vi_neg.iloc[-2])
        curr_above = float(vi_pos.iloc[-1]) > float(vi_neg.iloc[-1])
        return prev_below and curr_above
    elif direction.lower() == "bearish":
        prev_above = float(vi_pos.iloc[-2]) >= float(vi_neg.iloc[-2])
        curr_below = float(vi_pos.iloc[-1]) < float(vi_neg.iloc[-1])
        return prev_above and curr_below

    return False


# =============================================================================
# PSAR Signals
# =============================================================================

@RuleRegistry.register("psar_bullish")
def psar_bullish(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> bool:
    """
    Check if PSAR indicates bullish trend (PSAR below price).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        step (float): PSAR acceleration factor step. Range: 0.01-0.1. Default: 0.02.
        max_step (float): PSAR max acceleration factor. Range: 0.1-0.5. Default: 0.2.

    Returns:
        bool: True if PSAR < Close, False otherwise.
    """
    if len(df) < 2:
        return False

    result = PSAR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'step': step, 'max_step': max_step}
    )
    psar = result['psar']

    if pd.isna(psar.iloc[-1]):
        return False

    return float(psar.iloc[-1]) < float(df["Close"].iloc[-1])


@RuleRegistry.register("psar_bearish")
def psar_bearish(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> bool:
    """
    Check if PSAR indicates bearish trend (PSAR above price).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        step (float): PSAR acceleration factor step. Range: 0.01-0.1. Default: 0.02.
        max_step (float): PSAR max acceleration factor. Range: 0.1-0.5. Default: 0.2.

    Returns:
        bool: True if PSAR > Close, False otherwise.
    """
    if len(df) < 2:
        return False

    result = PSAR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'step': step, 'max_step': max_step}
    )
    psar = result['psar']

    if pd.isna(psar.iloc[-1]):
        return False

    return float(psar.iloc[-1]) > float(df["Close"].iloc[-1])


@RuleRegistry.register("psar_reversal")
def psar_reversal(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2, direction: str = "bullish") -> bool:
    """
    Check if PSAR flips sides (potential reversal).

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        step (float): PSAR acceleration factor step. Range: 0.01-0.1. Default: 0.02.
        max_step (float): PSAR max acceleration factor. Range: 0.1-0.5. Default: 0.2.
        direction (str): Reversal direction, 'bullish' (flip to below price) or 'bearish'. Default: bullish.

    Returns:
        bool: True if PSAR reversal detected, False otherwise.
    """
    if len(df) < 3:
        return False

    result = PSAR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'step': step, 'max_step': max_step}
    )
    psar = result['psar']

    if len(psar) < 2 or pd.isna(psar.iloc[-1]) or pd.isna(psar.iloc[-2]):
        return False

    close = df["Close"]

    if direction.lower() == "bullish":
        # Was above price (bearish), now below (bullish)
        prev_above = float(psar.iloc[-2]) > float(close.iloc[-2])
        curr_below = float(psar.iloc[-1]) < float(close.iloc[-1])
        return prev_above and curr_below
    elif direction.lower() == "bearish":
        # Was below price (bullish), now above (bearish)
        prev_below = float(psar.iloc[-2]) < float(close.iloc[-2])
        curr_above = float(psar.iloc[-1]) > float(close.iloc[-1])
        return prev_below and curr_above

    return False


# =============================================================================
# STC Signals
# =============================================================================

@RuleRegistry.register("stc_overbought")
def stc_overbought(df: pd.DataFrame, window_slow: int = 50, window_fast: int = 23, cycle: int = 10, smooth1: int = 3, smooth2: int = 3, threshold: float = 75.0) -> bool:
    """
    Check if STC indicates overbought condition.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 2-200. Default: 50.
        window_fast (int): Fast EMA period. Range: 2-200. Default: 23.
        cycle (int): Cycle period. Range: 1-200. Default: 10.
        smooth1 (int): First smoothing period. Range: 1-200. Default: 3.
        smooth2 (int): Second smoothing period. Range: 1-200. Default: 3.
        threshold (float): Overbought threshold. Range: 0.0-100.0. Default: 75.0.

    Returns:
        bool: True if STC > threshold, False otherwise.
    """
    if len(df) < window_slow + cycle:
        return False

    result = STC.compute(
        data={'close': df["Close"]},
        params={
            'window_slow': window_slow,
            'window_fast': window_fast,
            'cycle': cycle,
            'smooth1': smooth1,
            'smooth2': smooth2
        }
    )
    stc = result['stc']

    if pd.isna(stc.iloc[-1]):
        return False

    return float(stc.iloc[-1]) > threshold


@RuleRegistry.register("stc_oversold")
def stc_oversold(df: pd.DataFrame, window_slow: int = 50, window_fast: int = 23, cycle: int = 10, smooth1: int = 3, smooth2: int = 3, threshold: float = 25.0) -> bool:
    """
    Check if STC indicates oversold condition.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 2-200. Default: 50.
        window_fast (int): Fast EMA period. Range: 2-200. Default: 23.
        cycle (int): Cycle period. Range: 1-200. Default: 10.
        smooth1 (int): First smoothing period. Range: 1-200. Default: 3.
        smooth2 (int): Second smoothing period. Range: 1-200. Default: 3.
        threshold (float): Oversold threshold. Range: 0.0-100.0. Default: 25.0.

    Returns:
        bool: True if STC < threshold, False otherwise.
    """
    if len(df) < window_slow + cycle:
        return False

    result = STC.compute(
        data={'close': df["Close"]},
        params={
            'window_slow': window_slow,
            'window_fast': window_fast,
            'cycle': cycle,
            'smooth1': smooth1,
            'smooth2': smooth2
        }
    )
    stc = result['stc']

    if pd.isna(stc.iloc[-1]):
        return False

    return float(stc.iloc[-1]) < threshold
