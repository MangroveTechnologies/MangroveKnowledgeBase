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
    DEMA,
    TEMA,
    TRIMA,
    SMMA,
    EPMA,
    HMA,
    ALMA,
    T3,
    MAMA,
    HeikinAshi,
    ChandelierExit,
    WilliamsAlligator,
    SuperTrend,
    MARibbon,
    MultiTFTrend,
    Divergence,
    RSI,
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

    result = TRIX.compute(data={'close': df["Close"]}, params={'window': window, 'window_sign': 9})
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

    result = TRIX.compute(data={'close': df["Close"]}, params={'window': window, 'window_sign': 9})
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


# =============================================================================
# Wave A Moving Average Signals (DEMA, TEMA, TRIMA, SMMA, EPMA)
# =============================================================================
# Pattern: for each MA, we register is_above_<ma>, <ma>_cross_up, <ma>_cross_down.
# Each wraps a shared helper that handles NaN checks, warmup validation, and
# crossover detection, so the logic is uniform across MA families.


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


# --- DEMA signals ---

@RuleRegistry.register("is_above_dema")
def is_above_dema(df: pd.DataFrame, window: int = 21) -> bool:
    """
    Check if the current price is above the Double Exponential Moving Average (DEMA).

    DEMA reduces lag compared to a standard EMA by combining two EMA passes.
    Useful for trend-following filters where responsiveness matters.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): DEMA window in bars. Range: 2-200. Default: 21.

    Returns:
        bool: True if close > DEMA, False otherwise.
    """
    return _ma_is_above(df, DEMA, 'dema', window)


@RuleRegistry.register("dema_cross_up")
def dema_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect a bullish DEMA crossover (fast DEMA crosses above slow DEMA).

    Lower-lag equivalent of an SMA/EMA golden cross.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast DEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow DEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bullish DEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, DEMA, 'dema', window_fast, window_slow, "bullish")


@RuleRegistry.register("dema_cross_down")
def dema_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect a bearish DEMA crossover (fast DEMA crosses below slow DEMA).

    Lower-lag equivalent of an SMA/EMA death cross.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast DEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow DEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bearish DEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, DEMA, 'dema', window_fast, window_slow, "bearish")


# --- TEMA signals ---

@RuleRegistry.register("is_above_tema")
def is_above_tema(df: pd.DataFrame, window: int = 21) -> bool:
    """
    Check if the current price is above the Triple Exponential Moving Average (TEMA).

    TEMA has even less lag than DEMA by combining three EMA passes.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TEMA window in bars. Range: 2-200. Default: 21.

    Returns:
        bool: True if close > TEMA, False otherwise.
    """
    return _ma_is_above(df, TEMA, 'tema', window)


@RuleRegistry.register("tema_cross_up")
def tema_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect a bullish TEMA crossover (fast TEMA crosses above slow TEMA).

    Very low-lag cross signal; expect more whipsaw in noisy markets.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow TEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bullish TEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TEMA, 'tema', window_fast, window_slow, "bullish")


@RuleRegistry.register("tema_cross_down")
def tema_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """
    Detect a bearish TEMA crossover (fast TEMA crosses below slow TEMA).

    Very low-lag cross signal; expect more whipsaw in noisy markets.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow TEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bearish TEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TEMA, 'tema', window_fast, window_slow, "bearish")


# --- TRIMA signals ---

@RuleRegistry.register("is_above_trima")
def is_above_trima(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if the current price is above the Triangular Moving Average (TRIMA).

    TRIMA is a double-smoothed SMA that weights the middle of the window more
    heavily, producing a smoother trend line than SMA.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TRIMA window in bars. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > TRIMA, False otherwise.
    """
    return _ma_is_above(df, TRIMA, 'trima', window)


@RuleRegistry.register("trima_cross_up")
def trima_cross_up(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """
    Detect a bullish TRIMA crossover (fast TRIMA crosses above slow TRIMA).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TRIMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow TRIMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bullish TRIMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TRIMA, 'trima', window_fast, window_slow, "bullish")


@RuleRegistry.register("trima_cross_down")
def trima_cross_down(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """
    Detect a bearish TRIMA crossover (fast TRIMA crosses below slow TRIMA).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TRIMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow TRIMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bearish TRIMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TRIMA, 'trima', window_fast, window_slow, "bearish")


# --- SMMA signals ---

