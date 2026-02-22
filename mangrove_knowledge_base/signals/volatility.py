"""Volatility-based trading signals.

This module contains signal functions based on volatility indicators including:
- Bollinger Bands
- ATR (Average True Range)
- Keltner Channel
- Donchian Channel
- Ulcer Index
"""

import logging

import pandas as pd

from mangrove_knowledge_base.registry import RuleRegistry

# Import volatility indicator classes
from mangrove_knowledge_base.indicators import (
    ATR,
    BollingerBands,
    KeltnerChannel,
    DonchianChannel,
    UlcerIndex,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Bollinger Bands Signals
# =============================================================================

@RuleRegistry.register("bb_upper_breakout")
def bb_upper_breakout(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2
) -> bool:
    """
    Detect price breaking above the upper Bollinger Band.

    Fires on the bar where price crosses above the upper band,
    not while price remains above it. Crypto assets frequently test bands during high volatility; use with volume confirmation.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.

    Returns:
        bool: True on the bar where close crosses above upper band.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = BollingerBands.compute(
        data={'close': closes},
        params={'window': window, 'window_dev': window_dev}
    )
    upper = result['hband']

    if pd.isna(upper.iloc[-1]) or pd.isna(upper.iloc[-2]):
        return False

    prev_close = float(closes.iloc[-2])
    curr_close = float(closes.iloc[-1])
    prev_upper = float(upper.iloc[-2])
    curr_upper = float(upper.iloc[-1])

    return prev_close <= prev_upper and curr_close > curr_upper


@RuleRegistry.register("bb_lower_breakout")
def bb_lower_breakout(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2
) -> bool:
    """
    Detect price breaking below the lower Bollinger Band.

    Fires on the bar where price crosses below the lower band,
    not while price remains below it. Crypto assets frequently test bands during high volatility; use with volume confirmation.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.

    Returns:
        bool: True on the bar where close crosses below lower band.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = BollingerBands.compute(
        data={'close': closes},
        params={'window': window, 'window_dev': window_dev}
    )
    lower = result['lband']

    if pd.isna(lower.iloc[-1]) or pd.isna(lower.iloc[-2]):
        return False

    prev_close = float(closes.iloc[-2])
    curr_close = float(closes.iloc[-1])
    prev_lower = float(lower.iloc[-2])
    curr_lower = float(lower.iloc[-1])

    return prev_close >= prev_lower and curr_close < curr_lower


@RuleRegistry.register("bb_squeeze")
def bb_squeeze(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2, threshold: float = 5.0
) -> bool:
    """
    Detect Bollinger Band squeeze onset (low volatility, potential breakout).

    Fires on the bar where band width drops below the threshold,
    not while it remains below.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.
        threshold (float): Band width percentage threshold. Range: 1-20. Default: 5.0.

    Returns:
        bool: True on the bar where band width crosses below threshold.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = BollingerBands.compute(
        data={'close': closes},
        params={'window': window, 'window_dev': window_dev}
    )
    band_width = result['wband']

    if pd.isna(band_width.iloc[-1]) or pd.isna(band_width.iloc[-2]):
        return False

    prev_width = float(band_width.iloc[-2])
    curr_width = float(band_width.iloc[-1])

    return prev_width >= threshold and curr_width < threshold




# =============================================================================
# ATR/Volatility Signals
# =============================================================================

@RuleRegistry.register("atr_high_volatility")
def atr_high_volatility(
    df: pd.DataFrame, window: int = 14, threshold_pct: float = 3.0
) -> bool:
    """
    Check if ATR indicates high volatility relative to price.

    High volatility (ATR as % of close > threshold) can indicate
    potential trading opportunities or increased risk.

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR period. Range: 5-50. Default: 14.
        threshold_pct (float): ATR as percentage of close threshold. Range: 0.5-10. Default: 3.0.

    Returns:
        bool: True if ATR% > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ATR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    atr = result['atr']

    if pd.isna(atr.iloc[-1]):
        return False

    close = float(df["Close"].iloc[-1])
    if close == 0:
        return False

    atr_pct = (float(atr.iloc[-1]) / close) * 100
    return atr_pct > threshold_pct




# =============================================================================
# Keltner Channel Signals
# =============================================================================

@RuleRegistry.register("kc_upper_breakout")
def kc_upper_breakout(df: pd.DataFrame, window: int = 20, window_atr: int = 10, multiplier: float = 2.0, original_version: bool = False) -> bool:
    """
    Detect price breaking above upper Keltner Channel band.

    Fires on the bar where price crosses above the upper band.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period. Range: 10-50. Default: 20.
        window_atr (int): ATR period. Range: 5-30. Default: 10.
        multiplier (float): ATR multiplier for band width. Range: 0.5-5.0. Default: 2.0.
        original_version (bool): Use original Keltner Channel formula instead of EMA+ATR. Default: False.

    Returns:
        bool: True on the bar where close crosses above upper band.
    """
    if len(df) < max(window, window_atr) + 1:
        return False

    result = KeltnerChannel.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'window_atr': window_atr, 'original_version': original_version, 'multiplier': multiplier}
    )
    upper = result['hband']

    if pd.isna(upper.iloc[-1]) or pd.isna(upper.iloc[-2]):
        return False

    prev_close = float(df["Close"].iloc[-2])
    curr_close = float(df["Close"].iloc[-1])
    prev_upper = float(upper.iloc[-2])
    curr_upper = float(upper.iloc[-1])

    return prev_close <= prev_upper and curr_close > curr_upper


