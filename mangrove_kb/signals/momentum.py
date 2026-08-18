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
from mangrove_kb.signals._common import zero_cross, moved_signals

from mangrove_kb.indicators import (
    ADOSC,
    ADX,
    Aroon,
    AwesomeOscillator,
    DPO,
    DailyReturn,
    EaseOfMovement,
    ForceIndex,
    KST,
    KVO,
    MACD,
    MOM,
    MassIndex,
    MultiTFSlope,
    PPO,
    PVO,
    ROC,
    RSI,
    SwingDelta,
    TRIX,
    Vortex,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ROC (Rate of Change) Signals
# =============================================================================

@RuleRegistry.register("roc_positive")
def roc_positive(df: pd.DataFrame, window: int = 12, threshold: float = 0.0) -> bool:
    """Signal: roc_positive

    Check if Rate of Change indicates positive momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window - 1

    Formula:
        roc[t] > threshold

    Inputs:
        close: closing price

    Params:
        window [default=12, min=1, max=50]: ROC period
        threshold [default=0.0, min=-10.0, max=10.0]: Positive momentum threshold

    Outputs:
        fired [boolean, 0..1]:
            True if ROC > threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ROC period. Range: 1-50. Default: 12.
        threshold (float): Positive momentum threshold. Range: -10-10. Default: 0.0.

    Returns:
        bool: True if ROC > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ROC.compute(data={'close': df["close"]}, params={'window': window})
    roc = result['roc']

    if pd.isna(roc.iloc[-1]):
        return False

    return float(roc.iloc[-1]) > threshold


@RuleRegistry.register("roc_negative")
def roc_negative(df: pd.DataFrame, window: int = 12, threshold: float = 0.0) -> bool:
    """Signal: roc_negative

    Check if Rate of Change indicates negative momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window - 1

    Formula:
        roc[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=12, min=1, max=50]: ROC period
        threshold [default=0.0, min=-10.0, max=10.0]: Negative momentum threshold

    Outputs:
        fired [boolean, 0..1]:
            True if ROC < threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ROC period. Range: 1-50. Default: 12.
        threshold (float): Negative momentum threshold. Range: -10-10. Default: 0.0.

    Returns:
        bool: True if ROC < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ROC.compute(data={'close': df["close"]}, params={'window': window})
    roc = result['roc']

    if pd.isna(roc.iloc[-1]):
        return False

    return float(roc.iloc[-1]) < threshold


@RuleRegistry.register("roc_momentum_shift")
def roc_momentum_shift(df: pd.DataFrame, window: int = 12, direction: str = "bullish") -> bool:
    """Signal: roc_momentum_shift

    Check if ROC crosses zero (momentum shift).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window

    Formula:
        roc[t-1] <= 0 and roc[t] > 0 when direction is bullish; roc[t-1] >= 0 and roc[t] < 0 when bearish

    Inputs:
        close: closing price

    Params:
        window [default=12, min=1, max=50]: ROC period
        direction: Direction: 'bullish' for cross above zero, 'bearish' for cross below

    Outputs:
        fired [boolean, 0..1]:
            True if momentum shift detected, False otherwise

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ROC period. Range: 1-50. Default: 12.
        direction (str): Direction: 'bullish' for cross above zero, 'bearish' for cross below. Default: bullish.

    Returns:
        bool: True if momentum shift detected, False otherwise.
    """
    if len(df) < window + 1:
        return False

    result = ROC.compute(data={'close': df["close"]}, params={'window': window})
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
    """Signal: ao_bullish

    Check if Awesome Oscillator indicates bullish momentum.

    Reference: https://www.tradingview.com/support/solutions/43000501826-awesome-oscillator-ao/
    Warmup: window_slow - 1

    Formula:
        ao[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_fast [default=5, min=2, max=15]: Fast SMA window
        window_slow [default=34, min=20, max=60]: Slow SMA window
        threshold [default=0.0, min=0.0]: Bullish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if AO > threshold, False otherwise

    Type: FILTER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
        params={'window1': window_fast, 'window2': window_slow}
    )
    ao = result['ao']

    if pd.isna(ao.iloc[-1]):
        return False

    return float(ao.iloc[-1]) > threshold


@RuleRegistry.register("ao_bearish")
def ao_bearish(df: pd.DataFrame, window_fast: int = 5, window_slow: int = 34, threshold: float = 0.0) -> bool:
    """Signal: ao_bearish

    Check if Awesome Oscillator indicates bearish momentum.

    Reference: https://www.tradingview.com/support/solutions/43000501826-awesome-oscillator-ao/
    Warmup: window_slow - 1

    Formula:
        ao[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_fast [default=5, min=2, max=15]: Fast SMA window
        window_slow [default=34, min=20, max=60]: Slow SMA window
        threshold [default=0.0, min=0.0]: Bearish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if AO < threshold, False otherwise

    Type: FILTER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
        params={'window1': window_fast, 'window2': window_slow}
    )
    ao = result['ao']

    if pd.isna(ao.iloc[-1]):
        return False

    return float(ao.iloc[-1]) < threshold


@RuleRegistry.register("ao_zero_cross")
def ao_zero_cross(df: pd.DataFrame, window_fast: int = 5, window_slow: int = 34, direction: str = "bullish") -> bool:
    """Signal: ao_zero_cross

    Check if Awesome Oscillator crosses zero line.

    Reference: https://www.tradingview.com/support/solutions/43000501826-awesome-oscillator-ao/
    Warmup: window_slow

    Formula:
        ao[t-1] <= 0 and ao[t] > 0 when direction is bullish; ao[t-1] >= 0 and ao[t] < 0 when bearish

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_fast [default=5, min=2, max=15]: Fast SMA window
        window_slow [default=34, min=20, max=60]: Slow SMA window
        direction: Direction: 'bullish' for cross above, 'bearish' for cross below

    Outputs:
        fired [boolean, 0..1]:
            True if zero cross detected, False otherwise

    Type: TRIGGER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
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
    """Signal: ppo_bullish_cross

    Check if PPO crosses above signal line (bullish).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-price-oscillator-ppo
    Warmup: window_slow + window_sign - 1

    Formula:
        ppo[t-1] <= ppo_signal[t-1] and ppo[t] > ppo_signal[t]

    Inputs:
        close: closing price

    Params:
        window_slow [default=26, min=15, max=50]: Slow EMA period
        window_fast [default=12, min=5, max=20]: Fast EMA period
        window_sign [default=9, min=3, max=15]: Signal line period

    Outputs:
        fired [boolean, 0..1]:
            True if PPO crosses above signal, False otherwise

    Type: TRIGGER
    Requires: close

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
        data={'close': df["close"]},
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
    """Signal: ppo_bearish_cross

    Check if PPO crosses below signal line (bearish).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-price-oscillator-ppo
    Warmup: window_slow + window_sign - 1

    Formula:
        ppo[t-1] >= ppo_signal[t-1] and ppo[t] < ppo_signal[t]

    Inputs:
        close: closing price

    Params:
        window_slow [default=26, min=15, max=50]: Slow EMA period
        window_fast [default=12, min=5, max=20]: Fast EMA period
        window_sign [default=9, min=3, max=15]: Signal line period

    Outputs:
        fired [boolean, 0..1]:
            True if PPO crosses below signal, False otherwise

    Type: TRIGGER
    Requires: close

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
        data={'close': df["close"]},
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
    """Signal: pvo_bullish_cross

    Check if PVO crosses above signal line (bullish volume).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-volume-oscillator-pvo
    Warmup: window_slow + window_sign - 1

    Formula:
        pvo[t-1] <= pvo_signal[t-1] and pvo[t] > pvo_signal[t] -- computed from VOLUME, not price

    Inputs:
        volume: units traded during the bar

    Params:
        window_slow [default=26, min=15, max=50]: Slow EMA period
        window_fast [default=12, min=5, max=20]: Fast EMA period
        window_sign [default=9, min=3, max=15]: Signal line period

    Outputs:
        fired [boolean, 0..1]:
            True if PVO crosses above signal, False otherwise

    Type: TRIGGER
    Requires: volume

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
        data={'volume': df["volume"]},
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
    """Signal: pvo_bearish_cross

    Check if PVO crosses below signal line (bearish volume).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-volume-oscillator-pvo
    Warmup: window_slow + window_sign - 1

    Formula:
        pvo[t-1] >= pvo_signal[t-1] and pvo[t] < pvo_signal[t] -- computed from VOLUME, not price

    Inputs:
        volume: units traded during the bar

    Params:
        window_slow [default=26, min=15, max=50]: Slow EMA period
        window_fast [default=12, min=5, max=20]: Fast EMA period
        window_sign [default=9, min=3, max=15]: Signal line period

    Outputs:
        fired [boolean, 0..1]:
            True if PVO crosses below signal, False otherwise

    Type: TRIGGER
    Requires: volume

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
        data={'volume': df["volume"]},
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
    """Signal: mom_bullish

    Check if Momentum (close - close[-n]) is positive. Indicates upward price momentum over the
    lookback window.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window

    Formula:
        mom[t] > 0

    Inputs:
        close: closing price

    Params:
        window [default=10, min=1, max=200]: Lookback period

    Outputs:
        fired [boolean, 0..1]:
            True if MOM > 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM > 0, False otherwise.
    """
    closes = df["close"]
    if len(closes) <= window:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    if pd.isna(mom.iloc[-1]):
        return False
    return bool(mom.iloc[-1] > 0)


@RuleRegistry.register("mom_bearish")
def mom_bearish(df: pd.DataFrame, window: int = 10) -> bool:
    """Signal: mom_bearish

    Check if Momentum (close - close[-n]) is negative. Indicates downward price momentum over the
    lookback window.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window

    Formula:
        mom[t] < 0

    Inputs:
        close: closing price

    Params:
        window [default=10, min=1, max=200]: Lookback period

    Outputs:
        fired [boolean, 0..1]:
            True if MOM < 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM < 0, False otherwise.
    """
    closes = df["close"]
    if len(closes) <= window:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    if pd.isna(mom.iloc[-1]):
        return False
    return bool(mom.iloc[-1] < 0)


@RuleRegistry.register("mom_cross_up")
def mom_cross_up(df: pd.DataFrame, window: int = 10) -> bool:
    """Signal: mom_cross_up

    Detect Momentum crossing above zero (bullish zero-line cross).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window + 1

    Formula:
        mom[t-1] <= 0 and mom[t] > 0

    Inputs:
        close: closing price

    Params:
        window [default=10, min=1, max=200]: Lookback period

    Outputs:
        fired [boolean, 0..1]:
            True if MOM crosses above zero on the current bar

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM crosses above zero on the current bar.
    """
    closes = df["close"]
    if len(closes) <= window + 1:
        return False
    mom = MOM.compute(data={'close': closes}, params={'window': window})['mom']
    return zero_cross(mom, "up")


@RuleRegistry.register("mom_cross_down")
def mom_cross_down(df: pd.DataFrame, window: int = 10) -> bool:
    """Signal: mom_cross_down

    Detect Momentum crossing below zero (bearish zero-line cross).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window + 1

    Formula:
        mom[t-1] >= 0 and mom[t] < 0

    Inputs:
        close: closing price

    Params:
        window [default=10, min=1, max=200]: Lookback period

    Outputs:
        fired [boolean, 0..1]:
            True if MOM crosses below zero on the current bar

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 1-200. Default: 10.

    Returns:
        bool: True if MOM crosses below zero on the current bar.
    """
    closes = df["close"]
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
    """Signal: macd_line_positive

    Check if the MACD line (EMA fast - EMA slow) is above zero (bullish momentum regime).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow - 1

    Formula:
        macd[t] > 0 -- the MACD LINE, not the histogram

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=100]: Fast EMA period
        window_slow [default=26, min=5, max=200]: Slow EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if the MACD line > 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line > 0, False otherwise.
    """
    closes = df["close"]
    if len(closes) < window_slow:
        return False
    macd_line = _macd_line(closes, window_fast, window_slow)
    if pd.isna(macd_line.iloc[-1]):
        return False
    return bool(macd_line.iloc[-1] > 0)


@RuleRegistry.register("macd_line_negative")
def macd_line_negative(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """Signal: macd_line_negative

    Check if the MACD line is below zero (bearish momentum regime).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow - 1

    Formula:
        macd[t] < 0 -- the MACD LINE, not the histogram

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=100]: Fast EMA period
        window_slow [default=26, min=5, max=200]: Slow EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if the MACD line < 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line < 0, False otherwise.
    """
    closes = df["close"]
    if len(closes) < window_slow:
        return False
    macd_line = _macd_line(closes, window_fast, window_slow)
    if pd.isna(macd_line.iloc[-1]):
        return False
    return bool(macd_line.iloc[-1] < 0)


@RuleRegistry.register("macd_line_cross_up")
def macd_line_cross_up(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """Signal: macd_line_cross_up

    Detect the MACD line crossing above zero (bullish momentum onset).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow

    Formula:
        macd[t-1] <= 0 and macd[t] > 0

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=100]: Fast EMA period
        window_slow [default=26, min=5, max=200]: Slow EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if the MACD line crosses above zero on the current bar

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line crosses above zero on the current bar.
    """
    closes = df["close"]
    if len(closes) < window_slow + 1:
        return False
    return zero_cross(_macd_line(closes, window_fast, window_slow), "up")


@RuleRegistry.register("macd_line_cross_down")
def macd_line_cross_down(df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26) -> bool:
    """Signal: macd_line_cross_down

    Detect the MACD line crossing below zero (bearish momentum onset).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow

    Formula:
        macd[t-1] >= 0 and macd[t] < 0

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=100]: Fast EMA period
        window_slow [default=26, min=5, max=200]: Slow EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if the MACD line crosses below zero on the current bar

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA period. Range: 2-100. Default: 12.
        window_slow (int): Slow EMA period. Range: 5-200. Default: 26.

    Returns:
        bool: True if the MACD line crosses below zero on the current bar.
    """
    closes = df["close"]
    if len(closes) < window_slow + 1:
        return False
    return zero_cross(_macd_line(closes, window_fast, window_slow), "down")


# The released names. They evaluate and warn; they are not separate signals, so the catalogue still
# reports one signal per behaviour. Verified behaviour-identical to the names they point at over
# 3,762 evaluations per pair on BTC daily closes across window_fast/window_slow of (12,26), (5,35)
# and (20,50) -- zero mismatches, as expected from an APO series byte-identical to MACD.macd.
RuleRegistry.alias("apo_bullish", "macd_line_positive")
RuleRegistry.alias("apo_bearish", "macd_line_negative")
RuleRegistry.alias("apo_cross_up", "macd_line_cross_up")
RuleRegistry.alias("apo_cross_down", "macd_line_cross_down")


# --- CMO signals ---


def _kvo_lines(df: pd.DataFrame, fast: int, slow: int, signal_window: int):
    """Helper: compute KVO + signal, return None if insufficient data."""
    if len(df) < slow + signal_window + 1:
        return None
    out = KVO.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"]},
        params={'fast': fast, 'slow': slow, 'signal_window': signal_window},
    )
    return out['kvo'], out['kvo_signal']


@RuleRegistry.register("adosc_bearish")
def adosc_bearish(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """Signal: adosc_bearish

    Check if Chaikin A/D Oscillator is negative (distribution regime).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-oscillator
    Warmup: slow

    Formula:
        adosc[t] < 0

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=3, min=2, max=20]: Fast EMA period for AD
        slow [default=10, min=5, max=50]: Slow EMA period for AD

    Outputs:
        fired [boolean, 0..1]:
            True if ADOSC < 0, False otherwise

    Type: FILTER
    Requires: high, low, close, volume

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if pd.isna(adosc.iloc[-1]):
        return False
    return bool(adosc.iloc[-1] < 0)