@RuleRegistry.register("is_above_smma")
def is_above_smma(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if the current price is above the Smoothed Moving Average (SMMA / Wilder's).

    SMMA uses Wilder's smoothing (alpha=1/n) rather than EMA's 2/(n+1), producing
    a slower, more stable trend line. Same family used inside RSI and ATR.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): SMMA window in bars. Range: 2-200. Default: 14.

    Returns:
        bool: True if close > SMMA, False otherwise.
    """
    return _ma_is_above(df, SMMA, 'smma', window)


@RuleRegistry.register("smma_cross_up")
def smma_cross_up(df: pd.DataFrame, window_fast: int = 14, window_slow: int = 50) -> bool:
    """
    Detect a bullish SMMA crossover (fast SMMA crosses above slow SMMA).

    Slower, more stable crossover than EMA cross; fewer false triggers.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMMA window. Range: 2-100. Default: 14.
        window_slow (int): Slow SMMA window. Range: 2-200. Default: 50.

    Returns:
        bool: True if bullish SMMA crossover detected on the current bar.
    """
    return _ma_crossover(df, SMMA, 'smma', window_fast, window_slow, "bullish")


@RuleRegistry.register("smma_cross_down")
def smma_cross_down(df: pd.DataFrame, window_fast: int = 14, window_slow: int = 50) -> bool:
    """
    Detect a bearish SMMA crossover (fast SMMA crosses below slow SMMA).

    Slower, more stable crossover than EMA cross; fewer false triggers.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMMA window. Range: 2-100. Default: 14.
        window_slow (int): Slow SMMA window. Range: 2-200. Default: 50.

    Returns:
        bool: True if bearish SMMA crossover detected on the current bar.
    """
    return _ma_crossover(df, SMMA, 'smma', window_fast, window_slow, "bearish")


# --- EPMA signals ---

@RuleRegistry.register("is_above_epma")
def is_above_epma(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if the current price is above the End Point Moving Average (EPMA / LSMA).

    EPMA is the endpoint of a linear regression over the window, projecting the
    trend to "now" rather than averaging past values.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EPMA window in bars. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > EPMA, False otherwise.
    """
    return _ma_is_above(df, EPMA, 'epma', window)


@RuleRegistry.register("epma_cross_up")
def epma_cross_up(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """
    Detect a bullish EPMA crossover (fast EPMA crosses above slow EPMA).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EPMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow EPMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bullish EPMA crossover detected on the current bar.
    """
    return _ma_crossover(df, EPMA, 'epma', window_fast, window_slow, "bullish")


@RuleRegistry.register("epma_cross_down")
def epma_cross_down(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """
    Detect a bearish EPMA crossover (fast EPMA crosses below slow EPMA).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EPMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow EPMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bearish EPMA crossover detected on the current bar.
    """
    return _ma_crossover(df, EPMA, 'epma', window_fast, window_slow, "bearish")


# =============================================================================
# Wave B Moving Average Signals (HMA, ALMA, T3, MAMA)
# =============================================================================
# HMA, ALMA, T3 follow the same is_above / cross_up / cross_down pattern as
# the Wave A MAs. MAMA is special: it returns MAMA+FAMA in a single compute
# call and signals are based on MAMA/FAMA crossovers (not two separate-window
# computations), so they don't use the _ma_crossover helper.


# --- HMA signals ---

@RuleRegistry.register("is_above_hma")
def is_above_hma(df: pd.DataFrame, window: int = 16) -> bool:
    """
    Check if the current price is above the Hull Moving Average (HMA).

    HMA tracks price with very low lag while remaining smoother than WMA.
    A common crypto trend filter.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): HMA window in bars. Range: 4-200. Default: 16.

    Returns:
        bool: True if close > HMA, False otherwise.
    """
    return _ma_is_above(df, HMA, 'hma', window)


@RuleRegistry.register("hma_cross_up")
def hma_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 25) -> bool:
    """
    Detect a bullish HMA crossover (fast HMA crosses above slow HMA).

    Low-lag crossover; fires earlier than SMA/EMA equivalents.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast HMA window. Range: 4-100. Default: 9.
        window_slow (int): Slow HMA window. Range: 4-200. Default: 25.

    Returns:
        bool: True if bullish HMA crossover detected on the current bar.
    """
    return _ma_crossover(df, HMA, 'hma', window_fast, window_slow, "bullish")


@RuleRegistry.register("hma_cross_down")
def hma_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 25) -> bool:
    """
    Detect a bearish HMA crossover (fast HMA crosses below slow HMA).

    Low-lag crossover; fires earlier than SMA/EMA equivalents.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast HMA window. Range: 4-100. Default: 9.
        window_slow (int): Slow HMA window. Range: 4-200. Default: 25.

    Returns:
        bool: True if bearish HMA crossover detected on the current bar.
    """
    return _ma_crossover(df, HMA, 'hma', window_fast, window_slow, "bearish")


# --- ALMA signals ---

@RuleRegistry.register("is_above_alma")
def is_above_alma(df: pd.DataFrame, window: int = 21, offset: float = 0.85, sigma: float = 6.0) -> bool:
    """
    Check if the current price is above the Arnaud Legoux Moving Average (ALMA).

    ALMA is a Gaussian-weighted MA that can be tuned to react faster (offset
    near 1, lower sigma) or smoother (offset near 0, higher sigma).

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ALMA window in bars. Range: 2-200. Default: 21.
        offset (float): Weight center, 0=oldest, 1=newest. Range: 0.0-1.0. Default: 0.85.
        sigma (float): Gaussian spread. Higher = smoother. Range: 0.1-20.0. Default: 6.0.

    Returns:
        bool: True if close > ALMA, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window:
        return False
    result = ALMA.compute(data={'close': closes}, params={'window': window, 'offset': offset, 'sigma': sigma})
    alma = result['alma']
    if alma.empty or pd.isna(alma.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > alma.iloc[-1])


@RuleRegistry.register("alma_cross_up")
def alma_cross_up(
    df: pd.DataFrame,
    window_fast: int = 9,
    window_slow: int = 21,
    offset: float = 0.85,
    sigma: float = 6.0,
) -> bool:
    """
    Detect a bullish ALMA crossover (fast ALMA crosses above slow ALMA).

    Both ALMAs use the same offset and sigma; only the window differs.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast ALMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow ALMA window. Range: 2-200. Default: 21.
        offset (float): Weight center. Range: 0.0-1.0. Default: 0.85.
        sigma (float): Gaussian spread. Range: 0.1-20.0. Default: 6.0.

    Returns:
        bool: True if bullish ALMA crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    common = {'offset': offset, 'sigma': sigma}
    fast = ALMA.compute(data={'close': closes}, params={'window': window_fast, **common})['alma']
    slow = ALMA.compute(data={'close': closes}, params={'window': window_slow, **common})['alma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)


@RuleRegistry.register("alma_cross_down")
def alma_cross_down(
    df: pd.DataFrame,
    window_fast: int = 9,
    window_slow: int = 21,
    offset: float = 0.85,
    sigma: float = 6.0,
) -> bool:
    """
    Detect a bearish ALMA crossover (fast ALMA crosses below slow ALMA).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast ALMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow ALMA window. Range: 2-200. Default: 21.
        offset (float): Weight center. Range: 0.0-1.0. Default: 0.85.
        sigma (float): Gaussian spread. Range: 0.1-20.0. Default: 6.0.

    Returns:
        bool: True if bearish ALMA crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    common = {'offset': offset, 'sigma': sigma}
    fast = ALMA.compute(data={'close': closes}, params={'window': window_fast, **common})['alma']
    slow = ALMA.compute(data={'close': closes}, params={'window': window_slow, **common})['alma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


# --- T3 signals ---

@RuleRegistry.register("is_above_t3")
def is_above_t3(df: pd.DataFrame, window: int = 10, volume_factor: float = 0.7) -> bool:
    """
    Check if the current price is above the Tillson T3 moving average.

    T3 is a smooth low-lag MA that combines 6 EMAs via the volume factor.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): T3 window in bars. Range: 2-200. Default: 10.
        volume_factor (float): Tillson volume factor, controls smoothness. Range: 0.0-1.0. Default: 0.7.

    Returns:
        bool: True if close > T3, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window * 6:
        return False
    result = T3.compute(data={'close': closes}, params={'window': window, 'volume_factor': volume_factor})
    t3 = result['t3']
    if t3.empty or pd.isna(t3.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > t3.iloc[-1])


@RuleRegistry.register("t3_cross_up")
def t3_cross_up(
    df: pd.DataFrame,
    window_fast: int = 5,
    window_slow: int = 10,
    volume_factor: float = 0.7,
) -> bool:
    """
    Detect a bullish T3 crossover (fast T3 crosses above slow T3).

    Very smooth, low-lag crossover. Both T3s share the same volume_factor.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast T3 window. Range: 2-100. Default: 5.
        window_slow (int): Slow T3 window. Range: 2-200. Default: 10.
        volume_factor (float): Tillson volume factor. Range: 0.0-1.0. Default: 0.7.

    Returns:
        bool: True if bullish T3 crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow * 6 + 1:
        return False
    common = {'volume_factor': volume_factor}
    fast = T3.compute(data={'close': closes}, params={'window': window_fast, **common})['t3']
    slow = T3.compute(data={'close': closes}, params={'window': window_slow, **common})['t3']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)


@RuleRegistry.register("t3_cross_down")
def t3_cross_down(
    df: pd.DataFrame,
    window_fast: int = 5,
    window_slow: int = 10,
    volume_factor: float = 0.7,
) -> bool:
    """
    Detect a bearish T3 crossover (fast T3 crosses below slow T3).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast T3 window. Range: 2-100. Default: 5.
        window_slow (int): Slow T3 window. Range: 2-200. Default: 10.
        volume_factor (float): Tillson volume factor. Range: 0.0-1.0. Default: 0.7.

    Returns:
        bool: True if bearish T3 crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow * 6 + 1:
        return False
    common = {'volume_factor': volume_factor}
    fast = T3.compute(data={'close': closes}, params={'window': window_fast, **common})['t3']
    slow = T3.compute(data={'close': closes}, params={'window': window_slow, **common})['t3']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


# --- MAMA signals ---

def _mama_compute(df: pd.DataFrame, fast_limit: float, slow_limit: float):
    """Helper: compute MAMA+FAMA once for signal evaluation."""
    closes = df["Close"]
    # MAMA now consumes median price per Ehlers, and masks 40 warmup bars rather than 6.
    if len(closes) <= MAMA._WARMUP_BARS:
        return None
    result = MAMA.compute(data={'high': df["High"], 'low': df["Low"]},
                          params={'fast_limit': fast_limit, 'slow_limit': slow_limit})
    mama, fama = result['mama'], result['fama']
    if len(mama) < 2 or pd.isna(mama.iloc[-1]) or pd.isna(fama.iloc[-1]):
        return None
    return mama, fama


@RuleRegistry.register("is_above_mama")
def is_above_mama(df: pd.DataFrame, fast_limit: float = 0.5, slow_limit: float = 0.05) -> bool:
    """
    Check if the current price is above the MESA Adaptive Moving Average (MAMA).

    MAMA adapts its smoothing to volatility via a Hilbert transform.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast_limit (float): Upper alpha bound (fast response). Range: 0.1-1.0. Default: 0.5.
        slow_limit (float): Lower alpha bound (slow response). Range: 0.01-0.5. Default: 0.05.

    Returns:
        bool: True if close > MAMA, False otherwise.
    """
    out = _mama_compute(df, fast_limit, slow_limit)
    if out is None:
        return False
    mama, _ = out
    return bool(df["Close"].iloc[-1] > mama.iloc[-1])


@RuleRegistry.register("mama_cross_up")
def mama_cross_up(df: pd.DataFrame, fast_limit: float = 0.5, slow_limit: float = 0.05) -> bool:
    """
    Detect a bullish MAMA/FAMA crossover (MAMA crosses above FAMA).

    Classic Ehlers entry signal: MAMA rising above FAMA signals an uptrend.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast_limit (float): Upper alpha bound. Range: 0.1-1.0. Default: 0.5.
        slow_limit (float): Lower alpha bound. Range: 0.01-0.5. Default: 0.05.

    Returns:
        bool: True if bullish MAMA/FAMA crossover detected on the current bar.
    """
    out = _mama_compute(df, fast_limit, slow_limit)
    if out is None:
        return False
    mama, fama = out
    if pd.isna(mama.iloc[-2]) or pd.isna(fama.iloc[-2]):
        return False
    return bool(mama.iloc[-2] <= fama.iloc[-2] and mama.iloc[-1] > fama.iloc[-1])


@RuleRegistry.register("mama_cross_down")
def mama_cross_down(df: pd.DataFrame, fast_limit: float = 0.5, slow_limit: float = 0.05) -> bool:
    """
    Detect a bearish MAMA/FAMA crossover (MAMA crosses below FAMA).

    Classic Ehlers exit signal: MAMA falling below FAMA signals a downtrend.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast_limit (float): Upper alpha bound. Range: 0.1-1.0. Default: 0.5.
        slow_limit (float): Lower alpha bound. Range: 0.01-0.5. Default: 0.05.

    Returns:
        bool: True if bearish MAMA/FAMA crossover detected on the current bar.
    """
    out = _mama_compute(df, fast_limit, slow_limit)
    if out is None:
        return False
    mama, fama = out
    if pd.isna(mama.iloc[-2]) or pd.isna(fama.iloc[-2]):
        return False
    return bool(mama.iloc[-2] >= fama.iloc[-2] and mama.iloc[-1] < fama.iloc[-1])


# =============================================================================
# Wave E Trend Signals (HeikinAshi, Chandelier, Alligator, SuperTrend)
# =============================================================================


# --- HeikinAshi signals ---

@RuleRegistry.register("heikin_ashi_bullish")
def heikin_ashi_bullish(df: pd.DataFrame) -> bool:
    """
    Check if the current Heikin-Ashi candle is bullish (HA_close > HA_open).

    A bullish HA candle indicates buying pressure on the smoothed bar.
    Strings of bullish HA candles indicate a sustained uptrend.

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if HA_close > HA_open on the current bar.
    """
    if len(df) < 1:
        return False
    out = HeikinAshi.compute(
        data={'open': df["Open"], 'high': df["High"], 'low': df["Low"], 'close': df["Close"]}, params={}
    )
    if pd.isna(out['ha_close'].iloc[-1]) or pd.isna(out['ha_open'].iloc[-1]):
        return False
    return bool(out['ha_close'].iloc[-1] > out['ha_open'].iloc[-1])


@RuleRegistry.register("heikin_ashi_bearish")
def heikin_ashi_bearish(df: pd.DataFrame) -> bool:
    """
    Check if the current Heikin-Ashi candle is bearish (HA_close < HA_open).

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if HA_close < HA_open on the current bar.
    """
    if len(df) < 1:
        return False
    out = HeikinAshi.compute(
        data={'open': df["Open"], 'high': df["High"], 'low': df["Low"], 'close': df["Close"]}, params={}
    )
    if pd.isna(out['ha_close'].iloc[-1]) or pd.isna(out['ha_open'].iloc[-1]):
        return False
    return bool(out['ha_close'].iloc[-1] < out['ha_open'].iloc[-1])


# --- ChandelierExit signals ---

def _chandelier_stops(df: pd.DataFrame, window: int, multiplier: float):
    """Helper: compute long and short stops, return None if insufficient data."""
    if len(df) < window + 1:
        return None
    out = ChandelierExit.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'multiplier': multiplier},
    )
    return out['long_stop'], out['short_stop']


