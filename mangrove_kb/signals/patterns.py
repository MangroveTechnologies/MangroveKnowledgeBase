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

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators.pattern_indicators import (
    Doji,
    LongLeggedDoji,
    DragonflyDoji,
    GravestoneDoji,
    Hammer,
    HangingMan,
    InvertedHammer,
    ShootingStar,
    Marubozu,
    SpinningTop,
    Engulfing,
    Harami,
    PiercingLine,
    DarkCloudCover,
    TweezerTops,
    TweezerBottoms,
    MorningStar,
    EveningStar,
    ThreeWhiteSoldiers,
    ThreeBlackCrows,
    ThreeInsideUp,
    ThreeInsideDown,
    InsideBar,
    OutsideBar,
    PinBar,
    TwoBarReversal,
    NarrowRange,
)

logger = logging.getLogger(__name__)


def _ohlc_data(df: pd.DataFrame) -> dict:
    """Extract OHLC data dict from DataFrame."""
    return {
        "open": df["Open"],
        "high": df["High"],
        "low": df["Low"],
        "close": df["Close"],
    }


def _oc_data(df: pd.DataFrame) -> dict:
    """Extract Open/Close data dict from DataFrame."""
    return {"open": df["Open"], "close": df["Close"]}


def _hl_data(df: pd.DataFrame) -> dict:
    """Extract High/Low data dict from DataFrame."""
    return {"high": df["High"], "low": df["Low"]}


# =============================================================================
# Single-Candle TRIGGER Signals
# =============================================================================


@RuleRegistry.register("doji_trigger")
def doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1) -> bool:
    """
    Check if a doji pattern is detected on the current bar.

    A doji forms when open and close are nearly equal relative to the
    candle's range, signaling indecision. References: [NISON], [KB-07], [CM45T3R].

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
    result = Doji.compute(data=_ohlc_data(df), params={"body_threshold": body_threshold})
    return int(result["doji"].iloc[-1]) == 1


@RuleRegistry.register("long_legged_doji_trigger")
def long_legged_doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1,
                              wick_threshold: float = 0.25) -> bool:
    """
    Check if a long-legged doji is detected on the current bar.

    A doji with both upper and lower wicks at least wick_threshold of
    the total range, indicating extreme indecision. References: [NISON], [STOCKCHARTS].

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
    result = LongLeggedDoji.compute(
        data=_ohlc_data(df),
        params={"body_threshold": body_threshold, "wick_threshold": wick_threshold},
    )
    return int(result["long_legged_doji"].iloc[-1]) == 1


@RuleRegistry.register("dragonfly_doji_trigger")
def dragonfly_doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1,
                            upper_wick_max: float = 0.1) -> bool:
    """
    Check if a dragonfly doji is detected on the current bar.

    A doji with open/close near the high and a long lower shadow.
    Bullish signal at support. References: [NISON], [STOCKCHARTS], [TRENDSPIDER].

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
    result = DragonflyDoji.compute(
        data=_ohlc_data(df),
        params={"body_threshold": body_threshold, "upper_wick_max": upper_wick_max},
    )
    return int(result["dragonfly_doji"].iloc[-1]) == 1


@RuleRegistry.register("gravestone_doji_trigger")
def gravestone_doji_trigger(df: pd.DataFrame, body_threshold: float = 0.1,
                             lower_wick_max: float = 0.1) -> bool:
    """
    Check if a gravestone doji is detected on the current bar.

    A doji with open/close near the low and a long upper shadow.
    Bearish signal at resistance. References: [NISON], [STOCKCHARTS], [TRENDSPIDER].

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
    result = GravestoneDoji.compute(
        data=_ohlc_data(df),
        params={"body_threshold": body_threshold, "lower_wick_max": lower_wick_max},
    )
    return int(result["gravestone_doji"].iloc[-1]) == 1


