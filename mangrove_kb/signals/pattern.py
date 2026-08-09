"""Candlestick and multi-bar pattern signal functions.

This module contains signal functions based on candlestick pattern indicators:
- Doji (standard, long-legged, dragonfly, gravestone)
- Hammer / Hanging Man / Inverted Hammer / Shooting Star
- Marubozu / Spinning Top
- Engulfing / Harami
- Piercing Line / Dark Cloud Cover
- Tweezer Tops / Bottoms
- Morning Star / Evening Star
- Three White Soldiers / Three Black Crows
- Three Inside Up / Down
- Inside Bar / Outside Bar / Pin Bar
- Two-Bar Reversal / NR7

Each signal is registered with RuleRegistry and returns a boolean.
TRIGGER signals detect the pattern on the current (last) bar.
FILTER signals check for patterns within a recent window.

Detection logic references: see findings/chart-patterns-plan.md Section 5.
"""

import logging
import warnings

import pandas as pd

import numpy as np

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators.pattern_indicators import CandleGeometry, CandleRaw, CandleRelation

logger = logging.getLogger(__name__)








def _hit(series: pd.Series, window: int) -> bool:
    """True if any value in the last `window` entries is > 0.

    Used by the FILTER composites below to short-circuit the compute/check
    loop: each pattern indicator is computed only until the first positive
    hit is found in its last-`window` slice.
    """
    return bool((series.iloc[-window:] > 0).any())


# =============================================================================
# Single-Candle TRIGGER Signals
# =============================================================================


@RuleRegistry.register("doji_trigger")
def doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1) -> bool:
    """
    Check if a doji pattern is detected on the current bar.

    A doji forms when open and close are nearly equal relative to the
    candle's range, signaling indecision. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_threshold (float): Maximum body-to-range ratio. Range: 0.01-0.3. Default: 0.1.

    Returns:
        bool: True if doji detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=body_threshold)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("long_legged_doji_trigger")
def long_legged_doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1,
                              wick_threshold: float = 0.25) -> bool:
    """
    Check if a long-legged doji is detected on the current bar.

    A doji with both upper and lower wicks at least wick_threshold of
    the total range, indicating extreme indecision. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_threshold (float): Maximum body-to-range ratio. Range: 0.01-0.3. Default: 0.1.
        wick_threshold (float): Minimum wick-to-range ratio for both wicks. Range: 0.1-0.5. Default: 0.25.

    Returns:
        bool: True if long-legged doji detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _long_legged_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=body_threshold, wick_threshold=wick_threshold)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("dragonfly_doji_trigger")
def dragonfly_doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1,
                            upper_wick_max: float = 0.1) -> bool:
    """
    Check if a dragonfly doji is detected on the current bar.

    A doji with open/close near the high and a long lower shadow.
    Bullish signal at support. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_threshold (float): Maximum body-to-range ratio. Range: 0.01-0.3. Default: 0.1.
        upper_wick_max (float): Maximum upper wick-to-range ratio. Range: 0.01-0.2. Default: 0.1.

    Returns:
        bool: True if dragonfly doji detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _dragonfly_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=body_threshold, upper_wick_max=upper_wick_max)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("gravestone_doji_trigger")
def gravestone_doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1,
                             lower_wick_max: float = 0.1) -> bool:
    """
    Check if a gravestone doji is detected on the current bar.

    A doji with open/close near the low and a long upper shadow.
    Bearish signal at resistance. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_threshold (float): Maximum body-to-range ratio. Range: 0.01-0.3. Default: 0.1.
        lower_wick_max (float): Maximum lower wick-to-range ratio. Range: 0.01-0.2. Default: 0.1.

    Returns:
        bool: True if gravestone doji detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _gravestone_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=body_threshold, lower_wick_max=lower_wick_max)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("hammer_trigger")
def hammer_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                    upper_wick_max: float = 0.1) -> bool:
    """
    Check if a hammer shape is detected on the current bar.

    Small body at upper end with long lower wick and minimal upper wick.
    Bullish reversal after downtrend. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum lower wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        upper_wick_max (float): Maximum upper wick to body ratio. Range: 0.01-0.5. Default: 0.1.

    Returns:
        bool: True if hammer detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _hammer(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=wick_ratio, upper_wick_max=upper_wick_max)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("shooting_star_trigger")
def shooting_star_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                           lower_wick_max: float = 0.1) -> bool:
    """
    Check if a shooting star shape is detected on the current bar.

    Small body at lower end with long upper wick and minimal lower wick.
    Bearish reversal after uptrend. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns


    DEPRECATED: identical to `inverted_hammer_trigger`. `_shooting_star` calls `_inverted_hammer`
    and renames the output, so the two fire on exactly the same bars -- verified identical across
    499 bars. The distinction is the prior trend, which this implementation does not encode. Kept
    because the name is referenced outside this repository. Use `inverted_hammer_trigger`.

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum upper wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        lower_wick_max (float): Maximum lower wick to body ratio. Range: 0.01-0.5. Default: 0.1.

    Returns:
        bool: True if shooting star detected on current bar, False otherwise.
    """
    warnings.warn(
        "shooting_star_trigger is deprecated: it computes exactly what inverted_hammer_trigger computes. "
        "Use inverted_hammer_trigger.",
        DeprecationWarning, stacklevel=3)
    if len(df) < 1:
        return False
    result = _shooting_star(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=wick_ratio, lower_wick_max=lower_wick_max)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("hanging_man_trigger")
def hanging_man_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                         upper_wick_max: float = 0.1) -> bool:
    """
    Check if a hanging man shape is detected on the current bar.

    Same shape as hammer (small body, long lower wick) but interpreted as a
    bearish reversal when appearing after an uptrend. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-pattern-dictionary


    DEPRECATED: identical to `hammer_trigger`. `_hanging_man` calls `_hammer` and renames the
    output, so the two fire on exactly the same bars -- verified identical across 499 bars. A
    hanging man IS a hammer; what distinguishes them is the prior trend, which this implementation
    does not encode. Kept because the name is referenced outside this repository (MangroveOracle's
    signals_metadata.json, strategy cohort files, experiment outputs). Use `hammer_trigger`.

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum lower wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        upper_wick_max (float): Maximum upper wick to body ratio. Range: 0.01-0.5. Default: 0.1.

    Returns:
        bool: True if hanging man detected on current bar, False otherwise.
    """
    warnings.warn(
        "hanging_man_trigger is deprecated: it computes exactly what hammer_trigger computes. "
        "Use hammer_trigger.",
        DeprecationWarning, stacklevel=3)
    if len(df) < 1:
        return False
    result = _hanging_man(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=wick_ratio, upper_wick_max=upper_wick_max)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("inverted_hammer_trigger")
def inverted_hammer_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                              lower_wick_max: float = 0.1) -> bool:
    """
    Check if an inverted hammer shape is detected on the current bar.

    Same shape as shooting star (small body, long upper wick) but interpreted as a
    bullish reversal when appearing after a downtrend. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum upper wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        lower_wick_max (float): Maximum lower wick to body ratio. Range: 0.01-0.5. Default: 0.1.

    Returns:
        bool: True if inverted hammer detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _inverted_hammer(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=wick_ratio, lower_wick_max=lower_wick_max)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("marubozu_bullish_trigger")