@RuleRegistry.register("chandelier_long_stop_hit")
def chandelier_long_stop_hit(df: pd.DataFrame, window: int = 22, multiplier: float = 3.0) -> bool:
    """
    Check if close has breached the Chandelier long stop (close < long_stop).

    If holding a long position, this is your exit trigger.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling high/ATR window. Range: 5-100. Default: 22.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if close < long_stop, False otherwise.
    """
    stops = _chandelier_stops(df, window, multiplier)
    if stops is None:
        return False
    long_stop, _ = stops
    if pd.isna(long_stop.iloc[-1]):
        return False
    return bool(df["Close"].iloc[-1] < long_stop.iloc[-1])


@RuleRegistry.register("chandelier_short_stop_hit")
def chandelier_short_stop_hit(df: pd.DataFrame, window: int = 22, multiplier: float = 3.0) -> bool:
    """
    Check if close has breached the Chandelier short stop (close > short_stop).

    If holding a short position, this is your exit trigger.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling low/ATR window. Range: 5-100. Default: 22.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if close > short_stop, False otherwise.
    """
    stops = _chandelier_stops(df, window, multiplier)
    if stops is None:
        return False
    _, short_stop = stops
    if pd.isna(short_stop.iloc[-1]):
        return False
    return bool(df["Close"].iloc[-1] > short_stop.iloc[-1])


