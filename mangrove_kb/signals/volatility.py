"""Volatility-based trading signals.

This module contains signal functions based on volatility indicators including:
- Bollinger Bands
- ATR (Average True Range)
- Keltner Channel
- Donchian Channel
- Ulcer Index
"""

import logging

import numpy as np
import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import deprecated_signal, renamed_signals

# Import volatility indicator classes
from mangrove_kb.indicators import (
    ATR,
    ATRTrailingStop,
    BollingerBands,
    ChandelierLevels,
    DonchianChannel,
    KeltnerChannel,
    NATR,
    STARCBands,
    SqueezeDepth,
    SuperTrendBands,
    UlcerIndex,
    VolatilityEnvelope,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Bollinger Bands Signals
# =============================================================================

@RuleRegistry.register("bb_upper_breakout")
def bb_upper_breakout(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2
) -> bool:
    """Signal: bb_upper_breakout

    Detect price breaking above the upper Bollinger Band. Fires on the bar where price crosses above
    the upper band, not while price remains above it. Crypto assets frequently test bands during
    high volatility; use with volume confirmation.

    Friendly-Name: Upside Range Breakout
    Display-Name: Bollinger Band Upper Breakout
    Short-Description: Price just broke above its normal trading range.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands
    Warmup: window

    Formula:
        close[t-1] <= hband[t-1] and close[t] > hband[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: MA period for center band
        window_dev [default=2, min=1, max=5]: Standard deviation multiplier

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close crosses above upper band

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.

    Returns:
        bool: True on the bar where close crosses above upper band.
    """
    closes = df["close"]
    if len(closes) < window + 1:
        return False

    result = BollingerBands.compute(
        data={'close': closes},
        params={'window': window, 'window_dev': window_dev}
    )
    hband = result['hband']

    if pd.isna(hband.iloc[-1]) or pd.isna(hband.iloc[-2]):
        return False

    prev_close = float(closes.iloc[-2])
    curr_close = float(closes.iloc[-1])
    prev_hband = float(hband.iloc[-2])
    curr_hband = float(hband.iloc[-1])

    return prev_close <= prev_hband and curr_close > curr_hband


@RuleRegistry.register("bb_lower_breakout")
def bb_lower_breakout(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2
) -> bool:
    """Signal: bb_lower_breakout

    Detect price breaking below the lower Bollinger Band. Fires on the bar where price crosses below
    the lower band, not while price remains below it. Crypto assets frequently test bands during
    high volatility; use with volume confirmation.

    Friendly-Name: Downside Range Breakout
    Display-Name: Bollinger Band Lower Breakout
    Short-Description: Price just broke below its normal trading range.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands
    Warmup: window

    Formula:
        close[t-1] >= lband[t-1] and close[t] < lband[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: MA period for center band
        window_dev [default=2, min=1, max=5]: Standard deviation multiplier

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close crosses below lower band

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.

    Returns:
        bool: True on the bar where close crosses below lower band.
    """
    closes = df["close"]
    if len(closes) < window + 1:
        return False

    result = BollingerBands.compute(
        data={'close': closes},
        params={'window': window, 'window_dev': window_dev}
    )
    lband = result['lband']

    if pd.isna(lband.iloc[-1]) or pd.isna(lband.iloc[-2]):
        return False

    prev_close = float(closes.iloc[-2])
    curr_close = float(closes.iloc[-1])
    prev_lband = float(lband.iloc[-2])
    curr_lband = float(lband.iloc[-1])

    return prev_close >= prev_lband and curr_close < curr_lband


@RuleRegistry.register("bb_squeeze")
def bb_squeeze(
    df: pd.DataFrame, window: int = 20, window_dev: int = 2, threshold: float = 5.0
) -> bool:
    """Signal: bb_squeeze

    Detect Bollinger Band squeeze onset (low volatility, potential breakout). Fires on the bar where
    band width drops below the threshold, not while it remains below.

    Friendly-Name: Market Goes Quiet
    Display-Name: Bollinger Band Squeeze
    Short-Description: Price swings just narrowed sharply, which often comes before a big move.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/bollinger-bandwidth
    Warmup: window

    Formula:
        wband[t-1] >= threshold and wband[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: MA period for center band
        window_dev [default=2, min=1, max=5]: Standard deviation multiplier
        threshold [default=5.0, min=1.0, max=20.0]: Band width percentage threshold

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where band width crosses below threshold

    Type: TRIGGER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.
        threshold (float): Band width percentage threshold. Range: 1-20. Default: 5.0.

    Returns:
        bool: True on the bar where band width crosses below threshold.
    """
    closes = df["close"]
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


# --- Band-state filters -----------------------------------------------------
#
# These four were `hband_indicator` / `lband_indicator` outputs on BollingerBands and
# KeltnerChannel: `np.where(close > hband, 1.0, 0.0)`, a boolean decision over a numeric series the
# indicator already emitted. An indicator emits a numeric measurement; a signal emits a boolean
# predicate. They are signals, so they live here.
#
# They are STATE, not crossings -- deliberately distinct from bb_upper_breakout / bb_lower_breakout
# above, which are TRIGGERs firing only on the bar that crosses. These stay True for as long as
# close sits outside the band, which is what a regime filter needs. Before this move nothing in the
# package answered "is price outside the band right now"; the flags carried that meaning but no
# consumer could reach it, since an indicator output is not addressable as a rule.
#
# The strict inequality is carried over unchanged from the indicator: touching the band is not
# outside it.


@RuleRegistry.register("bb_above_upper")
def bb_above_upper(df: pd.DataFrame, window: int = 20, window_dev: int = 2) -> bool:
    """Signal: bb_above_upper

    Check if price is currently above the upper Bollinger Band. A state, not an event: true for
    every bar close sits above the band, unlike bb_upper_breakout which fires only on the bar that
    crosses it.

    Friendly-Name: Above Usual Range
    Display-Name: Above Bollinger Upper Band
    Short-Description: Price is trading above its normal range.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands
    Warmup: window - 1

    Formula:
        close[t] > hband[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: MA period for center band
        window_dev [default=2, min=1, max=5]: Standard deviation multiplier

    Outputs:
        fired [boolean, 0..1]:
            True if close > upper band on the current bar

    Type: FILTER
    Requires: close

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands

    Formula:
        close[t] > hband[t]

    Inputs:
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if close > upper band on the current bar

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.

    Returns:
        bool: True if close > upper band on the current bar.
    """
    closes = df["close"]
    if len(closes) < window:
        return False

    hband = BollingerBands.compute(
        data={'close': closes}, params={'window': window, 'window_dev': window_dev}
    )['hband']

    if pd.isna(hband.iloc[-1]):
        return False
    return bool(float(closes.iloc[-1]) > float(hband.iloc[-1]))


@RuleRegistry.register("bb_below_lower")
def bb_below_lower(df: pd.DataFrame, window: int = 20, window_dev: int = 2) -> bool:
    """Signal: bb_below_lower

    Check if price is currently below the lower Bollinger Band. A state, not an event: true for
    every bar close sits below the band, unlike bb_lower_breakout which fires only on the bar that
    crosses it.

    Friendly-Name: Below Usual Range
    Display-Name: Below Bollinger Lower Band
    Short-Description: Price is trading below its normal range.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands
    Warmup: window - 1

    Formula:
        close[t] < lband[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: MA period for center band
        window_dev [default=2, min=1, max=5]: Standard deviation multiplier

    Outputs:
        fired [boolean, 0..1]:
            True if close < lower band on the current bar

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MA period for center band. Range: 5-100. Default: 20.
        window_dev (int): Standard deviation multiplier. Range: 1-5. Default: 2.

    Returns:
        bool: True if close < lower band on the current bar.
    """
    closes = df["close"]
    if len(closes) < window:
        return False

    lband = BollingerBands.compute(
        data={'close': closes}, params={'window': window, 'window_dev': window_dev}
    )['lband']

    if pd.isna(lband.iloc[-1]):
        return False
    return bool(float(closes.iloc[-1]) < float(lband.iloc[-1]))


@RuleRegistry.register("kc_above_upper")
def kc_above_upper(
    df: pd.DataFrame, window: int = 20, window_atr: int = 10, multiplier: float = 2.0
) -> bool:
    """Signal: kc_above_upper

    Check if price is currently above the upper Keltner Channel band. A state, not an event: true
    for every bar close sits above the band.

    Friendly-Name: Above Volatility Channel
    Display-Name: Above Keltner Upper Band
    Short-Description: Price is trading above its normal volatility channel.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/keltner-channels
    Warmup: max(window, window_atr) - 1

    Formula:
        close[t] > hband[t] -- a STATE: true for every bar close sits above the band, unlike kc_upper_breakout which fires only on the bar that crosses it

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: EMA period for the center band
        window_atr [default=10, min=5, max=30]: ATR period
        multiplier [default=2.0, min=0.5, max=5.0]: ATR multiplier for band width

    Outputs:
        fired [boolean, 0..1]:
            True if close > upper band on the current bar

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for the center band. Range: 10-50. Default: 20.
        window_atr (int): ATR period. Range: 5-30. Default: 10.
        multiplier (float): ATR multiplier for band width. Range: 0.5-5. Default: 2.0.

    Returns:
        bool: True if close > upper band on the current bar.
    """
    closes = df["close"]
    if len(closes) < max(window, window_atr):
        return False

    hband = KeltnerChannel.compute(
        data={'high': df["high"], 'low': df["low"], 'close': closes},
        params={'window': window, 'window_atr': window_atr,
                'original_version': False, 'multiplier': multiplier},
    )['hband']

    if pd.isna(hband.iloc[-1]):
        return False
    return bool(float(closes.iloc[-1]) > float(hband.iloc[-1]))


@RuleRegistry.register("kc_below_lower")
def kc_below_lower(
    df: pd.DataFrame, window: int = 20, window_atr: int = 10, multiplier: float = 2.0
) -> bool:
    """Signal: kc_below_lower

    Check if price is currently below the lower Keltner Channel band. A state, not an event: true
    for every bar close sits below the band.

    Friendly-Name: Below Volatility Channel
    Display-Name: Below Keltner Lower Band
    Short-Description: Price is trading below its normal volatility channel.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/keltner-channels
    Warmup: max(window, window_atr) - 1

    Formula:
        close[t] < lband[t] -- a STATE: true for every bar close sits below the band, unlike kc_lower_breakout which fires only on the bar that crosses it

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: EMA period for the center band
        window_atr [default=10, min=5, max=30]: ATR period
        multiplier [default=2.0, min=0.5, max=5.0]: ATR multiplier for band width

    Outputs:
        fired [boolean, 0..1]:
            True if close < lower band on the current bar

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for the center band. Range: 10-50. Default: 20.
        window_atr (int): ATR period. Range: 5-30. Default: 10.
        multiplier (float): ATR multiplier for band width. Range: 0.5-5. Default: 2.0.

    Returns:
        bool: True if close < lower band on the current bar.
    """
    closes = df["close"]
    if len(closes) < max(window, window_atr):
        return False

    lband = KeltnerChannel.compute(
        data={'high': df["high"], 'low': df["low"], 'close': closes},
        params={'window': window, 'window_atr': window_atr,
                'original_version': False, 'multiplier': multiplier},
    )['lband']

    if pd.isna(lband.iloc[-1]):
        return False
    return bool(float(closes.iloc[-1]) < float(lband.iloc[-1]))


# =============================================================================
# ATR/Volatility Signals
# =============================================================================

@RuleRegistry.register("atr_high_volatility")
def atr_high_volatility(
    df: pd.DataFrame, window: int = 14, threshold_pct: float = 3.0
) -> bool:
    """Signal: atr_high_volatility

    Check if ATR indicates high volatility relative to price. High volatility (ATR as % of close >
    threshold) can indicate potential trading opportunities or increased risk.

    Friendly-Name: Big Price Swings
    Display-Name: ATR High Volatility
    Short-Description: Typical bar-to-bar price swings are large relative to price.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-true-range-atr
    Warmup: window - 1

    Formula:
        atr[t] / close[t] * 100 > threshold_pct -- ATR normalised by price here rather than read raw, so the threshold is comparable across instruments. False when close is zero.

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: ATR period
        threshold_pct [default=3.0, min=0.5, max=10.0]: ATR as percentage of close threshold

    Outputs:
        fired [boolean, 0..1]:
            True if ATR% > threshold, False otherwise

    Type: FILTER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window}
    )
    atr = result['atr']

    if pd.isna(atr.iloc[-1]):
        return False

    close = float(df["close"].iloc[-1])
    if close == 0:
        return False

    atr_pct = (float(atr.iloc[-1]) / close) * 100
    return atr_pct > threshold_pct


# =============================================================================
# Keltner Channel Signals
# =============================================================================

@RuleRegistry.register("kc_upper_breakout")
def kc_upper_breakout(df: pd.DataFrame, window: int = 20, window_atr: int = 10, multiplier: float = 2.0, original_version: bool = False) -> bool:
    """Signal: kc_upper_breakout

    Detect price breaking above upper Keltner Channel band. Fires on the bar where price crosses
    above the upper band.

    Friendly-Name: Breaks Above Channel
    Display-Name: Keltner Channel Upper Breakout
    Short-Description: Price just broke above its normal volatility channel.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/keltner-channels
    Warmup: max(window, window_atr)

    Formula:
        close[t-1] <= hband[t-1] and close[t] > hband[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: EMA period
        window_atr [default=10, min=5, max=30]: ATR period
        multiplier [default=2.0, min=0.5]: ATR multiplier for band width
        original_version [default=False]: Use original Keltner Channel formula instead of EMA+ATR

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close crosses above upper band

    Type: TRIGGER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'original_version': original_version,
                # The original formulation ignores both; the indicator requires None there.
                'window_atr': None if original_version else window_atr,
                'multiplier': None if original_version else multiplier}
    )
    hband = result['hband']

    if pd.isna(hband.iloc[-1]) or pd.isna(hband.iloc[-2]):
        return False

    prev_close = float(df["close"].iloc[-2])
    curr_close = float(df["close"].iloc[-1])
    prev_hband = float(hband.iloc[-2])
    curr_hband = float(hband.iloc[-1])

    return prev_close <= prev_hband and curr_close > curr_hband