def marubozu_bullish_trigger(df: pd.DataFrame, wick_tolerance: float = 0.05) -> bool:
    """
    Check if a bullish marubozu is detected on the current bar.

    Full-bodied bullish candle with minimal or no wicks.
    Signals strong buying conviction. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_tolerance (float): Maximum wick-to-range ratio. Range: 0.0-0.1. Default: 0.05.

    Returns:
        bool: True if bullish marubozu detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _marubozu(df["Open"], df["High"], df["Low"], df["Close"], wick_tolerance=wick_tolerance)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("marubozu_bearish_trigger")
def marubozu_bearish_trigger(df: pd.DataFrame, wick_tolerance: float = 0.05) -> bool:
    """
    Check if a bearish marubozu is detected on the current bar.

    Full-bodied bearish candle with minimal or no wicks.
    Signals strong selling conviction. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_tolerance (float): Maximum wick-to-range ratio. Range: 0.0-0.1. Default: 0.05.

    Returns:
        bool: True if bearish marubozu detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _marubozu(df["Open"], df["High"], df["Low"], df["Close"], wick_tolerance=wick_tolerance)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("spinning_top_trigger")
def spinning_top_trigger(df: pd.DataFrame, body_max: float = 0.3,
                          wick_min: float = 0.2) -> bool:
    """
    Check if a spinning top is detected on the current bar.

    Small body with significant wicks on both sides, signaling indecision.
    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_max (float): Maximum body-to-range ratio. Range: 0.1-0.5. Default: 0.3.
        wick_min (float): Minimum wick-to-range ratio for both wicks. Range: 0.1-0.5. Default: 0.2.

    Returns:
        bool: True if spinning top detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _spinning_top(df["Open"], df["High"], df["Low"], df["Close"], body_max=body_max, wick_min=wick_min)
    return int(result.iloc[-1]) == 1


# =============================================================================
# Two-Candle TRIGGER Signals
# =============================================================================


@RuleRegistry.register("bullish_engulfing_trigger")
def bullish_engulfing_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bullish engulfing pattern completed on the current bar.

    Current bullish candle's body completely contains the previous bearish
    candle's body. Strong bullish reversal. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bullish engulfing detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _engulfing(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("bearish_engulfing_trigger")
def bearish_engulfing_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bearish engulfing pattern completed on the current bar.

    Current bearish candle's body completely contains the previous bullish
    candle's body. Strong bearish reversal. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bearish engulfing detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _engulfing(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("bullish_harami_trigger")
def bullish_harami_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bullish harami pattern completed on the current bar.

    Current small bullish candle's body is inside the previous large bearish
    candle's body. Potential bullish reversal. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bullish harami detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _harami(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("bearish_harami_trigger")
def bearish_harami_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bearish harami pattern completed on the current bar.

    Current small bearish candle's body is inside the previous large bullish
    candle's body. Potential bearish reversal. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bearish harami detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _harami(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("piercing_line_trigger")
def piercing_line_trigger(df: pd.DataFrame, min_penetration: float = 0.5, require_gap: bool = False) -> bool:
    """
    Check if a piercing line pattern completed on the current bar.

    Bullish reversal: bearish candle followed by bullish candle opening below
    prior low (classic) or prior close (relaxed) and closing above midpoint of
    prior body.

    DEFAULT IS THE RELAXED FORM, because the classic one cannot fire here. It
    requires the bar to open below the prior LOW, and a 24/7 market does not
    gap: measured on 1,294 BTC daily bars, the open is below the prior low
    ZERO times, so require_gap=True yields 0 fires against 63 for the relaxed
    form. Set require_gap=True only for a market that actually closes.
    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        min_penetration (float): Minimum penetration into previous body. Range: 0.3-0.8. Default: 0.5.
        require_gap (bool): If True, requires open below previous low (classic Nison), which cannot occur in a 24/7 market. If False, requires open below previous close. Range: true-false. Default: false.

    Returns:
        bool: True if piercing line detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _piercing_line(df["Open"], df["High"], df["Low"], df["Close"], min_penetration=min_penetration, require_gap=require_gap)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("dark_cloud_cover_trigger")