@RuleRegistry.register("hammer_trigger")
def hammer_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                    upper_wick_max: float = 0.1) -> bool:
    """
    Check if a hammer shape is detected on the current bar.

    Small body at upper end with long lower wick and minimal upper wick.
    Bullish reversal after downtrend. References: [NISON], [KB-07], [CM45T3R].

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
    result = Hammer.compute(
        data=_ohlc_data(df),
        params={"wick_ratio": wick_ratio, "upper_wick_max": upper_wick_max},
    )
    return int(result["hammer"].iloc[-1]) == 1


@RuleRegistry.register("shooting_star_trigger")
def shooting_star_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                           lower_wick_max: float = 0.1) -> bool:
    """
    Check if a shooting star shape is detected on the current bar.

    Small body at lower end with long upper wick and minimal lower wick.
    Bearish reversal after uptrend. References: [NISON], [STOCKCHARTS].

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum upper wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        lower_wick_max (float): Maximum lower wick to body ratio. Range: 0.01-0.5. Default: 0.1.

    Returns:
        bool: True if shooting star detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = ShootingStar.compute(
        data=_ohlc_data(df),
        params={"wick_ratio": wick_ratio, "lower_wick_max": lower_wick_max},
    )
    return int(result["shooting_star"].iloc[-1]) == 1


@RuleRegistry.register("hanging_man_trigger")
def hanging_man_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                         upper_wick_max: float = 0.1) -> bool:
    """
    Check if a hanging man shape is detected on the current bar.

    Same shape as hammer (small body, long lower wick) but interpreted as a
    bearish reversal when appearing after an uptrend. References: [NISON], [STOCKCHARTS].

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        wick_ratio (float): Minimum lower wick to body ratio. Range: 1.5-5.0. Default: 2.0.
        upper_wick_max (float): Maximum upper wick to body ratio. Range: 0.01-0.5. Default: 0.1.

    Returns:
        bool: True if hanging man detected on current bar, False otherwise.
    """
    if len(df) < 1:
        return False
    result = HangingMan.compute(
        data=_ohlc_data(df),
        params={"wick_ratio": wick_ratio, "upper_wick_max": upper_wick_max},
    )
    return int(result["hanging_man"].iloc[-1]) == 1


@RuleRegistry.register("inverted_hammer_trigger")
def inverted_hammer_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                              lower_wick_max: float = 0.1) -> bool:
    """
    Check if an inverted hammer shape is detected on the current bar.

    Same shape as shooting star (small body, long upper wick) but interpreted as a
    bullish reversal when appearing after a downtrend. References: [NISON], [STOCKCHARTS].

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
    result = InvertedHammer.compute(
        data=_ohlc_data(df),
        params={"wick_ratio": wick_ratio, "lower_wick_max": lower_wick_max},
    )
    return int(result["inverted_hammer"].iloc[-1]) == 1


@RuleRegistry.register("marubozu_bullish_trigger")
def marubozu_bullish_trigger(df: pd.DataFrame, wick_tolerance: float = 0.05) -> bool:
    """
    Check if a bullish marubozu is detected on the current bar.

    Full-bodied bullish candle with minimal or no wicks.
    Signals strong buying conviction. References: [NISON], [KB-07], [CM45T3R].

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
    result = Marubozu.compute(data=_ohlc_data(df), params={"wick_tolerance": wick_tolerance})
    return int(result["marubozu"].iloc[-1]) == 1


@RuleRegistry.register("marubozu_bearish_trigger")
def marubozu_bearish_trigger(df: pd.DataFrame, wick_tolerance: float = 0.05) -> bool:
    """
    Check if a bearish marubozu is detected on the current bar.

    Full-bodied bearish candle with minimal or no wicks.
    Signals strong selling conviction. References: [NISON], [KB-07], [CM45T3R].

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
    result = Marubozu.compute(data=_ohlc_data(df), params={"wick_tolerance": wick_tolerance})
    return int(result["marubozu"].iloc[-1]) == -1


@RuleRegistry.register("spinning_top_trigger")
def spinning_top_trigger(df: pd.DataFrame, body_max: float = 0.3,
                          wick_min: float = 0.2) -> bool:
    """
    Check if a spinning top is detected on the current bar.

    Small body with significant wicks on both sides, signaling indecision.
    References: [NISON], [CM45T3R], [STOCKCHARTS].

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
    result = SpinningTop.compute(
        data=_ohlc_data(df),
        params={"body_max": body_max, "wick_min": wick_min},
    )
    return int(result["spinning_top"].iloc[-1]) == 1