# --- WilliamsAlligator signals ---

def _alligator_lines(df: pd.DataFrame, jaw: int, teeth: int, lips: int,
                     jaw_offset: int, teeth_offset: int, lips_offset: int):
    """Helper: compute alligator lines, return None if insufficient data."""
    if len(df) < jaw + jaw_offset + 1:
        return None
    out = WilliamsAlligator.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={
            'jaw': jaw, 'teeth': teeth, 'lips': lips,
            'jaw_offset': jaw_offset, 'teeth_offset': teeth_offset, 'lips_offset': lips_offset,
        },
    )
    return out['jaw'], out['teeth'], out['lips']


@RuleRegistry.register("alligator_bullish")
def alligator_bullish(
    df: pd.DataFrame,
    jaw: int = 13, teeth: int = 8, lips: int = 5,
    jaw_offset: int = 8, teeth_offset: int = 5, lips_offset: int = 3,
) -> bool:
    """
    Check if Williams Alligator lines are in bullish alignment (lips > teeth > jaw).

    Bill Williams's "hungry alligator" state: strong uptrend, all lines
    spreading upward.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        jaw (int): Jaw SMMA period. Range: 5-50. Default: 13.
        teeth (int): Teeth SMMA period. Range: 3-30. Default: 8.
        lips (int): Lips SMMA period. Range: 2-20. Default: 5.
        jaw_offset (int): Jaw forward shift. Range: 0-20. Default: 8.
        teeth_offset (int): Teeth forward shift. Range: 0-15. Default: 5.
        lips_offset (int): Lips forward shift. Range: 0-10. Default: 3.

    Returns:
        bool: True if lips > teeth > jaw on the current bar.
    """
    lines = _alligator_lines(df, jaw, teeth, lips, jaw_offset, teeth_offset, lips_offset)
    if lines is None:
        return False
    jaw_s, teeth_s, lips_s = lines
    if pd.isna(jaw_s.iloc[-1]) or pd.isna(teeth_s.iloc[-1]) or pd.isna(lips_s.iloc[-1]):
        return False
    return bool(lips_s.iloc[-1] > teeth_s.iloc[-1] > jaw_s.iloc[-1])


