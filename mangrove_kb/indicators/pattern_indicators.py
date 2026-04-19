"""Candlestick and multi-bar pattern indicator classes.

Provides vectorized pattern detection across entire DataFrames.
All indicators follow the IndicatorInterface convention: stateless
classmethod-based computation with _data, _params, _outputs, and _compute().

Pattern indicator output convention:
    1  = bullish pattern detected
   -1  = bearish pattern detected
    0  = no pattern detected

References key (see findings/chart-patterns-plan.md Section 5 for full citations):
    [NISON]     Steve Nison, Japanese Candlestick Charting Techniques
    [KB-07]     MangroveKnowledgeBase knowledge-base/07-chart-patterns.md
    [CM45T3R]   cm45t3r/candlestick open-source library
    [LUXALGO]   LuxAlgo candlestick pattern documentation
    [STOCKCHARTS] StockCharts Candlestick Pattern Dictionary
    [TRENDSPIDER] TrendSpider pattern definitions
    [CRABEL]    Toby Crabel, Day Trading with Short Term Price Patterns
    [TSR]       Trading Setups Review, 10 Price Action Bar Patterns
    [BULKOWSKI] Thomas Bulkowski, Encyclopedia of Candlestick Charts
"""

import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.pattern_utils import (
    candle_body,
    candle_range,
    upper_wick,
    lower_wick,
    is_bullish,
    is_bearish,
)


# =============================================================================
# Single-Candle Patterns
# =============================================================================


class Doji(IndicatorInterface):
    """Doji pattern detection.

    A doji forms when open and close are nearly equal relative to the
    candle's range, signaling indecision between buyers and sellers.

    References: [NISON], [KB-07], [CM45T3R], [LUXALGO]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_threshold"]
    _outputs = ["doji"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        rng = candle_range(h, l)
        threshold = params["body_threshold"]

        detected = ((rng > 0) & (body <= rng * threshold)).astype(int)
        return {"doji": pd.Series(detected, index=o.index, name="doji")}


class LongLeggedDoji(IndicatorInterface):
    """Long-legged doji pattern detection.

    A doji with both upper and lower wicks at least wick_threshold
    of the total range, indicating extreme indecision.

    References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_threshold", "wick_threshold"]
    _outputs = ["long_legged_doji"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        rng = candle_range(h, l)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)

        is_doji = (rng > 0) & (body <= rng * params["body_threshold"])
        long_wicks = (uw >= rng * params["wick_threshold"]) & (lw >= rng * params["wick_threshold"])

        detected = (is_doji & long_wicks).astype(int)
        return {"long_legged_doji": pd.Series(detected, index=o.index, name="long_legged_doji")}


class DragonflyDoji(IndicatorInterface):
    """Dragonfly doji pattern detection.

    A doji with open/close near the high and a long lower shadow.
    Bullish signal especially at support.

    References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_threshold", "upper_wick_max"]
    _outputs = ["dragonfly_doji"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        rng = candle_range(h, l)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)

        is_doji = (rng > 0) & (body <= rng * params["body_threshold"])
        small_upper = uw <= rng * params["upper_wick_max"]
        long_lower = lw > body

        detected = (is_doji & small_upper & long_lower).astype(int)
        return {"dragonfly_doji": pd.Series(detected, index=o.index, name="dragonfly_doji")}


class GravestoneDoji(IndicatorInterface):
    """Gravestone doji pattern detection.

    A doji with open/close near the low and a long upper shadow.
    Bearish signal especially at resistance.

    References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_threshold", "lower_wick_max"]
    _outputs = ["gravestone_doji"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        rng = candle_range(h, l)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)

        is_doji = (rng > 0) & (body <= rng * params["body_threshold"])
        small_lower = lw <= rng * params["lower_wick_max"]
        long_upper = uw > body

        detected = (is_doji & small_lower & long_upper).astype(int)
        return {"gravestone_doji": pd.Series(detected, index=o.index, name="gravestone_doji")}


class Hammer(IndicatorInterface):
    """Hammer pattern detection (shape only).

    Small body at upper end with long lower wick and minimal upper wick.
    Structurally identical to Hanging Man; context distinguishes them.

    References: [NISON], [KB-07], [CM45T3R], [LUXALGO], [STOCKCHARTS]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["wick_ratio", "upper_wick_max"]
    _outputs = ["hammer"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)

        has_body = body > 0
        long_lower = lw >= body * params["wick_ratio"]
        small_upper = uw <= body * params["upper_wick_max"]

        detected = (has_body & long_lower & small_upper).astype(int)
        return {"hammer": pd.Series(detected, index=o.index, name="hammer")}


class HangingMan(IndicatorInterface):
    """Hanging man pattern detection (shape only).

    Same shape as Hammer. Bearish when appearing after uptrend.
    Context applied at the signal level, not here.

    References: [NISON], [STOCKCHARTS]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["wick_ratio", "upper_wick_max"]
    _outputs = ["hanging_man"]

    @classmethod
    def _compute(cls, data, params):
        result = Hammer._compute(data, params)
        return {"hanging_man": pd.Series(result["hammer"].values, index=data["open"].index, name="hanging_man")}


