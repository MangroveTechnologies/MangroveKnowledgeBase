"""Signals still grouped by use case, not by ontology class.

`trend` is not one of the seven classes on the ontology's axis -- it is a use-case grouping that
predates the class axis, and the 64 signals whose class could be determined have moved to
`averaging.py`, `momentum.py` and `oscillator.py`, named for the class of the indicator each one
reads.

The 10 left here cannot be placed yet, for two different reasons:

  7  read an indicator that emits a VERDICT rather than a measurement -- SuperTrend's `direction`
     is +1 long / -1 short, and PSAR's up/down indicators are flip flags. An indicator states what
     it measured; deciding what that means is the signal layer's job, so these have no measurement
     to inherit a class from.

   3 read TTMSqueeze, which emits `squeeze_on` and `squeeze_fired` (both booleans) beside
     `momentum` (a number) -- a verdict and a measurement in one indicator. Pinned behind one
     decision that also covers MultiTFTrend.

This file empties as those decisions are made. Registered signal names never change when a signal
moves; `mangrove_kb.signals.volume` and `.patterns` show what a rename costs consumers.
"""


import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import _ma_crossover, _ma_is_above, moved_signals

# Import trend indicator classes
from mangrove_kb.indicators import (
    PSAR,
    SuperTrend,
    TTMSqueeze,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Ichimoku Signals
# =============================================================================


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
# Wave A Moving Average Signals (DEMA, TEMA, TRIMA, SMMA, EPMA)
# =============================================================================
# Pattern: for each MA, we register is_above_<ma>, <ma>_cross_up, <ma>_cross_down.
# Each wraps a shared helper that handles NaN checks, warmup validation, and
# crossover detection, so the logic is uniform across MA families.


# --- DEMA signals ---


# --- TEMA signals ---


# --- TRIMA signals ---


# --- SMMA signals ---


# --- EPMA signals ---


# =============================================================================
# Wave B Moving Average Signals (HMA, ALMA, T3, MAMA)
# =============================================================================
# HMA, ALMA, T3 follow the same is_above / cross_up / cross_down pattern as
# the Wave A MAs. MAMA is special: it returns MAMA+FAMA in a single compute
# call and signals are based on MAMA/FAMA crossovers (not two separate-window
# computations), so they don't use the _ma_crossover helper.


# --- HMA signals ---


# --- ALMA signals ---


# --- T3 signals ---


# --- MAMA signals ---


# =============================================================================
# Wave E Trend Signals (HeikinAshi, Chandelier, Alligator, SuperTrend)
# =============================================================================


# --- HeikinAshi signals ---


# --- WilliamsAlligator signals ---


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
# Wave G Signal Patterns (MA Ribbon, TTMSqueeze, Divergence, MultiTFTrend)
# =============================================================================


# --- MA Ribbon signals ---
#
# These used to read three boolean outputs off an `MARibbon` indicator. That class emitted nothing
# BUT booleans -- it stacked N SMAs and asked three ordering questions -- so under our own
# definition it was not an indicator at all: an indicator emits a numeric measurement, a signal
# emits a boolean predicate. It was three signals wearing an indicator's clothes, and it is gone.
#
# The ordering test now lives here, in the signals that always were its only consumer. The SMAs come
# straight from the SMA indicator, which is what the design allows: a signal is a predicate over
# series, and those series may be indicator outputs or raw OHLC. Nothing new is computed and no
# registered signal name changed -- MangroveOracle's plan_generator references all three by name.

_DEFAULT_RIBBON_WINDOWS = (5, 8, 13, 21, 34, 55, 89, 144)


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


# --- Multi-Timeframe Trend signals ---

# Signals that were in this file when 1.3.4 shipped and are now in the file named for
# their ontology class. Reached by name, with a DeprecationWarning; see
# `moved_signals` for why this is PEP 562 rather than a plain re-export.
_MOVED = {
    "averaging": (
        "alligator_bearish", "alligator_bullish", "alligator_sleeping", "alma_cross_down",
        "alma_cross_up", "dema_cross_down", "dema_cross_up", "ema_cross_down", "ema_cross_up",
        "ema_crossover", "epma_cross_down", "epma_cross_up", "heikin_ashi_bearish",
        "heikin_ashi_bullish", "hma_cross_down", "hma_cross_up", "ichimoku_bearish",
        "ichimoku_bullish", "ichimoku_tk_cross", "is_above_alma", "is_above_dema",
        "is_above_epma", "is_above_hma", "is_above_mama", "is_above_sma", "is_above_smma",
        "is_above_t3", "is_above_tema", "is_above_trima", "ma_ribbon_bearish",
        "ma_ribbon_bullish", "ma_ribbon_tangled", "mama_cross_down", "mama_cross_up",
        "price_above_ema", "sma_cross_down", "sma_cross_up", "sma_crossover",
        "smma_cross_down", "smma_cross_up", "t3_cross_down", "t3_cross_up", "tema_cross_down",
        "tema_cross_up", "trima_cross_down", "trima_cross_up", "wma_cross_down",
        "wma_cross_up"
    ),
    "momentum": (
        "adx_bullish_di", "adx_strong_trend", "aroon_crossover", "aroon_down_trend",
        "aroon_up_trend", "dpo_negative", "dpo_positive", "kst_bearish_cross",
        "kst_bullish_cross", "macd_bearish_cross", "macd_bullish_cross", "macd_positive",
        "mass_reversal_signal", "multi_tf_trend_bearish", "multi_tf_trend_bullish",
        "rsi_bearish_divergence", "rsi_bullish_divergence", "rsi_hidden_bearish_divergence",
        "rsi_hidden_bullish_divergence", "trix_bearish", "trix_bullish", "vortex_bearish",
        "vortex_bullish", "vortex_crossover"
    ),
    "oscillator": (
        "cci_overbought", "cci_oversold", "stc_overbought", "stc_oversold"
    ),
    "volatility": (
        "chandelier_long_stop_hit", "chandelier_short_stop_hit"
    ),
}

__getattr__ = moved_signals("mangrove_kb.signals.trend", _MOVED)
