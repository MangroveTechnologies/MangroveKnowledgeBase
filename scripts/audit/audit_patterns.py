#!/usr/bin/env python3
"""OBSOLETE -- will not import: the 27 pattern indicator classes it depends on were
removed, and pattern detection now lives as private detectors in
`mangrove_kb.signals.pattern`; this needs rewriting against the signals.

Audit pattern indicators using synthetic OHLC tests and BTC daily data.

Since pattern indicators output discrete values (0, 1, -1) and have no
numerical reference library, this audit uses:
  1. Synthetic positive tests: crafted OHLC data that SHOULD trigger each pattern
  2. Synthetic negative tests: crafted OHLC data that should NOT trigger
  3. BTC daily data: run each pattern and verify detection rates are reasonable
"""
import sys
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from audit import load_btc_daily, RESULTS_DIR

# Pattern indicator classes
from mangrove_kb.indicators.pattern_indicators import (
    Doji, LongLeggedDoji, DragonflyDoji, GravestoneDoji,
    Hammer, HangingMan, InvertedHammer, ShootingStar,
    Marubozu, SpinningTop,
    Engulfing, Harami, PiercingLine, DarkCloudCover,
    TweezerTops, TweezerBottoms,
    MorningStar, EveningStar,
    ThreeWhiteSoldiers, ThreeBlackCrows,
    ThreeInsideUp, ThreeInsideDown,
    InsideBar, OutsideBar, PinBar, TwoBarReversal,
    NarrowRange,
)


# ---------------------------------------------------------------------------
# Data result container
# ---------------------------------------------------------------------------

@dataclass
class PatternAuditResult:
    pattern_name: str
    positive_test: bool          # synthetic pattern detected correctly
    negative_test: bool          # non-pattern correctly rejected
    btc_detections: int          # count on real data
    btc_total_bars: int
    detection_rate: float
    pass_fail: bool
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern_name,
            "positive_test": self.positive_test,
            "negative_test": self.negative_test,
            "btc_detections": self.btc_detections,
            "btc_total_bars": self.btc_total_bars,
            "detection_rate": f"{self.detection_rate:.2%}",
            "pass": self.pass_fail,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Helper: build OHLC dict from arrays
# ---------------------------------------------------------------------------

def make_data(opens, highs, lows, closes):
    """Build the data dict expected by IndicatorInterface.compute()."""
    return {
        "open": pd.Series(opens, dtype=float),
        "high": pd.Series(highs, dtype=float),
        "low": pd.Series(lows, dtype=float),
        "close": pd.Series(closes, dtype=float),
    }


def make_oc(opens, closes):
    """Build data dict with only open/close (for Engulfing, Harami, etc.)."""
    return {
        "open": pd.Series(opens, dtype=float),
        "close": pd.Series(closes, dtype=float),
    }


def make_hl(highs, lows):
    """Build data dict with only high/low (for InsideBar, OutsideBar, NarrowRange)."""
    return {
        "high": pd.Series(highs, dtype=float),
        "low": pd.Series(lows, dtype=float),
    }


def last_val(result_dict, key):
    """Get the last value from a result series."""
    return int(result_dict[key].iloc[-1])


# ---------------------------------------------------------------------------
# Synthetic test definitions for each pattern
# ---------------------------------------------------------------------------

def test_doji():
    """Doji: body <= range * 0.1, range > 0."""
    # Positive: open=100, close=100.05, high=105, low=95 => body=0.05, range=10, ratio=0.005
    pos = Doji.compute(make_data([100], [105], [95], [100.05]), {"body_threshold": 0.1})
    p = last_val(pos, "doji") == 1
    # Negative: open=100, close=108, high=110, low=95 => body=8, range=15, ratio=0.533
    neg = Doji.compute(make_data([100], [110], [95], [108]), {"body_threshold": 0.1})
    n = last_val(neg, "doji") == 0
    return p, n


def test_long_legged_doji():
    """LongLeggedDoji: doji + both wicks >= range * 0.3."""
    # Positive: open=100, close=100.05, high=106, low=94 => body=0.05, range=12
    #   upper_wick = 106 - 100.05 = 5.95, lower_wick = 100 - 94 = 6
    #   uw/range = 0.496, lw/range = 0.5 => both >= 0.3
    pos = LongLeggedDoji.compute(
        make_data([100], [106], [94], [100.05]),
        {"body_threshold": 0.1, "wick_threshold": 0.3},
    )
    p = last_val(pos, "long_legged_doji") == 1
    # Negative: body too large
    neg = LongLeggedDoji.compute(
        make_data([96], [106], [94], [104]),
        {"body_threshold": 0.1, "wick_threshold": 0.3},
    )
    n = last_val(neg, "long_legged_doji") == 0
    return p, n


def test_dragonfly_doji():
    """DragonflyDoji: doji + small upper wick + long lower wick > body."""
    # Positive: open=100, close=100.05, high=100.2, low=90
    #   body=0.05, range=10.2, uw=100.2-100.05=0.15, lw=100-90=10
    #   body/range=0.005 (<0.1), uw/range=0.015 (<0.1), lw>body
    pos = DragonflyDoji.compute(
        make_data([100], [100.2], [90], [100.05]),
        {"body_threshold": 0.1, "upper_wick_max": 0.1},
    )
    p = last_val(pos, "dragonfly_doji") == 1
    # Negative: large upper wick (gravestone shape)
    neg = DragonflyDoji.compute(
        make_data([100], [110], [99.5], [100.05]),
        {"body_threshold": 0.1, "upper_wick_max": 0.1},
    )
    n = last_val(neg, "dragonfly_doji") == 0
    return p, n


