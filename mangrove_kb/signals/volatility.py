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

from mangrove_kb.registry import RuleRegistry

# Import volatility indicator classes
from mangrove_kb.indicators import (
    ATR,
    BollingerBands,
    KeltnerChannel,
    DonchianChannel,
    UlcerIndex,
    NATR,
    ATRTrailingStop,
    STARCBands,
    VolatilityStop,
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
    Family: breakout
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
    Family: breakout
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
    Family: volatility
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
    Family: volatility
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
    Family: breakout
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
    Family: breakout
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

    Fires on the bar where close exceeds the prior period's upper band.
    The channel is computed from the N bars BEFORE the current bar (offset=1)
    so the current bar's high doesn't inflate the band it's compared against.

    Type: TRIGGER
    Family: breakout
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-100. Default: 20.

    Returns:
        bool: True on the bar where close breaks above the prior upper band.
    """
    if len(df) < window + 2:
        return False

    result = DonchianChannel.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'offset': 1}
    )
    upper = result['hband']

    if pd.isna(upper.iloc[-1]) or pd.isna(upper.iloc[-2]):
        return False

    prev_close = float(df["Close"].iloc[-2])
    curr_close = float(df["Close"].iloc[-1])
    prev_upper = float(upper.iloc[-2])
    curr_upper = float(upper.iloc[-1])

    return prev_close <= prev_upper and curr_close > curr_upper


@RuleRegistry.register("dc_lower_breakout")
def dc_lower_breakout(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Detect price breaking below lower Donchian Channel (new low).

    Fires on the bar where close drops below the prior period's lower band.
    The channel is computed from the N bars BEFORE the current bar (offset=1)
    so the current bar's low doesn't deflate the band it's compared against.

    Type: TRIGGER
    Family: breakout
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-100. Default: 20.

    Returns:
        bool: True on the bar where close breaks below the prior lower band.
    """
    if len(df) < window + 2:
        return False

    result = DonchianChannel.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'offset': 1}
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
# Ulcer Index Signals
# =============================================================================

@RuleRegistry.register("ulcer_high_risk")
def ulcer_high_risk(df: pd.DataFrame, window: int = 14, threshold: float = 10.0) -> bool:
    """
    Check if Ulcer Index indicates high downside risk.

    Higher Ulcer Index values indicate greater downside volatility.

    Type: FILTER
    Family: volatility
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
    Family: volatility
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


# =============================================================================
# Wave D Volatility Signals (NATR, ATRTrailingStop, STARCBands, VolatilityStop)
# =============================================================================


@RuleRegistry.register("natr_high_volatility")
def natr_high_volatility(df: pd.DataFrame, window: int = 14, threshold: float = 2.0) -> bool:
    """
    Check if normalized ATR is above a high-volatility threshold.

    NATR = 100 * ATR / close, so the threshold is a percentage. Values above
    ~2-3% typically indicate elevated volatility in equities; crypto markets
    can run 4-6%+ routinely.

    Type: FILTER
    Family: volatility
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): NATR window. Range: 5-100. Default: 14.
        threshold (float): High volatility threshold as percentage. Range: 0.5-20.0. Default: 2.0.

    Returns:
        bool: True if NATR > threshold, False otherwise.
    """
    if len(df) < window + 1:
        return False
    natr = NATR.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]}, params={'window': window})['natr']
    if pd.isna(natr.iloc[-1]):
        return False
    return bool(natr.iloc[-1] > threshold)


@RuleRegistry.register("natr_low_volatility")
def natr_low_volatility(df: pd.DataFrame, window: int = 14, threshold: float = 1.0) -> bool:
    """
    Check if normalized ATR is below a low-volatility threshold.

    Useful as a squeeze / consolidation filter.

    Type: FILTER
    Family: volatility
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): NATR window. Range: 5-100. Default: 14.
        threshold (float): Low volatility threshold as percentage. Range: 0.1-5.0. Default: 1.0.

    Returns:
        bool: True if NATR < threshold, False otherwise.
    """
    if len(df) < window + 1:
        return False
    natr = NATR.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]}, params={'window': window})['natr']
    if pd.isna(natr.iloc[-1]):
        return False
    return bool(natr.iloc[-1] < threshold)


def _atr_trailing_stop_direction(df: pd.DataFrame, window: int, multiplier: float):
    """Helper: compute ATRTrailingStop and return the direction series, or None if not enough data."""
    if len(df) < window + 2:
        return None
    out = ATRTrailingStop.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'multiplier': multiplier},
    )
    return out['direction']


@RuleRegistry.register("atr_trailing_stop_long")
def atr_trailing_stop_long(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Check if ATR Trailing Stop is in the long regime (+1 direction).

    Type: FILTER
    Family: trend_following
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-100. Default: 14.
        multiplier (float): ATR multiplier for stop distance. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if trailing stop is in long regime, False otherwise.
    """
    direction = _atr_trailing_stop_direction(df, window, multiplier)
    if direction is None or pd.isna(direction.iloc[-1]):
        return False
    return direction.iloc[-1] == 1


