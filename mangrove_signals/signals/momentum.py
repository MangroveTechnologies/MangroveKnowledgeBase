"""Momentum-based trading signals.

This module contains signal functions based on momentum indicators including:
- RSI (Relative Strength Index)
- TSI (True Strength Index)
- Stochastic Oscillator
- Williams %R
- Ultimate Oscillator
- KAMA (Kaufman Adaptive Moving Average)
- ROC (Rate of Change)
- Awesome Oscillator
- Stochastic RSI
- PPO (Percentage Price Oscillator)
- PVO (Percentage Volume Oscillator)
"""

import logging

import pandas as pd

from mangrove_signals.registry import RuleRegistry

# Import momentum indicator classes
from mangrove_signals.indicators import (
    RSI,
    TSI,
    UltimateOscillator,
    StochasticOscillator,
    KAMA,
    ROC,
    AwesomeOscillator,
    WilliamsR,
    StochRSI,
    PPO,
    PVO,
)

logger = logging.getLogger(__name__)


# =============================================================================
# RSI-Based Signals
# =============================================================================

@RuleRegistry.register("rsi_overbought")
def rsi_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 70.0) -> bool:
    """
    Check if RSI is above the overbought threshold.

    RSI values above 70 typically indicate overbought conditions,
    suggesting the asset may be due for a pullback. In crypto markets, consider higher thresholds (80/20) during strong trends.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold. Range: 50-100. Default: 70.0.

    Returns:
        bool: True if RSI > threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']
    if pd.isna(rsi.iloc[-1]):
        return False

    return float(rsi.iloc[-1]) > threshold


@RuleRegistry.register("rsi_oversold")
def rsi_oversold(df: pd.DataFrame, window: int = 14, threshold: float = 30.0) -> bool:
    """
    Check if RSI is below the oversold threshold.

    RSI values below 30 typically indicate oversold conditions,
    suggesting the asset may be due for a bounce. In crypto markets, consider higher thresholds (80/20) during strong trends.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Oversold threshold. Range: 0-50. Default: 30.0.

    Returns:
        bool: True if RSI < threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']
    if pd.isna(rsi.iloc[-1]):
        return False

    return float(rsi.iloc[-1]) < threshold


@RuleRegistry.register("rsi_cross_up")
def rsi_cross_up(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """
    Check if RSI crosses above a threshold level.

    Returns True when RSI was at or below the threshold in the previous bar
    and is now above the threshold in the current bar. In crypto markets, consider higher thresholds (80/20) during strong trends.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Threshold level to cross above. Range: 0-100. Default: 50.0.

    Returns:
        bool: True if RSI crosses above threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']

    if len(rsi) < 2:
        return False

    prev_rsi = rsi.iloc[-2]
    curr_rsi = rsi.iloc[-1]

    if pd.isna(prev_rsi) or pd.isna(curr_rsi):
        return False

    # Check for crossover: RSI was below/equal to threshold, now above
    return prev_rsi <= threshold and curr_rsi > threshold


@RuleRegistry.register("rsi_cross_down")
def rsi_cross_down(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """
    Check if RSI crosses below a threshold level.

    Returns True when RSI was at or above the threshold in the previous bar
    and is now below the threshold in the current bar. In crypto markets, consider higher thresholds (80/20) during strong trends.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Threshold level to cross below. Range: 0-100. Default: 50.0.

    Returns:
        bool: True if RSI crosses below threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']

    if len(rsi) < 2:
        return False

    prev_rsi = rsi.iloc[-2]
    curr_rsi = rsi.iloc[-1]

    if pd.isna(prev_rsi) or pd.isna(curr_rsi):
        return False

    # Check for crossover: RSI was above/equal to threshold, now below
    return prev_rsi >= threshold and curr_rsi < threshold


# =============================================================================
# Stochastic Signals
# =============================================================================

@RuleRegistry.register("stoch_overbought")
def stoch_overbought(
    df: pd.DataFrame, window: int = 14, smooth_window: int = 3, threshold: float = 80.0
) -> bool:
    """
    Check if Stochastic %K is above the overbought threshold.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): %K period. Range: 5-50. Default: 14.
        smooth_window (int): %K smoothing period. Range: 1-10. Default: 3.
        threshold (float): Overbought threshold. Range: 70-100. Default: 80.0.

    Returns:
        bool: True if %K > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = StochasticOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'smooth_window': smooth_window}
    )
    stoch_k = result['stoch_k']

    if pd.isna(stoch_k.iloc[-1]):
        return False

    return float(stoch_k.iloc[-1]) > threshold


@RuleRegistry.register("stoch_oversold")
def stoch_oversold(
    df: pd.DataFrame, window: int = 14, smooth_window: int = 3, threshold: float = 20.0
) -> bool:
    """
    Check if Stochastic %K is below the oversold threshold.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): %K period. Range: 5-50. Default: 14.
        smooth_window (int): %K smoothing period. Range: 1-10. Default: 3.
        threshold (float): Oversold threshold. Range: 0-30. Default: 20.0.

    Returns:
        bool: True if %K < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = StochasticOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'smooth_window': smooth_window}
    )
    stoch_k = result['stoch_k']

    if pd.isna(stoch_k.iloc[-1]):
        return False

    return float(stoch_k.iloc[-1]) < threshold