@RuleRegistry.register("kc_lower_breakout")
def kc_lower_breakout(df: pd.DataFrame, window: int = 20, window_atr: int = 10, multiplier: float = 2.0, original_version: bool = False) -> bool:
    """Signal: kc_lower_breakout

    Detect price breaking below lower Keltner Channel band. Fires on the bar where price crosses
    below the lower band.

    Friendly-Name: Breaks Below Channel
    Display-Name: Keltner Channel Lower Breakout
    Short-Description: Price just broke below its normal volatility channel.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/keltner-channels
    Warmup: max(window, window_atr)

    Formula:
        close[t-1] >= lband[t-1] and close[t] < lband[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: EMA period
        window_atr [default=10, min=5, max=30]: ATR period
        multiplier [default=2.0, min=0.5]: ATR multiplier for band width
        original_version [default=False]: Use original Keltner Channel formula instead of EMA+ATR

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close crosses below lower band

    Type: TRIGGER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'original_version': original_version,
                # The original formulation ignores both; the indicator requires None there.
                'window_atr': None if original_version else window_atr,
                'multiplier': None if original_version else multiplier}
    )
    lband = result['lband']

    if pd.isna(lband.iloc[-1]) or pd.isna(lband.iloc[-2]):
        return False

    prev_close = float(df["close"].iloc[-2])
    curr_close = float(df["close"].iloc[-1])
    prev_lband = float(lband.iloc[-2])
    curr_lband = float(lband.iloc[-1])

    return prev_close >= prev_lband and curr_close < curr_lband


# =============================================================================
# Donchian Channel Signals
# =============================================================================

@RuleRegistry.register("dc_upper_breakout")
def dc_upper_breakout(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: dc_upper_breakout

    Detect price breaking above upper Donchian Channel (new high). Fires on the bar where close
    exceeds the prior period's upper band. The channel is computed from the N bars BEFORE the
    current bar so the current bar's high doesn't inflate the band it's compared against -- that is
    the Donchian convention and the indicator's own behaviour.

    Friendly-Name: New Period High
    Display-Name: Donchian Channel Upper Breakout
    Short-Description: Price just closed above the highest high of the prior period.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/price-channels
    Warmup: window + 1

    Formula:
        close[t-1] <= hband[t-1] and close[t] > hband[t] -- the channel spans the bars PRECEDING each bar (include_current_bar=False), which is what makes a break possible at all

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=5, max=100]: Lookback period

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close breaks above the prior upper band

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-100. Default: 20.

    Returns:
        bool: True on the bar where close breaks above the prior upper band.
    """
    if len(df) < window + 2:
        return False

    result = DonchianChannel.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'include_current_bar': False}
    )
    hband = result['hband']

    if pd.isna(hband.iloc[-1]) or pd.isna(hband.iloc[-2]):
        return False

    prev_close = float(df["close"].iloc[-2])
    curr_close = float(df["close"].iloc[-1])
    prev_hband = float(hband.iloc[-2])
    curr_hband = float(hband.iloc[-1])

    return prev_close <= prev_hband and curr_close > curr_hband