@RuleRegistry.register("atr_trailing_stop_short")
def atr_trailing_stop_short(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Check if ATR Trailing Stop is in the short regime (-1 direction).

    Type: FILTER
    Family: trend_following
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-100. Default: 14.
        multiplier (float): ATR multiplier for stop distance. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if trailing stop is in short regime, False otherwise.
    """
    direction = _atr_trailing_stop_direction(df, window, multiplier)
    if direction is None or pd.isna(direction.iloc[-1]):
        return False
    return direction.iloc[-1] == -1


@RuleRegistry.register("atr_trailing_stop_flip_up")
def atr_trailing_stop_flip_up(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Detect ATR Trailing Stop flipping from short (-1) to long (+1).

    Bullish trend-following entry signal.

    Type: TRIGGER
    Family: trend_following
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-100. Default: 14.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if direction flipped from -1 to +1 on the current bar.
    """
    direction = _atr_trailing_stop_direction(df, window, multiplier)
    if direction is None or len(direction) < 2:
        return False
    prev, curr = direction.iloc[-2], direction.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    return bool(prev == -1 and curr == 1)


@RuleRegistry.register("atr_trailing_stop_flip_down")
def atr_trailing_stop_flip_down(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Detect ATR Trailing Stop flipping from long (+1) to short (-1).

    Bearish trend-following entry signal.

    Type: TRIGGER
    Family: trend_following
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-100. Default: 14.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if direction flipped from +1 to -1 on the current bar.
    """
    direction = _atr_trailing_stop_direction(df, window, multiplier)
    if direction is None or len(direction) < 2:
        return False
    prev, curr = direction.iloc[-2], direction.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    return bool(prev == 1 and curr == -1)


@RuleRegistry.register("starc_upper_breakout")
def starc_upper_breakout(
    df: pd.DataFrame, window: int = 20, window_atr: int = 15, multiplier: float = 2.0
) -> bool:
    """
    Check if close is above the STARC upper band (breakout).

    Type: FILTER
    Family: mean_reversion
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): SMA window. Range: 5-100. Default: 20.
        window_atr (int): ATR window. Range: 5-100. Default: 15.
        multiplier (float): ATR multiplier for band width. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if close > upper band, False otherwise.
    """
    if len(df) < max(window, window_atr) + 1:
        return False
    out = STARCBands.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'window_atr': window_atr, 'multiplier': multiplier},
    )
    hband = out['starc_hband']
    if pd.isna(hband.iloc[-1]):
        return False
    return bool(df["Close"].iloc[-1] > hband.iloc[-1])


@RuleRegistry.register("starc_lower_breakout")
def starc_lower_breakout(
    df: pd.DataFrame, window: int = 20, window_atr: int = 15, multiplier: float = 2.0
) -> bool:
    """
    Check if close is below the STARC lower band (breakdown).

    Type: FILTER
    Family: mean_reversion
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): SMA window. Range: 5-100. Default: 20.
        window_atr (int): ATR window. Range: 5-100. Default: 15.
        multiplier (float): ATR multiplier for band width. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if close < lower band, False otherwise.
    """
    if len(df) < max(window, window_atr) + 1:
        return False
    out = STARCBands.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'window_atr': window_atr, 'multiplier': multiplier},
    )
    lband = out['starc_lband']
    if pd.isna(lband.iloc[-1]):
        return False
    return bool(df["Close"].iloc[-1] < lband.iloc[-1])


@RuleRegistry.register("volatility_stop_upper")
def volatility_stop_upper(df: pd.DataFrame, window: int = 20, multiplier: float = 2.0) -> bool:
    """
    Check if close has reached or exceeded the stdev-based volatility upper stop.

    Indicates the price has moved multiplier standard deviations above the
    current bar -- a potential exhaustion / mean-reversion signal.

    Type: FILTER
    Family: mean_reversion
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling stdev window. Range: 5-100. Default: 20.
        multiplier (float): Stdev multiplier for stop distance. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if close >= upper volatility stop, False otherwise.
    """
    if len(df) < window + 1:
        return False
    out = VolatilityStop.compute(data={'close': df["Close"]}, params={'window': window, 'multiplier': multiplier})
    hband = out['vstop_hband']
    if pd.isna(hband.iloc[-1]):
        return False
    return bool(df["Close"].iloc[-1] >= hband.iloc[-1])


@RuleRegistry.register("volatility_stop_lower")
def volatility_stop_lower(df: pd.DataFrame, window: int = 20, multiplier: float = 2.0) -> bool:
    """
    Check if close has reached or fallen below the stdev-based volatility lower stop.

    Type: FILTER
    Family: mean_reversion
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling stdev window. Range: 5-100. Default: 20.
        multiplier (float): Stdev multiplier for stop distance. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if close <= lower volatility stop, False otherwise.
    """
    if len(df) < window + 1:
        return False
    out = VolatilityStop.compute(data={'close': df["Close"]}, params={'window': window, 'multiplier': multiplier})
    lband = out['vstop_lband']
    if pd.isna(lband.iloc[-1]):
        return False
    return bool(df["Close"].iloc[-1] <= lband.iloc[-1])