@RuleRegistry.register("alligator_bearish")
def alligator_bearish(
    df: pd.DataFrame,
    jaw: int = 13, teeth: int = 8, lips: int = 5,
    jaw_offset: int = 8, teeth_offset: int = 5, lips_offset: int = 3,
) -> bool:
    """
    Check if Williams Alligator lines are in bearish alignment (lips < teeth < jaw).

    Strong downtrend, all lines spreading downward.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        jaw (int): Jaw SMMA period. Range: 5-50. Default: 13.
        teeth (int): Teeth SMMA period. Range: 3-30. Default: 8.
        lips (int): Lips SMMA period. Range: 2-20. Default: 5.
        jaw_offset (int): Jaw forward shift. Range: 0-20. Default: 8.
        teeth_offset (int): Teeth forward shift. Range: 0-15. Default: 5.
        lips_offset (int): Lips forward shift. Range: 0-10. Default: 3.

    Returns:
        bool: True if lips < teeth < jaw on the current bar.
    """
    lines = _alligator_lines(df, jaw, teeth, lips, jaw_offset, teeth_offset, lips_offset)
    if lines is None:
        return False
    jaw_s, teeth_s, lips_s = lines
    if pd.isna(jaw_s.iloc[-1]) or pd.isna(teeth_s.iloc[-1]) or pd.isna(lips_s.iloc[-1]):
        return False
    return bool(lips_s.iloc[-1] < teeth_s.iloc[-1] < jaw_s.iloc[-1])


@RuleRegistry.register("alligator_sleeping")
def alligator_sleeping(
    df: pd.DataFrame,
    jaw: int = 13, teeth: int = 8, lips: int = 5,
    jaw_offset: int = 8, teeth_offset: int = 5, lips_offset: int = 3,
) -> bool:
    """
    Check if the Williams Alligator is sleeping (lines tangled, no trend).

    True when lines are neither strictly bullish-aligned nor bearish-aligned.
    Used as a no-trade filter during consolidation.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        jaw (int): Jaw SMMA period. Range: 5-50. Default: 13.
        teeth (int): Teeth SMMA period. Range: 3-30. Default: 8.
        lips (int): Lips SMMA period. Range: 2-20. Default: 5.
        jaw_offset (int): Jaw forward shift. Range: 0-20. Default: 8.
        teeth_offset (int): Teeth forward shift. Range: 0-15. Default: 5.
        lips_offset (int): Lips forward shift. Range: 0-10. Default: 3.

    Returns:
        bool: True if lines are tangled (no strict bullish or bearish alignment).
    """
    lines = _alligator_lines(df, jaw, teeth, lips, jaw_offset, teeth_offset, lips_offset)
    if lines is None:
        return False
    jaw_s, teeth_s, lips_s = lines
    if pd.isna(jaw_s.iloc[-1]) or pd.isna(teeth_s.iloc[-1]) or pd.isna(lips_s.iloc[-1]):
        return False
    j, t, l = jaw_s.iloc[-1], teeth_s.iloc[-1], lips_s.iloc[-1]
    bullish = l > t > j
    bearish = l < t < j
    return not (bullish or bearish)