@RuleRegistry.register("dc_lower_breakout")
def dc_lower_breakout(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: dc_lower_breakout

    Detect price breaking below lower Donchian Channel (new low). Fires on the bar where close drops
    below the prior period's lower band. The channel is computed from the N bars BEFORE the current
    bar so the current bar's low doesn't deflate the band it's compared against -- that is the
    Donchian convention and the indicator's own behaviour.

    Friendly-Name: New Period Low
    Display-Name: Donchian Channel Lower Breakout
    Short-Description: Price just closed below the lowest low of the prior period.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/price-channels
    Warmup: window + 1

    Formula:
        close[t-1] >= lband[t-1] and close[t] < lband[t] -- the channel spans the bars PRECEDING each bar (include_current_bar=False)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=5, max=100]: Lookback period

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close breaks below the prior lower band

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 5-100. Default: 20.

    Returns:
        bool: True on the bar where close breaks below the prior lower band.
    """
    if len(df) < window + 2:
        return False

    result = DonchianChannel.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'include_current_bar': False}
    )
    lband = result['lband']

    if pd.isna(lband.iloc[-1]) or pd.isna(lband.iloc[-2]):
        return False

    prev_close = float(df["close"].iloc[-2])
    curr_close = float(df["close"].iloc[-1])
    prev_lband = float(lband.iloc[-2])
    curr_lband = float(lband.iloc[-1])

    return prev_close >= prev_lband and curr_close < curr_lband


# =============================================================================
# Ulcer Index Signals
# =============================================================================

@RuleRegistry.register("ulcer_high_risk")
def ulcer_high_risk(df: pd.DataFrame, window: int = 14, threshold: float = 10.0) -> bool:
    """Signal: ulcer_high_risk

    Check if Ulcer Index indicates high downside risk. Higher Ulcer Index values indicate greater
    downside volatility.

    Friendly-Name: Deep Drawdowns
    Display-Name: Ulcer Index High Risk
    Short-Description: Price has spent recent bars well below its highs, a sign of high downside risk.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index
    Warmup: window - 1

    Formula:
        ulcer_index[t] > threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=5, max=50]: Lookback period
        threshold [default=10.0, min=5.0, max=30.0]: High risk threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Ulcer Index > threshold, False otherwise

    Type: FILTER
    Requires: close

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
        data={'close': df["close"]},
        params={'window': window}
    )
    ui = result['ulcer_index']

    if pd.isna(ui.iloc[-1]):
        return False

    return float(ui.iloc[-1]) > threshold