class InvertedHammer(IndicatorInterface):
    """Inverted hammer pattern detection (shape only).

    Small body at lower end with long upper wick and minimal lower wick.
    Structurally identical to Shooting Star; context distinguishes them.

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["wick_ratio", "lower_wick_max"]
    _outputs = ["inverted_hammer"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)

        has_body = body > 0
        long_upper = uw >= body * params["wick_ratio"]
        small_lower = lw <= body * params["lower_wick_max"]

        detected = (has_body & long_upper & small_lower).astype(int)
        return {"inverted_hammer": pd.Series(detected, index=o.index, name="inverted_hammer")}


class ShootingStar(IndicatorInterface):
    """Shooting star pattern detection (shape only).

    Same shape as Inverted Hammer. Bearish when appearing after uptrend.
    Context applied at the signal level, not here.

    References: [NISON], [STOCKCHARTS]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["wick_ratio", "lower_wick_max"]
    _outputs = ["shooting_star"]

    @classmethod
    def _compute(cls, data, params):
        result = InvertedHammer._compute(data, params)
        return {"shooting_star": pd.Series(result["inverted_hammer"].values, index=data["open"].index, name="shooting_star")}


class Marubozu(IndicatorInterface):
    """Marubozu pattern detection.

    Full-bodied candle with minimal or no wicks on either side.
    Returns 1 for bullish (Close > Open), -1 for bearish.

    References: [NISON], [KB-07], [CM45T3R], [STOCKCHARTS]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["wick_tolerance"]
    _outputs = ["marubozu"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        rng = candle_range(h, l)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)
        tol = params["wick_tolerance"]

        small_wicks = (rng > 0) & (uw <= rng * tol) & (lw <= rng * tol)
        bull = is_bullish(o, c)
        bear = is_bearish(o, c)

        result = pd.Series(0, index=o.index, name="marubozu")
        result[small_wicks & bull] = 1
        result[small_wicks & bear] = -1
        return {"marubozu": result}


class SpinningTop(IndicatorInterface):
    """Spinning top pattern detection.

    Small body with significant wicks on both sides, signaling indecision.
    Body can be larger than doji (up to 30% vs 10% of range).

    References: [NISON], [CM45T3R], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_max", "wick_min"]
    _outputs = ["spinning_top"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        rng = candle_range(h, l)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)

        small_body = (rng > 0) & (body <= rng * params["body_max"])
        both_wicks = (uw >= rng * params["wick_min"]) & (lw >= rng * params["wick_min"])

        detected = (small_body & both_wicks).astype(int)
        return {"spinning_top": pd.Series(detected, index=o.index, name="spinning_top")}


# =============================================================================
# Two-Candle Patterns
# =============================================================================


class Engulfing(IndicatorInterface):
    """Engulfing pattern detection.

    Second candle's body completely contains the first candle's body.
    Returns 1 for bullish engulfing, -1 for bearish engulfing.

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "close"]
    _params = []
    _outputs = ["engulfing"]

    @classmethod
    def _compute(cls, data, params):
        o, c = data["open"], data["close"]
        prev_o, prev_c = o.shift(1), c.shift(1)

        prev_bear = prev_c < prev_o
        prev_bull = prev_c > prev_o
        curr_bull = c > o
        curr_bear = c < o

        bullish = prev_bear & curr_bull & (o < prev_c) & (c > prev_o)
        bearish = prev_bull & curr_bear & (o > prev_c) & (c < prev_o)

        result = pd.Series(0, index=o.index, name="engulfing")
        result[bullish] = 1
        result[bearish] = -1
        return {"engulfing": result}


class Harami(IndicatorInterface):
    """Harami pattern detection.

    Second candle's body is completely contained within the first candle's body.
    Returns 1 for bullish harami, -1 for bearish harami.

    References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "close"]
    _params = []
    _outputs = ["harami"]

    @classmethod
    def _compute(cls, data, params):
        o, c = data["open"], data["close"]
        prev_o, prev_c = o.shift(1), c.shift(1)

        prev_bear = prev_c < prev_o
        prev_bull = prev_c > prev_o
        curr_bull = c > o
        curr_bear = c < o

        bullish = prev_bear & curr_bull & (o > prev_c) & (c < prev_o)
        bearish = prev_bull & curr_bear & (o < prev_c) & (c > prev_o)

        result = pd.Series(0, index=o.index, name="harami")
        result[bullish] = 1
        result[bearish] = -1
        return {"harami": result}