def test_gravestone_doji():
    """GravestoneDoji: doji + small lower wick + long upper wick > body."""
    # Positive: open=100, close=100.05, high=110, low=99.9
    #   body=0.05, range=10.1, lw=min(100,100.05)-99.9=0.1, uw=110-100.05=9.95
    #   body/range=0.005, lw/range=0.01, uw>body
    pos = GravestoneDoji.compute(
        make_data([100], [110], [99.9], [100.05]),
        {"body_threshold": 0.1, "lower_wick_max": 0.1},
    )
    p = last_val(pos, "gravestone_doji") == 1
    # Negative: large lower wick (dragonfly shape)
    neg = GravestoneDoji.compute(
        make_data([100], [100.2], [90], [100.05]),
        {"body_threshold": 0.1, "lower_wick_max": 0.1},
    )
    n = last_val(neg, "gravestone_doji") == 0
    return p, n


def test_hammer():
    """Hammer: body>0, lower_wick >= body*2, upper_wick <= body*0.5."""
    # Positive: open=100, close=101, high=101.3, low=96
    #   body=1, uw=101.3-101=0.3, lw=100-96=4
    #   lw>=body*2 (4>=2), uw<=body*0.5 (0.3<=0.5)
    pos = Hammer.compute(
        make_data([100], [101.3], [96], [101]),
        {"wick_ratio": 2.0, "upper_wick_max": 0.5},
    )
    p = last_val(pos, "hammer") == 1
    # Negative: large upper wick
    neg = Hammer.compute(
        make_data([100], [108], [99], [101]),
        {"wick_ratio": 2.0, "upper_wick_max": 0.5},
    )
    n = last_val(neg, "hammer") == 0
    return p, n


def test_hanging_man():
    """HangingMan: same shape as Hammer (delegates)."""
    # Positive: same hammer shape
    pos = HangingMan.compute(
        make_data([100], [101.3], [96], [101]),
        {"wick_ratio": 2.0, "upper_wick_max": 0.5},
    )
    p = last_val(pos, "hanging_man") == 1
    # Negative: no lower wick at all
    neg = HangingMan.compute(
        make_data([100], [108], [100], [105]),
        {"wick_ratio": 2.0, "upper_wick_max": 0.5},
    )
    n = last_val(neg, "hanging_man") == 0
    return p, n


def test_inverted_hammer():
    """InvertedHammer: body>0, upper_wick >= body*2, lower_wick <= body*0.1."""
    # Positive: open=100, close=101, high=104, low=99.95
    #   body=1, uw=104-101=3, lw=100-99.95=0.05
    #   uw>=body*2 (3>=2), lw<=body*0.1 (0.05<=0.1)
    pos = InvertedHammer.compute(
        make_data([100], [104], [99.95], [101]),
        {"wick_ratio": 2.0, "lower_wick_max": 0.1},
    )
    p = last_val(pos, "inverted_hammer") == 1
    # Negative: large lower wick
    neg = InvertedHammer.compute(
        make_data([100], [101], [92], [101]),
        {"wick_ratio": 2.0, "lower_wick_max": 0.1},
    )
    n = last_val(neg, "inverted_hammer") == 0
    return p, n


def test_shooting_star():
    """ShootingStar: same shape as InvertedHammer (delegates)."""
    # Positive: same inverted hammer shape
    pos = ShootingStar.compute(
        make_data([100], [104], [99.95], [101]),
        {"wick_ratio": 2.0, "lower_wick_max": 0.1},
    )
    p = last_val(pos, "shooting_star") == 1
    # Negative: short upper wick
    neg = ShootingStar.compute(
        make_data([100], [101], [92], [101]),
        {"wick_ratio": 2.0, "lower_wick_max": 0.1},
    )
    n = last_val(neg, "shooting_star") == 0
    return p, n


def test_marubozu():
    """Marubozu: wicks <= range * 0.05 on both sides. 1=bullish, -1=bearish."""
    # Positive bullish: open=100, close=110, high=110.3, low=99.8
    #   range=10.5, uw=110.3-110=0.3, lw=100-99.8=0.2
    #   uw/range=0.029, lw/range=0.019 => both < 0.05
    pos = Marubozu.compute(
        make_data([100], [110.3], [99.8], [110]),
        {"wick_tolerance": 0.05},
    )
    p_bull = last_val(pos, "marubozu") == 1
    # Positive bearish: open=110, close=100, high=110.3, low=99.8
    pos_bear = Marubozu.compute(
        make_data([110], [110.3], [99.8], [100]),
        {"wick_tolerance": 0.05},
    )
    p_bear = last_val(pos_bear, "marubozu") == -1
    # Negative: large wicks
    neg = Marubozu.compute(
        make_data([100], [115], [90], [105]),
        {"wick_tolerance": 0.05},
    )
    n = last_val(neg, "marubozu") == 0
    p = p_bull and p_bear
    return p, n


def test_spinning_top():
    """SpinningTop: body <= range * 0.3, both wicks >= range * 0.2."""
    # Positive: open=100, close=101, high=104, low=96
    #   body=1, range=8, uw=104-101=3, lw=100-96=4
    #   body/range=0.125 (<0.3), uw/range=0.375 (>=0.2), lw/range=0.5 (>=0.2)
    pos = SpinningTop.compute(
        make_data([100], [104], [96], [101]),
        {"body_max": 0.3, "wick_min": 0.2},
    )
    p = last_val(pos, "spinning_top") == 1
    # Negative: large body (marubozu shape)
    neg = SpinningTop.compute(
        make_data([96], [110.5], [95.5], [110]),
        {"body_max": 0.3, "wick_min": 0.2},
    )
    n = last_val(neg, "spinning_top") == 0
    return p, n