# =============================================================================
# Williams %R Signals
# =============================================================================

@RuleRegistry.register("williams_r_overbought")
def williams_r_overbought(df: pd.DataFrame, window: int = 14, threshold: float = -20.0) -> bool:
    """
    Check if Williams %R is above the overbought threshold.

    Williams %R ranges from -100 to 0. Values above -20 indicate overbought.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback window. Range: 5-50. Default: 14.
        threshold (float): Overbought threshold. Range: -30-0. Default: -20.0.

    Returns:
        bool: True if Williams %R > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = WilliamsR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    wr = result['wr']

    if pd.isna(wr.iloc[-1]):
        return False

    return float(wr.iloc[-1]) > threshold


@RuleRegistry.register("williams_r_oversold")
def williams_r_oversold(df: pd.DataFrame, window: int = 14, threshold: float = -80.0) -> bool:
    """
    Check if Williams %R is below the oversold threshold.

    Williams %R ranges from -100 to 0. Values below -80 indicate oversold.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback window. Range: 5-50. Default: 14.
        threshold (float): Oversold threshold. Range: -100--70. Default: -80.0.

    Returns:
        bool: True if Williams %R < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = WilliamsR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    wr = result['wr']

    if pd.isna(wr.iloc[-1]):
        return False

    return float(wr.iloc[-1]) < threshold


# =============================================================================
# TSI (True Strength Index) Signals
# =============================================================================

@RuleRegistry.register("tsi_bullish")
def tsi_bullish(df: pd.DataFrame, window_slow: int = 25, window_fast: int = 13, threshold: float = 0.0) -> bool:
    """
    Check if True Strength Index indicates bullish momentum.

    TSI above zero indicates bullish momentum.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 10-50. Default: 25.
        window_fast (int): Fast EMA period. Range: 5-25. Default: 13.
        threshold (float): Bullish threshold. Range: -50-50. Default: 0.0.

    Returns:
        bool: True if TSI > threshold, False otherwise.
    """
    if len(df) < window_slow + window_fast:
        return False

    result = TSI.compute(
        data={'close': df["Close"]},
        params={'window_slow': window_slow, 'window_fast': window_fast}
    )
    tsi = result['tsi']

    if pd.isna(tsi.iloc[-1]):
        return False

    return float(tsi.iloc[-1]) > threshold


@RuleRegistry.register("tsi_bearish")
def tsi_bearish(df: pd.DataFrame, window_slow: int = 25, window_fast: int = 13, threshold: float = 0.0) -> bool:
    """
    Check if True Strength Index indicates bearish momentum.

    TSI below zero indicates bearish momentum.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 10-50. Default: 25.
        window_fast (int): Fast EMA period. Range: 5-25. Default: 13.
        threshold (float): Bearish threshold. Range: -50-50. Default: 0.0.

    Returns:
        bool: True if TSI < threshold, False otherwise.
    """
    if len(df) < window_slow + window_fast:
        return False

    result = TSI.compute(
        data={'close': df["Close"]},
        params={'window_slow': window_slow, 'window_fast': window_fast}
    )
    tsi = result['tsi']

    if pd.isna(tsi.iloc[-1]):
        return False

    return float(tsi.iloc[-1]) < threshold


# =============================================================================
# Ultimate Oscillator Signals
# =============================================================================

@RuleRegistry.register("uo_overbought")
def uo_overbought(df: pd.DataFrame, window_short: int = 7, window_medium: int = 14, window_long: int = 28, threshold: float = 70.0) -> bool:
    """
    Check if Ultimate Oscillator indicates overbought condition.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_short (int): Short window. Range: 3-20. Default: 7.
        window_medium (int): Medium window. Range: 7-30. Default: 14.
        window_long (int): Long window. Range: 14-50. Default: 28.
        threshold (float): Overbought threshold. Range: 60-90. Default: 70.0.

    Returns:
        bool: True if UO > threshold, False otherwise.
    """
    if len(df) < window_long:
        return False

    result = UltimateOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window1': window_short, 'window2': window_medium, 'window3': window_long,
                'weight1': 4.0, 'weight2': 2.0, 'weight3': 1.0}
    )
    uo = result['ultimate_oscillator']

    if pd.isna(uo.iloc[-1]):
        return False

    return float(uo.iloc[-1]) > threshold