# --- SuperTrend signals ---

def _supertrend_direction(df: pd.DataFrame, window: int, multiplier: float):
    """Helper: compute SuperTrend direction series, return None if insufficient data."""
    if len(df) < window + 1:
        return None
    out = SuperTrend.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'multiplier': multiplier},
    )
    return out['direction']


@RuleRegistry.register("supertrend_long")
def supertrend_long(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """
    Check if SuperTrend is in the long regime (+1 direction).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if SuperTrend direction == +1.
    """
    direction = _supertrend_direction(df, window, multiplier)
    if direction is None or pd.isna(direction.iloc[-1]):
        return False
    return direction.iloc[-1] == 1


@RuleRegistry.register("supertrend_short")
def supertrend_short(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """
    Check if SuperTrend is in the short regime (-1 direction).

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if SuperTrend direction == -1.
    """
    direction = _supertrend_direction(df, window, multiplier)
    if direction is None or pd.isna(direction.iloc[-1]):
        return False
    return direction.iloc[-1] == -1


@RuleRegistry.register("supertrend_flip_up")
def supertrend_flip_up(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """
    Detect SuperTrend flipping from short (-1) to long (+1).

    Classic SuperTrend bullish entry signal.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if direction flipped -1 -> +1 on the current bar.
    """
    direction = _supertrend_direction(df, window, multiplier)
    if direction is None or len(direction) < 2:
        return False
    prev, curr = direction.iloc[-2], direction.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    return bool(prev == -1 and curr == 1)


@RuleRegistry.register("supertrend_flip_down")
def supertrend_flip_down(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """
    Detect SuperTrend flipping from long (+1) to short (-1).

    Classic SuperTrend bearish entry signal.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if direction flipped +1 -> -1 on the current bar.
    """
    direction = _supertrend_direction(df, window, multiplier)
    if direction is None or len(direction) < 2:
        return False
    prev, curr = direction.iloc[-2], direction.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    return bool(prev == 1 and curr == -1)


# =============================================================================
# Wave G Signal Patterns (MARibbon, TTMSqueeze, Divergence, MultiTFTrend)
# =============================================================================

from mangrove_kb.indicators import TTMSqueeze  # local import to avoid circular issues at module load


# --- MA Ribbon signals ---

_DEFAULT_RIBBON_WINDOWS = (5, 8, 13, 21, 34, 55, 89, 144)


@RuleRegistry.register("ma_ribbon_bullish")
def ma_ribbon_bullish(df: pd.DataFrame, windows: tuple = _DEFAULT_RIBBON_WINDOWS) -> bool:
    """
    Check if all MAs in the ribbon are in strict bullish alignment (faster above slower).

    Uses 8 Fibonacci-spaced SMAs by default. Strict alignment means
    SMA(5) > SMA(8) > SMA(13) > ... > SMA(144). This is a strong trend filter
    -- when true, the market is in a clear uptrend across all horizons.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        windows (tuple): Strictly increasing tuple of SMA periods. Range: 2-1000 per element. Default: (5, 8, 13, 21, 34, 55, 89, 144).

    Returns:
        bool: True if ribbon is bullish-aligned on the current bar.
    """
    closes = df["Close"]
    windows_list = list(windows)
    if len(closes) < max(windows_list):
        return False
    out = MARibbon.compute(data={'close': closes}, params={'windows': windows_list})
    if pd.isna(out['ribbon_bullish'].iloc[-1]):
        return False
    return bool(out['ribbon_bullish'].iloc[-1])


@RuleRegistry.register("ma_ribbon_bearish")
def ma_ribbon_bearish(df: pd.DataFrame, windows: tuple = _DEFAULT_RIBBON_WINDOWS) -> bool:
    """
    Check if all MAs in the ribbon are in strict bearish alignment (faster below slower).

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        windows (tuple): Strictly increasing tuple of SMA periods. Range: 2-1000 per element. Default: (5, 8, 13, 21, 34, 55, 89, 144).

    Returns:
        bool: True if ribbon is bearish-aligned on the current bar.
    """
    closes = df["Close"]
    windows_list = list(windows)
    if len(closes) < max(windows_list):
        return False
    out = MARibbon.compute(data={'close': closes}, params={'windows': windows_list})
    if pd.isna(out['ribbon_bearish'].iloc[-1]):
        return False
    return bool(out['ribbon_bearish'].iloc[-1])


@RuleRegistry.register("ma_ribbon_tangled")
def ma_ribbon_tangled(df: pd.DataFrame, windows: tuple = _DEFAULT_RIBBON_WINDOWS) -> bool:
    """
    Check if MAs in the ribbon are tangled (no strict alignment -- consolidation filter).

    Useful as a no-trade filter during choppy markets.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        windows (tuple): Strictly increasing tuple of SMA periods. Range: 2-1000 per element. Default: (5, 8, 13, 21, 34, 55, 89, 144).

    Returns:
        bool: True if ribbon is neither bullish nor bearish aligned.
    """
    closes = df["Close"]
    windows_list = list(windows)
    if len(closes) < max(windows_list):
        return False
    out = MARibbon.compute(data={'close': closes}, params={'windows': windows_list})
    if pd.isna(out['ribbon_tangled'].iloc[-1]):
        return False
    return bool(out['ribbon_tangled'].iloc[-1])


# --- TTM Squeeze signals ---

_TTM_DEFAULTS = dict(bb_window=20, bb_std=2.0, kc_window=20, kc_atr_mult=1.5, mom_window=12)


@RuleRegistry.register("ttm_squeeze_active")
def ttm_squeeze_active(
    df: pd.DataFrame,
    bb_window: int = 20, bb_std: float = 2.0,
    kc_window: int = 20, kc_atr_mult: float = 1.5,
    mom_window: int = 12,
) -> bool:
    """
    Check if the TTM Squeeze is active (BB inside KC -- volatility contraction).

    Use as a no-breakout filter: when true, market is coiled and waiting
    for a directional move.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        bb_window (int): Bollinger Band window. Range: 5-100. Default: 20.
        bb_std (float): Bollinger std multiplier. Range: 1.0-4.0. Default: 2.0.
        kc_window (int): Keltner Channel window (used for both EMA and ATR). Range: 5-100. Default: 20.
        kc_atr_mult (float): Keltner ATR multiplier. Range: 0.5-3.0. Default: 1.5.
        mom_window (int): Momentum regression window. Range: 5-50. Default: 12.

    Returns:
        bool: True if squeeze is on.
    """
    if len(df) < max(bb_window, kc_window) + 1:
        return False
    out = TTMSqueeze.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'bb_window': bb_window, 'bb_std': bb_std, 'kc_window': kc_window,
                'kc_atr_mult': kc_atr_mult, 'mom_window': mom_window},
    )
    if pd.isna(out['squeeze_on'].iloc[-1]):
        return False
    return bool(out['squeeze_on'].iloc[-1])


@RuleRegistry.register("ttm_squeeze_fired_bullish")
def ttm_squeeze_fired_bullish(
    df: pd.DataFrame,
    bb_window: int = 20, bb_std: float = 2.0,
    kc_window: int = 20, kc_atr_mult: float = 1.5,
    mom_window: int = 12,
) -> bool:
    """
    Detect TTM Squeeze release with bullish momentum.

    Fires when the squeeze just ended (was on previous bar, off now) AND
    momentum is positive. Classic Carter entry signal.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        bb_window (int): Bollinger Band window. Range: 5-100. Default: 20.
        bb_std (float): Bollinger std multiplier. Range: 1.0-4.0. Default: 2.0.
        kc_window (int): Keltner Channel window. Range: 5-100. Default: 20.
        kc_atr_mult (float): Keltner ATR multiplier. Range: 0.5-3.0. Default: 1.5.
        mom_window (int): Momentum regression window. Range: 5-50. Default: 12.

    Returns:
        bool: True on bar where squeeze fires with positive momentum.
    """
    if len(df) < max(bb_window, kc_window) + 2:
        return False
    out = TTMSqueeze.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'bb_window': bb_window, 'bb_std': bb_std, 'kc_window': kc_window,
                'kc_atr_mult': kc_atr_mult, 'mom_window': mom_window},
    )
    fired = out['squeeze_fired'].iloc[-1]
    mom = out['momentum'].iloc[-1]
    if pd.isna(fired) or pd.isna(mom):
        return False
    return bool(fired and mom > 0)