def dark_cloud_cover_trigger(df: pd.DataFrame, min_penetration: float = 0.5, require_gap: bool = False) -> bool:
    """
    Check if a dark cloud cover pattern completed on the current bar.

    Bearish reversal: bullish candle followed by bearish candle opening above
    prior high (classic) or prior close (relaxed) and closing below midpoint of
    prior body.

    DEFAULT IS THE RELAXED FORM, because the classic one cannot fire here. It
    requires the bar to open above the prior HIGH, and a 24/7 market does not
    gap: measured on 1,294 BTC daily bars, the open is above the prior high
    ZERO times, so require_gap=True yields 0 fires against 67 for the relaxed
    form. Set require_gap=True only for a market that actually closes.
    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        min_penetration (float): Minimum penetration into previous body. Range: 0.3-0.8. Default: 0.5.
        require_gap (bool): If True, requires open above previous high (classic Nison), which cannot occur in a 24/7 market. If False, requires open above previous close. Range: true-false. Default: false.

    Returns:
        bool: True if dark cloud cover detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _dark_cloud_cover(df["Open"], df["High"], df["Low"], df["Close"], min_penetration=min_penetration, require_gap=require_gap)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("tweezer_tops_trigger")
def tweezer_tops_trigger(df: pd.DataFrame, tolerance: float = 0.01) -> bool:
    """
    Check if a tweezer tops pattern completed on the current bar.

    Two consecutive candles with approximately equal highs, first bullish
    and second bearish. Bearish reversal. Reference: https://thepatternsite.com/TweezersTop.html

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        tolerance (float): Maximum high-to-high difference as fraction of average range. Range: 0.001-0.05. Default: 0.01.

    Returns:
        bool: True if tweezer tops detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _tweezer_tops(df["Open"], df["High"], df["Low"], df["Close"], tolerance=tolerance)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("tweezer_bottoms_trigger")
def tweezer_bottoms_trigger(df: pd.DataFrame, tolerance: float = 0.01) -> bool:
    """
    Check if a tweezer bottoms pattern completed on the current bar.

    Two consecutive candles with approximately equal lows, first bearish
    and second bullish. Bullish reversal. Reference: https://thepatternsite.com/TweezersBottom.html

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        tolerance (float): Maximum low-to-low difference as fraction of average range. Range: 0.001-0.05. Default: 0.01.

    Returns:
        bool: True if tweezer bottoms detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _tweezer_bottoms(df["Open"], df["High"], df["Low"], df["Close"], tolerance=tolerance)
    return int(result.iloc[-1]) == 1


# =============================================================================
# Three-Candle TRIGGER Signals
# =============================================================================


@RuleRegistry.register("morning_star_trigger")
def morning_star_trigger(df: pd.DataFrame, body_threshold: float = 0.3) -> bool:
    """
    Check if a morning star pattern completed on the current bar.

    Three-candle bullish reversal: bearish candle, small-bodied star, then
    bullish candle closing above midpoint of first. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_threshold (float): Maximum body-to-range ratio for middle candle. Range: 0.1-0.5. Default: 0.3.

    Returns:
        bool: True if morning star detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = _morning_star(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=body_threshold)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("evening_star_trigger")
def evening_star_trigger(df: pd.DataFrame, body_threshold: float = 0.3) -> bool:
    """
    Check if an evening star pattern completed on the current bar.

    Three-candle bearish reversal: bullish candle, small-bodied star, then
    bearish candle closing below midpoint of first. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        body_threshold (float): Maximum body-to-range ratio for middle candle. Range: 0.1-0.5. Default: 0.3.

    Returns:
        bool: True if evening star detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = _evening_star(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=body_threshold)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("three_white_soldiers_trigger")
def three_white_soldiers_trigger(df: pd.DataFrame, min_body_ratio: float = 0.5) -> bool:
    """
    Check if three white soldiers pattern completed on the current bar.

    Three consecutive bullish candles with higher closes, each opening within
    the previous body. Strong bullish signal. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-pattern-dictionary

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        min_body_ratio (float): Minimum body-to-range ratio per candle. Range: 0.3-0.8. Default: 0.5.

    Returns:
        bool: True if three white soldiers detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = _three_white_soldiers(df["Open"], df["High"], df["Low"], df["Close"], min_body_ratio=min_body_ratio)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("three_black_crows_trigger")