@RuleRegistry.register("uo_oversold")
def uo_oversold(df: pd.DataFrame, window_short: int = 7, window_medium: int = 14, window_long: int = 28, threshold: float = 30.0) -> bool:
    """
    Check if Ultimate Oscillator indicates oversold condition.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_short (int): Short window. Range: 3-20. Default: 7.
        window_medium (int): Medium window. Range: 7-30. Default: 14.
        window_long (int): Long window. Range: 14-50. Default: 28.
        threshold (float): Oversold threshold. Range: 10-40. Default: 30.0.

    Returns:
        bool: True if UO < threshold, False otherwise.
    """
    if len(df) < window_long:
        return False

    result = UltimateOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window1': window_short, 'window2': window_medium, 'window3': window_long,
                'weight1': 4.0, 'weight2': 2.0, 'weight3': 1.0}
    )
    uo = result['ultimate_oscillator']

    if pd.isna(uo.iloc[-1]):
        return False

    return float(uo.iloc[-1]) < threshold


# =============================================================================
# KAMA (Kaufman Adaptive Moving Average) Signals
# =============================================================================

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


# =============================================================================
# ROC (Rate of Change) Signals
# =============================================================================

@RuleRegistry.register("roc_positive")
def roc_positive(df: pd.DataFrame, window: int = 12, threshold: float = 0.0) -> bool:
    """
    Check if Rate of Change indicates positive momentum.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ROC period. Range: 1-50. Default: 12.
        threshold (float): Positive momentum threshold. Range: -10-10. Default: 0.0.

    Returns:
        bool: True if ROC > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ROC.compute(data={'close': df["Close"]}, params={'window': window})
    roc = result['roc']

    if pd.isna(roc.iloc[-1]):
        return False

    return float(roc.iloc[-1]) > threshold


@RuleRegistry.register("roc_negative")
def roc_negative(df: pd.DataFrame, window: int = 12, threshold: float = 0.0) -> bool:
    """
    Check if Rate of Change indicates negative momentum.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ROC period. Range: 1-50. Default: 12.
        threshold (float): Negative momentum threshold. Range: -10-10. Default: 0.0.

    Returns:
        bool: True if ROC < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ROC.compute(data={'close': df["Close"]}, params={'window': window})
    roc = result['roc']

    if pd.isna(roc.iloc[-1]):
        return False

    return float(roc.iloc[-1]) < threshold


@RuleRegistry.register("roc_momentum_shift")
def roc_momentum_shift(df: pd.DataFrame, window: int = 12, direction: str = "bullish") -> bool:
    """
    Check if ROC crosses zero (momentum shift).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ROC period. Range: 1-50. Default: 12.
        direction (str): Direction: 'bullish' for cross above zero, 'bearish' for cross below. Default: bullish.

    Returns:
        bool: True if momentum shift detected, False otherwise.
    """
    if len(df) < window + 1:
        return False

    result = ROC.compute(data={'close': df["Close"]}, params={'window': window})
    roc = result['roc']

    if len(roc) < 2 or pd.isna(roc.iloc[-1]) or pd.isna(roc.iloc[-2]):
        return False

    if direction.lower() == "bullish":
        return float(roc.iloc[-2]) <= 0 and float(roc.iloc[-1]) > 0
    elif direction.lower() == "bearish":
        return float(roc.iloc[-2]) >= 0 and float(roc.iloc[-1]) < 0

    return False


# =============================================================================
# Awesome Oscillator Signals
# =============================================================================

@RuleRegistry.register("ao_bullish")
def ao_bullish(df: pd.DataFrame, window_fast: int = 5, window_slow: int = 34, threshold: float = 0.0) -> bool:
    """
    Check if Awesome Oscillator indicates bullish momentum.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window. Range: 2-15. Default: 5.
        window_slow (int): Slow SMA window. Range: 20-60. Default: 34.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if AO > threshold, False otherwise.
    """
    if len(df) < window_slow:
        return False

    result = AwesomeOscillator.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_fast, 'window2': window_slow}
    )
    ao = result['ao']

    if pd.isna(ao.iloc[-1]):
        return False

    return float(ao.iloc[-1]) > threshold