@RuleRegistry.register("ttm_squeeze_fired_bearish")
def ttm_squeeze_fired_bearish(
    df: pd.DataFrame,
    bb_window: int = 20, bb_std: float = 2.0,
    kc_window: int = 20, kc_atr_mult: float = 1.5,
    mom_window: int = 12,
) -> bool:
    """
    Detect TTM Squeeze release with bearish momentum.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        bb_window (int): Bollinger Band window. Range: 5-100. Default: 20.
        bb_std (float): Bollinger std multiplier. Range: 1.0-4.0. Default: 2.0.
        kc_window (int): Keltner Channel window. Range: 5-100. Default: 20.
        kc_atr_mult (float): Keltner ATR multiplier. Range: 0.5-3.0. Default: 1.5.
        mom_window (int): Momentum regression window. Range: 5-50. Default: 12.

    Returns:
        bool: True on bar where squeeze fires with negative momentum.
    """
    if len(df) < max(bb_window, kc_window) + 2:
        return False
    out = TTMSqueeze.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'bb_window': bb_window, 'bb_std': bb_std, 'kc_window': kc_window,
                'kc_atr_mult': kc_atr_mult, 'mom_window': mom_window},
    )
    fired = out['squeeze_fired'].iloc[-1]
    mom = out['momentum'].iloc[-1]
    if pd.isna(fired) or pd.isna(mom):
        return False
    return bool(fired and mom < 0)