def three_black_crows_trigger(df: pd.DataFrame, min_body_ratio: float = 0.5) -> bool:
    """
    Check if three black crows pattern completed on the current bar.

    Three consecutive bearish candles with lower closes, each opening within
    the previous body. Strong bearish signal. Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-pattern-dictionary

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        min_body_ratio (float): Minimum body-to-range ratio per candle. Range: 0.3-0.8. Default: 0.5.

    Returns:
        bool: True if three black crows detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = _three_black_crows(df["Open"], df["High"], df["Low"], df["Close"], min_body_ratio=min_body_ratio)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("three_inside_up_trigger")
def three_inside_up_trigger(df: pd.DataFrame) -> bool:
    """
    Check if three inside up pattern completed on the current bar.

    Bearish candle, bullish harami, then bullish close above first candle's open.
    Confirmed bullish reversal. Reference: https://thepatternsite.com/ThreeInsideUp.html

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if three inside up detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = _three_inside_up(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("three_inside_down_trigger")
def three_inside_down_trigger(df: pd.DataFrame) -> bool:
    """
    Check if three inside down pattern completed on the current bar.

    Bullish candle, bearish harami, then bearish close below first candle's open.
    Confirmed bearish reversal. Reference: https://thepatternsite.com/ThreeInsideDown.html

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if three inside down detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = _three_inside_down(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == -1


# =============================================================================
# Multi-Bar TRIGGER Signals
# =============================================================================


@RuleRegistry.register("inside_bar_trigger")
def inside_bar_trigger(df: pd.DataFrame) -> bool:
    """
    Check if an inside bar is detected on the current bar.

    Current bar's range is completely contained within the previous bar's range.
    Signals consolidation and potential breakout. Reference: https://thepatternsite.com/InsideDays.html

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if inside bar detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _inside_bar(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("outside_bar_trigger")
def outside_bar_trigger(df: pd.DataFrame) -> bool:
    """
    Check if an outside bar is detected on the current bar.

    Current bar's range completely engulfs the previous bar's range.
    Signals increased volatility. Reference: https://thepatternsite.com/OutsideDays.html

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if outside bar detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _outside_bar(df["Open"], df["High"], df["Low"], df["Close"])
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("bullish_pin_bar_trigger")
def bullish_pin_bar_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                             body_position: float = 0.33) -> bool:
    """
    Check if a bullish pin bar is detected on the current bar.

    Long lower wick with body in the upper portion of the range.
    Bullish reversal at support. Reference: https://www.tradingsetupsreview.com/pinocchio-bar-trade-setup-pin-bar/

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum dominant wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        body_position (float): Maximum body distance from end as fraction of range. Range: 0.1-0.5. Default: 0.33.

    Returns:
        bool: True if bullish pin bar detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _pin_bar(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=wick_ratio, body_position=body_position)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("bearish_pin_bar_trigger")
def bearish_pin_bar_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                              body_position: float = 0.33) -> bool:
    """
    Check if a bearish pin bar is detected on the current bar.

    Long upper wick with body in the lower portion of the range.
    Bearish reversal at resistance. Reference: https://www.tradingsetupsreview.com/pinocchio-bar-trade-setup-pin-bar/

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum dominant wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        body_position (float): Maximum body distance from end as fraction of range. Range: 0.1-0.5. Default: 0.33.

    Returns:
        bool: True if bearish pin bar detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _pin_bar(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=wick_ratio, body_position=body_position)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("two_bar_reversal_bullish_trigger")
def two_bar_reversal_bullish_trigger(df: pd.DataFrame, close_proximity: float = 0.25) -> bool:
    """
    Check if a bullish two-bar reversal completed on the current bar.

    Bearish bar followed by bullish bar that takes out the low then
    closes above the prior open. The close_proximity parameter controls how
    close the close must be to the high/low extreme. Reference: https://www.tradingsetupsreview.com/two-bar-reversal-pattern-trading-guide/

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        close_proximity (float): How close the close must be to the extreme, as a fraction of range. Lower is stricter. Range: 0.1-0.5. Default: 0.25.

    Returns:
        bool: True if bullish two-bar reversal detected, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _two_bar_reversal(df["Open"], df["High"], df["Low"], df["Close"], close_proximity=close_proximity)
    return int(result.iloc[-1]) == 1


@RuleRegistry.register("two_bar_reversal_bearish_trigger")
def two_bar_reversal_bearish_trigger(df: pd.DataFrame, close_proximity: float = 0.25) -> bool:
    """
    Check if a bearish two-bar reversal completed on the current bar.

    Bullish bar followed by bearish bar that takes out the high then
    closes below the prior open. The close_proximity parameter controls how
    close the close must be to the high/low extreme. Reference: https://www.tradingsetupsreview.com/two-bar-reversal-pattern-trading-guide/

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        close_proximity (float): How close the close must be to the extreme, as a fraction of range. Lower is stricter. Range: 0.1-0.5. Default: 0.25.

    Returns:
        bool: True if bearish two-bar reversal detected, False otherwise.
    """
    if len(df) < 2:
        return False
    result = _two_bar_reversal(df["Open"], df["High"], df["Low"], df["Close"], close_proximity=close_proximity)
    return int(result.iloc[-1]) == -1


@RuleRegistry.register("nr7_trigger")
def nr7_trigger(df: pd.DataFrame, window: int = 7) -> bool:
    """
    Check if a narrow range day is detected on the current bar.

    Current bar has the smallest range within the window period.
    Signals volatility compression and imminent breakout.
    Default window=7 for NR7; use 4 for NR4. Reference: https://thepatternsite.com/nr7.html

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of bars to compare range against. Range: 4-20. Default: 7.

    Returns:
        bool: True if narrow range detected on current bar, False otherwise.
    """
    if len(df) < window:
        return False
    result = _narrow_range(df["Open"], df["High"], df["Low"], df["Close"], window=window)
    return int(result.iloc[-1]) == 1


# =============================================================================
# FILTER Signals (Pattern Within Recent Window)
# =============================================================================


@RuleRegistry.register("bullish_pattern_recent")
def bullish_pattern_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if any bullish candlestick pattern was detected within recent window.

    Scans for hammer, inverted hammer, bullish engulfing, bullish harami,
    piercing line, morning star, dragonfly doji, three white soldiers,
    three inside up, tweezer bottoms, and bullish pin bar within the recent window.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if any bullish pattern found in recent window, False otherwise.
    """
    if len(df) < 2:
        return False
    w = window

    if _hit(_hammer(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, upper_wick_max=0.1), w):
        return True
    if _hit(_inverted_hammer(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, lower_wick_max=0.1), w):
        return True
    if _hit(_engulfing(df["Open"], df["High"], df["Low"], df["Close"]).clip(lower=0), w):
        return True
    if _hit(_harami(df["Open"], df["High"], df["Low"], df["Close"]).clip(lower=0), w):
        return True
    if _hit(_piercing_line(df["Open"], df["High"], df["Low"], df["Close"], min_penetration=0.5, require_gap=False), w):
        return True
    if _hit(_dragonfly_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.1, upper_wick_max=0.1), w):
        return True
    if _hit(_tweezer_bottoms(df["Open"], df["High"], df["Low"], df["Close"], tolerance=0.01), w):
        return True
    if _hit(_pin_bar(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, body_position=0.33).clip(lower=0), w):
        return True

    if len(df) >= 3:
        if _hit(_morning_star(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.3), w):
            return True
        if _hit(_three_white_soldiers(df["Open"], df["High"], df["Low"], df["Close"], min_body_ratio=0.5), w):
            return True
        if _hit(_three_inside_up(df["Open"], df["High"], df["Low"], df["Close"]), w):
            return True

    return False


@RuleRegistry.register("bearish_pattern_recent")
def bearish_pattern_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if any bearish candlestick pattern was detected within recent window.

    Scans for hanging man, shooting star, bearish engulfing, bearish harami,
    dark cloud cover, evening star, gravestone doji, three black crows,
    three inside down, tweezer tops, and bearish pin bar within the recent window.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if any bearish pattern found in recent window, False otherwise.
    """
    if len(df) < 2:
        return False
    w = window

    if _hit(_hanging_man(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, upper_wick_max=0.1), w):
        return True
    if _hit(_shooting_star(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, lower_wick_max=0.1), w):
        return True
    if _hit(_engulfing(df["Open"], df["High"], df["Low"], df["Close"]).clip(upper=0).abs(), w):
        return True
    if _hit(_harami(df["Open"], df["High"], df["Low"], df["Close"]).clip(upper=0).abs(), w):
        return True
    if _hit(_dark_cloud_cover(df["Open"], df["High"], df["Low"], df["Close"], min_penetration=0.5, require_gap=False).abs(), w):
        return True
    if _hit(_gravestone_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.1, lower_wick_max=0.1), w):
        return True
    if _hit(_tweezer_tops(df["Open"], df["High"], df["Low"], df["Close"], tolerance=0.01).abs(), w):
        return True
    if _hit(_pin_bar(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, body_position=0.33).clip(upper=0).abs(), w):
        return True

    if len(df) >= 3:
        if _hit(_evening_star(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.3).abs(), w):
            return True
        if _hit(_three_black_crows(df["Open"], df["High"], df["Low"], df["Close"], min_body_ratio=0.5).abs(), w):
            return True
        if _hit(_three_inside_down(df["Open"], df["High"], df["Low"], df["Close"]).abs(), w):
            return True

    return False