@RuleRegistry.register("adosc_bullish")
def adosc_bullish(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """Signal: adosc_bullish

    Check if Chaikin A/D Oscillator is positive (accumulation regime). Positive ADOSC = AD line's
    fast EMA above its slow EMA, indicating short-term buying pressure relative to longer-term
    trend.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-oscillator
    Warmup: slow

    Formula:
        adosc[t] > 0

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=3, min=2, max=20]: Fast EMA period for AD
        slow [default=10, min=5, max=50]: Slow EMA period for AD

    Outputs:
        fired [boolean, 0..1]:
            True if ADOSC > 0, False otherwise

    Type: FILTER
    Requires: high, low, close, volume

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if pd.isna(adosc.iloc[-1]):
        return False
    return bool(adosc.iloc[-1] > 0)


@RuleRegistry.register("adosc_cross_down")
def adosc_cross_down(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """Signal: adosc_cross_down

    Detect ADOSC crossing below zero (distribution onset).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-oscillator
    Warmup: slow + 1

    Formula:
        adosc[t-1] >= 0 and adosc[t] < 0

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=3, min=2, max=20]: Fast EMA period for AD
        slow [default=10, min=5, max=50]: Slow EMA period for AD

    Outputs:
        fired [boolean, 0..1]:
            True if ADOSC crosses below zero on the current bar

    Type: TRIGGER
    Requires: high, low, close, volume

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if len(adosc) < 2 or pd.isna(adosc.iloc[-1]) or pd.isna(adosc.iloc[-2]):
        return False
    return bool(adosc.iloc[-2] >= 0 > adosc.iloc[-1])