@RuleRegistry.register("kc_lower_breakout")
def kc_lower_breakout(df: pd.DataFrame, window: int = 20, window_atr: int = 10, multiplier: float = 2.0, original_version: bool = False) -> bool:
    """
    Detect price breaking below lower Keltner Channel band.

    Fires on the bar where price crosses below the lower band.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period. Range: 10-50. Default: 20.
        window_atr (int): ATR period. Range: 5-30. Default: 10.
        multiplier (float): ATR multiplier for band width. Range: 0.5-5.0. Default: 2.0.
        original_version (bool): Use original Keltner Channel formula instead of EMA+ATR. Default: False.

    Returns:
        bool: True on the bar where close crosses below lower band.
    """
    if len(df) < max(window, window_atr) + 1:
        return False

    result = KeltnerChannel.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'window_atr': window_atr, 'original_version': original_version, 'multiplier': multiplier}
    )
    lower = result['lband']

    if pd.isna(lower.iloc[-1]) or pd.isna(lower.iloc[-2]):
        return False

    prev_close = float(df["Close"].iloc[-2])
    curr_close = float(df["Close"].iloc[-1])
    prev_lower = float(lower.iloc[-2])
    curr_lower = float(lower.iloc[-1])

    return prev_close >= prev_lower and curr_close < curr_lower


# =============================================================================
# Donchian Channel Signals
# =============================================================================

@RuleRegistry.register("dc_upper_breakout")
def dc_upper_breakout(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Detect price breaking above upper Donchian Channel (new high).

    Fires on the bar where price crosses above the upper band.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-100. Default: 20.

    Returns:
        bool: True on the bar where close crosses above upper band.
    """
    if len(df) < window + 1:
        return False

    result = DonchianChannel.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'offset': 0}
    )
    upper = result['hband']

    if pd.isna(upper.iloc[-1]) or pd.isna(upper.iloc[-2]):
        return False

    prev_close = float(df["Close"].iloc[-2])
    curr_close = float(df["Close"].iloc[-1])
    prev_upper = float(upper.iloc[-2])
    curr_upper = float(upper.iloc[-1])

    return prev_close < prev_upper and curr_close >= curr_upper


@RuleRegistry.register("dc_lower_breakout")
def dc_lower_breakout(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Detect price breaking below lower Donchian Channel (new low).

    Fires on the bar where price crosses below the lower band.

    Type: TRIGGER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-100. Default: 20.

    Returns:
        bool: True on the bar where close crosses below lower band.
    """
    if len(df) < window + 1:
        return False

    result = DonchianChannel.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'offset': 0}
    )
    lower = result['lband']

    if pd.isna(lower.iloc[-1]) or pd.isna(lower.iloc[-2]):
        return False

    prev_close = float(df["Close"].iloc[-2])
    curr_close = float(df["Close"].iloc[-1])
    prev_lower = float(lower.iloc[-2])
    curr_lower = float(lower.iloc[-1])

    return prev_close > prev_lower and curr_close <= curr_lower


# =============================================================================
# Ulcer Index Signals
# =============================================================================

@RuleRegistry.register("ulcer_high_risk")
def ulcer_high_risk(df: pd.DataFrame, window: int = 14, threshold: float = 10.0) -> bool:
    """
    Check if Ulcer Index indicates high downside risk.

    Higher Ulcer Index values indicate greater downside volatility.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-50. Default: 14.
        threshold (float): High risk threshold. Range: 5-30. Default: 10.0.

    Returns:
        bool: True if Ulcer Index > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = UlcerIndex.compute(
        data={'close': df["Close"]},
        params={'window': window}
    )
    ui = result['ulcer_index']

    if pd.isna(ui.iloc[-1]):
        return False

    return float(ui.iloc[-1]) > threshold


@RuleRegistry.register("ulcer_low_risk")
def ulcer_low_risk(df: pd.DataFrame, window: int = 14, threshold: float = 5.0) -> bool:
    """
    Check if Ulcer Index indicates low downside risk.

    Lower Ulcer Index values indicate lower downside volatility.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-50. Default: 14.
        threshold (float): Low risk threshold. Range: 1-15. Default: 5.0.

    Returns:
        bool: True if Ulcer Index < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = UlcerIndex.compute(
        data={'close': df["Close"]},
        params={'window': window}
    )
    ui = result['ulcer_index']

    if pd.isna(ui.iloc[-1]):
        return False

    return float(ui.iloc[-1]) < threshold