def test_engulfing():
    """Engulfing: 2nd body engulfs 1st. 1=bullish, -1=bearish."""
    # Positive bullish: bar0 bearish (o=105,c=100), bar1 bullish (o=99,c=106)
    #   prev_bear: 100<105, curr_bull: 106>99, o<prev_c (99<100), c>prev_o (106>105)
    pos_bull = Engulfing.compute(
        make_oc([105, 99], [100, 106]),
        {},
    )
    p_bull = last_val(pos_bull, "engulfing") == 1
    # Positive bearish: bar0 bullish (o=100,c=105), bar1 bearish (o=106,c=99)
    pos_bear = Engulfing.compute(
        make_oc([100, 106], [105, 99]),
        {},
    )
    p_bear = last_val(pos_bear, "engulfing") == -1
    # Negative: same direction (both bullish)
    neg = Engulfing.compute(
        make_oc([100, 99], [105, 106]),
        {},
    )
    n = last_val(neg, "engulfing") == 0
    p = p_bull and p_bear
    return p, n


def test_harami():
    """Harami: 2nd body contained in 1st. 1=bullish, -1=bearish."""
    # Positive bullish: bar0 bearish (o=110,c=100), bar1 bullish (o=101,c=109)
    #   prev_bear: 100<110, curr_bull: 109>101, o>prev_c (101>100), c<prev_o (109<110)
    pos_bull = Harami.compute(
        make_oc([110, 101], [100, 109]),
        {},
    )
    p_bull = last_val(pos_bull, "harami") == 1
    # Positive bearish: bar0 bullish (o=100,c=110), bar1 bearish (o=109,c=101)
    pos_bear = Harami.compute(
        make_oc([100, 109], [110, 101]),
        {},
    )
    p_bear = last_val(pos_bear, "harami") == -1
    # Negative: 2nd body not contained (extends beyond 1st)
    neg = Harami.compute(
        make_oc([100, 99], [105, 106]),
        {},
    )
    n = last_val(neg, "harami") == 0
    p = p_bull and p_bear
    return p, n


def test_piercing_line():
    """PiercingLine: bearish -> bullish opening below prior low, closing above midpoint."""
    # bar0: bearish o=110, h=112, l=98, c=100 (midpoint=(110+100)/2=105)
    # bar1: bullish o=97, h=108, l=96, c=108
    #   prev_bear (100<110), curr_bull (108>97), gaps_below (97<98),
    #   penetrates: c > prev_c + (prev_o - prev_c)*0.5 => 108 > 100 + 5 = 105
    pos = PiercingLine.compute(
        make_data([110, 97], [112, 108], [98, 96], [100, 108]),
        {"min_penetration": 0.5},
    )
    p = last_val(pos, "piercing_line") == 1
    # Negative: does not gap below prior low
    neg = PiercingLine.compute(
        make_data([110, 99], [112, 108], [98, 98], [100, 108]),
        {"min_penetration": 0.5},
    )
    n = last_val(neg, "piercing_line") == 0
    return p, n


def test_dark_cloud_cover():
    """DarkCloudCover: bullish -> bearish opening above prior high, closing below midpoint."""
    # bar0: bullish o=100, h=112, l=98, c=110 (midpoint=(100+110)/2=105)
    # bar1: bearish o=113, h=114, l=102, c=103
    #   prev_bull (110>100), curr_bear (103<113), gaps_above (113>112),
    #   penetrates: c < prev_c - (prev_c - prev_o)*0.5 => 103 < 110 - 5 = 105
    pos = DarkCloudCover.compute(
        make_data([100, 113], [112, 114], [98, 102], [110, 103]),
        {"min_penetration": 0.5},
    )
    p = last_val(pos, "dark_cloud_cover") == -1
    # Negative: does not gap above prior high
    neg = DarkCloudCover.compute(
        make_data([100, 111], [112, 114], [98, 102], [110, 103]),
        {"min_penetration": 0.5},
    )
    n = last_val(neg, "dark_cloud_cover") == 0
    return p, n


def test_tweezer_tops():
    """TweezerTops: matching highs, prev bullish, curr bearish."""
    # Need 20+ bars for rolling avg_rng. Use 21 bars of context + 2 pattern bars.
    # Fill 21 context bars with range=10, then pattern bars at end.
    n_context = 21
    opens = [100.0] * n_context + [100.0, 108.0]
    highs = [110.0] * n_context + [110.0, 110.0]   # matching highs
    lows = [100.0] * n_context + [99.0, 102.0]
    closes = [105.0] * n_context + [108.0, 102.0]   # prev bull, curr bear
    # avg_rng ~ 10, tolerance=0.01, |110-110|=0 <= 10*0.01=0.1
    pos = TweezerTops.compute(
        make_data(opens, highs, lows, closes),
        {"tolerance": 0.01},
    )
    p = last_val(pos, "tweezer_tops") == -1
    # Negative: highs differ by a lot
    neg_highs = [110.0] * n_context + [110.0, 115.0]
    neg = TweezerTops.compute(
        make_data(opens, neg_highs, lows, closes),
        {"tolerance": 0.01},
    )
    n = last_val(neg, "tweezer_tops") == 0
    return p, n