# =============================================================================
# Two-Candle TRIGGER Signals
# =============================================================================


@RuleRegistry.register("bullish_engulfing_trigger")
def bullish_engulfing_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bullish engulfing pattern completed on the current bar.

    Current bullish candle's body completely contains the previous bearish
    candle's body. Strong bullish reversal. References: [NISON], [KB-07], [STOCKCHARTS].

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bullish engulfing detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = Engulfing.compute(data=_oc_data(df), params={})
    return int(result["engulfing"].iloc[-1]) == 1


@RuleRegistry.register("bearish_engulfing_trigger")
def bearish_engulfing_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bearish engulfing pattern completed on the current bar.

    Current bearish candle's body completely contains the previous bullish
    candle's body. Strong bearish reversal. References: [NISON], [KB-07], [STOCKCHARTS].

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bearish engulfing detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = Engulfing.compute(data=_oc_data(df), params={})
    return int(result["engulfing"].iloc[-1]) == -1


@RuleRegistry.register("bullish_harami_trigger")
def bullish_harami_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bullish harami pattern completed on the current bar.

    Current small bullish candle's body is inside the previous large bearish
    candle's body. Potential bullish reversal. References: [NISON], [STOCKCHARTS].

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bullish harami detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = Harami.compute(data=_oc_data(df), params={})
    return int(result["harami"].iloc[-1]) == 1


@RuleRegistry.register("bearish_harami_trigger")
def bearish_harami_trigger(df: pd.DataFrame) -> bool:
    """
    Check if a bearish harami pattern completed on the current bar.

    Current small bearish candle's body is inside the previous large bullish
    candle's body. Potential bearish reversal. References: [NISON], [STOCKCHARTS].

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if bearish harami detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = Harami.compute(data=_oc_data(df), params={})
    return int(result["harami"].iloc[-1]) == -1


@RuleRegistry.register("piercing_line_trigger")
def piercing_line_trigger(df: pd.DataFrame, min_penetration: float = 0.5, require_gap: bool = True) -> bool:
    """
    Check if a piercing line pattern completed on the current bar.

    Bullish reversal: bearish candle followed by bullish candle opening below
    prior low (classic) or prior close (relaxed) and closing above midpoint of
    prior body. The classic definition requires a price gap, which is rare in
    24/7 crypto/forex markets. Set require_gap=False for those markets.
    References: [NISON], [KB-07].

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        min_penetration (float): Minimum penetration into previous body. Range: 0.3-0.8. Default: 0.5.
        require_gap (bool): If True, requires open below previous low (classic Nison). If False, requires open below previous close (relaxed for 24/7 markets). Range: true-false. Default: true.

    Returns:
        bool: True if piercing line detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = PiercingLine.compute(data=_ohlc_data(df), params={"min_penetration": min_penetration, "require_gap": require_gap})
    return int(result["piercing_line"].iloc[-1]) == 1


@RuleRegistry.register("dark_cloud_cover_trigger")
def dark_cloud_cover_trigger(df: pd.DataFrame, min_penetration: float = 0.5, require_gap: bool = True) -> bool:
    """
    Check if a dark cloud cover pattern completed on the current bar.

    Bearish reversal: bullish candle followed by bearish candle opening above
    prior high (classic) or prior close (relaxed) and closing below midpoint of
    prior body. The classic definition requires a price gap, which is rare in
    24/7 crypto/forex markets. Set require_gap=False for those markets.
    References: [NISON], [KB-07].

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        min_penetration (float): Minimum penetration into previous body. Range: 0.3-0.8. Default: 0.5.
        require_gap (bool): If True, requires open above previous high (classic Nison). If False, requires open above previous close (relaxed for 24/7 markets). Range: true-false. Default: true.

    Returns:
        bool: True if dark cloud cover detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = DarkCloudCover.compute(data=_ohlc_data(df), params={"min_penetration": min_penetration, "require_gap": require_gap})
    return int(result["dark_cloud_cover"].iloc[-1]) == -1


@RuleRegistry.register("tweezer_tops_trigger")
def tweezer_tops_trigger(df: pd.DataFrame, tolerance: float = 0.01) -> bool:
    """
    Check if a tweezer tops pattern completed on the current bar.

    Two consecutive candles with approximately equal highs, first bullish
    and second bearish. Bearish reversal. References: [NISON], [CM45T3R].

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
    result = TweezerTops.compute(data=_ohlc_data(df), params={"tolerance": tolerance})
    return int(result["tweezer_tops"].iloc[-1]) == -1