@RuleRegistry.register("reversal_pattern_bullish")
def reversal_pattern_bullish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bullish reversal pattern was detected within recent window.

    Scans for hammer, inverted hammer, bullish engulfing, morning star,
    piercing line, and dragonfly doji -- the classic bullish reversal patterns.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bullish-reversal-patterns

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if bullish reversal pattern found in recent window, False otherwise.
    """
    if len(df) < 2:
        return False
    w = window

    if _hit(_hammer(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, upper_wick_max=0.1), w):
        return True
    if _hit(_inverted_hammer(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, lower_wick_max=0.1), w):
        return True
    if _hit(_engulfing(df["Open"], df["High"], df["Low"], df["Close"]).clip(lower=0), w):
        return True
    if _hit(_piercing_line(df["Open"], df["High"], df["Low"], df["Close"], min_penetration=0.5, require_gap=False), w):
        return True
    if _hit(_dragonfly_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.1, upper_wick_max=0.1), w):
        return True

    if len(df) >= 3:
        if _hit(_morning_star(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.3), w):
            return True

    return False


@RuleRegistry.register("reversal_pattern_bearish")
def reversal_pattern_bearish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bearish reversal pattern was detected within recent window.

    Scans for hanging man, shooting star, bearish engulfing, evening star,
    dark cloud cover, and gravestone doji -- the classic bearish reversal patterns.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-bearish-reversal-patterns

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if bearish reversal pattern found in recent window, False otherwise.
    """
    if len(df) < 2:
        return False
    w = window

    if _hit(_hanging_man(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, upper_wick_max=0.1), w):
        return True
    if _hit(_shooting_star(df["Open"], df["High"], df["Low"], df["Close"], wick_ratio=2.0, lower_wick_max=0.1), w):
        return True
    if _hit(_engulfing(df["Open"], df["High"], df["Low"], df["Close"]).clip(upper=0).abs(), w):
        return True
    if _hit(_dark_cloud_cover(df["Open"], df["High"], df["Low"], df["Close"], min_penetration=0.5, require_gap=False).abs(), w):
        return True
    if _hit(_gravestone_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.1, lower_wick_max=0.1), w):
        return True

    if len(df) >= 3:
        if _hit(_evening_star(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.3).abs(), w):
            return True

    return False


@RuleRegistry.register("continuation_pattern_bullish")
def continuation_pattern_bullish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bullish continuation pattern was detected within recent window.

    Scans for three white soldiers and three inside up.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-pattern-dictionary

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if bullish continuation pattern found in recent window, False otherwise.
    """
    if len(df) < 3:
        return False
    w = window

    if _hit(_three_white_soldiers(df["Open"], df["High"], df["Low"], df["Close"], min_body_ratio=0.5), w):
        return True
    if _hit(_three_inside_up(df["Open"], df["High"], df["Low"], df["Close"]), w):
        return True
    return False


@RuleRegistry.register("continuation_pattern_bearish")
def continuation_pattern_bearish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bearish continuation pattern was detected within recent window.

    Scans for three black crows and three inside down.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/candlestick-pattern-dictionary

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if bearish continuation pattern found in recent window, False otherwise.
    """
    if len(df) < 3:
        return False
    w = window

    if _hit(_three_black_crows(df["Open"], df["High"], df["Low"], df["Close"], min_body_ratio=0.5).abs(), w):
        return True
    if _hit(_three_inside_down(df["Open"], df["High"], df["Low"], df["Close"]).abs(), w):
        return True
    return False


@RuleRegistry.register("indecision_pattern_recent")
def indecision_pattern_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if an indecision pattern was detected within recent window.

    Scans for doji, spinning top, inside bar, and NR7.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if indecision pattern found in recent window, False otherwise.
    """
    if len(df) < 2:
        return False
    w = window

    if _hit(_doji(df["Open"], df["High"], df["Low"], df["Close"], body_threshold=0.1), w):
        return True
    if _hit(_spinning_top(df["Open"], df["High"], df["Low"], df["Close"], body_max=0.3, wick_min=0.2), w):
        return True
    if _hit(_inside_bar(df["Open"], df["High"], df["Low"], df["Close"]), w):
        return True
    if len(df) >= 7:
        if _hit(_narrow_range(df["Open"], df["High"], df["Low"], df["Close"], window=7), w):
            return True
    return False


@RuleRegistry.register("strong_body_recent")
def strong_body_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a marubozu (strong body) was detected within recent window.

    Scans for both bullish and bearish marubozu patterns.

    Reference: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Number of recent bars to check. Range: 1-20. Default: 5.

    Returns:
        bool: True if marubozu found in recent window, False otherwise.
    """
    if len(df) < 1:
        return False
    result = _marubozu(df["Open"], df["High"], df["Low"], df["Close"], wick_tolerance=0.05)
    recent = result.iloc[-window:]
    return (recent != 0).any()