@RuleRegistry.register("ulcer_low_risk")
def ulcer_low_risk(df: pd.DataFrame, window: int = 14, threshold: float = 5.0) -> bool:
    """Signal: ulcer_low_risk

    Check if Ulcer Index indicates low downside risk. Lower Ulcer Index values indicate lower
    downside volatility.

    Friendly-Name: Shallow Drawdowns
    Display-Name: Ulcer Index Low Risk
    Short-Description: Price has stayed close to its recent highs, a sign of low downside risk.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index
    Warmup: window - 1

    Formula:
        ulcer_index[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=5, max=50]: Lookback period
        threshold [default=5.0, min=1.0, max=15.0]: Low risk threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Ulcer Index < threshold, False otherwise

    Type: FILTER
    Requires: close

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
        data={'close': df["close"]},
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
    """Signal: natr_high_volatility

    Check if normalized ATR is above a high-volatility threshold. NATR = 100 * ATR / close, so the
    threshold is a percentage. Values above ~2-3% typically indicate elevated volatility in
    equities; crypto markets can run 4-6%+ routinely.

    Friendly-Name: Volatile Market
    Display-Name: Normalized ATR High Volatility
    Short-Description: Price is swinging more than usual as a percent of price.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/volatility_indicators.html
    Warmup: window

    Formula:
        natr[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=100]: NATR window
        threshold [default=2.0, min=0.5]: High volatility threshold as percentage

    Outputs:
        fired [boolean, 0..1]:
            True if NATR > threshold, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): NATR window. Range: 5-100. Default: 14.
        threshold (float): High volatility threshold as percentage. Range: 0.5-20.0. Default: 2.0.

    Returns:
        bool: True if NATR > threshold, False otherwise.
    """
    if len(df) < window + 1:
        return False
    natr = NATR.compute(data={'high': df["high"], 'low': df["low"], 'close': df["close"]}, params={'window': window})['natr']
    if pd.isna(natr.iloc[-1]):
        return False
    return bool(natr.iloc[-1] > threshold)


@RuleRegistry.register("natr_low_volatility")
def natr_low_volatility(df: pd.DataFrame, window: int = 14, threshold: float = 1.0) -> bool:
    """Signal: natr_low_volatility

    Check if normalized ATR is below a low-volatility threshold. Useful as a squeeze / consolidation
    filter.

    Friendly-Name: Calm Market
    Display-Name: Normalized ATR Low Volatility
    Short-Description: Price is swinging less than usual, often before a larger move.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/volatility_indicators.html
    Warmup: window

    Formula:
        natr[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=100]: NATR window
        threshold [default=1.0, min=0.1]: Low volatility threshold as percentage

    Outputs:
        fired [boolean, 0..1]:
            True if NATR < threshold, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): NATR window. Range: 5-100. Default: 14.
        threshold (float): Low volatility threshold as percentage. Range: 0.1-5.0. Default: 1.0.

    Returns:
        bool: True if NATR < threshold, False otherwise.
    """
    if len(df) < window + 1:
        return False
    natr = NATR.compute(data={'high': df["high"], 'low': df["low"], 'close': df["close"]}, params={'window': window})['natr']
    if pd.isna(natr.iloc[-1]):
        return False
    return bool(natr.iloc[-1] < threshold)


def _atr_trailing_stop_direction(df: pd.DataFrame, window: int, multiplier: float):
    """Helper: compute ATRTrailingStop and return the direction series, or None if not enough data."""
    if len(df) < window + 2:
        return None
    out = ATRTrailingStop.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'multiplier': multiplier},
    )
    return out['direction']


@RuleRegistry.register("atr_trailing_stop_long")
@deprecated_signal(
    "ATRTrailingStop carries its stop level forward and emits `direction` (+1 long / -1 "
    "short); this signal reads that verdict, so it is not in the ontology graph"
)
def atr_trailing_stop_long(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Check if ATR Trailing Stop is in the long regime (+1 direction).

    Type: FILTER
    Requires: high, low, close
    Disabled: True
    Disabled-Reason: ATRTrailingStop is a stop policy, not a measurement; a trailing stop belongs in the exit rules of an execution config, not in a signal pool. Stored strategies that name this signal keep evaluating.

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
@deprecated_signal(
    "ATRTrailingStop carries its stop level forward and emits `direction` (+1 long / -1 "
    "short); this signal reads that verdict, so it is not in the ontology graph"
)
def atr_trailing_stop_short(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Check if ATR Trailing Stop is in the short regime (-1 direction).

    Type: FILTER
    Requires: high, low, close
    Disabled: True
    Disabled-Reason: ATRTrailingStop is a stop policy, not a measurement; a trailing stop belongs in the exit rules of an execution config, not in a signal pool. Stored strategies that name this signal keep evaluating.

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
@deprecated_signal(
    "ATRTrailingStop carries its stop level forward and emits `direction` (+1 long / -1 "
    "short); this signal reads that verdict, so it is not in the ontology graph"
)
def atr_trailing_stop_flip_up(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Detect ATR Trailing Stop flipping from short (-1) to long (+1).

    Bullish trend-following entry signal.

    Type: TRIGGER
    Requires: high, low, close
    Disabled: True
    Disabled-Reason: ATRTrailingStop is a stop policy, not a measurement; a trailing stop belongs in the exit rules of an execution config, not in a signal pool. Stored strategies that name this signal keep evaluating.

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
@deprecated_signal(
    "ATRTrailingStop carries its stop level forward and emits `direction` (+1 long / -1 "
    "short); this signal reads that verdict, so it is not in the ontology graph"
)
def atr_trailing_stop_flip_down(df: pd.DataFrame, window: int = 14, multiplier: float = 3.0) -> bool:
    """
    Detect ATR Trailing Stop flipping from long (+1) to short (-1).

    Bearish trend-following entry signal.

    Type: TRIGGER
    Requires: high, low, close
    Disabled: True
    Disabled-Reason: ATRTrailingStop is a stop policy, not a measurement; a trailing stop belongs in the exit rules of an execution config, not in a signal pool. Stored strategies that name this signal keep evaluating.

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
    """Signal: starc_upper_breakout

    Check if close is above the STARC upper band (breakout).

    Friendly-Name: Stretched Above Average
    Display-Name: Above STARC Upper Band
    Short-Description: Price is trading far above its average and may be overextended.

    Warmup: max(window, window_atr)

    Formula:
        close[t] > starc_hband[t] -- a STATE despite the name: true for every bar close sits above the band, not only the bar that crosses it

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=5, max=100]: SMA window
        window_atr [default=15, min=5, max=100]: ATR window
        multiplier [default=2.0, min=0.5]: ATR multiplier for band width

    Outputs:
        fired [boolean, 0..1]:
            True if close > upper band, False otherwise

    Type: FILTER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'window_atr': window_atr, 'multiplier': multiplier},
    )
    hband = out['starc_hband']
    if pd.isna(hband.iloc[-1]):
        return False
    return bool(df["close"].iloc[-1] > hband.iloc[-1])


@RuleRegistry.register("starc_lower_breakout")
def starc_lower_breakout(
    df: pd.DataFrame, window: int = 20, window_atr: int = 15, multiplier: float = 2.0
) -> bool:
    """Signal: starc_lower_breakout

    Check if close is below the STARC lower band (breakdown).

    Friendly-Name: Stretched Below Average
    Display-Name: Below STARC Lower Band
    Short-Description: Price is trading far below its average and may be overdone.

    Warmup: max(window, window_atr)

    Formula:
        close[t] < starc_lband[t] -- a STATE despite the name: true for every bar close sits below the band

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=5, max=100]: SMA window
        window_atr [default=15, min=5, max=100]: ATR window
        multiplier [default=2.0, min=0.5]: ATR multiplier for band width

    Outputs:
        fired [boolean, 0..1]:
            True if close < lower band, False otherwise

    Type: FILTER
    Requires: high, low, close

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
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'window_atr': window_atr, 'multiplier': multiplier},
    )
    lband = out['starc_lband']
    if pd.isna(lband.iloc[-1]):
        return False
    return bool(df["close"].iloc[-1] < lband.iloc[-1])