@RuleRegistry.register("ao_bearish")
def ao_bearish(df: pd.DataFrame, window_fast: int = 5, window_slow: int = 34, threshold: float = 0.0) -> bool:
    """
    Check if Awesome Oscillator indicates bearish momentum.

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window. Range: 2-15. Default: 5.
        window_slow (int): Slow SMA window. Range: 20-60. Default: 34.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if AO < threshold, False otherwise.
    """
    if len(df) < window_slow:
        return False

    result = AwesomeOscillator.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_fast, 'window2': window_slow}
    )
    ao = result['ao']

    if pd.isna(ao.iloc[-1]):
        return False

    return float(ao.iloc[-1]) < threshold


@RuleRegistry.register("ao_zero_cross")
def ao_zero_cross(df: pd.DataFrame, window_fast: int = 5, window_slow: int = 34, direction: str = "bullish") -> bool:
    """
    Check if Awesome Oscillator crosses zero line.

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window. Range: 2-15. Default: 5.
        window_slow (int): Slow SMA window. Range: 20-60. Default: 34.
        direction (str): Direction: 'bullish' for cross above, 'bearish' for cross below. Default: bullish.

    Returns:
        bool: True if zero cross detected, False otherwise.
    """
    if len(df) < window_slow + 1:
        return False

    result = AwesomeOscillator.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_fast, 'window2': window_slow}
    )
    ao = result['ao']

    if len(ao) < 2 or pd.isna(ao.iloc[-1]) or pd.isna(ao.iloc[-2]):
        return False

    if isinstance(direction, int):
        direction = "bullish" if direction == 1 else "bearish"

    if direction.lower() == "bullish":
        return float(ao.iloc[-2]) <= 0 and float(ao.iloc[-1]) > 0
    elif direction.lower() == "bearish":
        return float(ao.iloc[-2]) >= 0 and float(ao.iloc[-1]) < 0

    return False


# =============================================================================
# Stochastic RSI Signals
# =============================================================================

@RuleRegistry.register("stochrsi_overbought")
def stochrsi_overbought(df: pd.DataFrame, window: int = 14, smooth1: int = 3, smooth2: int = 3, threshold: float = 0.8) -> bool:
    """
    Check if Stochastic RSI indicates overbought condition. In crypto markets, consider adjusting thresholds during strong trends.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI period. Range: 5-30. Default: 14.
        smooth1 (int): Stochastic %K smoothing. Range: 1-10. Default: 3.
        smooth2 (int): Stochastic %D smoothing. Range: 1-10. Default: 3.
        threshold (float): Overbought threshold (0-1 scale). Range: 0.6-1.0. Default: 0.8.

    Returns:
        bool: True if StochRSI > threshold, False otherwise.
    """
    if len(df) < window + smooth1 + smooth2:
        return False

    result = StochRSI.compute(
        data={'close': df["Close"]},
        params={'window': window, 'smooth1': smooth1, 'smooth2': smooth2}
    )
    stochrsi = result['stochrsi']

    if pd.isna(stochrsi.iloc[-1]):
        return False

    return float(stochrsi.iloc[-1]) > threshold


@RuleRegistry.register("stochrsi_oversold")
def stochrsi_oversold(df: pd.DataFrame, window: int = 14, smooth1: int = 3, smooth2: int = 3, threshold: float = 0.2) -> bool:
    """
    Check if Stochastic RSI indicates oversold condition. In crypto markets, consider adjusting thresholds during strong trends.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI period. Range: 5-30. Default: 14.
        smooth1 (int): Stochastic %K smoothing. Range: 1-10. Default: 3.
        smooth2 (int): Stochastic %D smoothing. Range: 1-10. Default: 3.
        threshold (float): Oversold threshold (0-1 scale). Range: 0.0-0.4. Default: 0.2.

    Returns:
        bool: True if StochRSI < threshold, False otherwise.
    """
    if len(df) < window + smooth1 + smooth2:
        return False

    result = StochRSI.compute(
        data={'close': df["Close"]},
        params={'window': window, 'smooth1': smooth1, 'smooth2': smooth2}
    )
    stochrsi = result['stochrsi']

    if pd.isna(stochrsi.iloc[-1]):
        return False

    return float(stochrsi.iloc[-1]) < threshold


# =============================================================================
# PPO (Percentage Price Oscillator) Signals
# =============================================================================