# ===========================================================================
# Pattern detection -- per-bar series, PRIVATE to this module
# ===========================================================================
#
# Each returns a pd.Series aligned to the input index, not a decision. The
# registered signals above reduce that series to a bool over a window.
#
# These were IndicatorInterface subclasses in indicators/pattern_indicators.py,
# which put boolean-valued outputs in the indicator layer. An indicator
# measures; these decide. The numeric substrate -- body, range, wicks, and the
# relationship of one bar to the previous -- stays there as CandleGeometry and
# CandleRelation.


def _dark_cloud_cover(open_, high, low, close, min_penetration, require_gap) -> pd.Series:
    """DarkCloudCover detection. Per-bar series, not a decision."""
    _r = CandleRaw.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = _r["open"], _r["high"], _r["low"], _r["close"]
    prev_o, prev_c, prev_h = o.shift(1), c.shift(1), h.shift(1)
    pen = min_penetration

    prev_bull = prev_c > prev_o
    curr_bear = c < o

    if require_gap:
        gaps_above = o > prev_h  # Classic Nison: open above previous high
    else:
        gaps_above = o > prev_c  # Relaxed: open above previous close (for 24/7 markets)
    penetrates = c < prev_c - (prev_c - prev_o) * pen

    detected = prev_bull & curr_bear & gaps_above & penetrates
    result = pd.Series(0, index=o.index, name="dark_cloud_cover")
    result[detected] = -1
    return result


def _doji(open_, high, low, close, body_threshold) -> pd.Series:
    """Doji detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    rng = _g["range"]
    threshold = body_threshold

    detected = ((rng > 0) & (body <= rng * threshold)).astype(int)
    return pd.Series(detected, index=o.index, name="doji")


def _dragonfly_doji(open_, high, low, close, body_threshold, upper_wick_max) -> pd.Series:
    """DragonflyDoji detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    rng = _g["range"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]

    is_doji = (rng > 0) & (body <= rng * body_threshold)
    small_upper = uw <= rng * upper_wick_max
    long_lower = lw > body

    detected = (is_doji & small_upper & long_lower).astype(int)
    return pd.Series(detected, index=o.index, name="dragonfly_doji")


def _engulfing(open_, high, low, close) -> pd.Series:
    """Engulfing detection. Per-bar series, not a decision."""
    _r = CandleRelation.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, c = open_, close
    prev_o, prev_c = o.shift(1), c.shift(1)

    prev_bear = prev_c < prev_o
    prev_bull = prev_c > prev_o
    curr_bull = c > o
    curr_bear = c < o

    engulfs = (_r["body_low_delta"] < 0) & (_r["body_high_delta"] > 0)
    bullish = prev_bear & curr_bull & engulfs
    bearish = prev_bull & curr_bear & engulfs

    result = pd.Series(0, index=o.index, name="engulfing")
    result[bullish] = 1
    result[bearish] = -1
    return result


def _evening_star(open_, high, low, close, body_threshold) -> pd.Series:
    """EveningStar detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    rng = _g["range"]

    o2, c2 = o.shift(2), c.shift(2)
    o1, c1 = o.shift(1), c.shift(1)
    rng1 = rng.shift(1)

    first_bullish = c2 > o2
    star_small = _g["body"].shift(1) <= rng1 * body_threshold
    third_bearish = c < o
    midpoint = (o2 + c2) / 2
    closes_below_mid = c < midpoint

    detected = (first_bullish & star_small & third_bearish & closes_below_mid)
    result = pd.Series(0, index=o.index, name="evening_star")
    result[detected] = -1
    return result


def _gravestone_doji(open_, high, low, close, body_threshold, lower_wick_max) -> pd.Series:
    """GravestoneDoji detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    rng = _g["range"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]

    is_doji = (rng > 0) & (body <= rng * body_threshold)
    small_lower = lw <= rng * lower_wick_max
    long_upper = uw > body

    detected = (is_doji & small_lower & long_upper).astype(int)
    return pd.Series(detected, index=o.index, name="gravestone_doji")


def _hammer(open_, high, low, close, wick_ratio, upper_wick_max) -> pd.Series:
    """Hammer detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]

    has_body = body > 0
    long_lower = lw >= body * wick_ratio
    small_upper = uw <= body * upper_wick_max

    detected = (has_body & long_lower & small_upper).astype(int)
    return pd.Series(detected, index=o.index, name="hammer")


def _hanging_man(open_, high, low, close, wick_ratio, upper_wick_max) -> pd.Series:
    """HangingMan detection. Per-bar series, not a decision."""
    # Identical computation to _hammer: what distinguishes a hanging man from a
    # hammer is the PRIOR TREND, which this bar-local geometry does not encode.
    return pd.Series(
        _hammer(open_, high, low, close, wick_ratio, upper_wick_max).values,
        index=open_.index, name="hanging_man")


def _harami(open_, high, low, close) -> pd.Series:
    """Harami detection. Per-bar series, not a decision."""
    _r = CandleRelation.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, c = open_, close
    prev_o, prev_c = o.shift(1), c.shift(1)

    prev_bear = prev_c < prev_o
    prev_bull = prev_c > prev_o
    curr_bull = c > o
    curr_bear = c < o

    contained = (_r["body_low_delta"] > 0) & (_r["body_high_delta"] < 0)
    bullish = prev_bear & curr_bull & contained
    bearish = prev_bull & curr_bear & contained

    result = pd.Series(0, index=o.index, name="harami")
    result[bullish] = 1
    result[bearish] = -1
    return result


def _inside_bar(open_, high, low, close) -> pd.Series:
    """InsideBar detection. Per-bar series, not a decision."""
    _r = CandleRelation.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    # nested inside the previous bar: upper edge below it, lower edge above it
    detected = ((_r["range_high_delta"] < 0) & (_r["range_low_delta"] > 0)).astype(int)
    return pd.Series(detected, index=high.index, name="inside_bar")


def _inverted_hammer(open_, high, low, close, wick_ratio, lower_wick_max) -> pd.Series:
    """InvertedHammer detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]

    has_body = body > 0
    long_upper = uw >= body * wick_ratio
    small_lower = lw <= body * lower_wick_max

    detected = (has_body & long_upper & small_lower).astype(int)
    return pd.Series(detected, index=o.index, name="inverted_hammer")