def test_tweezer_bottoms():
    """TweezerBottoms: matching lows, prev bearish, curr bullish."""
    n_context = 21
    opens = [100.0] * n_context + [108.0, 100.0]
    highs = [110.0] * n_context + [109.0, 108.0]
    lows = [100.0] * n_context + [100.0, 100.0]   # matching lows
    closes = [105.0] * n_context + [102.0, 106.0]   # prev bear, curr bull
    pos = TweezerBottoms.compute(
        make_data(opens, highs, lows, closes),
        {"tolerance": 0.01},
    )
    p = last_val(pos, "tweezer_bottoms") == 1
    # Negative: lows differ by a lot
    neg_lows = [100.0] * n_context + [100.0, 95.0]
    neg = TweezerBottoms.compute(
        make_data(opens, highs, neg_lows, closes),
        {"tolerance": 0.01},
    )
    n = last_val(neg, "tweezer_bottoms") == 0
    return p, n


def test_morning_star():
    """MorningStar: bearish, small star, bullish closing above midpoint of first."""
    # bar0: bearish o=110, h=112, l=98, c=100 (midpoint=105)
    # bar1: small star o=99, h=100, l=98, c=99.5 (body=0.5, range=2, ratio=0.25 <0.3)
    # bar2: bullish o=100, h=112, l=99, c=108 (c>105)
    pos = MorningStar.compute(
        make_data([110, 99, 100], [112, 100, 112], [98, 98, 99], [100, 99.5, 108]),
        {"body_threshold": 0.3},
    )
    p = last_val(pos, "morning_star") == 1
    # Negative: star body too large
    neg = MorningStar.compute(
        make_data([110, 95, 100], [112, 107, 112], [98, 94, 99], [100, 106, 108]),
        {"body_threshold": 0.3},
    )
    n = last_val(neg, "morning_star") == 0
    return p, n


def test_evening_star():
    """EveningStar: bullish, small star, bearish closing below midpoint of first."""
    # bar0: bullish o=100, h=112, l=98, c=110 (midpoint=105)
    # bar1: small star o=111, h=112, l=110, c=111.3 (body=0.3, range=2, ratio=0.15 <0.3)
    # bar2: bearish o=109, h=110, l=98, c=103 (c<105)
    pos = EveningStar.compute(
        make_data([100, 111, 109], [112, 112, 110], [98, 110, 98], [110, 111.3, 103]),
        {"body_threshold": 0.3},
    )
    p = last_val(pos, "evening_star") == -1
    # Negative: third candle closes above midpoint
    neg = EveningStar.compute(
        make_data([100, 111, 109], [112, 112, 115], [98, 110, 108], [110, 111.3, 112]),
        {"body_threshold": 0.3},
    )
    n = last_val(neg, "evening_star") == 0
    return p, n


def test_three_white_soldiers():
    """ThreeWhiteSoldiers: 3 bullish, higher closes, opens within prior body, strong bodies."""
    # bar0: o=100, h=110, l=99, c=109 (body=9, range=11, ratio=0.818)
    # bar1: o=103, h=115, l=102, c=114 (opens within [100,109], body=11, range=13, 0.846)
    # bar2: o=107, h=122, l=106, c=121 (opens within [103,114], body=14, range=16, 0.875)
    # All bullish, higher closes (109<114<121)
    pos = ThreeWhiteSoldiers.compute(
        make_data(
            [100, 103, 107], [110, 115, 122], [99, 102, 106], [109, 114, 121]
        ),
        {"min_body_ratio": 0.5},
    )
    p = last_val(pos, "three_white_soldiers") == 1
    # Negative: one candle is bearish
    neg = ThreeWhiteSoldiers.compute(
        make_data(
            [100, 114, 107], [110, 115, 122], [99, 102, 106], [109, 103, 121]
        ),
        {"min_body_ratio": 0.5},
    )
    n = last_val(neg, "three_white_soldiers") == 0
    return p, n


def test_three_black_crows():
    """ThreeBlackCrows: 3 bearish, lower closes, opens within prior body, strong bodies."""
    # bar0: o=120, h=121, l=110, c=111 (body=9, range=11, 0.818)
    # bar1: o=117, h=118, l=105, c=106 (opens within [111,120], body=11, range=13, 0.846)
    # bar2: o=113, h=114, l=98, c=99 (opens within [106,117], body=14, range=16, 0.875)
    # All bearish, lower closes (111>106>99)
    pos = ThreeBlackCrows.compute(
        make_data(
            [120, 117, 113], [121, 118, 114], [110, 105, 98], [111, 106, 99]
        ),
        {"min_body_ratio": 0.5},
    )
    p = last_val(pos, "three_black_crows") == -1
    # Negative: one candle is bullish
    neg = ThreeBlackCrows.compute(
        make_data(
            [120, 106, 113], [121, 118, 114], [110, 105, 98], [111, 117, 99]
        ),
        {"min_body_ratio": 0.5},
    )
    n = last_val(neg, "three_black_crows") == 0
    return p, n


def test_three_inside_up():
    """ThreeInsideUp: bearish, bullish harami, bullish closing above first open."""
    # bar0: bearish o=110, c=100
    # bar1: bullish harami o=101, c=109 (o>prev_c=100, c<prev_o=110)
    # bar2: bullish o=105, c=112 (c>o2=110)
    pos = ThreeInsideUp.compute(
        make_oc([110, 101, 105], [100, 109, 112]),
        {},
    )
    p = last_val(pos, "three_inside_up") == 1
    # Negative: third candle does not close above first open
    neg = ThreeInsideUp.compute(
        make_oc([110, 101, 105], [100, 109, 108]),
        {},
    )
    n = last_val(neg, "three_inside_up") == 0
    return p, n


