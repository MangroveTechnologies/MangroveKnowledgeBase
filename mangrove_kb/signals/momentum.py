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

from mangrove_kb.registry import RuleRegistry

# Import momentum indicator classes
from mangrove_kb.indicators import (
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
    MOM,
    BOP,
    APO,
    CMO,
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
    Family: mean_reversion
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
    Family: mean_reversion
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
    Family: momentum
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
    Family: momentum
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
    Family: mean_reversion
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
    Family: mean_reversion
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
    Family: mean_reversion
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
    Family: mean_reversion
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
    Family: momentum
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
    Family: momentum
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
    Family: mean_reversion
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
    Family: mean_reversion
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
    Family: trend_following
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
    Family: trend_following
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
    Family: momentum
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
    Family: momentum
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
    Family: momentum
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
    Family: momentum
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
    Family: momentum
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
    Family: momentum
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
    Family: mean_reversion
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
    Family: mean_reversion
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
    Family: momentum
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
    Family: momentum
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
    Family: volatility
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
    Family: volatility
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


# =============================================================================
# Wave C Momentum Signals (MOM, BOP, APO, CMO)
# =============================================================================
# MOM, BOP, APO are zero-centered: positive = bullish, negative = bearish.
# Each exposes bullish/bearish FILTER signals plus zero-line crossover TRIGGERs.
# CMO is bounded [-100, +100] so uses overbought/oversold FILTERs and
# threshold-crossover TRIGGERs, matching the RSI pattern.


def _zero_cross_signal(series: pd.Series, direction: str) -> bool:
    """Helper: detect zero-line crossover in the given direction on the last bar."""
    if len(series) < 2:
        return False
    prev, curr = series.iloc[-2], series.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    if direction == "up":
        return bool(prev <= 0 < curr)
    return bool(prev >= 0 > curr)


# --- MOM signals ---

@RuleRegistry.register("mom_bullish")
def mom_bullish(df: pd.DataFrame, window: int = 10) -> bool:
    """
    Check if Momentum (close - close[-n]) is positive.

    Indicates upward price momentum over the lookback window.

    Type: FILTER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM > 0, False otherwise.
    """
    closes = df["Close"]
    if len(closes) <= window:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    if pd.isna(mom.iloc[-1]):
        return False
    return bool(mom.iloc[-1] > 0)


@RuleRegistry.register("mom_bearish")
def mom_bearish(df: pd.DataFrame, window: int = 10) -> bool:
    """
    Check if Momentum (close - close[-n]) is negative.

    Indicates downward price momentum over the lookback window.

    Type: FILTER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM < 0, False otherwise.
    """
    closes = df["Close"]
    if len(closes) <= window:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    if pd.isna(mom.iloc[-1]):
        return False
    return bool(mom.iloc[-1] < 0)


@RuleRegistry.register("mom_cross_up")
def mom_cross_up(df: pd.DataFrame, window: int = 10) -> bool:
    """
    Detect Momentum crossing above zero (bullish zero-line cross).

    Type: TRIGGER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM crosses above zero on the current bar.
    """
    closes = df["Close"]
    if len(closes) <= window + 1:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    return _zero_cross_signal(mom, "up")


@RuleRegistry.register("mom_cross_down")
def mom_cross_down(df: pd.DataFrame, window: int = 10) -> bool:
    """
    Detect Momentum crossing below zero (bearish zero-line cross).

    Type: TRIGGER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM crosses below zero on the current bar.
    """
    closes = df["Close"]
    if len(closes) <= window + 1:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    return _zero_cross_signal(mom, "down")


# --- BOP signals ---

@RuleRegistry.register("bop_bullish")
def bop_bullish(df: pd.DataFrame) -> bool:
    """
    Check if Balance of Power indicates buyers in control on the current bar.

    BOP = (close - open) / (high - low). Positive = buyers dominated the bar.

    Type: FILTER
    Family: momentum
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP > 0, False otherwise (including NaN when high==low).
    """
    if len(df) < 1:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    if pd.isna(bop.iloc[-1]):
        return False
    return bool(bop.iloc[-1] > 0)


@RuleRegistry.register("bop_bearish")
def bop_bearish(df: pd.DataFrame) -> bool:
    """
    Check if Balance of Power indicates sellers in control on the current bar.

    Type: FILTER
    Family: momentum
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP < 0, False otherwise.
    """
    if len(df) < 1:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    if pd.isna(bop.iloc[-1]):
        return False
    return bool(bop.iloc[-1] < 0)


@RuleRegistry.register("bop_cross_up")
def bop_cross_up(df: pd.DataFrame) -> bool:
    """
    Detect Balance of Power crossing above zero (sellers -> buyers).

    Type: TRIGGER
    Family: momentum
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP crosses above zero on the current bar.
    """
    if len(df) < 2:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    return _zero_cross_signal(bop, "up")


@RuleRegistry.register("bop_cross_down")
def bop_cross_down(df: pd.DataFrame) -> bool:
    """
    Detect Balance of Power crossing below zero (buyers -> sellers).

    Type: TRIGGER
    Family: momentum
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP crosses below zero on the current bar.
    """
    if len(df) < 2:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    return _zero_cross_signal(bop, "down")


# --- APO signals ---

@RuleRegistry.register("apo_bullish")
def apo_bullish(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Check if the Absolute Price Oscillator (EMA fast - EMA slow) is positive.

    Equivalent to the MACD line being above zero (bullish momentum regime).

    Type: FILTER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if APO > 0, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow:
        return False
    apo = APO.compute(data={'close': closes}, params={'window_fast': window_fast, 'window_slow': window_slow})['apo']
    if pd.isna(apo.iloc[-1]):
        return False
    return bool(apo.iloc[-1] > 0)


@RuleRegistry.register("apo_bearish")
def apo_bearish(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Check if the Absolute Price Oscillator is negative (bearish regime).

    Type: FILTER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if APO < 0, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow:
        return False
    apo = APO.compute(data={'close': closes}, params={'window_fast': window_fast, 'window_slow': window_slow})['apo']
    if pd.isna(apo.iloc[-1]):
        return False
    return bool(apo.iloc[-1] < 0)


@RuleRegistry.register("apo_cross_up")
def apo_cross_up(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Detect APO crossing above zero (bullish momentum onset).

    Type: TRIGGER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if APO crosses above zero on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    apo = APO.compute(data={'close': closes}, params={'window_fast': window_fast, 'window_slow': window_slow})['apo']
    return _zero_cross_signal(apo, "up")


@RuleRegistry.register("apo_cross_down")
def apo_cross_down(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Detect APO crossing below zero (bearish momentum onset).

    Type: TRIGGER
    Family: momentum
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if APO crosses below zero on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    apo = APO.compute(data={'close': closes}, params={'window_fast': window_fast, 'window_slow': window_slow})['apo']
    return _zero_cross_signal(apo, "down")


# --- CMO signals ---

@RuleRegistry.register("cmo_overbought")
def cmo_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """
    Check if Chande Momentum Oscillator is above the overbought threshold.

    CMO ranges from -100 to +100; default threshold of +50 is standard
    (analogous to RSI 70).

    Type: FILTER
    Family: mean_reversion
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold. Range: 20.0-90.0. Default: 50.0.

    Returns:
        bool: True if CMO >= threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if pd.isna(cmo.iloc[-1]):
        return False
    return bool(cmo.iloc[-1] >= threshold)


@RuleRegistry.register("cmo_oversold")
def cmo_oversold(df: pd.DataFrame, window: int = 14, threshold: float = -50.0) -> bool:
    """
    Check if Chande Momentum Oscillator is below the oversold threshold.

    Default threshold of -50 is standard (analogous to RSI 30).

    Type: FILTER
    Family: mean_reversion
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Oversold threshold. Range: -90.0--20.0. Default: -50.0.

    Returns:
        bool: True if CMO <= threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if pd.isna(cmo.iloc[-1]):
        return False
    return bool(cmo.iloc[-1] <= threshold)


@RuleRegistry.register("cmo_cross_up")
def cmo_cross_up(df: pd.DataFrame, window: int = 14, threshold: float = -50.0) -> bool:
    """
    Detect CMO crossing above the oversold threshold (bullish momentum return).

    Analogous to RSI crossing above 30.

    Type: TRIGGER
    Family: mean_reversion
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Oversold threshold to cross above. Range: -90.0--20.0. Default: -50.0.

    Returns:
        bool: True if CMO crosses above threshold on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window + 2:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if len(cmo) < 2 or pd.isna(cmo.iloc[-1]) or pd.isna(cmo.iloc[-2]):
        return False
    return bool(cmo.iloc[-2] <= threshold < cmo.iloc[-1])


@RuleRegistry.register("cmo_cross_down")
def cmo_cross_down(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """
    Detect CMO crossing below the overbought threshold (bearish momentum onset).

    Analogous to RSI crossing below 70.

    Type: TRIGGER
    Family: mean_reversion
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold to cross below. Range: 20.0-90.0. Default: 50.0.

    Returns:
        bool: True if CMO crosses below threshold on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window + 2:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if len(cmo) < 2 or pd.isna(cmo.iloc[-1]) or pd.isna(cmo.iloc[-2]):
        return False
    return bool(cmo.iloc[-2] >= threshold > cmo.iloc[-1])