@RuleRegistry.register("ve_above_upper")
def ve_above_upper(df: pd.DataFrame, window: int = 20, multiplier: float = 2.0) -> bool:
    """Signal: ve_above_upper

    Check if close is at or above the volatility envelope's upper band. Today's close is at least
    `multiplier` standard deviations above YESTERDAY's close, where the deviation is measured on
    recent returns. The envelope is centred on the previous close, not the current bar -- the old
    wording said "above the current bar", which would make the comparison vacuous. A STATE, not an
    event: true for every bar close stays at or beyond the band.

    Friendly-Name: Unusual Jump Up
    Display-Name: Above Volatility Envelope
    Short-Description: Price closed far above the previous close compared with normal moves.

    Warmup: window

    Formula:
        close[t] >= vstop_hband[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: Rolling stdev window
        multiplier [default=2.0, min=0.5]: Stdev multiplier for the band distance

    Outputs:
        fired [boolean, 0..1]:
            True if close >= vstop_hband, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling stdev window. Range: 5-100. Default: 20.
        multiplier (float): Stdev multiplier for the band distance. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if close >= vstop_hband, False otherwise.
    """
    if len(df) < window + 1:
        return False
    out = VolatilityEnvelope.compute(data={'close': df["close"]},
                                     params={'window': window, 'multiplier': multiplier})
    hband = out['vstop_hband']
    if pd.isna(hband.iloc[-1]):
        return False
    return bool(df["close"].iloc[-1] >= hband.iloc[-1])


@RuleRegistry.register("ve_below_lower")
def ve_below_lower(df: pd.DataFrame, window: int = 20, multiplier: float = 2.0) -> bool:
    """Signal: ve_below_lower

    Check if close is at or below the volatility envelope's lower band. Mirror of `ve_above_upper`:
    today's close is at least `multiplier` standard deviations below yesterday's. A STATE, not an
    event.

    Friendly-Name: Unusual Drop Down
    Display-Name: Below Volatility Envelope
    Short-Description: Price closed far below the previous close compared with normal moves.

    Warmup: window

    Formula:
        close[t] <= vstop_lband[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: Rolling stdev window
        multiplier [default=2.0, min=0.5]: Stdev multiplier for the band distance

    Outputs:
        fired [boolean, 0..1]:
            True if close <= vstop_lband, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling stdev window. Range: 5-100. Default: 20.
        multiplier (float): Stdev multiplier for the band distance. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if close <= vstop_lband, False otherwise.
    """
    if len(df) < window + 1:
        return False
    out = VolatilityEnvelope.compute(data={'close': df["close"]},
                                     params={'window': window, 'multiplier': multiplier})
    lband = out['vstop_lband']
    if pd.isna(lband.iloc[-1]):
        return False
    return bool(df["close"].iloc[-1] <= lband.iloc[-1])


# ---------------------------------------------------------------------------
# Chandelier Levels -- two volatility-scaled offsets from the window's extremes
# ---------------------------------------------------------------------------

def _chandelier_offsets(df: pd.DataFrame, window: int, multiplier: float):
    """Both offsets, or None before the window is filled.

    `len(df) < window`, not `window + 1`: the first defined value is at index `window - 1`, so a
    per-bar state predicate can answer from the window-th bar. The old bound discarded one bar more
    than the measurement needs.
    """
    if len(df) < window:
        return None
    out = ChandelierLevels.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'multiplier': multiplier},
    )
    return out['high_offset'], out['low_offset']


@RuleRegistry.register("cl_below_high_offset")
def cl_below_high_offset(df: pd.DataFrame, window: int = 22, multiplier: float = 3.0) -> bool:
    """Signal: cl_below_high_offset

    Check if close is below the Chandelier high offset (close < high_offset). A STATE, not an event:
    true for every bar close sits below the level, not only the bar that crosses it. Registered
    twice -- `chandelier_long_stop_hit` is the released name and names a use (an exit for a long)
    rather than what is measured.

    Friendly-Name: Well Off Highs
    Display-Name: Below Chandelier Exit (High)
    Short-Description: Price has fallen well below its recent high.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit
    Warmup: window - 1

    Formula:
        close[t] < high_offset[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=22, min=5, max=100]: Rolling extreme and ATR window
        multiplier [default=3.0, min=0.5]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True if close < high_offset, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling extreme and ATR window. Range: 5-100. Default: 22.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if close < high_offset, False otherwise.
    """
    offsets = _chandelier_offsets(df, window, multiplier)
    if offsets is None:
        return False
    high_offset, _ = offsets
    if pd.isna(high_offset.iloc[-1]):
        return False
    return bool(df["close"].iloc[-1] < high_offset.iloc[-1])