@RuleRegistry.register("adosc_cross_up")
def adosc_cross_up(df: pd.DataFrame, fast: int = 3, slow: int = 10) -> bool:
    """Signal: adosc_cross_up

    Detect ADOSC crossing above zero (accumulation onset).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-oscillator
    Warmup: slow + 1

    Formula:
        adosc[t-1] <= 0 and adosc[t] > 0

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=3, min=2, max=20]: Fast EMA period for AD
        slow [default=10, min=5, max=50]: Slow EMA period for AD

    Outputs:
        fired [boolean, 0..1]:
            True if ADOSC crosses above zero on the current bar

    Type: TRIGGER
    Requires: high, low, close, volume

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"]},
        params={'fast': fast, 'slow': slow},
    )['adosc']
    if len(adosc) < 2 or pd.isna(adosc.iloc[-1]) or pd.isna(adosc.iloc[-2]):
        return False
    return bool(adosc.iloc[-2] <= 0 < adosc.iloc[-1])


@RuleRegistry.register("daily_return_negative")
def daily_return_negative(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """Signal: daily_return_negative

    Check if daily return is negative.

    Warmup: 1

    Formula:
        daily_return[t] < threshold

    Inputs:
        close: closing price

    Params:
        threshold [default=0.0, min=0.0]: Maximum return threshold in percent

    Outputs:
        fired [boolean, 0..1]:
            True if daily return < threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Maximum return threshold in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if daily return < threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = DailyReturn.compute(data={'close': df["close"]}, params={})
    dr = result['daily_return']

    if pd.isna(dr.iloc[-1]):
        return False

    return float(dr.iloc[-1]) < threshold


@RuleRegistry.register("daily_return_positive")
def daily_return_positive(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """Signal: daily_return_positive

    Check if daily return is positive.

    Warmup: 1

    Formula:
        daily_return[t] > threshold

    Inputs:
        close: closing price

    Params:
        threshold [default=0.0, min=0.0]: Minimum return threshold in percent

    Outputs:
        fired [boolean, 0..1]:
            True if daily return > threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Minimum return threshold in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if daily return > threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = DailyReturn.compute(data={'close': df["close"]}, params={})
    dr = result['daily_return']

    if pd.isna(dr.iloc[-1]):
        return False

    return float(dr.iloc[-1]) > threshold


@RuleRegistry.register("eom_bearish")
def eom_bearish(df: pd.DataFrame, window: int = 14, threshold: float = 0.0) -> bool:
    """Signal: eom_bearish

    Check if Ease of Movement indicates bearish (easy downward movement).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ease-of-movement-emv
    Warmup: window - 1

    Formula:
        eom[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=30]: EOM period
        threshold [default=0.0, min=0.0]: Bearish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if EOM < threshold, False otherwise

    Type: FILTER
    Requires: high, low, volume

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
        data={"high": df["high"], "low": df["low"], "volume": df["volume"]},
        params={"window": window},
    )
    eom = result["eom"]

    if pd.isna(eom.iloc[-1]):
        return False

    return float(eom.iloc[-1]) < threshold