@RuleRegistry.register("tweezer_bottoms_trigger")
def tweezer_bottoms_trigger(df: pd.DataFrame, tolerance: float = 0.01) -> bool:
    """
    Check if a tweezer bottoms pattern completed on the current bar.

    Two consecutive candles with approximately equal lows, first bearish
    and second bullish. Bullish reversal. References: [NISON], [CM45T3R].

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
    result = TweezerBottoms.compute(data=_ohlc_data(df), params={"tolerance": tolerance})
    return int(result["tweezer_bottoms"].iloc[-1]) == 1


# =============================================================================
# Three-Candle TRIGGER Signals
# =============================================================================


@RuleRegistry.register("morning_star_trigger")
def morning_star_trigger(df: pd.DataFrame, body_threshold: float = 0.3) -> bool:
    """
    Check if a morning star pattern completed on the current bar.

    Three-candle bullish reversal: bearish candle, small-bodied star, then
    bullish candle closing above midpoint of first. References: [NISON], [KB-07].

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
    result = MorningStar.compute(data=_ohlc_data(df), params={"body_threshold": body_threshold})
    return int(result["morning_star"].iloc[-1]) == 1


@RuleRegistry.register("evening_star_trigger")
def evening_star_trigger(df: pd.DataFrame, body_threshold: float = 0.3) -> bool:
    """
    Check if an evening star pattern completed on the current bar.

    Three-candle bearish reversal: bullish candle, small-bodied star, then
    bearish candle closing below midpoint of first. References: [NISON], [KB-07].

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
    result = EveningStar.compute(data=_ohlc_data(df), params={"body_threshold": body_threshold})
    return int(result["evening_star"].iloc[-1]) == -1


@RuleRegistry.register("three_white_soldiers_trigger")
def three_white_soldiers_trigger(df: pd.DataFrame, min_body_ratio: float = 0.5) -> bool:
    """
    Check if three white soldiers pattern completed on the current bar.

    Three consecutive bullish candles with higher closes, each opening within
    the previous body. Strong bullish signal. References: [NISON], [KB-07], [STOCKCHARTS].

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
    result = ThreeWhiteSoldiers.compute(data=_ohlc_data(df), params={"min_body_ratio": min_body_ratio})
    return int(result["three_white_soldiers"].iloc[-1]) == 1


@RuleRegistry.register("three_black_crows_trigger")
def three_black_crows_trigger(df: pd.DataFrame, min_body_ratio: float = 0.5) -> bool:
    """
    Check if three black crows pattern completed on the current bar.

    Three consecutive bearish candles with lower closes, each opening within
    the previous body. Strong bearish signal. References: [NISON], [KB-07], [STOCKCHARTS].

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
    result = ThreeBlackCrows.compute(data=_ohlc_data(df), params={"min_body_ratio": min_body_ratio})
    return int(result["three_black_crows"].iloc[-1]) == -1


@RuleRegistry.register("three_inside_up_trigger")
def three_inside_up_trigger(df: pd.DataFrame) -> bool:
    """
    Check if three inside up pattern completed on the current bar.

    Bearish candle, bullish harami, then bullish close above first candle's open.
    Confirmed bullish reversal. References: [NISON], [KB-07], [TRENDSPIDER].

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if three inside up detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = ThreeInsideUp.compute(data=_oc_data(df), params={})
    return int(result["three_inside_up"].iloc[-1]) == 1