class PiercingLine(IndicatorInterface):
    """Piercing line pattern detection.

    Bullish reversal: bearish candle followed by bullish candle that
    opens below the prior low and closes above the midpoint of the
    prior body.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {
            'min_penetration': float (default 0.5) - Minimum penetration into first candle body. Range: 0.3-0.8.
            'require_gap': bool (default True) - If True, requires open below previous low (classic Nison definition). If False, requires open below previous close (relaxed for 24/7 crypto/forex markets).
        }

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["min_penetration", "require_gap"]
    _outputs = ["piercing_line"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        prev_o, prev_c, prev_l = o.shift(1), c.shift(1), l.shift(1)
        pen = params["min_penetration"]

        prev_bear = prev_c < prev_o
        curr_bull = c > o
        require_gap = params.get("require_gap", True)
        if require_gap:
            gaps_below = o < prev_l  # Classic Nison: open below previous low
        else:
            gaps_below = o < prev_c  # Relaxed: open below previous close (for 24/7 markets)
        penetrates = c > prev_c + (prev_o - prev_c) * pen

        detected = (prev_bear & curr_bull & gaps_below & penetrates).astype(int)
        return {"piercing_line": pd.Series(detected, index=o.index, name="piercing_line")}


class DarkCloudCover(IndicatorInterface):
    """Dark cloud cover pattern detection.

    Bearish reversal: bullish candle followed by bearish candle that
    opens above the prior high and closes below the midpoint of the
    prior body.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {
            'min_penetration': float (default 0.5) - Minimum penetration into first candle body. Range: 0.3-0.8.
            'require_gap': bool (default True) - If True, requires open above previous high (classic Nison definition). If False, requires open above previous close (relaxed for 24/7 crypto/forex markets).
        }

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["min_penetration", "require_gap"]
    _outputs = ["dark_cloud_cover"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        prev_o, prev_c, prev_h = o.shift(1), c.shift(1), h.shift(1)
        pen = params["min_penetration"]

        prev_bull = prev_c > prev_o
        curr_bear = c < o
        require_gap = params.get("require_gap", True)
        if require_gap:
            gaps_above = o > prev_h  # Classic Nison: open above previous high
        else:
            gaps_above = o > prev_c  # Relaxed: open above previous close (for 24/7 markets)
        penetrates = c < prev_c - (prev_c - prev_o) * pen

        detected = prev_bull & curr_bear & gaps_above & penetrates
        result = pd.Series(0, index=o.index, name="dark_cloud_cover")
        result[detected] = -1
        return {"dark_cloud_cover": result}


class TweezerTops(IndicatorInterface):
    """Tweezer tops pattern detection.

    Two consecutive candles with approximately equal highs where the
    first is bullish and the second is bearish. Bearish reversal signal.

    References: [NISON], [CM45T3R], [STOCKCHARTS]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["tolerance"]
    _outputs = ["tweezer_tops"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        prev_h = h.shift(1)
        prev_o, prev_c = o.shift(1), c.shift(1)
        rng = candle_range(h, l)
        avg_window = params.get("avg_window", 20)
        avg_rng = rng.rolling(window=avg_window, min_periods=1).mean()
        tol = params["tolerance"]

        matching_highs = (h - prev_h).abs() <= avg_rng * tol
        prev_bull = prev_c > prev_o
        curr_bear = c < o

        detected = (matching_highs & prev_bull & curr_bear)
        result = pd.Series(0, index=o.index, name="tweezer_tops")
        result[detected] = -1
        return {"tweezer_tops": result}


class TweezerBottoms(IndicatorInterface):
    """Tweezer bottoms pattern detection.

    Two consecutive candles with approximately equal lows where the
    first is bearish and the second is bullish. Bullish reversal signal.

    References: [NISON], [CM45T3R], [STOCKCHARTS]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["tolerance"]
    _outputs = ["tweezer_bottoms"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        prev_l = l.shift(1)
        prev_o, prev_c = o.shift(1), c.shift(1)
        rng = candle_range(h, l)
        avg_window = params.get("avg_window", 20)
        avg_rng = rng.rolling(window=avg_window, min_periods=1).mean()
        tol = params["tolerance"]

        matching_lows = (l - prev_l).abs() <= avg_rng * tol
        prev_bear = prev_c < prev_o
        curr_bull = c > o

        detected = (matching_lows & prev_bear & curr_bull).astype(int)
        return {"tweezer_bottoms": pd.Series(detected, index=o.index, name="tweezer_bottoms")}


# =============================================================================
# Three-Candle Patterns
# =============================================================================


class MorningStar(IndicatorInterface):
    """Morning star pattern detection.

    Three-candle bullish reversal: bearish candle, small-bodied star,
    then bullish candle closing above the midpoint of the first.

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_threshold"]
    _outputs = ["morning_star"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        rng = candle_range(h, l)

        o2, c2 = o.shift(2), c.shift(2)
        o1, c1 = o.shift(1), c.shift(1)
        rng1 = rng.shift(1)

        first_bearish = c2 < o2
        star_small = candle_body(o1, c1) <= rng1 * params["body_threshold"]
        third_bullish = c > o
        midpoint = (o2 + c2) / 2
        closes_above_mid = c > midpoint

        detected = (first_bearish & star_small & third_bullish & closes_above_mid).astype(int)
        return {"morning_star": pd.Series(detected, index=o.index, name="morning_star")}


class EveningStar(IndicatorInterface):
    """Evening star pattern detection.

    Three-candle bearish reversal: bullish candle, small-bodied star,
    then bearish candle closing below the midpoint of the first.

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["body_threshold"]
    _outputs = ["evening_star"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        rng = candle_range(h, l)

        o2, c2 = o.shift(2), c.shift(2)
        o1, c1 = o.shift(1), c.shift(1)
        rng1 = rng.shift(1)

        first_bullish = c2 > o2
        star_small = candle_body(o1, c1) <= rng1 * params["body_threshold"]
        third_bearish = c < o
        midpoint = (o2 + c2) / 2
        closes_below_mid = c < midpoint

        detected = (first_bullish & star_small & third_bearish & closes_below_mid)
        result = pd.Series(0, index=o.index, name="evening_star")
        result[detected] = -1
        return {"evening_star": result}


class ThreeWhiteSoldiers(IndicatorInterface):
    """Three white soldiers pattern detection.

    Three consecutive bullish candles with progressively higher closes,
    each opening within the previous body. Strong bullish signal.

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["min_body_ratio"]
    _outputs = ["three_white_soldiers"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        rng = candle_range(h, l)
        body = candle_body(o, c)
        min_ratio = params["min_body_ratio"]

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
        return {"three_white_soldiers": pd.Series(detected, index=o.index, name="three_white_soldiers")}


class ThreeBlackCrows(IndicatorInterface):
    """Three black crows pattern detection.

    Three consecutive bearish candles with progressively lower closes,
    each opening within the previous body. Strong bearish signal.

    References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["min_body_ratio"]
    _outputs = ["three_black_crows"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        rng = candle_range(h, l)
        body = candle_body(o, c)
        min_ratio = params["min_body_ratio"]

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
        return {"three_black_crows": result}


class ThreeInsideUp(IndicatorInterface):
    """Three inside up pattern detection.

    Bearish candle, bullish harami, then bullish candle closing above
    the first candle's open. Confirmed bullish reversal.

    References: [NISON], [KB-07], [TRENDSPIDER]
    """

    _data = ["open", "close"]
    _params = []
    _outputs = ["three_inside_up"]

    @classmethod
    def _compute(cls, data, params):
        o, c = data["open"], data["close"]
        o2, c2 = o.shift(2), c.shift(2)
        o1, c1 = o.shift(1), c.shift(1)

        first_bearish = c2 < o2
        harami = (c1 > o1) & (o1 > c2) & (c1 < o2)
        third_bullish = (c > o) & (c > o2)

        detected = (first_bearish & harami & third_bullish).astype(int)
        return {"three_inside_up": pd.Series(detected, index=o.index, name="three_inside_up")}


class ThreeInsideDown(IndicatorInterface):
    """Three inside down pattern detection.

    Bullish candle, bearish harami, then bearish candle closing below
    the first candle's open. Confirmed bearish reversal.

    References: [NISON], [KB-07], [TRENDSPIDER]
    """

    _data = ["open", "close"]
    _params = []
    _outputs = ["three_inside_down"]

    @classmethod
    def _compute(cls, data, params):
        o, c = data["open"], data["close"]
        o2, c2 = o.shift(2), c.shift(2)
        o1, c1 = o.shift(1), c.shift(1)

        first_bullish = c2 > o2
        harami = (c1 < o1) & (o1 < c2) & (c1 > o2)
        third_bearish = (c < o) & (c < o2)

        detected = (first_bullish & harami & third_bearish)
        result = pd.Series(0, index=o.index, name="three_inside_down")
        result[detected] = -1
        return {"three_inside_down": result}


# =============================================================================
# Multi-Bar Patterns
# =============================================================================


class InsideBar(IndicatorInterface):
    """Inside bar pattern detection.

    Current bar's range is completely contained within the previous
    bar's range. Signals consolidation and potential breakout.

    References: [KB-07], [TSR], [NETPICKS]
    """

    _data = ["high", "low"]
    _params = []
    _outputs = ["inside_bar"]

    @classmethod
    def _compute(cls, data, params):
        h, l = data["high"], data["low"]
        prev_h, prev_l = h.shift(1), l.shift(1)

        detected = ((h < prev_h) & (l > prev_l)).astype(int)
        return {"inside_bar": pd.Series(detected, index=h.index, name="inside_bar")}


class OutsideBar(IndicatorInterface):
    """Outside bar pattern detection.

    Current bar's range completely engulfs the previous bar's range.
    Signals increased volatility and potential reversal or continuation.

    References: [KB-07], [TSR]
    """

    _data = ["high", "low"]
    _params = []
    _outputs = ["outside_bar"]

    @classmethod
    def _compute(cls, data, params):
        h, l = data["high"], data["low"]
        prev_h, prev_l = h.shift(1), l.shift(1)

        detected = ((h > prev_h) & (l < prev_l)).astype(int)
        return {"outside_bar": pd.Series(detected, index=h.index, name="outside_bar")}


class PinBar(IndicatorInterface):
    """Pin bar pattern detection.

    A bar with a long dominant wick and body positioned at one end of
    the range. Returns 1 for bullish (long lower wick), -1 for bearish.

    References: [KB-07], [TSR], [PRICEACTION]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["wick_ratio", "body_position"]
    _outputs = ["pin_bar"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        body = candle_body(o, c)
        rng = candle_range(h, l)
        uw = upper_wick(o, h, c)
        lw = lower_wick(o, l, c)
        wr = params["wick_ratio"]
        bp = params["body_position"]

        has_body = body > 0
        body_bottom = pd.concat([o, c], axis=1).min(axis=1)
        body_top = pd.concat([o, c], axis=1).max(axis=1)

        bullish = has_body & (lw >= body * wr) & (body_bottom > l + rng * (1 - bp))
        bearish = has_body & (uw >= body * wr) & (body_top < h - rng * (1 - bp))

        result = pd.Series(0, index=o.index, name="pin_bar")
        result[bullish] = 1
        result[bearish] = -1
        return {"pin_bar": result}


class TwoBarReversal(IndicatorInterface):
    """Two-bar reversal pattern detection.

    Two consecutive bars closing in opposite directions where the second
    bar takes out an extreme of the first. Returns 1 for bullish, -1 for bearish.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {
            'close_proximity': float (default 0.25) - How close the close must be to the high/low, as a fraction of the bar's range. Range: 0.1-0.5. Lower values are stricter (close must be nearer the extreme).
        }

    References: [KB-07], [TSR], [DAILYFOREX]
    """

    _data = ["open", "high", "low", "close"]
    _params = ["close_proximity"]
    _outputs = ["two_bar_reversal"]

    @classmethod
    def _compute(cls, data, params):
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        rng = candle_range(h, l)
        prev_o, prev_h, prev_l, prev_c = o.shift(1), h.shift(1), l.shift(1), c.shift(1)
        prev_rng = rng.shift(1)

        # Close near high/low: within close_proximity fraction of the extreme
        close_proximity = params.get("close_proximity", 0.25)
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
        return {"two_bar_reversal": result}


class NarrowRange(IndicatorInterface):
    """Narrow range pattern detection (NR4/NR7).

    Detects when the current bar has the smallest range within the
    window period. Default window=7 gives NR7; use 4 for NR4.

    References: [CRABEL], [KB-07], [CHARTSCHOOL-NR7], [BULKOWSKI]
    """

    _data = ["high", "low"]
    _params = ["window"]
    _outputs = ["narrow_range"]

    @classmethod
    def _compute(cls, data, params):
        h, l = data["high"], data["low"]
        rng = candle_range(h, l)
        window = params["window"]

        # Current range must be strictly less than all previous N ranges
        rolling_min = rng.shift(1).rolling(window=window - 1, min_periods=window - 1).min()
        detected = (rng < rolling_min).astype(int)
        # NaN rows get 0
        detected = detected.fillna(0).astype(int)
        return {"narrow_range": pd.Series(detected, index=h.index, name="narrow_range")}