def _long_legged_doji(open_, high, low, close, body_threshold, wick_threshold) -> pd.Series:
    """LongLeggedDoji detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    rng = _g["range"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]

    is_doji = (rng > 0) & (body <= rng * body_threshold)
    long_wicks = (uw >= rng * wick_threshold) & (lw >= rng * wick_threshold)

    detected = (is_doji & long_wicks).astype(int)
    return pd.Series(detected, index=o.index, name="long_legged_doji")


def _marubozu(open_, high, low, close, wick_tolerance) -> pd.Series:
    """Marubozu detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    rng = _g["range"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]
    tol = wick_tolerance

    small_wicks = (rng > 0) & (uw <= rng * tol) & (lw <= rng * tol)
    bull = (_g["signed_body"] > 0)
    bear = (_g["signed_body"] < 0)

    result = pd.Series(0, index=o.index, name="marubozu")
    result[small_wicks & bull] = 1
    result[small_wicks & bear] = -1
    return result


def _morning_star(open_, high, low, close, body_threshold) -> pd.Series:
    """MorningStar detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    rng = _g["range"]

    o2, c2 = o.shift(2), c.shift(2)
    o1, c1 = o.shift(1), c.shift(1)
    rng1 = rng.shift(1)

    first_bearish = c2 < o2
    star_small = _g["body"].shift(1) <= rng1 * body_threshold
    third_bullish = c > o
    midpoint = (o2 + c2) / 2
    closes_above_mid = c > midpoint

    detected = (first_bearish & star_small & third_bullish & closes_above_mid).astype(int)
    return pd.Series(detected, index=o.index, name="morning_star")


def _narrow_range(open_, high, low, close, window) -> pd.Series:
    """NarrowRange detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    h, l = high, low
    rng = _g["range"]

    # Current range must be strictly less than all previous N ranges
    rolling_min = rng.shift(1).rolling(window=window - 1, min_periods=window - 1).min()
    detected = (rng < rolling_min).astype(int)
    # NaN rows get 0
    detected = detected.fillna(0).astype(int)
    return pd.Series(detected, index=h.index, name="narrow_range")


def _outside_bar(open_, high, low, close) -> pd.Series:
    """OutsideBar detection. Per-bar series, not a decision."""
    _r = CandleRelation.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    # contains the previous bar: upper edge above it, lower edge below it
    detected = ((_r["range_high_delta"] > 0) & (_r["range_low_delta"] < 0)).astype(int)
    return pd.Series(detected, index=high.index, name="outside_bar")


def _piercing_line(open_, high, low, close, min_penetration, require_gap) -> pd.Series:
    """PiercingLine detection. Per-bar series, not a decision."""
    _r = CandleRaw.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = _r["open"], _r["high"], _r["low"], _r["close"]
    prev_o, prev_c, prev_l = o.shift(1), c.shift(1), l.shift(1)
    pen = min_penetration

    prev_bear = prev_c < prev_o
    curr_bull = c > o

    if require_gap:
        gaps_below = o < prev_l  # Classic Nison: open below previous low
    else:
        gaps_below = o < prev_c  # Relaxed: open below previous close (for 24/7 markets)
    penetrates = c > prev_c + (prev_o - prev_c) * pen

    detected = (prev_bear & curr_bull & gaps_below & penetrates).astype(int)
    return pd.Series(detected, index=o.index, name="piercing_line")


def _pin_bar(open_, high, low, close, wick_ratio, body_position) -> pd.Series:
    """PinBar detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    rng = _g["range"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]
    wr = wick_ratio
    bp = body_position

    has_body = body > 0
    body_bottom = pd.concat([o, c], axis=1).min(axis=1)
    body_top = pd.concat([o, c], axis=1).max(axis=1)

    bullish = has_body & (lw >= body * wr) & (body_bottom > l + rng * (1 - bp))
    bearish = has_body & (uw >= body * wr) & (body_top < h - rng * (1 - bp))

    result = pd.Series(0, index=o.index, name="pin_bar")
    result[bullish] = 1
    result[bearish] = -1
    return result


def _shooting_star(open_, high, low, close, wick_ratio, lower_wick_max) -> pd.Series:
    """ShootingStar detection. Per-bar series, not a decision."""
    # Identical computation to _inverted_hammer, distinguished only by prior
    # trend, which is not encoded here. See the note on _hanging_man.
    return pd.Series(
        _inverted_hammer(open_, high, low, close, wick_ratio, lower_wick_max).values,
        index=open_.index, name="shooting_star")


def _spinning_top(open_, high, low, close, body_max, wick_min) -> pd.Series:
    """SpinningTop detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    body = _g["body"]
    rng = _g["range"]
    uw = _g["upper_wick"]
    lw = _g["lower_wick"]

    small_body = (rng > 0) & (body <= rng * body_max)
    both_wicks = (uw >= rng * wick_min) & (lw >= rng * wick_min)

    detected = (small_body & both_wicks).astype(int)
    return pd.Series(detected, index=o.index, name="spinning_top")


