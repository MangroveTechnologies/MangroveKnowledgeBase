"""Oscillator signals.

Signals whose class is `oscillator` -- the class of the indicator each one reads. The file name is the
class, so a signal's location and its position in the ontology graph agree. Registered names are
unchanged; only the file moved.
"""

import logging

import numpy as np
import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import zero_cross
from mangrove_kb.indicators import (
    BOP,
    CMO,
    RSI,
    StochasticOscillator,
    StochRSI,
    TSI,
    UltimateOscillator,
    WilliamsR,
)

logger = logging.getLogger(__name__)


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


@RuleRegistry.register("cmo_overbought")
def cmo_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """
    Check if Chande Momentum Oscillator is above the overbought threshold.

    CMO ranges from -100 to +100; default threshold of +50 is standard
    (analogous to RSI 70).

    Type: FILTER
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


@RuleRegistry.register("bop_bullish")
def bop_bullish(df: pd.DataFrame) -> bool:
    """
    Check if Balance of Power indicates buyers in control on the current bar.

    BOP = (close - open) / (high - low). Positive = buyers dominated the bar.

    Type: FILTER
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
    return zero_cross(bop, "up")


@RuleRegistry.register("bop_cross_down")
def bop_cross_down(df: pd.DataFrame) -> bool:
    """
    Detect Balance of Power crossing below zero (buyers -> sellers).

    Type: TRIGGER
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
    return zero_cross(bop, "down")


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
