"""Momentum signals.

Signals whose class is `momentum` -- the class of the indicator each one reads. The file name is the
class, so a signal's location and its position in the ontology graph agree.

The bounded oscillators that used to live here (RSI, Stochastic, StochRSI, Williams %R, CMO, TSI,
BOP, Ultimate Oscillator) are `oscillator`, and the KAMA crossings are `averaging`. They moved to
the files named for those classes. Registered names are unchanged.

- MACD line, ROC, MOM, PPO, PVO, Awesome Oscillator
"""

import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import zero_cross

from mangrove_kb.indicators import (
    ADOSC,
    AwesomeOscillator,
    DailyReturn,
    EaseOfMovement,
    ForceIndex,
    KVO,
    MACD,
    MOM,
    PPO,
    PVO,
    ROC,
)

logger = logging.getLogger(__name__)


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


# =============================================================================
# Wave C Momentum Signals (MOM, BOP, APO, CMO)
# =============================================================================
# MOM, BOP, APO are zero-centered: positive = bullish, negative = bearish.
# Each exposes bullish/bearish FILTER signals plus zero-line crossover TRIGGERs.
# CMO is bounded [-100, +100] so uses overbought/oversold FILTERs and
# threshold-crossover TRIGGERs, matching the RSI pattern.


# --- MOM signals ---

@RuleRegistry.register("mom_bullish")
def mom_bullish(df: pd.DataFrame, window: int = 10) -> bool:
    """
    Check if Momentum (close - close[-n]) is positive.

    Indicates upward price momentum over the lookback window.

    Type: FILTER
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
    return zero_cross(mom, "up")


@RuleRegistry.register("mom_cross_down")
def mom_cross_down(df: pd.DataFrame, window: int = 10) -> bool:
    """
    Detect Momentum crossing below zero (bearish zero-line cross).

    Type: TRIGGER
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
    return zero_cross(mom, "down")


# --- BOP signals ---


# --- MACD-line signals (formerly the APO signals) ---
#
# These read the MACD LINE, which is where an oscillator built from the difference of two EMAs of
# close sits relative to zero. They were registered as `apo_*` and computed from an `APO` indicator
# that emitted a series byte-identical to `MACD.macd` -- verified, maximum difference 0.00e+00 over
# 400 bars, not approximately equal but the same series. The literature agrees this is expected:
# LuxAlgo calls APO "the MACD line under another name", and Fidelity frames MACD as APO with the
# periods and average type pinned. The duplicate indicator has been removed; these signals are
# unchanged in behaviour and now read the one indicator that measures this.
#
# Distinct from `macd_positive` in signals/trend.py, which reads the HISTOGRAM.
#
# `MACD` requires `window_sign` and these signals do not expose it, because the MACD line does not
# depend on it -- verified identical for window_sign 9 and 30. It is pinned to the conventional 9
# rather than surfaced as a knob that provably does nothing.
_MACD_LINE_SIGN_WINDOW = 9


def _macd_line(closes: pd.Series, window_fast: int, window_slow: int) -> pd.Series:
    return MACD.compute(
        data={'close': closes},
        params={'window_fast': window_fast, 'window_slow': window_slow,
                'window_sign': _MACD_LINE_SIGN_WINDOW},
    )['macd']