# --- Divergence signals (RSI-based by default; user supplies indicator via helper) ---

def _rsi_divergence(df: pd.DataFrame, rsi_window: int, swing_window: int, min_swing_distance: int):
    closes = df["Close"]
    if len(closes) < rsi_window + 2 * swing_window + min_swing_distance:
        return None
    rsi = RSI.compute(data={'close': closes}, params={'window': rsi_window})['rsi']
    out = Divergence.compute(
        data={'price': closes, 'indicator': rsi},
        params={'swing_window': swing_window, 'min_swing_distance': min_swing_distance},
    )
    return out


@RuleRegistry.register("rsi_bullish_divergence")
def rsi_bullish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """
    Detect a regular bullish RSI divergence: price lower low, RSI higher low.

    Classic reversal signal indicating bearish momentum is weakening.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between the two swing points compared. Range: 3-50. Default: 10.

    Returns:
        bool: True on bar where regular bullish divergence is confirmed.
    """
    out = _rsi_divergence(df, rsi_window, swing_window, min_swing_distance)
    if out is None:
        return False
    return bool(out['regular_bullish'].iloc[-1])


@RuleRegistry.register("rsi_bearish_divergence")
def rsi_bearish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """
    Detect a regular bearish RSI divergence: price higher high, RSI lower high.

    Classic reversal signal indicating bullish momentum is weakening.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between the two swing points compared. Range: 3-50. Default: 10.

    Returns:
        bool: True on bar where regular bearish divergence is confirmed.
    """
    out = _rsi_divergence(df, rsi_window, swing_window, min_swing_distance)
    if out is None:
        return False
    return bool(out['regular_bearish'].iloc[-1])


@RuleRegistry.register("rsi_hidden_bullish_divergence")
def rsi_hidden_bullish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """
    Detect a hidden bullish RSI divergence: price higher low, RSI lower low.

    Continuation signal in an uptrend -- indicates the uptrend is still
    intact despite a pullback.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between swings. Range: 3-50. Default: 10.

    Returns:
        bool: True on bar where hidden bullish divergence is confirmed.
    """
    out = _rsi_divergence(df, rsi_window, swing_window, min_swing_distance)
    if out is None:
        return False
    return bool(out['hidden_bullish'].iloc[-1])


@RuleRegistry.register("rsi_hidden_bearish_divergence")
def rsi_hidden_bearish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """
    Detect a hidden bearish RSI divergence: price lower high, RSI higher high.

    Continuation signal in a downtrend.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between swings. Range: 3-50. Default: 10.

    Returns:
        bool: True on bar where hidden bearish divergence is confirmed.
    """
    out = _rsi_divergence(df, rsi_window, swing_window, min_swing_distance)
    if out is None:
        return False
    return bool(out['hidden_bearish'].iloc[-1])


# --- Multi-Timeframe Trend signals ---

@RuleRegistry.register("multi_tf_trend_bullish")
def multi_tf_trend_bullish(
    df: pd.DataFrame, higher_tf: str = "1W", window: int = 10, slope_threshold: float = 0.0,
) -> bool:
    """
    Check if the higher-timeframe EMA is rising (trend confirmation filter).

    Requires a DatetimeIndex. Resamples to the specified higher timeframe,
    computes an EMA on the resampled closes, and returns True if the EMA
    slope is positive. Broadcasts back to the current bar's timestamp so
    lower-TF signals can be filtered by higher-TF trend.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data (DatetimeIndex required).
        higher_tf (str): Pandas offset alias for the higher timeframe. Range: 1min-1Y. Default: 1W.
        window (int): EMA period on the resampled close. Range: 2-100. Default: 10.
        slope_threshold (float): Relative slope threshold for non-flat classification. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if higher-TF trend == +1 on the current bar.
    """
    closes = df["Close"]
    if len(closes) < 2 or not isinstance(closes.index, pd.DatetimeIndex):
        return False
    out = MultiTFTrend.compute(
        data={'close': closes},
        params={'higher_tf': higher_tf, 'window': window, 'slope_threshold': slope_threshold},
    )
    val = out['higher_tf_trend'].iloc[-1]
    if pd.isna(val):
        return False
    return val == 1


@RuleRegistry.register("multi_tf_trend_bearish")
def multi_tf_trend_bearish(
    df: pd.DataFrame, higher_tf: str = "1W", window: int = 10, slope_threshold: float = 0.0,
) -> bool:
    """
    Check if the higher-timeframe EMA is falling.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data (DatetimeIndex required).
        higher_tf (str): Pandas offset alias. Range: 1min-1Y. Default: 1W.
        window (int): EMA period. Range: 2-100. Default: 10.
        slope_threshold (float): Slope threshold for non-flat. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if higher-TF trend == -1 on the current bar.
    """
    closes = df["Close"]
    if len(closes) < 2 or not isinstance(closes.index, pd.DatetimeIndex):
        return False
    out = MultiTFTrend.compute(
        data={'close': closes},
        params={'higher_tf': higher_tf, 'window': window, 'slope_threshold': slope_threshold},
    )
    val = out['higher_tf_trend'].iloc[-1]
    if pd.isna(val):
        return False
    return val == -1