def test_three_inside_down():
    """ThreeInsideDown: bullish, bearish harami, bearish closing below first open."""
    # bar0: bullish o=100, c=110
    # bar1: bearish harami o=109, c=101 (o<prev_c=110, c>prev_o=100)
    # bar2: bearish o=105, c=98 (c<o2=100)
    pos = ThreeInsideDown.compute(
        make_oc([100, 109, 105], [110, 101, 98]),
        {},
    )
    p = last_val(pos, "three_inside_down") == -1
    # Negative: third candle does not close below first open
    neg = ThreeInsideDown.compute(
        make_oc([100, 109, 105], [110, 101, 102]),
        {},
    )
    n = last_val(neg, "three_inside_down") == 0
    return p, n


def test_inside_bar():
    """InsideBar: current h < prev_h AND current l > prev_l."""
    # bar0: h=110, l=90
    # bar1: h=105, l=95 (inside)
    pos = InsideBar.compute(
        make_hl([110, 105], [90, 95]),
        {},
    )
    p = last_val(pos, "inside_bar") == 1
    # Negative: current bar extends beyond
    neg = InsideBar.compute(
        make_hl([110, 115], [90, 85]),
        {},
    )
    n = last_val(neg, "inside_bar") == 0
    return p, n


def test_outside_bar():
    """OutsideBar: current h > prev_h AND current l < prev_l."""
    # bar0: h=105, l=95
    # bar1: h=110, l=90 (outside)
    pos = OutsideBar.compute(
        make_hl([105, 110], [95, 90]),
        {},
    )
    p = last_val(pos, "outside_bar") == 1
    # Negative: current bar is inside
    neg = OutsideBar.compute(
        make_hl([110, 105], [90, 95]),
        {},
    )
    n = last_val(neg, "outside_bar") == 0
    return p, n


def test_pin_bar():
    """PinBar: long dominant wick, body at one end. 1=bullish, -1=bearish."""
    # Bullish: long lower wick, body near top
    # o=108, h=110, l=96, c=109 => body=1, lw=108-96=12, uw=110-109=1
    #   has_body, lw>=body*2 (12>=2), body_bottom=108, body needs to be > l + rng*(1-0.33) = 96+14*0.67=105.38
    #   108 > 105.38 => bullish
    pos_bull = PinBar.compute(
        make_data([108], [110], [96], [109]),
        {"wick_ratio": 2.0, "body_position": 0.33},
    )
    p_bull = last_val(pos_bull, "pin_bar") == 1
    # Bearish: long upper wick, body near bottom
    # o=102, h=114, l=100, c=101 => body=1, uw=114-102=12, lw=101-100=1
    #   body_top=102, needs body_top < h - rng*(1-0.33) = 114-14*0.67 = 104.62
    #   102 < 104.62 => bearish
    pos_bear = PinBar.compute(
        make_data([102], [114], [100], [101]),
        {"wick_ratio": 2.0, "body_position": 0.33},
    )
    p_bear = last_val(pos_bear, "pin_bar") == -1
    # Negative: body in middle, balanced wicks
    neg = PinBar.compute(
        make_data([103], [110], [96], [104]),
        {"wick_ratio": 2.0, "body_position": 0.33},
    )
    n = last_val(neg, "pin_bar") == 0
    p = p_bull and p_bear
    return p, n


def test_two_bar_reversal():
    """TwoBarReversal: opposite direction bars with specific close positions."""
    # Bullish: prev bear closing near low, curr bull closing near high,
    #   l <= prev_l, c > prev_o
    # bar0: o=110, h=112, l=100, c=101 (bear, close near low: 101-100=1 <= 12*0.25=3)
    # bar1: o=99, h=115, l=99, c=114 (bull, close near high: 115-114=1 <= 16*0.25=4,
    #   l<=prev_l: 99<=100, c>prev_o: 114>110)
    pos_bull = TwoBarReversal.compute(
        make_data([110, 99], [112, 115], [100, 99], [101, 114]),
        {},
    )
    p_bull = last_val(pos_bull, "two_bar_reversal") == 1
    # Bearish: prev bull closing near high, curr bear closing near low
    # bar0: o=100, h=112, l=99, c=111 (bull, close near high: 112-111=1 <= 13*0.25=3.25)
    # bar1: o=113, h=113, l=96, c=97 (bear, close near low: 97-96=1 <= 17*0.25=4.25,
    #   h>=prev_h: 113>=112, c<prev_o: 97<100)
    pos_bear = TwoBarReversal.compute(
        make_data([100, 113], [112, 113], [99, 96], [111, 97]),
        {},
    )
    p_bear = last_val(pos_bear, "two_bar_reversal") == -1
    # Negative: both bars same direction
    neg = TwoBarReversal.compute(
        make_data([100, 105], [112, 115], [99, 104], [110, 114]),
        {},
    )
    n = last_val(neg, "two_bar_reversal") == 0
    p = p_bull and p_bear
    return p, n


def test_narrow_range():
    """NarrowRange: current bar has smallest range in window."""
    # 7-bar window. Need 7+ bars. Bar at idx 7 has range < all prev 6.
    # Context bars with range=10, then target bar with range=1
    highs = [110, 112, 111, 113, 110, 112, 111, 100.5]
    lows = [100, 102, 101, 103, 100, 102, 101, 100.0]
    # ranges: 10, 10, 10, 10, 10, 10, 10, 0.5
    # rolling_min of shift(1) over window-1=6: min of [10,10,10,10,10,10] = 10
    # 0.5 < 10 => detected
    pos = NarrowRange.compute(
        make_hl(highs, lows),
        {"window": 7},
    )
    p = last_val(pos, "narrow_range") == 1
    # Negative: current bar has largest range
    neg_highs = [105, 104, 103, 106, 105, 104, 103, 120]
    neg_lows = [100, 101, 100, 101, 100, 101, 100, 90]
    neg = NarrowRange.compute(
        make_hl(neg_highs, neg_lows),
        {"window": 7},
    )
    n = last_val(neg, "narrow_range") == 0
    return p, n


# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

PATTERN_TESTS = {
    # Single-candle
    "Doji": test_doji,
    "LongLeggedDoji": test_long_legged_doji,
    "DragonflyDoji": test_dragonfly_doji,
    "GravestoneDoji": test_gravestone_doji,
    "Hammer": test_hammer,
    "HangingMan": test_hanging_man,
    "InvertedHammer": test_inverted_hammer,
    "ShootingStar": test_shooting_star,
    "Marubozu": test_marubozu,
    "SpinningTop": test_spinning_top,
    # Two-candle
    "Engulfing": test_engulfing,
    "Harami": test_harami,
    "PiercingLine": test_piercing_line,
    "DarkCloudCover": test_dark_cloud_cover,
    "TweezerTops": test_tweezer_tops,
    "TweezerBottoms": test_tweezer_bottoms,
    # Three-candle
    "MorningStar": test_morning_star,
    "EveningStar": test_evening_star,
    "ThreeWhiteSoldiers": test_three_white_soldiers,
    "ThreeBlackCrows": test_three_black_crows,
    "ThreeInsideUp": test_three_inside_up,
    "ThreeInsideDown": test_three_inside_down,
    # Multi-bar
    "InsideBar": test_inside_bar,
    "OutsideBar": test_outside_bar,
    "PinBar": test_pin_bar,
    "TwoBarReversal": test_two_bar_reversal,
    "NarrowRange": test_narrow_range,
}

# Default params for BTC run (same as used in signals/pattern.py)
BTC_PARAMS = {
    "Doji": {"body_threshold": 0.1},
    "LongLeggedDoji": {"body_threshold": 0.1, "wick_threshold": 0.3},
    "DragonflyDoji": {"body_threshold": 0.1, "upper_wick_max": 0.1},
    "GravestoneDoji": {"body_threshold": 0.1, "lower_wick_max": 0.1},
    "Hammer": {"wick_ratio": 2.0, "upper_wick_max": 0.5},
    "HangingMan": {"wick_ratio": 2.0, "upper_wick_max": 0.5},
    "InvertedHammer": {"wick_ratio": 2.0, "lower_wick_max": 0.1},
    "ShootingStar": {"wick_ratio": 2.0, "lower_wick_max": 0.1},
    "Marubozu": {"wick_tolerance": 0.05},
    "SpinningTop": {"body_max": 0.3, "wick_min": 0.2},
    "Engulfing": {},
    "Harami": {},
    "PiercingLine": {"min_penetration": 0.5},
    "DarkCloudCover": {"min_penetration": 0.5},
    "TweezerTops": {"tolerance": 0.01},
    "TweezerBottoms": {"tolerance": 0.01},
    "MorningStar": {"body_threshold": 0.3},
    "EveningStar": {"body_threshold": 0.3},
    "ThreeWhiteSoldiers": {"min_body_ratio": 0.5},
    "ThreeBlackCrows": {"min_body_ratio": 0.5},
    "ThreeInsideUp": {},
    "ThreeInsideDown": {},
    "InsideBar": {},
    "OutsideBar": {},
    "PinBar": {"wick_ratio": 2.0, "body_position": 0.33},
    "TwoBarReversal": {},
    "NarrowRange": {"window": 7},
}

# Indicator class lookup
PATTERN_CLASSES = {
    "Doji": Doji,
    "LongLeggedDoji": LongLeggedDoji,
    "DragonflyDoji": DragonflyDoji,
    "GravestoneDoji": GravestoneDoji,
    "Hammer": Hammer,
    "HangingMan": HangingMan,
    "InvertedHammer": InvertedHammer,
    "ShootingStar": ShootingStar,
    "Marubozu": Marubozu,
    "SpinningTop": SpinningTop,
    "Engulfing": Engulfing,
    "Harami": Harami,
    "PiercingLine": PiercingLine,
    "DarkCloudCover": DarkCloudCover,
    "TweezerTops": TweezerTops,
    "TweezerBottoms": TweezerBottoms,
    "MorningStar": MorningStar,
    "EveningStar": EveningStar,
    "ThreeWhiteSoldiers": ThreeWhiteSoldiers,
    "ThreeBlackCrows": ThreeBlackCrows,
    "ThreeInsideUp": ThreeInsideUp,
    "ThreeInsideDown": ThreeInsideDown,
    "InsideBar": InsideBar,
    "OutsideBar": OutsideBar,
    "PinBar": PinBar,
    "TwoBarReversal": TwoBarReversal,
    "NarrowRange": NarrowRange,
}