@RuleRegistry.register("eom_bullish")
def eom_bullish(df: pd.DataFrame, window: int = 14, threshold: float = 0.0) -> bool:
    """Signal: eom_bullish

    Check if Ease of Movement indicates bullish (easy upward movement).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ease-of-movement-emv
    Warmup: window - 1

    Formula:
        eom[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=30]: EOM period
        threshold [default=0.0, min=0.0]: Bullish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if EOM > threshold, False otherwise

    Type: FILTER
    Requires: high, low, volume

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
        data={"high": df["high"], "low": df["low"], "volume": df["volume"]},
        params={"window": window},
    )
    eom = result["eom"]

    if pd.isna(eom.iloc[-1]):
        return False

    return float(eom.iloc[-1]) > threshold


@RuleRegistry.register("force_bearish")
def force_bearish(df: pd.DataFrame, window: int = 13, threshold: float = 0.0) -> bool:
    """Signal: force_bearish

    Check if Force Index indicates bearish momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/force-index
    Warmup: window - 1

    Formula:
        fi[t] < threshold

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=13, min=5, max=30]: EMA period for smoothing
        threshold [default=0.0, min=0.0]: Bearish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Force Index < threshold, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for smoothing. Range: 5-30. Default: 13.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if Force Index < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ForceIndex.compute(data={'close': df["close"], 'volume': df["volume"]}, params={'window': window,
    })
    fi = result['fi']

    if pd.isna(fi.iloc[-1]):
        return False

    return float(fi.iloc[-1]) < threshold


@RuleRegistry.register("force_bullish")
def force_bullish(df: pd.DataFrame, window: int = 13, threshold: float = 0.0) -> bool:
    """Signal: force_bullish

    Check if Force Index indicates bullish momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/force-index
    Warmup: window - 1

    Formula:
        fi[t] > threshold

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=13, min=5, max=30]: EMA period for smoothing
        threshold [default=0.0, min=0.0]: Bullish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Force Index > threshold, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for smoothing. Range: 5-30. Default: 13.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if Force Index > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ForceIndex.compute(data={'close': df["close"], 'volume': df["volume"]}, params={'window': window,
    })
    fi = result['fi']

    if pd.isna(fi.iloc[-1]):
        return False

    return float(fi.iloc[-1]) > threshold


@RuleRegistry.register("kvo_bearish")
def kvo_bearish(
    df: pd.DataFrame, fast: int = 34, slow: int = 55, signal_window: int = 13
) -> bool:
    """Signal: kvo_bearish

    Check if KVO is below its signal line (bearish volume regime).

    Reference: https://www.tradingview.com/scripts/klingeroscillator/
    Warmup: slow + signal_window

    Formula:
        kvo[t] < kvo_signal[t] -- same simplified-variant caveat

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=34, min=5, max=100]: Fast EMA period for signed volume
        slow [default=55, min=10, max=200]: Slow EMA period for signed volume
        signal_window [default=13, min=2, max=50]: Signal-line EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if KVO < signal line on the current bar

    Type: FILTER
    Requires: high, low, close, volume

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
    """Signal: kvo_bearish_cross

    Detect KVO crossing below its signal line (bearish volume onset).

    Reference: https://www.tradingview.com/scripts/klingeroscillator/
    Warmup: slow + signal_window

    Formula:
        kvo[t-1] >= kvo_signal[t-1] and kvo[t] < kvo_signal[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=34, min=5, max=100]: Fast EMA period for signed volume
        slow [default=55, min=10, max=200]: Slow EMA period for signed volume
        signal_window [default=13, min=2, max=50]: Signal-line EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if KVO crosses below signal line on the current bar

    Type: TRIGGER
    Requires: high, low, close, volume

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
    """Signal: kvo_bullish

    Check if KVO is above its signal line (bullish volume regime).

    Reference: https://www.tradingview.com/scripts/klingeroscillator/
    Warmup: slow + signal_window

    Formula:
        kvo[t] > kvo_signal[t] -- the SIMPLIFIED KVO variant; its level is roughly 150x smaller than Klinger's original and the two are not comparable

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=34, min=5, max=100]: Fast EMA period for signed volume
        slow [default=55, min=10, max=200]: Slow EMA period for signed volume
        signal_window [default=13, min=2, max=50]: Signal-line EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if KVO > signal line on the current bar

    Type: FILTER
    Requires: high, low, close, volume

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
    """Signal: kvo_bullish_cross

    Detect KVO crossing above its signal line (bullish volume onset). Classic Klinger entry trigger;
    often confirms a price divergence.

    Reference: https://www.tradingview.com/scripts/klingeroscillator/
    Warmup: slow + signal_window

    Formula:
        kvo[t-1] <= kvo_signal[t-1] and kvo[t] > kvo_signal[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=34, min=5, max=100]: Fast EMA period for signed volume
        slow [default=55, min=10, max=200]: Slow EMA period for signed volume
        signal_window [default=13, min=2, max=50]: Signal-line EMA period

    Outputs:
        fired [boolean, 0..1]:
            True if KVO crosses above signal line on the current bar

    Type: TRIGGER
    Requires: high, low, close, volume

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


# ---------------------------------------------------------------------------
# Moved from trend.py, which held four classes at once.
# Signals whose class is `momentum` -- the class of the indicator each one reads.
# ---------------------------------------------------------------------------

@RuleRegistry.register("adx_bullish_di")
def adx_bullish_di(df: pd.DataFrame, window: int = 14) -> bool:
    """Signal: adx_bullish_di

    Check if +DI is greater than -DI (bullish directional movement). When +DI > -DI, bulls have the
    upper hand.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx
    Warmup: window * 2 - 1

    Formula:
        adx_pos[t] > adx_neg[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: ADX period

    Outputs:
        fired [boolean, 0..1]:
            True if +DI > -DI, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ADX period. Range: 5-50. Default: 14.

    Returns:
        bool: True if +DI > -DI, False otherwise.
    """
    if len(df) < window * 2:
        return False

    result = ADX.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window}
    )
    di_pos = result['adx_pos']
    di_neg = result['adx_neg']

    if pd.isna(di_pos.iloc[-1]) or pd.isna(di_neg.iloc[-1]):
        return False

    return float(di_pos.iloc[-1]) > float(di_neg.iloc[-1])

@RuleRegistry.register("adx_strong_trend")
def adx_strong_trend(df: pd.DataFrame, window: int = 14, threshold: float = 25.0) -> bool:
    """Signal: adx_strong_trend

    Check if ADX indicates a strong trend. ADX values above 25 typically indicate a strong trend
    (either up or down).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx
    Warmup: window * 2 - 1

    Formula:
        adx[t] > threshold -- trend STRENGTH, undirected

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: ADX period
        threshold [default=25.0, min=15.0, max=50.0]: Trend strength threshold

    Outputs:
        fired [boolean, 0..1]:
            True if ADX > threshold, False otherwise

    Type: FILTER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window}
    )
    adx = result['adx']

    if pd.isna(adx.iloc[-1]):
        return False

    return float(adx.iloc[-1]) > threshold