@RuleRegistry.register("three_inside_down_trigger")
def three_inside_down_trigger(df: pd.DataFrame) -> bool:
    """
    Check if three inside down pattern completed on the current bar.

    Bullish candle, bearish harami, then bearish close below first candle's open.
    Confirmed bearish reversal. References: [NISON], [KB-07], [TRENDSPIDER].

    Type: TRIGGER
    Requires: Open, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if three inside down detected on current bar, False otherwise.
    """
    if len(df) < 3:
        return False
    result = ThreeInsideDown.compute(data=_oc_data(df), params={})
    return int(result["three_inside_down"].iloc[-1]) == -1


# =============================================================================
# Multi-Bar TRIGGER Signals
# =============================================================================


@RuleRegistry.register("inside_bar_trigger")
def inside_bar_trigger(df: pd.DataFrame) -> bool:
    """
    Check if an inside bar is detected on the current bar.

    Current bar's range is completely contained within the previous bar's range.
    Signals consolidation and potential breakout. References: [KB-07], [TSR].

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if inside bar detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = InsideBar.compute(data=_hl_data(df), params={})
    return int(result["inside_bar"].iloc[-1]) == 1


@RuleRegistry.register("outside_bar_trigger")
def outside_bar_trigger(df: pd.DataFrame) -> bool:
    """
    Check if an outside bar is detected on the current bar.

    Current bar's range completely engulfs the previous bar's range.
    Signals increased volatility. References: [KB-07], [TSR].

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if outside bar detected on current bar, False otherwise.
    """
    if len(df) < 2:
        return False
    result = OutsideBar.compute(data=_hl_data(df), params={})
    return int(result["outside_bar"].iloc[-1]) == 1


@RuleRegistry.register("bullish_pin_bar_trigger")
def bullish_pin_bar_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                             body_position: float = 0.33) -> bool:
    """
    Check if a bullish pin bar is detected on the current bar.

    Long lower wick with body in the upper portion of the range.
    Bullish reversal at support. References: [KB-07], [TSR], [PRICEACTION].

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
    result = PinBar.compute(
        data=_ohlc_data(df),
        params={"wick_ratio": wick_ratio, "body_position": body_position},
    )
    return int(result["pin_bar"].iloc[-1]) == 1


@RuleRegistry.register("bearish_pin_bar_trigger")
def bearish_pin_bar_trigger(df: pd.DataFrame, wick_ratio: float = 2.0,
                              body_position: float = 0.33) -> bool:
    """
    Check if a bearish pin bar is detected on the current bar.

    Long upper wick with body in the lower portion of the range.
    Bearish reversal at resistance. References: [KB-07], [TSR], [PRICEACTION].

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
    result = PinBar.compute(
        data=_ohlc_data(df),
        params={"wick_ratio": wick_ratio, "body_position": body_position},
    )
    return int(result["pin_bar"].iloc[-1]) == -1


@RuleRegistry.register("two_bar_reversal_bullish_trigger")
def two_bar_reversal_bullish_trigger(df: pd.DataFrame, close_proximity: float = 0.25) -> bool:
    """
    Check if a bullish two-bar reversal completed on the current bar.

    Bearish bar followed by bullish bar that takes out the low then
    closes above the prior open. The close_proximity parameter controls how
    close the close must be to the high/low extreme. References: [KB-07], [TSR], [DAILYFOREX].

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
    result = TwoBarReversal.compute(data=_ohlc_data(df), params={"close_proximity": close_proximity})
    return int(result["two_bar_reversal"].iloc[-1]) == 1