# Which data keys each pattern needs for BTC run
PATTERN_DATA_KEYS = {
    "Doji": ["open", "high", "low", "close"],
    "LongLeggedDoji": ["open", "high", "low", "close"],
    "DragonflyDoji": ["open", "high", "low", "close"],
    "GravestoneDoji": ["open", "high", "low", "close"],
    "Hammer": ["open", "high", "low", "close"],
    "HangingMan": ["open", "high", "low", "close"],
    "InvertedHammer": ["open", "high", "low", "close"],
    "ShootingStar": ["open", "high", "low", "close"],
    "Marubozu": ["open", "high", "low", "close"],
    "SpinningTop": ["open", "high", "low", "close"],
    "Engulfing": ["open", "close"],
    "Harami": ["open", "close"],
    "PiercingLine": ["open", "high", "low", "close"],
    "DarkCloudCover": ["open", "high", "low", "close"],
    "TweezerTops": ["open", "high", "low", "close"],
    "TweezerBottoms": ["open", "high", "low", "close"],
    "MorningStar": ["open", "high", "low", "close"],
    "EveningStar": ["open", "high", "low", "close"],
    "ThreeWhiteSoldiers": ["open", "high", "low", "close"],
    "ThreeBlackCrows": ["open", "high", "low", "close"],
    "ThreeInsideUp": ["open", "close"],
    "ThreeInsideDown": ["open", "close"],
    "InsideBar": ["high", "low"],
    "OutsideBar": ["high", "low"],
    "PinBar": ["open", "high", "low", "close"],
    "TwoBarReversal": ["open", "high", "low", "close"],
    "NarrowRange": ["high", "low"],
}

# Reasonable detection rate ranges for BTC daily (approximate)
# Notes on crypto-specific ranges:
#   - DragonflyDoji/GravestoneDoji: strict wick constraints (0.1) make these very rare
#   - InvertedHammer/ShootingStar: lower_wick_max=0.1 (vs body) is extremely strict
#   - SpinningTop: body_max=0.3 captures many indecision candles in volatile BTC
#   - TweezerTops/Bottoms: tolerance=0.01 vs avg range makes exact matching rare on crypto
#   - PiercingLine/DarkCloudCover: gap requirement (open beyond prior high/low) is rare on
#     24/7 crypto markets with no overnight gaps
EXPECTED_RATE_RANGES = {
    "Doji": (0.02, 0.30),
    "LongLeggedDoji": (0.01, 0.15),
    "DragonflyDoji": (0.0, 0.15),          # strict upper_wick_max=0.1 makes this rare
    "GravestoneDoji": (0.0, 0.15),          # strict lower_wick_max=0.1 makes this rare
    "Hammer": (0.01, 0.15),
    "HangingMan": (0.01, 0.15),
    "InvertedHammer": (0.0, 0.10),          # strict lower_wick_max=0.1 vs body
    "ShootingStar": (0.0, 0.10),            # strict lower_wick_max=0.1 vs body
    "Marubozu": (0.001, 0.15),
    "SpinningTop": (0.01, 0.35),            # body_max=0.3 is common in volatile BTC
    "Engulfing": (0.01, 0.15),
    "Harami": (0.01, 0.15),
    "PiercingLine": (0.0, 0.05),            # gap requirement rare on 24/7 crypto
    "DarkCloudCover": (0.0, 0.05),          # gap requirement rare on 24/7 crypto
    "TweezerTops": (0.0, 0.15),             # tight tolerance makes matching rare
    "TweezerBottoms": (0.0, 0.15),          # tight tolerance makes matching rare
    "MorningStar": (0.001, 0.10),
    "EveningStar": (0.001, 0.10),
    "ThreeWhiteSoldiers": (0.0, 0.05),
    "ThreeBlackCrows": (0.0, 0.05),
    "ThreeInsideUp": (0.001, 0.10),
    "ThreeInsideDown": (0.001, 0.10),
    "InsideBar": (0.05, 0.30),
    "OutsideBar": (0.02, 0.20),
    "PinBar": (0.01, 0.20),
    "TwoBarReversal": (0.001, 0.10),
    "NarrowRange": (0.01, 0.20),
}


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

def run_audit():
    """Run synthetic tests and BTC data tests for all 27 pattern indicators."""
    print("=" * 80)
    print("PATTERN INDICATOR AUDIT")
    print("=" * 80)
    print()

    # Load BTC data
    print("Loading BTC daily data...")
    df = load_btc_daily()
    btc_data = {col: df[col] for col in ["open", "high", "low", "close"]}
    total_bars = len(df)
    print(f"  {total_bars} bars loaded")
    print()

    results: list[PatternAuditResult] = []

    # Run each pattern
    for name, test_fn in PATTERN_TESTS.items():
        # --- Synthetic tests ---
        try:
            pos, neg = test_fn()
        except Exception as e:
            pos, neg = False, False
            print(f"  ERROR in synthetic test for {name}: {e}")

        # --- BTC data test ---
        cls = PATTERN_CLASSES[name]
        params = BTC_PARAMS[name]
        data_keys = PATTERN_DATA_KEYS[name]
        data_subset = {k: btc_data[k] for k in data_keys}

        try:
            btc_result = cls.compute(data_subset, params)
            output_key = cls._outputs[0]
            series = btc_result[output_key]
            # Count non-zero detections (1 or -1)
            detections = int((series != 0).sum())
        except Exception as e:
            detections = -1
            print(f"  ERROR in BTC test for {name}: {e}")

        detection_rate = detections / total_bars if detections >= 0 else 0.0

        # Check if detection rate is in expected range
        rate_lo, rate_hi = EXPECTED_RATE_RANGES.get(name, (0.0, 1.0))
        rate_ok = rate_lo <= detection_rate <= rate_hi

        notes_parts = []
        if not pos:
            notes_parts.append("POSITIVE synthetic test failed")
        if not neg:
            notes_parts.append("NEGATIVE synthetic test failed")
        if not rate_ok:
            notes_parts.append(
                f"Detection rate {detection_rate:.2%} outside expected "
                f"[{rate_lo:.1%}, {rate_hi:.1%}]"
            )
        if detections < 0:
            notes_parts.append("BTC compute raised an error")

        pass_fail = pos and neg and rate_ok and detections >= 0

        result = PatternAuditResult(
            pattern_name=name,
            positive_test=pos,
            negative_test=neg,
            btc_detections=max(detections, 0),
            btc_total_bars=total_bars,
            detection_rate=detection_rate,
            pass_fail=pass_fail,
            notes="; ".join(notes_parts),
        )
        results.append(result)

    # --- Print results table ---
    print()
    print(f"{'Pattern':<25} {'Pos':>5} {'Neg':>5} {'BTC Det':>8} {'Rate':>8} {'Result':>8}  Notes")
    print("-" * 100)
    for r in results:
        pos_str = "OK" if r.positive_test else "FAIL"
        neg_str = "OK" if r.negative_test else "FAIL"
        det_str = str(r.btc_detections) if r.btc_detections >= 0 else "ERR"
        rate_str = f"{r.detection_rate:.2%}"
        status = "PASS" if r.pass_fail else "FAIL"
        notes = r.notes[:40] if r.notes else ""
        print(
            f"{r.pattern_name:<25} {pos_str:>5} {neg_str:>5} {det_str:>8} "
            f"{rate_str:>8} {status:>8}  {notes}"
        )

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.pass_fail)
    failed = total - passed
    print()
    print(f"SUMMARY: {passed}/{total} PASS, {failed} FAIL")
    print()

    # --- Generate markdown report ---
    report = generate_pattern_report(results, total_bars)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "pattern_report.md"
    report_path.write_text(report)
    print(f"Report written to {report_path}")

    # Return exit code
    return 0 if failed == 0 else 1