@RuleRegistry.register("cl_above_low_offset")
def cl_above_low_offset(df: pd.DataFrame, window: int = 22, multiplier: float = 3.0) -> bool:
    """Signal: cl_above_low_offset

    Check if close is above the Chandelier low offset (close > low_offset). A STATE, not an event.
    The two offsets are anchored to opposite extremes and can cross, so this and
    `cl_below_high_offset` are both true on some bars -- 15 of 1,294 BTC daily bars at the defaults.
    That is not a contradiction: they are two independent levels, not a band pair.

    Friendly-Name: Well Off Lows
    Display-Name: Above Chandelier Exit (Low)
    Short-Description: Price has risen well above its recent low.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit
    Warmup: window - 1

    Formula:
        close[t] > low_offset[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=22, min=5, max=100]: Rolling extreme and ATR window
        multiplier [default=3.0, min=0.5]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True if close > low_offset, False otherwise

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling extreme and ATR window. Range: 5-100. Default: 22.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if close > low_offset, False otherwise.
    """
    offsets = _chandelier_offsets(df, window, multiplier)
    if offsets is None:
        return False
    _, low_offset = offsets
    if pd.isna(low_offset.iloc[-1]):
        return False
    return bool(df["close"].iloc[-1] > low_offset.iloc[-1])


@RuleRegistry.register("cl_high_offset_break")
def cl_high_offset_break(df: pd.DataFrame, window: int = 22, multiplier: float = 3.0) -> bool:
    """Signal: cl_high_offset_break

    Detect close crossing below the Chandelier high offset. The EVENT paired with
    `cl_below_high_offset`'s state. The state is true for every bar close stays under the level --
    356 of 1,294 BTC daily bars at the defaults -- while this fires only on the bar that breaches
    it. A strategy wanting the event cannot recover it from the state without keeping its own
    history, which is why both exist.

    Friendly-Name: Falls Far From High
    Display-Name: Chandelier Exit (High) Break
    Short-Description: Price just fell well below its recent high, a common exit point for buyers.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit
    Warmup: window

    Formula:
        close[t-1] >= high_offset[t-1] and close[t] < high_offset[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=22, min=5, max=100]: Rolling extreme and ATR window
        multiplier [default=3.0, min=0.5]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close crosses below high_offset

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling extreme and ATR window. Range: 5-100. Default: 22.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True on the bar where close crosses below high_offset.
    """
    if len(df) < window + 1:
        return False
    offsets = _chandelier_offsets(df, window, multiplier)
    if offsets is None:
        return False
    high_offset, _ = offsets
    if pd.isna(high_offset.iloc[-1]) or pd.isna(high_offset.iloc[-2]):
        return False
    close = df["close"]
    return bool(close.iloc[-2] >= high_offset.iloc[-2] and close.iloc[-1] < high_offset.iloc[-1])


@RuleRegistry.register("cl_low_offset_break")
def cl_low_offset_break(df: pd.DataFrame, window: int = 22, multiplier: float = 3.0) -> bool:
    """Signal: cl_low_offset_break

    Detect close crossing above the Chandelier low offset. The EVENT paired with
    `cl_above_low_offset`'s state, which holds for 477 of 1,294 BTC daily bars at the defaults. The
    two offsets are anchored to OPPOSITE extremes -- high_offset below the rolling high, low_offset
    above the rolling low -- so they cross constantly: high_offset sits BELOW low_offset on 73% of
    BTC daily bars at the defaults. They are two independent levels, not a band pair, and nothing
    here may assume high_offset >= low_offset. Simultaneous firing with `cl_high_offset_break` is
    therefore not excluded by construction, though it does not occur on any of the seven fixtures.

    Friendly-Name: Climbs Far From Low
    Display-Name: Chandelier Exit (Low) Break
    Short-Description: Price just climbed well above its recent low.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit
    Warmup: window

    Formula:
        close[t-1] <= low_offset[t-1] and close[t] > low_offset[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=22, min=5, max=100]: Rolling extreme and ATR window
        multiplier [default=3.0, min=0.5]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True on the bar where close crosses above low_offset

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Rolling extreme and ATR window. Range: 5-100. Default: 22.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True on the bar where close crosses above low_offset.
    """
    if len(df) < window + 1:
        return False
    offsets = _chandelier_offsets(df, window, multiplier)
    if offsets is None:
        return False
    _, low_offset = offsets
    if pd.isna(low_offset.iloc[-1]) or pd.isna(low_offset.iloc[-2]):
        return False
    close = df["close"]
    return bool(close.iloc[-2] <= low_offset.iloc[-2] and close.iloc[-1] > low_offset.iloc[-1])


# The released names. They evaluate and warn; they are not separate signals, so the catalogue still
# reports one signal per behaviour. MangroveOracle's signals_metadata.json and its strategy cohort
# files hold these strings.
RuleRegistry.alias("chandelier_long_stop_hit", "cl_below_high_offset")
RuleRegistry.alias("chandelier_short_stop_hit", "cl_above_low_offset")
RuleRegistry.alias("volatility_stop_upper", "ve_above_upper")
RuleRegistry.alias("volatility_stop_lower", "ve_below_lower")


# ---------------------------------------------------------------------------
# TTM Squeeze, read from SqueezeDepth's measurement
# ---------------------------------------------------------------------------

def _squeeze(df, bb_window, bb_std, kc_window, kc_atr_mult, mom_window, need=1):
    if len(df) < max(bb_window, kc_window) + need:
        return None
    return SqueezeDepth.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'bb_window': bb_window, 'bb_std': bb_std, 'kc_window': kc_window,
                'kc_atr_mult': kc_atr_mult, 'mom_window': mom_window},
    )