@RuleRegistry.register("ppo_bullish_cross")
def ppo_bullish_cross(df: pd.DataFrame, window_slow: int = 26, window_fast: int = 12, window_sign: int = 9) -> bool:
    """
    Check if PPO crosses above signal line (bullish).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 15-50. Default: 26.
        window_fast (int): Fast EMA period. Range: 5-20. Default: 12.
        window_sign (int): Signal line period. Range: 3-15. Default: 9.

    Returns:
        bool: True if PPO crosses above signal, False otherwise.
    """
    if len(df) < window_slow + window_sign:
        return False

    result = PPO.compute(
        data={'close': df["Close"]},
        params={'window_slow': window_slow, 'window_fast': window_fast, 'window_sign': window_sign}
    )
    ppo = result['ppo']
    signal = result['ppo_signal']

    if len(ppo) < 2 or pd.isna(ppo.iloc[-1]) or pd.isna(signal.iloc[-1]):
        return False

    prev_below = float(ppo.iloc[-2]) <= float(signal.iloc[-2])
    curr_above = float(ppo.iloc[-1]) > float(signal.iloc[-1])

    return prev_below and curr_above


@RuleRegistry.register("ppo_bearish_cross")
def ppo_bearish_cross(df: pd.DataFrame, window_slow: int = 26, window_fast: int = 12, window_sign: int = 9) -> bool:
    """
    Check if PPO crosses below signal line (bearish).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 15-50. Default: 26.
        window_fast (int): Fast EMA period. Range: 5-20. Default: 12.
        window_sign (int): Signal line period. Range: 3-15. Default: 9.

    Returns:
        bool: True if PPO crosses below signal, False otherwise.
    """
    if len(df) < window_slow + window_sign:
        return False

    result = PPO.compute(
        data={'close': df["Close"]},
        params={'window_slow': window_slow, 'window_fast': window_fast, 'window_sign': window_sign}
    )
    ppo = result['ppo']
    signal = result['ppo_signal']

    if len(ppo) < 2 or pd.isna(ppo.iloc[-1]) or pd.isna(signal.iloc[-1]):
        return False

    prev_above = float(ppo.iloc[-2]) >= float(signal.iloc[-2])
    curr_below = float(ppo.iloc[-1]) < float(signal.iloc[-1])

    return prev_above and curr_below


# =============================================================================
# PVO (Percentage Volume Oscillator) Signals
# =============================================================================

@RuleRegistry.register("pvo_bullish_cross")
def pvo_bullish_cross(df: pd.DataFrame, window_slow: int = 26, window_fast: int = 12, window_sign: int = 9) -> bool:
    """
    Check if PVO crosses above signal line (bullish volume).

    Type: TRIGGER
    Requires: Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 15-50. Default: 26.
        window_fast (int): Fast EMA period. Range: 5-20. Default: 12.
        window_sign (int): Signal line period. Range: 3-15. Default: 9.

    Returns:
        bool: True if PVO crosses above signal, False otherwise.
    """
    if len(df) < window_slow + window_sign:
        return False

    result = PVO.compute(
        data={'volume': df["Volume"]},
        params={'window_slow': window_slow, 'window_fast': window_fast, 'window_sign': window_sign}
    )
    pvo = result['pvo']
    signal = result['pvo_signal']

    if len(pvo) < 2 or pd.isna(pvo.iloc[-1]) or pd.isna(signal.iloc[-1]):
        return False

    prev_below = float(pvo.iloc[-2]) <= float(signal.iloc[-2])
    curr_above = float(pvo.iloc[-1]) > float(signal.iloc[-1])

    return prev_below and curr_above


@RuleRegistry.register("pvo_bearish_cross")
def pvo_bearish_cross(df: pd.DataFrame, window_slow: int = 26, window_fast: int = 12, window_sign: int = 9) -> bool:
    """
    Check if PVO crosses below signal line (bearish volume).

    Type: TRIGGER
    Requires: Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 15-50. Default: 26.
        window_fast (int): Fast EMA period. Range: 5-20. Default: 12.
        window_sign (int): Signal line period. Range: 3-15. Default: 9.

    Returns:
        bool: True if PVO crosses below signal, False otherwise.
    """
    if len(df) < window_slow + window_sign:
        return False

    result = PVO.compute(
        data={'volume': df["Volume"]},
        params={'window_slow': window_slow, 'window_fast': window_fast, 'window_sign': window_sign}
    )
    pvo = result['pvo']
    signal = result['pvo_signal']

    if len(pvo) < 2 or pd.isna(pvo.iloc[-1]) or pd.isna(signal.iloc[-1]):
        return False

    prev_above = float(pvo.iloc[-2]) >= float(signal.iloc[-2])
    curr_below = float(pvo.iloc[-1]) < float(signal.iloc[-1])

    return prev_above and curr_below