@RuleRegistry.register("aroon_crossover")
def aroon_crossover(df: pd.DataFrame, window: int = 25, direction: str = "bullish") -> bool:
    """Signal: aroon_crossover

    Check if Aroon lines cross (trend change signal).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/aroon
    Warmup: window

    Formula:
        direction == 'bullish': aroon_up[t-1] <= aroon_down[t-1] and aroon_up[t] > aroon_down[t]; direction == 'bearish': aroon_up[t-1] >= aroon_down[t-1] and aroon_up[t] < aroon_down[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window [default=25, min=10, max=50]: Lookback period
        direction: Crossover direction, 'bullish' or 'bearish'

    Outputs:
        fired [boolean, 0..1]:
            True if crossover detected, False otherwise

    Type: TRIGGER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
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

@RuleRegistry.register("aroon_down_trend")
def aroon_down_trend(df: pd.DataFrame, window: int = 25, threshold: float = 70.0) -> bool:
    """Signal: aroon_down_trend

    Check if Aroon Down indicates strong downtrend.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/aroon
    Warmup: window - 1

    Formula:
        aroon_down[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window [default=25, min=10, max=50]: Lookback period
        threshold [default=70.0, min=50.0, max=100.0]: Strong trend threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Aroon Down > threshold, False otherwise

    Type: FILTER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
        params={'window': window}
    )
    aroon_down = result['aroon_down']

    if pd.isna(aroon_down.iloc[-1]):
        return False

    return float(aroon_down.iloc[-1]) > threshold

@RuleRegistry.register("aroon_up_trend")
def aroon_up_trend(df: pd.DataFrame, window: int = 25, threshold: float = 70.0) -> bool:
    """Signal: aroon_up_trend

    Check if Aroon Up indicates strong uptrend.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/aroon
    Warmup: window - 1

    Formula:
        aroon_up[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window [default=25, min=10, max=50]: Lookback period
        threshold [default=70.0, min=50.0, max=100.0]: Strong trend threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Aroon Up > threshold, False otherwise

    Type: FILTER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
        params={'window': window}
    )
    aroon_up = result['aroon_up']

    if pd.isna(aroon_up.iloc[-1]):
        return False

    return float(aroon_up.iloc[-1]) > threshold

@RuleRegistry.register("dpo_negative")
def dpo_negative(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: dpo_negative

    Check if DPO is negative (price below detrended average).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/detrended-price-oscillator-dpo
    Warmup: window - 1

    Formula:
        dpo[t] < 0

    Inputs:
        close: closing price

    Params:
        window [default=20, min=10, max=50]: DPO period

    Outputs:
        fired [boolean, 0..1]:
            True if DPO < 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): DPO period. Range: 10-50. Default: 20.

    Returns:
        bool: True if DPO < 0, False otherwise.
    """
    if len(df) < window:
        return False

    result = DPO.compute(data={'close': df["close"]}, params={'window': window})
    dpo = result['dpo']

    if pd.isna(dpo.iloc[-1]):
        return False

    return float(dpo.iloc[-1]) < 0

@RuleRegistry.register("dpo_positive")
def dpo_positive(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: dpo_positive

    Check if DPO is positive (price above detrended average).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/detrended-price-oscillator-dpo
    Warmup: window - 1

    Formula:
        dpo[t] > 0

    Inputs:
        close: closing price

    Params:
        window [default=20, min=10, max=50]: DPO period

    Outputs:
        fired [boolean, 0..1]:
            True if DPO > 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): DPO period. Range: 10-50. Default: 20.

    Returns:
        bool: True if DPO > 0, False otherwise.
    """
    if len(df) < window:
        return False

    result = DPO.compute(data={'close': df["close"]}, params={'window': window})
    dpo = result['dpo']

    if pd.isna(dpo.iloc[-1]):
        return False

    return float(dpo.iloc[-1]) > 0

@RuleRegistry.register("kst_bearish_cross")
def kst_bearish_cross(df: pd.DataFrame, roc1: int = 10, roc2: int = 15, roc3: int = 20, roc4: int = 30, window_sma1: int = 10, window_sma2: int = 10, window_sma3: int = 10, window_sma4: int = 15, nsig: int = 9) -> bool:
    """Signal: kst_bearish_cross

    Check if KST crosses below signal line (bearish).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-know-sure-thing-kst
    Warmup: roc4 + window_sma4 + nsig - 1

    Formula:
        kst[t-1] >= kst_signal[t-1] and kst[t] < kst_signal[t]

    Inputs:
        close: closing price

    Params:
        roc1 [default=10, min=1, max=200]: ROC1 period
        roc2 [default=15, min=1, max=200]: ROC2 period
        roc3 [default=20, min=1, max=200]: ROC3 period
        roc4 [default=30, min=1, max=200]: ROC4 period
        window_sma1 [default=10, min=2, max=200]: SMA1 smoothing window for ROC1
        window_sma2 [default=10, min=2, max=200]: SMA2 smoothing window for ROC2
        window_sma3 [default=10, min=2, max=200]: SMA3 smoothing window for ROC3
        window_sma4 [default=15, min=2, max=200]: SMA4 smoothing window for ROC4
        nsig [default=9, min=1, max=200]: Signal line period

    Outputs:
        fired [boolean, 0..1]:
            True if KST crosses below signal, False otherwise

    Type: TRIGGER
    Requires: close

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
        data={'close': df["close"]},
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