@RuleRegistry.register("macd_line_positive")
def macd_line_positive(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Check if the MACD line (EMA fast - EMA slow) is above zero (bullish momentum regime).

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line > 0, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow:
        return False
    macd_line = _macd_line(closes, window_fast, window_slow)
    if pd.isna(macd_line.iloc[-1]):
        return False
    return bool(macd_line.iloc[-1] > 0)


@RuleRegistry.register("macd_line_negative")
def macd_line_negative(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Check if the MACD line is below zero (bearish momentum regime).

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line < 0, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow:
        return False
    macd_line = _macd_line(closes, window_fast, window_slow)
    if pd.isna(macd_line.iloc[-1]):
        return False
    return bool(macd_line.iloc[-1] < 0)


@RuleRegistry.register("macd_line_cross_up")
def macd_line_cross_up(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Detect the MACD line crossing above zero (bullish momentum onset).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line crosses above zero on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    return zero_cross(_macd_line(closes, window_fast, window_slow), "up")


@RuleRegistry.register("macd_line_cross_down")
def macd_line_cross_down(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """
    Detect the MACD line crossing below zero (bearish momentum onset).

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line crosses below zero on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    return zero_cross(_macd_line(closes, window_fast, window_slow), "down")


# --- CMO signals ---


def _kvo_lines(df: pd.DataFrame, fast: int, slow: int, signal_window: int):
    """Helper: compute KVO + signal, return None if insufficient data."""
    if len(df) < slow + signal_window + 1:
        return None
    out = KVO.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]},
        params={'fast': fast, 'slow': slow, 'signal_window': signal_window},
    )
    return out['kvo'], out['kvo_signal']


@RuleRegistry.register("adosc_bearish")
def adosc_bearish(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """
    Check if Chaikin A/D Oscillator is negative (distribution regime).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for AD. Range: 2-20. Default: 3.
        slow (int): Slow EMA period for AD. Range: 5-50. Default: 10.

    Returns:
        bool: True if ADOSC < 0, False otherwise.
    """
    if len(df) < slow + 1:
        return False
    adosc = ADOSC.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if pd.isna(adosc.iloc[-1]):
        return False
    return bool(adosc.iloc[-1] < 0)


@RuleRegistry.register("adosc_bullish")
def adosc_bullish(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """
    Check if Chaikin A/D Oscillator is positive (accumulation regime).

    Positive ADOSC = AD line's fast EMA above its slow EMA, indicating
    short-term buying pressure relative to longer-term trend.

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for AD. Range: 2-20. Default: 3.
        slow (int): Slow EMA period for AD. Range: 5-50. Default: 10.

    Returns:
        bool: True if ADOSC > 0, False otherwise.
    """
    if len(df) < slow + 1:
        return False
    adosc = ADOSC.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if pd.isna(adosc.iloc[-1]):
        return False
    return bool(adosc.iloc[-1] > 0)


@RuleRegistry.register("adosc_cross_down")
def adosc_cross_down(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """
    Detect ADOSC crossing below zero (distribution onset).

    Type: TRIGGER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for AD. Range: 2-20. Default: 3.
        slow (int): Slow EMA period for AD. Range: 5-50. Default: 10.

    Returns:
        bool: True if ADOSC crosses below zero on the current bar.
    """
    if len(df) < slow + 2:
        return False
    adosc = ADOSC.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if len(adosc) < 2 or pd.isna(adosc.iloc[-1]) or pd.isna(adosc.iloc[-2]):
        return False
    return bool(adosc.iloc[-2] >= 0 > adosc.iloc[-1])


@RuleRegistry.register("adosc_cross_up")
def adosc_cross_up(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """
    Detect ADOSC crossing above zero (accumulation onset).

    Type: TRIGGER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for AD. Range: 2-20. Default: 3.
        slow (int): Slow EMA period for AD. Range: 5-50. Default: 10.

    Returns:
        bool: True if ADOSC crosses above zero on the current bar.
    """
    if len(df) < slow + 2:
        return False
    adosc = ADOSC.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if len(adosc) < 2 or pd.isna(adosc.iloc[-1]) or pd.isna(adosc.iloc[-2]):
        return False
    return bool(adosc.iloc[-2] <= 0 < adosc.iloc[-1])


@RuleRegistry.register("daily_return_negative")
def daily_return_negative(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """
    Check if daily return is negative.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Maximum return threshold in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if daily return < threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = DailyReturn.compute(data={'close': df["Close"]}, params={})
    dr = result['daily_return']

    if pd.isna(dr.iloc[-1]):
        return False

    return float(dr.iloc[-1]) < threshold


@RuleRegistry.register("daily_return_positive")
def daily_return_positive(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """
    Check if daily return is positive.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Minimum return threshold in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if daily return > threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = DailyReturn.compute(data={'close': df["Close"]}, params={})
    dr = result['daily_return']

    if pd.isna(dr.iloc[-1]):
        return False

    return float(dr.iloc[-1]) > threshold


@RuleRegistry.register("eom_bearish")
def eom_bearish(df: pd.DataFrame, window: int = 14, threshold: float = 0.0) -> bool:
    """
    Check if Ease of Movement indicates bearish (easy downward movement).

    Type: FILTER
    Requires: High, Low, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EOM period. Range: 5-30. Default: 14.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if EOM < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    # IndicatorInterface-style indicators use a stateless compute() API.
    result = EaseOfMovement.compute(
        data={"high": df["High"], "low": df["Low"], "volume": df["Volume"]},
        params={"window": window},
    )
    eom = result["eom"]

    if pd.isna(eom.iloc[-1]):
        return False

    return float(eom.iloc[-1]) < threshold


@RuleRegistry.register("eom_bullish")
def eom_bullish(df: pd.DataFrame, window: int = 14, threshold: float = 0.0) -> bool:
    """
    Check if Ease of Movement indicates bullish (easy upward movement).

    Type: FILTER
    Requires: High, Low, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EOM period. Range: 5-30. Default: 14.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if EOM > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    # IndicatorInterface-style indicators use a stateless compute() API.
    # EaseOfMovement outputs {'eom': ..., 'sma_eom': ...}; we use the raw eom series here.
    result = EaseOfMovement.compute(
        data={"high": df["High"], "low": df["Low"], "volume": df["Volume"]},
        params={"window": window},
    )
    eom = result["eom"]

    if pd.isna(eom.iloc[-1]):
        return False

    return float(eom.iloc[-1]) > threshold


@RuleRegistry.register("force_bearish")
def force_bearish(df: pd.DataFrame, window: int = 13, threshold: float = 0.0) -> bool:
    """
    Check if Force Index indicates bearish momentum.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for smoothing. Range: 5-30. Default: 13.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if Force Index < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ForceIndex.compute(data={'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    fi = result['fi']

    if pd.isna(fi.iloc[-1]):
        return False

    return float(fi.iloc[-1]) < threshold


@RuleRegistry.register("force_bullish")
def force_bullish(df: pd.DataFrame, window: int = 13, threshold: float = 0.0) -> bool:
    """
    Check if Force Index indicates bullish momentum.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for smoothing. Range: 5-30. Default: 13.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if Force Index > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ForceIndex.compute(data={'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    fi = result['fi']

    if pd.isna(fi.iloc[-1]):
        return False

    return float(fi.iloc[-1]) > threshold


@RuleRegistry.register("kvo_bearish")
def kvo_bearish(
    df: pd.DataFrame, fast: int = 34, slow: int = 55, signal_window: int = 13
) -> bool:
    """
    Check if KVO is below its signal line (bearish volume regime).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for signed volume. Range: 5-100. Default: 34.
        slow (int): Slow EMA period for signed volume. Range: 10-200. Default: 55.
        signal_window (int): Signal-line EMA period. Range: 2-50. Default: 13.

    Returns:
        bool: True if KVO < signal line on the current bar.
    """
    lines = _kvo_lines(df, fast, slow, signal_window)
    if lines is None:
        return False
    kvo, sig = lines
    if pd.isna(kvo.iloc[-1]) or pd.isna(sig.iloc[-1]):
        return False
    return bool(kvo.iloc[-1] < sig.iloc[-1])


@RuleRegistry.register("kvo_bearish_cross")
def kvo_bearish_cross(
    df: pd.DataFrame, fast: int = 34, slow: int = 55, signal_window: int = 13
) -> bool:
    """
    Detect KVO crossing below its signal line (bearish volume onset).

    Type: TRIGGER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for signed volume. Range: 5-100. Default: 34.
        slow (int): Slow EMA period for signed volume. Range: 10-200. Default: 55.
        signal_window (int): Signal-line EMA period. Range: 2-50. Default: 13.

    Returns:
        bool: True if KVO crosses below signal line on the current bar.
    """
    lines = _kvo_lines(df, fast, slow, signal_window)
    if lines is None:
        return False
    kvo, sig = lines
    if len(kvo) < 2 or pd.isna(kvo.iloc[-1]) or pd.isna(kvo.iloc[-2]) or pd.isna(sig.iloc[-1]) or pd.isna(sig.iloc[-2]):
        return False
    return bool(kvo.iloc[-2] >= sig.iloc[-2] and kvo.iloc[-1] < sig.iloc[-1])


@RuleRegistry.register("kvo_bullish")
def kvo_bullish(
    df: pd.DataFrame, fast: int = 34, slow: int = 55, signal_window: int = 13
) -> bool:
    """
    Check if KVO is above its signal line (bullish volume regime).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for signed volume. Range: 5-100. Default: 34.
        slow (int): Slow EMA period for signed volume. Range: 10-200. Default: 55.
        signal_window (int): Signal-line EMA period. Range: 2-50. Default: 13.

    Returns:
        bool: True if KVO > signal line on the current bar.
    """
    lines = _kvo_lines(df, fast, slow, signal_window)
    if lines is None:
        return False
    kvo, sig = lines
    if pd.isna(kvo.iloc[-1]) or pd.isna(sig.iloc[-1]):
        return False
    return bool(kvo.iloc[-1] > sig.iloc[-1])


@RuleRegistry.register("kvo_bullish_cross")
def kvo_bullish_cross(
    df: pd.DataFrame, fast: int = 34, slow: int = 55, signal_window: int = 13
) -> bool:
    """
    Detect KVO crossing above its signal line (bullish volume onset).

    Classic Klinger entry trigger; often confirms a price divergence.

    Type: TRIGGER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast (int): Fast EMA period for signed volume. Range: 5-100. Default: 34.
        slow (int): Slow EMA period for signed volume. Range: 10-200. Default: 55.
        signal_window (int): Signal-line EMA period. Range: 2-50. Default: 13.

    Returns:
        bool: True if KVO crosses above signal line on the current bar.
    """
    lines = _kvo_lines(df, fast, slow, signal_window)
    if lines is None:
        return False
    kvo, sig = lines
    if len(kvo) < 2 or pd.isna(kvo.iloc[-1]) or pd.isna(kvo.iloc[-2]) or pd.isna(sig.iloc[-1]) or pd.isna(sig.iloc[-2]):
        return False
    return bool(kvo.iloc[-2] <= sig.iloc[-2] and kvo.iloc[-1] > sig.iloc[-1])