@RuleRegistry.register("ttm_squeeze_active")
def ttm_squeeze_active(df: pd.DataFrame, bb_window: int = 20, bb_std: float = 2.0,
                       kc_window: int = 20, kc_atr_mult: float = 1.5,
                       mom_window: int = 12) -> bool:
    """Signal: ttm_squeeze_active

    Check if the Bollinger Bands are inside the Keltner Channel (the squeeze is on). `squeeze_depth`
    is how far inside the Keltner Channel the narrower Bollinger band sits, so a positive depth IS
    the squeeze. The indicator measures the distance; this decides that a positive distance counts.

    Friendly-Name: Market Coiling
    Display-Name: TTM Squeeze Active
    Short-Description: Price swings are unusually tight, building up for a larger move.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze
    Warmup: max(bb_window, kc_window)

    Formula:
        squeeze_depth[t] > 0 -- Bollinger Bands entirely inside the Keltner Channel

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        bb_window [default=20, min=5, max=100]: Bollinger window
        bb_std [default=2.0, min=0.5]: Bollinger standard deviations
        kc_window [default=20, min=5, max=100]: Keltner window
        kc_atr_mult [default=1.5, min=0.5]: Keltner ATR multiplier
        mom_window [default=12, min=5, max=50]: Momentum window

    Outputs:
        fired [boolean, 0..1]:
            True if squeeze_depth > 0

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        bb_window (int): Bollinger window. Range: 5-100. Default: 20.
        bb_std (float): Bollinger standard deviations. Range: 0.5-5.0. Default: 2.0.
        kc_window (int): Keltner window. Range: 5-100. Default: 20.
        kc_atr_mult (float): Keltner ATR multiplier. Range: 0.5-5.0. Default: 1.5.
        mom_window (int): Momentum window. Range: 5-50. Default: 12.

    Returns:
        bool: True if squeeze_depth > 0.
    """
    out = _squeeze(df, bb_window, bb_std, kc_window, kc_atr_mult, mom_window, need=1)
    if out is None or pd.isna(out['squeeze_depth'].iloc[-1]):
        return False
    return bool(out['squeeze_depth'].iloc[-1] > 0)


def _squeeze_fired(df, bb_window, bb_std, kc_window, kc_atr_mult, mom_window, momentum_positive):
    out = _squeeze(df, bb_window, bb_std, kc_window, kc_atr_mult, mom_window, need=2)
    if out is None:
        return False
    d, mom = out['squeeze_depth'], out['momentum'].iloc[-1]
    if len(d) < 2 or pd.isna(d.iloc[-1]) or pd.isna(d.iloc[-2]) or pd.isna(mom):
        return False
    released = bool(d.iloc[-2] > 0 and d.iloc[-1] <= 0)
    return released and bool((mom > 0) == momentum_positive)


@RuleRegistry.register("ttm_squeeze_fired_bullish")
def ttm_squeeze_fired_bullish(df: pd.DataFrame, bb_window: int = 20, bb_std: float = 2.0,
                              kc_window: int = 20, kc_atr_mult: float = 1.5,
                              mom_window: int = 12) -> bool:
    """Signal: ttm_squeeze_fired_bullish

    Detect a squeeze releasing with positive momentum. The release is `squeeze_depth` crossing down
    through zero -- the Bollinger bands leaving the Keltner channel. Direction comes from Carter's
    momentum on the same bar.

    Friendly-Name: Quiet Market Breaks Up
    Display-Name: TTM Squeeze Fired Bullish
    Short-Description: A calm, tight market just released with an upward move.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze
    Warmup: max(bb_window, kc_window, mom_window) + 1

    Formula:
        squeeze_depth[t-1] > 0 and squeeze_depth[t] <= 0 and momentum[t] > 0

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        bb_window [default=20, min=5, max=100]: Bollinger window
        bb_std [default=2.0, min=0.5]: Bollinger standard deviations
        kc_window [default=20, min=5, max=100]: Keltner window
        kc_atr_mult [default=1.5, min=0.5]: Keltner ATR multiplier
        mom_window [default=12, min=5, max=50]: Momentum window

    Outputs:
        fired [boolean, 0..1]:
            True on the bar the squeeze releases with momentum > 0

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        bb_window (int): Bollinger window. Range: 5-100. Default: 20.
        bb_std (float): Bollinger standard deviations. Range: 0.5-5.0. Default: 2.0.
        kc_window (int): Keltner window. Range: 5-100. Default: 20.
        kc_atr_mult (float): Keltner ATR multiplier. Range: 0.5-5.0. Default: 1.5.
        mom_window (int): Momentum window. Range: 5-50. Default: 12.

    Returns:
        bool: True on the bar the squeeze releases with momentum > 0.
    """
    return _squeeze_fired(df, bb_window, bb_std, kc_window, kc_atr_mult, mom_window, True)


@RuleRegistry.register("ttm_squeeze_fired_bearish")
def ttm_squeeze_fired_bearish(df: pd.DataFrame, bb_window: int = 20, bb_std: float = 2.0,
                              kc_window: int = 20, kc_atr_mult: float = 1.5,
                              mom_window: int = 12) -> bool:
    """Signal: ttm_squeeze_fired_bearish

    Detect a squeeze releasing with negative momentum. Mirror of `ttm_squeeze_fired_bullish`.

    Friendly-Name: Quiet Market Breaks Down
    Display-Name: TTM Squeeze Fired Bearish
    Short-Description: A calm, tight market just released with a downward move.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze
    Warmup: max(bb_window, kc_window, mom_window) + 1

    Formula:
        squeeze_depth[t-1] > 0 and squeeze_depth[t] <= 0 and momentum[t] < 0

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        bb_window [default=20, min=5, max=100]: Bollinger window
        bb_std [default=2.0, min=0.5]: Bollinger standard deviations
        kc_window [default=20, min=5, max=100]: Keltner window
        kc_atr_mult [default=1.5, min=0.5]: Keltner ATR multiplier
        mom_window [default=12, min=5, max=50]: Momentum window

    Outputs:
        fired [boolean, 0..1]:
            True on the bar the squeeze releases with momentum < 0

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        bb_window (int): Bollinger window. Range: 5-100. Default: 20.
        bb_std (float): Bollinger standard deviations. Range: 0.5-5.0. Default: 2.0.
        kc_window (int): Keltner window. Range: 5-100. Default: 20.
        kc_atr_mult (float): Keltner ATR multiplier. Range: 0.5-5.0. Default: 1.5.
        mom_window (int): Momentum window. Range: 5-50. Default: 12.

    Returns:
        bool: True on the bar the squeeze releases with momentum < 0.
    """
    return _squeeze_fired(df, bb_window, bb_std, kc_window, kc_atr_mult, mom_window, False)


# =============================================================================
# SuperTrend Signals
# =============================================================================
# SuperTrendBands emits the two ATR bands on every bar and nothing else. The long/short regime,
# the ratchet that pins the trailed band while a regime lasts, and the bar the regime changes are
# all decisions over those two levels, so they are made here.