@RuleRegistry.register("kst_bullish_cross")
def kst_bullish_cross(df: pd.DataFrame, roc1: int = 10, roc2: int = 15, roc3: int = 20, roc4: int = 30, window_sma1: int = 10, window_sma2: int = 10, window_sma3: int = 10, window_sma4: int = 15, nsig: int = 9) -> bool:
    """Signal: kst_bullish_cross

    Check if KST crosses above signal line (bullish).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-know-sure-thing-kst
    Warmup: roc4 + window_sma4 + nsig - 1

    Formula:
        kst[t-1] <= kst_signal[t-1] and kst[t] > kst_signal[t]

    Inputs:
        close: closing price

    Params:
        roc1 [default=10, min=1, max=200]: ROC1 period
        roc2 [default=15, min=1, max=200]: ROC2 period
        roc3 [default=20, min=1, max=200]: ROC3 period
        roc4 [default=30, min=1, max=200]: ROC4 period
        window_sma1 [default=10, min=2, max=200]: SMA1 smoothing window for ROC1
        window_sma2 [default=10, min=2, max=200]: SMA2 smoothing window for ROC2
        window_sma3 [default=10, min=2, max=200]: SMA3 smoothing window for ROC3
        window_sma4 [default=15, min=2, max=200]: SMA4 smoothing window for ROC4
        nsig [default=9, min=1, max=200]: Signal line period

    Outputs:
        fired [boolean, 0..1]:
            True if KST crosses above signal, False otherwise

    Type: TRIGGER
    Requires: close

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
        data={"close": df["close"]},
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

@RuleRegistry.register("macd_bearish_cross")
def macd_bearish_cross(
    df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9
) -> bool:
    """Signal: macd_bearish_cross

    Detect MACD bearish crossover (MACD line crosses below signal line). A bearish MACD crossover
    occurs when the MACD line crosses below the signal line, indicating potential downward momentum.
    Crypto's high volatility may produce frequent signals; use with trend confirmation.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow + window_sign - 1

    Formula:
        macd[t-1] >= signal[t-1] and macd[t] < signal[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=50]: Fast EMA window
        window_slow [default=26, min=10, max=100]: Slow EMA window
        window_sign [default=9, min=2, max=50]: Signal line EMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish crossover detected, False otherwise

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-50. Default: 12.
        window_slow (int): Slow EMA window. Range: 10-100. Default: 26.
        window_sign (int): Signal line EMA window. Range: 2-50. Default: 9.

    Returns:
        bool: True if bearish crossover detected, False otherwise.
    """
    closes = df["close"]
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

@RuleRegistry.register("macd_bullish_cross")
def macd_bullish_cross(
    df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9
) -> bool:
    """Signal: macd_bullish_cross

    Detect MACD bullish crossover (MACD line crosses above signal line). A bullish MACD crossover
    occurs when the MACD line crosses above the signal line, indicating potential upward momentum.
    Crypto's high volatility may produce frequent signals; use with trend confirmation.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow + window_sign - 1

    Formula:
        macd[t-1] <= signal[t-1] and macd[t] > signal[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=50]: Fast EMA window
        window_slow [default=26, min=10, max=100]: Slow EMA window
        window_sign [default=9, min=2, max=50]: Signal line EMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish crossover detected, False otherwise

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-50. Default: 12.
        window_slow (int): Slow EMA window. Range: 10-100. Default: 26.
        window_sign (int): Signal line EMA window. Range: 2-50. Default: 9.

    Returns:
        bool: True if bullish crossover detected, False otherwise.
    """
    closes = df["close"]
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

@RuleRegistry.register("macd_positive")
def macd_positive(
    df: pd.DataFrame, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9
) -> bool:
    """Signal: macd_positive

    Check if MACD histogram is positive (bullish momentum). Crypto's high volatility may produce
    frequent signals; use with trend confirmation.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: min_periods - 1

    Formula:
        histogram[t] > 0 -- the HISTOGRAM, macd minus signal; macd_line_positive is the one that reads the MACD line itself

    Inputs:
        close: closing price

    Params:
        window_fast [default=12, min=2, max=50]: Fast EMA window
        window_slow [default=26, min=10, max=100]: Slow EMA window
        window_sign [default=9, min=2, max=50]: Signal line EMA window

    Outputs:
        fired [boolean, 0..1]:
            True if MACD histogram > 0, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-50. Default: 12.
        window_slow (int): Slow EMA window. Range: 10-100. Default: 26.
        window_sign (int): Signal line EMA window. Range: 2-50. Default: 9.

    Returns:
        bool: True if MACD histogram > 0, False otherwise.
    """
    closes = df["close"]
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

@RuleRegistry.register("mass_reversal_signal")
def mass_reversal_signal(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 25, threshold_high: float = 27.0, threshold_low: float = 26.5) -> bool:
    """Signal: mass_reversal_signal

    Check if Mass Index signals potential reversal (reversal bulge). A reversal bulge occurs when
    Mass Index rises above 27 then falls below 26.5.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/mass-index
    Warmup: window_slow + window_fast - 1

    Formula:
        any(mass_index[t-9 .. t] > threshold_high) and mass_index[t] < threshold_low -- the reversal bulge: a spike above, then a fall back through the lower level

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_fast [default=9, min=5, max=15]: Fast EMA period
        window_slow [default=25, min=15, max=40]: Sum period
        threshold_high [default=27.0, min=25.0, max=30.0]: Upper threshold
        threshold_low [default=26.5, min=24.0, max=27.0]: Lower threshold

    Outputs:
        fired [boolean, 0..1]:
            True if reversal bulge detected, False otherwise

    Type: TRIGGER
    Requires: high, low

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
        data={'high': df["high"], 'low': df["low"]},
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

@RuleRegistry.register("multi_tf_trend_bearish")
def multi_tf_trend_bearish(
    df: pd.DataFrame, higher_tf: str = "1W", window: int = 10, slope_threshold: float = 0.0,
) -> bool:
    """Signal: multi_tf_trend_bearish

    Check if the higher-timeframe EMA is falling.

    Warmup: window * (base bars per higher_tf period)

    Formula:
        higher_tf_trend[t] == -1

    Inputs:
        close: closing price

    Params:
        higher_tf: Pandas offset alias for the higher timeframe
        window [default=10, min=2, max=100]: EMA period on the resampled close
        slope_threshold [default=0.0, min=0.0]: Relative slope threshold for non-flat classification

    Outputs:
        fired [boolean, 0..1]:
            True if higher-TF trend == -1 on the current bar

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data (DatetimeIndex required).
        higher_tf (str): Pandas offset alias for the higher timeframe. Range: 1min-1Y. Default: 1W.
        window (int): EMA period on the resampled close. Range: 2-100. Default: 10.
        slope_threshold (float): Relative slope threshold for non-flat classification. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if higher-TF trend == -1 on the current bar.
    """
    closes = df["close"]
    if len(closes) < 2 or not isinstance(closes.index, pd.DatetimeIndex):
        return False
    out = MultiTFSlope.compute(data={'close': closes},
                               params={'higher_tf': higher_tf, 'window': window})
    val = out['higher_tf_slope'].iloc[-1]
    if pd.isna(val):
        return False
    return bool(val < -slope_threshold)