def generate_pattern_report(results: list[PatternAuditResult], total_bars: int) -> str:
    """Generate markdown report for pattern audit results."""
    lines = []
    lines.append("# Pattern Indicator Audit Report")
    lines.append("")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Data**: BTC/USD Daily, {total_bars} bars")
    lines.append(f"**Method**: Synthetic OHLC validation + BTC detection-rate plausibility")
    lines.append("")

    total = len(results)
    passed = sum(1 for r in results if r.pass_fail)
    failed = total - passed

    lines.append(f"## Summary: {passed}/{total} PASS, {failed} FAIL")
    lines.append("")

    # Category groupings
    categories = {
        "Single-Candle": ["Doji", "LongLeggedDoji", "DragonflyDoji", "GravestoneDoji",
                          "Hammer", "HangingMan", "InvertedHammer", "ShootingStar",
                          "Marubozu", "SpinningTop"],
        "Two-Candle": ["Engulfing", "Harami", "PiercingLine", "DarkCloudCover",
                       "TweezerTops", "TweezerBottoms"],
        "Three-Candle": ["MorningStar", "EveningStar", "ThreeWhiteSoldiers",
                         "ThreeBlackCrows", "ThreeInsideUp", "ThreeInsideDown"],
        "Multi-Bar": ["InsideBar", "OutsideBar", "PinBar", "TwoBarReversal", "NarrowRange"],
    }

    # Category summary
    lines.append("| Category | Patterns | Pass | Fail |")
    lines.append("|----------|----------|------|------|")
    for cat, names in categories.items():
        cat_results = [r for r in results if r.pattern_name in names]
        cat_pass = sum(1 for r in cat_results if r.pass_fail)
        cat_fail = len(cat_results) - cat_pass
        lines.append(f"| {cat} | {len(cat_results)} | {cat_pass} | {cat_fail} |")
    lines.append("")

    # Failures section
    failures = [r for r in results if not r.pass_fail]
    if failures:
        lines.append(f"## Failures ({len(failures)})")
        lines.append("")
        for r in failures:
            lines.append(f"### {r.pattern_name} -- FAIL")
            lines.append(f"- Positive test: {'PASS' if r.positive_test else 'FAIL'}")
            lines.append(f"- Negative test: {'PASS' if r.negative_test else 'FAIL'}")
            lines.append(f"- BTC detections: {r.btc_detections}/{r.btc_total_bars} ({r.detection_rate:.2%})")
            if r.notes:
                lines.append(f"- Notes: {r.notes}")
            lines.append("")

    # Full detail table
    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| Pattern | Pos | Neg | BTC Detections | Rate | Status | Notes |")
    lines.append("|---------|-----|-----|----------------|------|--------|-------|")
    for r in results:
        pos = "PASS" if r.positive_test else "FAIL"
        neg = "PASS" if r.negative_test else "FAIL"
        status = "PASS" if r.pass_fail else "**FAIL**"
        notes = r.notes.replace("|", "/") if r.notes else ""
        lines.append(
            f"| {r.pattern_name} | {pos} | {neg} | "
            f"{r.btc_detections}/{r.btc_total_bars} | {r.detection_rate:.2%} | "
            f"{status} | {notes} |"
        )
    lines.append("")

    # BTC detection rate analysis
    lines.append("## BTC Detection Rate Analysis")
    lines.append("")
    lines.append("Expected ranges based on pattern frequency in typical markets:")
    lines.append("")
    for cat, names in categories.items():
        lines.append(f"### {cat}")
        lines.append("")
        for name in names:
            r = next((x for x in results if x.pattern_name == name), None)
            if r:
                lo, hi = EXPECTED_RATE_RANGES[name]
                in_range = "OK" if lo <= r.detection_rate <= hi else "OUT OF RANGE"
                lines.append(
                    f"- **{name}**: {r.btc_detections} detections "
                    f"({r.detection_rate:.2%}) -- expected [{lo:.1%}, {hi:.1%}] -- {in_range}"
                )
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(run_audit())