@RuleRegistry.register("two_bar_reversal_bearish_trigger")
def two_bar_reversal_bearish_trigger(df: pd.DataFrame, close_proximity: float = 0.25) -> bool:
    """
    Check if a bearish two-bar reversal completed on the current bar.

    Bullish bar followed by bearish bar that takes out the high then
    closes below the prior open. The close_proximity parameter controls how
    close the close must be to the high/low extreme. References: [KB-07], [TSR], [DAILYFOREX].

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
    result = TwoBarReversal.compute(data=_ohlc_data(df), params={"close_proximity": close_proximity})
    return int(result["two_bar_reversal"].iloc[-1]) == -1


@RuleRegistry.register("nr7_trigger")
def nr7_trigger(df: pd.DataFrame, window: int = 7) -> bool:
    """
    Check if a narrow range day is detected on the current bar.

    Current bar has the smallest range within the window period.
    Signals volatility compression and imminent breakout.
    Default window=7 for NR7; use 4 for NR4. References: [CRABEL], [KB-07], [BULKOWSKI].

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
    result = NarrowRange.compute(data=_hl_data(df), params={"window": window})
    return int(result["narrow_range"].iloc[-1]) == 1


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
    ohlc = _ohlc_data(df)
    oc = _oc_data(df)

    checks = [
        Hammer.compute(data=ohlc, params={"wick_ratio": 2.0, "upper_wick_max": 0.1})["hammer"],
        InvertedHammer.compute(data=ohlc, params={"wick_ratio": 2.0, "lower_wick_max": 0.1})["inverted_hammer"],
        Engulfing.compute(data=oc, params={})["engulfing"].clip(lower=0),
        Harami.compute(data=oc, params={})["harami"].clip(lower=0),
        PiercingLine.compute(data=ohlc, params={"min_penetration": 0.5, "require_gap": False})["piercing_line"],
        DragonflyDoji.compute(data=ohlc, params={"body_threshold": 0.1, "upper_wick_max": 0.1})["dragonfly_doji"],
        TweezerBottoms.compute(data=ohlc, params={"tolerance": 0.01})["tweezer_bottoms"],
        PinBar.compute(data=ohlc, params={"wick_ratio": 2.0, "body_position": 0.33})["pin_bar"].clip(lower=0),
    ]
    if len(df) >= 3:
        checks.extend([
            MorningStar.compute(data=ohlc, params={"body_threshold": 0.3})["morning_star"],
            ThreeWhiteSoldiers.compute(data=ohlc, params={"min_body_ratio": 0.5})["three_white_soldiers"],
            ThreeInsideUp.compute(data=oc, params={})["three_inside_up"],
        ])

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("bearish_pattern_recent")
def bearish_pattern_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if any bearish candlestick pattern was detected within recent window.

    Scans for hanging man, shooting star, bearish engulfing, bearish harami,
    dark cloud cover, evening star, gravestone doji, three black crows,
    three inside down, tweezer tops, and bearish pin bar within the recent window.

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
    ohlc = _ohlc_data(df)
    oc = _oc_data(df)

    checks = [
        HangingMan.compute(data=ohlc, params={"wick_ratio": 2.0, "upper_wick_max": 0.1})["hanging_man"],
        ShootingStar.compute(data=ohlc, params={"wick_ratio": 2.0, "lower_wick_max": 0.1})["shooting_star"],
        Engulfing.compute(data=oc, params={})["engulfing"].clip(upper=0).abs(),
        Harami.compute(data=oc, params={})["harami"].clip(upper=0).abs(),
        DarkCloudCover.compute(data=ohlc, params={"min_penetration": 0.5, "require_gap": False})["dark_cloud_cover"].abs(),
        GravestoneDoji.compute(data=ohlc, params={"body_threshold": 0.1, "lower_wick_max": 0.1})["gravestone_doji"],
        TweezerTops.compute(data=ohlc, params={"tolerance": 0.01})["tweezer_tops"].abs(),
        PinBar.compute(data=ohlc, params={"wick_ratio": 2.0, "body_position": 0.33})["pin_bar"].clip(upper=0).abs(),
    ]
    if len(df) >= 3:
        checks.extend([
            EveningStar.compute(data=ohlc, params={"body_threshold": 0.3})["evening_star"].abs(),
            ThreeBlackCrows.compute(data=ohlc, params={"min_body_ratio": 0.5})["three_black_crows"].abs(),
            ThreeInsideDown.compute(data=oc, params={})["three_inside_down"].abs(),
        ])

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("reversal_pattern_bullish")
def reversal_pattern_bullish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bullish reversal pattern was detected within recent window.

    Scans for hammer, inverted hammer, bullish engulfing, morning star,
    piercing line, and dragonfly doji -- the classic bullish reversal patterns.

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
    ohlc = _ohlc_data(df)
    oc = _oc_data(df)

    checks = [
        Hammer.compute(data=ohlc, params={"wick_ratio": 2.0, "upper_wick_max": 0.1})["hammer"],
        InvertedHammer.compute(data=ohlc, params={"wick_ratio": 2.0, "lower_wick_max": 0.1})["inverted_hammer"],
        Engulfing.compute(data=oc, params={})["engulfing"].clip(lower=0),
        PiercingLine.compute(data=ohlc, params={"min_penetration": 0.5, "require_gap": False})["piercing_line"],
        DragonflyDoji.compute(data=ohlc, params={"body_threshold": 0.1, "upper_wick_max": 0.1})["dragonfly_doji"],
    ]
    if len(df) >= 3:
        checks.append(
            MorningStar.compute(data=ohlc, params={"body_threshold": 0.3})["morning_star"]
        )

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("reversal_pattern_bearish")
def reversal_pattern_bearish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bearish reversal pattern was detected within recent window.

    Scans for hanging man, shooting star, bearish engulfing, evening star,
    dark cloud cover, and gravestone doji -- the classic bearish reversal patterns.

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
    ohlc = _ohlc_data(df)
    oc = _oc_data(df)

    checks = [
        HangingMan.compute(data=ohlc, params={"wick_ratio": 2.0, "upper_wick_max": 0.1})["hanging_man"],
        ShootingStar.compute(data=ohlc, params={"wick_ratio": 2.0, "lower_wick_max": 0.1})["shooting_star"],
        Engulfing.compute(data=oc, params={})["engulfing"].clip(upper=0).abs(),
        DarkCloudCover.compute(data=ohlc, params={"min_penetration": 0.5, "require_gap": False})["dark_cloud_cover"].abs(),
        GravestoneDoji.compute(data=ohlc, params={"body_threshold": 0.1, "lower_wick_max": 0.1})["gravestone_doji"],
    ]
    if len(df) >= 3:
        checks.append(
            EveningStar.compute(data=ohlc, params={"body_threshold": 0.3})["evening_star"].abs()
        )

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("continuation_pattern_bullish")
def continuation_pattern_bullish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bullish continuation pattern was detected within recent window.

    Scans for three white soldiers and three inside up.

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
    ohlc = _ohlc_data(df)
    oc = _oc_data(df)

    checks = [
        ThreeWhiteSoldiers.compute(data=ohlc, params={"min_body_ratio": 0.5})["three_white_soldiers"],
        ThreeInsideUp.compute(data=oc, params={})["three_inside_up"],
    ]

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("continuation_pattern_bearish")
def continuation_pattern_bearish(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a bearish continuation pattern was detected within recent window.

    Scans for three black crows and three inside down.

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
    ohlc = _ohlc_data(df)
    oc = _oc_data(df)

    checks = [
        ThreeBlackCrows.compute(data=ohlc, params={"min_body_ratio": 0.5})["three_black_crows"].abs(),
        ThreeInsideDown.compute(data=oc, params={})["three_inside_down"].abs(),
    ]

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("indecision_pattern_recent")
def indecision_pattern_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if an indecision pattern was detected within recent window.

    Scans for doji, spinning top, inside bar, and NR7.

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
    ohlc = _ohlc_data(df)
    hl = _hl_data(df)

    checks = [
        Doji.compute(data=ohlc, params={"body_threshold": 0.1})["doji"],
        SpinningTop.compute(data=ohlc, params={"body_max": 0.3, "wick_min": 0.2})["spinning_top"],
        InsideBar.compute(data=hl, params={})["inside_bar"],
    ]
    if len(df) >= 7:
        checks.append(
            NarrowRange.compute(data=hl, params={"window": 7})["narrow_range"]
        )

    for series in checks:
        recent = series.iloc[-window:]
        if (recent > 0).any():
            return True
    return False


@RuleRegistry.register("strong_body_recent")
def strong_body_recent(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Check if a marubozu (strong body) was detected within recent window.

    Scans for both bullish and bearish marubozu patterns.

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
    result = Marubozu.compute(data=_ohlc_data(df), params={"wick_tolerance": 0.05})
    recent = result["marubozu"].iloc[-window:]
    return (recent != 0).any()