@RuleRegistry.register("multi_tf_trend_bullish")
def multi_tf_trend_bullish(
    df: pd.DataFrame, higher_tf: str = "1W", window: int = 10, slope_threshold: float = 0.0,
) -> bool:
    """Signal: multi_tf_trend_bullish

    Check if the higher-timeframe EMA is rising (trend confirmation filter). Requires a
    DatetimeIndex. Resamples to the specified higher timeframe, computes an EMA on the resampled
    closes, and returns True if the EMA slope is positive. Broadcasts back to the current bar's
    timestamp so lower-TF signals can be filtered by higher-TF trend.

    Warmup: window * (base bars per higher_tf period)

    Formula:
        higher_tf_trend[t] == 1

    Inputs:
        close: closing price

    Params:
        higher_tf: Pandas offset alias for the higher timeframe
        window [default=10, min=2, max=100]: EMA period on the resampled close
        slope_threshold [default=0.0, min=0.0]: Relative slope threshold for non-flat classification

    Outputs:
        fired [boolean, 0..1]:
            True if higher-TF trend == +1 on the current bar

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data (DatetimeIndex required).
        higher_tf (str): Pandas offset alias for the higher timeframe. Range: 1min-1Y. Default: 1W.
        window (int): EMA period on the resampled close. Range: 2-100. Default: 10.
        slope_threshold (float): Relative slope threshold for non-flat classification. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if higher-TF trend == +1 on the current bar.
    """
    closes = df["close"]
    if len(closes) < 2 or not isinstance(closes.index, pd.DatetimeIndex):
        return False
    out = MultiTFSlope.compute(data={'close': closes},
                               params={'higher_tf': higher_tf, 'window': window})
    val = out['higher_tf_slope'].iloc[-1]
    if pd.isna(val):
        return False
    return bool(val > slope_threshold)

@RuleRegistry.register("trix_bearish")
def trix_bearish(df: pd.DataFrame, window: int = 15, threshold: float = 0.0) -> bool:
    """Signal: trix_bearish

    Check if TRIX indicates bearish momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/trix
    Warmup: window * 3 - 1

    Formula:
        trix[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=15, min=5, max=30]: TRIX period
        threshold [default=0.0, min=0.0]: Bearish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if TRIX < threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TRIX period. Range: 5-30. Default: 15.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if TRIX < threshold, False otherwise.
    """
    if len(df) < window * 3:
        return False

    result = TRIX.compute(data={'close': df["close"]}, params={'window': window, 'window_sign': 9})
    trix = result['trix']

    if pd.isna(trix.iloc[-1]):
        return False

    return float(trix.iloc[-1]) < threshold

@RuleRegistry.register("trix_bullish")
def trix_bullish(df: pd.DataFrame, window: int = 15, threshold: float = 0.0) -> bool:
    """Signal: trix_bullish

    Check if TRIX indicates bullish momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/trix
    Warmup: window * 3 - 1

    Formula:
        trix[t] > threshold

    Inputs:
        close: closing price

    Params:
        window [default=15, min=5, max=30]: TRIX period
        threshold [default=0.0, min=0.0]: Bullish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if TRIX > threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TRIX period. Range: 5-30. Default: 15.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if TRIX > threshold, False otherwise.
    """
    if len(df) < window * 3:
        return False

    result = TRIX.compute(data={'close': df["close"]}, params={'window': window, 'window_sign': 9})
    trix = result['trix']

    if pd.isna(trix.iloc[-1]):
        return False

    return float(trix.iloc[-1]) > threshold

@RuleRegistry.register("vortex_bearish")
def vortex_bearish(df: pd.DataFrame, window: int = 14) -> bool:
    """Signal: vortex_bearish

    Check if Vortex Indicator shows bearish trend (-VI > +VI).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/vortex-indicator
    Warmup: window - 1

    Formula:
        vortex_neg[t] > vortex_pos[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=30]: Vortex period

    Outputs:
        fired [boolean, 0..1]:
            True if -VI > +VI, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Vortex period. Range: 5-30. Default: 14.

    Returns:
        bool: True if -VI > +VI, False otherwise.
    """
    if len(df) < window:
        return False

    result = Vortex.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window}
    )
    vi_pos = result['vortex_pos']
    vi_neg = result['vortex_neg']

    if pd.isna(vi_pos.iloc[-1]) or pd.isna(vi_neg.iloc[-1]):
        return False

    return float(vi_neg.iloc[-1]) > float(vi_pos.iloc[-1])

@RuleRegistry.register("vortex_bullish")
def vortex_bullish(df: pd.DataFrame, window: int = 14) -> bool:
    """Signal: vortex_bullish

    Check if Vortex Indicator shows bullish trend (+VI > -VI).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/vortex-indicator
    Warmup: window - 1

    Formula:
        vortex_pos[t] > vortex_neg[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=30]: Vortex period

    Outputs:
        fired [boolean, 0..1]:
            True if +VI > -VI, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Vortex period. Range: 5-30. Default: 14.

    Returns:
        bool: True if +VI > -VI, False otherwise.
    """
    if len(df) < window:
        return False

    result = Vortex.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window}
    )
    vi_pos = result['vortex_pos']
    vi_neg = result['vortex_neg']

    if pd.isna(vi_pos.iloc[-1]) or pd.isna(vi_neg.iloc[-1]):
        return False

    return float(vi_pos.iloc[-1]) > float(vi_neg.iloc[-1])