def _three_black_crows(open_, high, low, close, min_body_ratio) -> pd.Series:
    """ThreeBlackCrows detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    rng = _g["range"]
    body = _g["body"]
    min_ratio = min_body_ratio

    o2, c2, rng2, body2 = o.shift(2), c.shift(2), rng.shift(2), body.shift(2)
    o1, c1, rng1, body1 = o.shift(1), c.shift(1), rng.shift(1), body.shift(1)

    all_bearish = (c2 < o2) & (c1 < o1) & (c < o)
    lower_closes = (c1 < c2) & (c < c1)
    opens_within = (o1 <= o2) & (o1 >= c2) & (o <= o1) & (o >= c1)
    strong_bodies = (
        (body2 >= rng2 * min_ratio)
        & (body1 >= rng1 * min_ratio)
        & (body >= rng * min_ratio)
    )

    detected = (all_bearish & lower_closes & opens_within & strong_bodies)
    result = pd.Series(0, index=o.index, name="three_black_crows")
    result[detected] = -1
    return result


def _three_inside_down(open_, high, low, close) -> pd.Series:
    """ThreeInsideDown detection. Per-bar series, not a decision.

    Takes the full bar rather than just open and close, so that its evidence comes
    from CandleRaw like every other detector here. The pattern reads only the two
    body edges; high and low are the rest of the bar it is a pattern in.
    """
    _r = CandleRaw.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, c = _r["open"], _r["close"]
    o2, c2 = o.shift(2), c.shift(2)
    o1, c1 = o.shift(1), c.shift(1)

    first_bullish = c2 > o2
    harami = (c1 < o1) & (o1 < c2) & (c1 > o2)
    third_bearish = (c < o) & (c < o2)

    detected = (first_bullish & harami & third_bearish)
    result = pd.Series(0, index=o.index, name="three_inside_down")
    result[detected] = -1
    return result


def _three_inside_up(open_, high, low, close) -> pd.Series:
    """ThreeInsideUp detection. Per-bar series, not a decision.

    Takes the full bar for the same reason as `_three_inside_down`: the evidence
    comes from CandleRaw, and the pattern reads the two body edges out of it.
    """
    _r = CandleRaw.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, c = _r["open"], _r["close"]
    o2, c2 = o.shift(2), c.shift(2)
    o1, c1 = o.shift(1), c.shift(1)

    first_bearish = c2 < o2
    harami = (c1 > o1) & (o1 > c2) & (c1 < o2)
    third_bullish = (c > o) & (c > o2)

    detected = (first_bearish & harami & third_bullish).astype(int)
    return pd.Series(detected, index=o.index, name="three_inside_up")


def _three_white_soldiers(open_, high, low, close, min_body_ratio) -> pd.Series:
    """ThreeWhiteSoldiers detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    rng = _g["range"]
    body = _g["body"]
    min_ratio = min_body_ratio

    o2, c2, rng2, body2 = o.shift(2), c.shift(2), rng.shift(2), body.shift(2)
    o1, c1, rng1, body1 = o.shift(1), c.shift(1), rng.shift(1), body.shift(1)

    all_bullish = (c2 > o2) & (c1 > o1) & (c > o)
    higher_closes = (c1 > c2) & (c > c1)
    opens_within = (o1 >= o2) & (o1 <= c2) & (o >= o1) & (o <= c1)
    strong_bodies = (
        (body2 >= rng2 * min_ratio)
        & (body1 >= rng1 * min_ratio)
        & (body >= rng * min_ratio)
    )

    detected = (all_bullish & higher_closes & opens_within & strong_bodies).astype(int)
    return pd.Series(detected, index=o.index, name="three_white_soldiers")


def _tweezer_bottoms(open_, high, low, close, tolerance, avg_window=20) -> pd.Series:
    """TweezerBottoms detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    prev_l = l.shift(1)
    prev_o, prev_c = o.shift(1), c.shift(1)
    rng = _g["range"]

    avg_rng = rng.rolling(window=avg_window, min_periods=1).mean()
    tol = tolerance

    matching_lows = (l - prev_l).abs() <= avg_rng * tol
    prev_bear = prev_c < prev_o
    curr_bull = c > o

    detected = (matching_lows & prev_bear & curr_bull).astype(int)
    return pd.Series(detected, index=o.index, name="tweezer_bottoms")


def _tweezer_tops(open_, high, low, close, tolerance, avg_window=20) -> pd.Series:
    """TweezerTops detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    prev_h = h.shift(1)
    prev_o, prev_c = o.shift(1), c.shift(1)
    rng = _g["range"]

    avg_rng = rng.rolling(window=avg_window, min_periods=1).mean()
    tol = tolerance

    matching_highs = (h - prev_h).abs() <= avg_rng * tol
    prev_bull = prev_c > prev_o
    curr_bear = c < o

    detected = (matching_highs & prev_bull & curr_bear)
    result = pd.Series(0, index=o.index, name="tweezer_tops")
    result[detected] = -1
    return result


def _two_bar_reversal(open_, high, low, close, close_proximity) -> pd.Series:
    """TwoBarReversal detection. Per-bar series, not a decision."""
    _g = CandleGeometry.compute(
        {"open": open_, "high": high, "low": low, "close": close}, {})
    o, h, l, c = open_, high, low, close
    rng = _g["range"]
    prev_o, prev_h, prev_l, prev_c = o.shift(1), h.shift(1), l.shift(1), c.shift(1)
    prev_rng = rng.shift(1)

    # Close near high/low: within close_proximity fraction of the extreme

    prev_close_near_low = (prev_c - prev_l) <= prev_rng * close_proximity
    prev_close_near_high = (prev_h - prev_c) <= prev_rng * close_proximity
    close_near_high = (h - c) <= rng * close_proximity
    close_near_low = (c - l) <= rng * close_proximity

    prev_bear = prev_c < prev_o
    prev_bull = prev_c > prev_o
    curr_bull = c > o
    curr_bear = c < o

    bullish = (prev_bear & prev_close_near_low & curr_bull & close_near_high
               & (l <= prev_l) & (c > prev_o))
    bearish = (prev_bull & prev_close_near_high & curr_bear & close_near_low
               & (h >= prev_h) & (c < prev_o))

    result = pd.Series(0, index=o.index, name="two_bar_reversal")
    result[bullish] = 1
    result[bearish] = -1
    return result