def _supertrend_regime(df: pd.DataFrame, window: int, multiplier: float):
    """The regime SuperTrend's rule derives from the two bands: +1 long or -1 short on each bar.

    A close above the previous bar's upper band puts the regime long; a close below the previous
    bar's lower band puts it short; otherwise the regime holds and the band on its side only moves
    in its favour -- the lower band never falls while long, the upper band never rises while short
    -- which is what makes the trailed band a stop. The regime is long until the first lower-band
    cross. NaN for the first `window` bars, where the previous bar's band is inside ATR's warmup;
    None when the frame is shorter than window + 1.
    """
    if len(df) < window + 1:
        return None
    bands = SuperTrendBands.compute(
        data={'high': df["high"], 'low': df["low"], 'close': df["close"]},
        params={'window': window, 'multiplier': multiplier},
    )
    upper = bands['upper_band'].to_numpy(dtype=np.float64, copy=True)
    lower = bands['lower_band'].to_numpy(dtype=np.float64, copy=True)
    close = df["close"].to_numpy(dtype=np.float64, copy=False)
    n = len(close)
    regime = np.full(n, np.nan)
    current = 1
    for i in range(1, n):
        if close[i] > upper[i - 1]:
            current = 1
        elif close[i] < lower[i - 1]:
            current = -1
        elif current == 1 and lower[i] < lower[i - 1]:
            lower[i] = lower[i - 1]
        elif current == -1 and upper[i] > upper[i - 1]:
            upper[i] = upper[i - 1]
        regime[i] = current
    regime[:window] = np.nan
    return pd.Series(regime, index=df.index, name='supertrend_regime')


def _supertrend_flip(df: pd.DataFrame, window: int, multiplier: float, to: int) -> bool:
    regime = _supertrend_regime(df, window, multiplier)
    if regime is None or len(regime) < 2:
        return False
    prev, curr = regime.iloc[-2], regime.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    return bool(prev == -to and curr == to)


@RuleRegistry.register("supertrend_long")
def supertrend_long(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """Signal: supertrend_long

    Check if SuperTrend's regime is long: close has crossed above the trailed upper band more
    recently than it crossed below the trailed lower band, so the lower band is the active trailing
    stop. The indicator emits both bands every bar; the regime, and the ratchet that holds the
    trailed band in place while it lasts, are decided here.

    Friendly-Name: SuperTrend Says Up
    Display-Name: SuperTrend Long Regime
    Short-Description: Price has stayed above its volatility-scaled trailing stop since the last upside break.

    Reference: https://www.tradingview.com/support/solutions/43000634738-supertrend/
    Warmup: window

    Formula:
        regime[t] == +1, where regime[t] = +1 if close[t] > upper_band[t-1], -1 if close[t] < lower_band[t-1], else regime[t-1] with the trailed band ratcheted in its favour; long until the first lower-band cross

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=10, min=5, max=50]: ATR window
        multiplier [default=3.0, min=0.5, max=10.0]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True if the regime on the current bar is long

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if the regime on the current bar is long.
    """
    regime = _supertrend_regime(df, window, multiplier)
    if regime is None or pd.isna(regime.iloc[-1]):
        return False
    return bool(regime.iloc[-1] == 1)


@RuleRegistry.register("supertrend_short")
def supertrend_short(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """Signal: supertrend_short

    Check if SuperTrend's regime is short: close has crossed below the trailed lower band more
    recently than it crossed above the trailed upper band, so the upper band is the active trailing
    stop. Mirror of `supertrend_long`.

    Friendly-Name: SuperTrend Says Down
    Display-Name: SuperTrend Short Regime
    Short-Description: Price has stayed below its volatility-scaled trailing stop since the last downside break.

    Reference: https://www.tradingview.com/support/solutions/43000634738-supertrend/
    Warmup: window

    Formula:
        regime[t] == -1, where regime[t] = +1 if close[t] > upper_band[t-1], -1 if close[t] < lower_band[t-1], else regime[t-1] with the trailed band ratcheted in its favour

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=10, min=5, max=50]: ATR window
        multiplier [default=3.0, min=0.5, max=10.0]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True if the regime on the current bar is short

    Type: FILTER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True if the regime on the current bar is short.
    """
    regime = _supertrend_regime(df, window, multiplier)
    if regime is None or pd.isna(regime.iloc[-1]):
        return False
    return bool(regime.iloc[-1] == -1)


@RuleRegistry.register("supertrend_flip_up")
def supertrend_flip_up(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """Signal: supertrend_flip_up

    Detect close crossing above the trailed upper band on this bar, ending a short regime. The
    classic SuperTrend long entry.

    Friendly-Name: SuperTrend Flips Up
    Display-Name: SuperTrend Flip to Long
    Short-Description: Price just broke above its trailing stop, turning the SuperTrend regime long.

    Reference: https://www.tradingview.com/support/solutions/43000634738-supertrend/
    Warmup: window + 1

    Formula:
        regime[t-1] == -1 and regime[t] == +1 -- close[t] > upper_band[t-1] after a short regime

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=10, min=5, max=50]: ATR window
        multiplier [default=3.0, min=0.5, max=10.0]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True on the bar the regime turns from short to long

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True on the bar the regime turns from short to long.
    """
    return _supertrend_flip(df, window, multiplier, to=1)


@RuleRegistry.register("supertrend_flip_down")
def supertrend_flip_down(df: pd.DataFrame, window: int = 10, multiplier: float = 3.0) -> bool:
    """Signal: supertrend_flip_down

    Detect close crossing below the trailed lower band on this bar, ending a long regime. The
    classic SuperTrend short entry, and the long exit.

    Friendly-Name: SuperTrend Flips Down
    Display-Name: SuperTrend Flip to Short
    Short-Description: Price just broke below its trailing stop, turning the SuperTrend regime short.

    Reference: https://www.tradingview.com/support/solutions/43000634738-supertrend/
    Warmup: window + 1

    Formula:
        regime[t-1] == +1 and regime[t] == -1 -- close[t] < lower_band[t-1] after a long regime

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=10, min=5, max=50]: ATR window
        multiplier [default=3.0, min=0.5, max=10.0]: ATR multiplier

    Outputs:
        fired [boolean, 0..1]:
            True on the bar the regime turns from long to short

    Type: TRIGGER
    Requires: high, low, close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ATR window. Range: 5-50. Default: 10.
        multiplier (float): ATR multiplier. Range: 0.5-10.0. Default: 3.0.

    Returns:
        bool: True on the bar the regime turns from long to short.
    """
    return _supertrend_flip(df, window, multiplier, to=-1)


__getattr__ = renamed_signals("mangrove_kb.signals.volatility")