@RuleRegistry.register("vortex_crossover")
def vortex_crossover(df: pd.DataFrame, window: int = 14, direction: str = "bullish") -> bool:
    """Signal: vortex_crossover

    Check if Vortex lines cross (trend change).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/vortex-indicator
    Warmup: window

    Formula:
        direction == 'bullish': vortex_pos[t-1] <= vortex_neg[t-1] and vortex_pos[t] > vortex_neg[t]; direction == 'bearish': vortex_pos[t-1] >= vortex_neg[t-1] and vortex_pos[t] < vortex_neg[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=30]: Vortex period
        direction: Crossover direction, 'bullish' (+VI crosses above -VI) or 'bearish'

    Outputs:
        fired [boolean, 0..1]:
            True if crossover detected, False otherwise

    Type: TRIGGER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
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

# ---------------------------------------------------------------------------
# Divergence between price and RSI, read from SwingDelta's measurements
# ---------------------------------------------------------------------------

def _rsi_swing_deltas(df: pd.DataFrame, rsi_window: int, swing_window: int, min_swing_distance: int):
    """The four swing deltas for price against its RSI, or None before enough bars.

    The four signals below differ only in which pair of deltas they read and which sign each must
    have. That comparison is the whole of the verdict; everything else -- finding the swings,
    pairing them, waiting for confirmation -- is measurement and lives in `SwingDelta`.
    """
    closes = df["close"]
    if len(closes) < rsi_window + 2 * swing_window + min_swing_distance:
        return None
    rsi = RSI.compute(data={'close': closes}, params={'window': rsi_window})['rsi']
    return SwingDelta.compute(
        data={'price': closes, 'indicator': rsi},
        params={'swing_window': swing_window, 'min_swing_distance': min_swing_distance},
    )


def _divergence(df, rsi_window, swing_window, min_swing_distance, side, price_sign, ind_sign):
    out = _rsi_swing_deltas(df, rsi_window, swing_window, min_swing_distance)
    if out is None:
        return False
    p = out[f"{side}_price_delta"].iloc[-1]
    i = out[f"{side}_indicator_delta"].iloc[-1]
    if pd.isna(p) or pd.isna(i):
        return False
    return bool((p > 0) == price_sign and (i > 0) == ind_sign)


@RuleRegistry.register("rsi_bullish_divergence")
def rsi_bullish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """Signal: rsi_bullish_divergence

    Detect a regular bullish RSI divergence: price lower low, RSI higher low. Price fell between its
    last two confirmed swing lows while RSI rose between the matching two.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: rsi_window + 2 * swing_window + min_swing_distance - 1

    Formula:
        low_price_delta[t] < 0 and low_indicator_delta[t] > 0 -- price fell between its last two confirmed swing lows while RSI rose

    Inputs:
        close: closing price

    Params:
        rsi_window [default=14, min=2, max=100]: RSI period
        swing_window [default=5, min=2, max=20]: Bars on each side to confirm swing extremum
        min_swing_distance [default=10, min=3, max=50]: Min bars between the two swing points
        compared

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where the divergence is confirmed

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between the two swing points compared. Range: 3-50. Default: 10.

    Returns:
        bool: True on the bar where the divergence is confirmed.
    """
    return _divergence(df, rsi_window, swing_window, min_swing_distance, "low", False, True)


@RuleRegistry.register("rsi_hidden_bullish_divergence")
def rsi_hidden_bullish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """Signal: rsi_hidden_bullish_divergence

    Detect a hidden bullish RSI divergence: price higher low, RSI lower low. Price rose between its
    last two confirmed swing lows while RSI fell between the matching two.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: rsi_window + 2 * swing_window + min_swing_distance - 1

    Formula:
        low_price_delta[t] > 0 and low_indicator_delta[t] < 0

    Inputs:
        close: closing price

    Params:
        rsi_window [default=14, min=2, max=100]: RSI period
        swing_window [default=5, min=2, max=20]: Bars on each side to confirm swing extremum
        min_swing_distance [default=10, min=3, max=50]: Min bars between the two swing points
        compared

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where the divergence is confirmed

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between the two swing points compared. Range: 3-50. Default: 10.

    Returns:
        bool: True on the bar where the divergence is confirmed.
    """
    return _divergence(df, rsi_window, swing_window, min_swing_distance, "low", True, False)


@RuleRegistry.register("rsi_bearish_divergence")
def rsi_bearish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """Signal: rsi_bearish_divergence

    Detect a regular bearish RSI divergence: price higher high, RSI lower high. Price rose between
    its last two confirmed swing highs while RSI fell between the matching two.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: rsi_window + 2 * swing_window + min_swing_distance - 1

    Formula:
        high_price_delta[t] > 0 and high_indicator_delta[t] < 0

    Inputs:
        close: closing price

    Params:
        rsi_window [default=14, min=2, max=100]: RSI period
        swing_window [default=5, min=2, max=20]: Bars on each side to confirm swing extremum
        min_swing_distance [default=10, min=3, max=50]: Min bars between the two swing points
        compared

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where the divergence is confirmed

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between the two swing points compared. Range: 3-50. Default: 10.

    Returns:
        bool: True on the bar where the divergence is confirmed.
    """
    return _divergence(df, rsi_window, swing_window, min_swing_distance, "high", True, False)


@RuleRegistry.register("rsi_hidden_bearish_divergence")
def rsi_hidden_bearish_divergence(
    df: pd.DataFrame, rsi_window: int = 14, swing_window: int = 5, min_swing_distance: int = 10,
) -> bool:
    """Signal: rsi_hidden_bearish_divergence

    Detect a hidden bearish RSI divergence: price lower high, RSI higher high. Price fell between
    its last two confirmed swing highs while RSI rose between the matching two.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: rsi_window + 2 * swing_window + min_swing_distance - 1

    Formula:
        high_price_delta[t] < 0 and high_indicator_delta[t] > 0

    Inputs:
        close: closing price

    Params:
        rsi_window [default=14, min=2, max=100]: RSI period
        swing_window [default=5, min=2, max=20]: Bars on each side to confirm swing extremum
        min_swing_distance [default=10, min=3, max=50]: Min bars between the two swing points
        compared

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where the divergence is confirmed

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        rsi_window (int): RSI period. Range: 2-100. Default: 14.
        swing_window (int): Bars on each side to confirm swing extremum. Range: 2-20. Default: 5.
        min_swing_distance (int): Min bars between the two swing points compared. Range: 3-50. Default: 10.

    Returns:
        bool: True on the bar where the divergence is confirmed.
    """
    return _divergence(df, rsi_window, swing_window, min_swing_distance, "high", False, True)

# Signals that were in this file when 1.3.4 shipped and are now in the file named for
# their ontology class. Reached by name, with a DeprecationWarning.
_MOVED = {
    "averaging": (
        "kama_cross_down", "kama_cross_up"
    ),
    "oscillator": (
        "bop_bearish", "bop_bullish", "bop_cross_down", "bop_cross_up", "cmo_cross_down",
        "cmo_cross_up", "cmo_overbought", "cmo_oversold", "rsi_cross_down", "rsi_cross_up",
        "rsi_overbought", "rsi_oversold", "stoch_overbought", "stoch_oversold",
        "stochrsi_overbought", "stochrsi_oversold", "tsi_bearish", "tsi_bullish",
        "uo_overbought", "uo_oversold", "williams_r_overbought", "williams_r_oversold"
    ),
}

_moved_getattr = moved_signals("mangrove_kb.signals.momentum", _MOVED)

__getattr__ = _moved_getattr
