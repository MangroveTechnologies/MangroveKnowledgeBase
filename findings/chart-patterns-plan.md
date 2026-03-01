# Chart Patterns Library Plan for MangroveKnowledgeBase

**Date:** 2026-02-25
**Status:** Planning -- no implementation yet
**Author:** Mangrove Technologies

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [Specification](#2-specification)
3. [Architecture](#3-architecture)
4. [Implementation Plan](#4-implementation-plan)
5. [References](#5-references)

---

## 1. Requirements

### 1.1 Purpose

Add candlestick pattern detection and multi-bar pattern recognition to MangroveKnowledgeBase as first-class indicators and signals. This fills a critical gap: the KB has comprehensive chart patterns documentation (`knowledge-base/07-chart-patterns.md`, ~993 lines of theory, detection logic, and pseudocode) but zero pattern detection code.

MangroveAI has a rudimentary `domains/patterns/patterns.py` with 6 basic candlestick patterns (Bullish/Bearish Engulfing, Morning/Evening Star, Three White Soldiers/Three Black Crows). That implementation:

- Is not integrated with the signal/indicator architecture (no `@RuleRegistry.register`, no `IndicatorInterface`, no docstring metadata)
- Only checks the last 3 bars (not vectorized over the DataFrame)
- Returns `dict[str, bool]` instead of `pd.Series` (cannot be used in backtesting over historical data)
- Missing many important patterns (Doji, Hammer, Shooting Star, Harami, Piercing Line, etc.)
- Lives in MangroveAI instead of MangroveKnowledgeBase (wrong location per migration plan)

The new library will be built from scratch in MangroveKnowledgeBase following established conventions, producing ~25 pattern indicator classes and ~30-40 pattern signal functions that plug directly into the existing strategy engine, backtester, and AI copilot without modification to those systems.

### 1.2 Scope

**Phase 1 (this plan):** Candlestick patterns and multi-bar patterns

| Category | Patterns | Count |
|----------|----------|-------|
| Single-candle | Doji (standard, long-legged, dragonfly, gravestone), Hammer, Hanging Man, Inverted Hammer, Shooting Star, Marubozu (bullish, bearish), Spinning Top | 11 |
| Two-candle | Bullish Engulfing, Bearish Engulfing, Bullish Harami, Bearish Harami, Piercing Line, Dark Cloud Cover, Tweezer Tops, Tweezer Bottoms | 8 |
| Three-candle | Morning Star, Evening Star, Three White Soldiers, Three Black Crows, Three Inside Up, Three Inside Down | 6 |
| Multi-bar | Inside Bar, Outside Bar, Pin Bar (bullish, bearish), Two-Bar Reversal (bullish, bearish), NR4, NR7 | 8 |
| **Total** | | **33** |

**Phase 2 (future, out of scope):** Chart formations (Head and Shoulders, Triangles, Flags, Wedges, Double/Triple Tops/Bottoms, Cup and Handle). These require swing point detection, trend line fitting, and fundamentally different algorithms. Phase 1 lays the groundwork by establishing pattern indicator conventions.

**Explicitly out of scope:**

| Excluded | Reason |
|----------|--------|
| TA-Lib integration or references | All TA-Lib references will be removed from MangroveKnowledgeBase. We implement from first principles using NumPy/Pandas only. |
| ML-based pattern recognition | Future work. Requires training data and model infrastructure not yet in place. |
| Pattern visualization | MangroveKnowledgeBase is a compute/metadata library. Visualization belongs in MangroveAI or notebooks. |
| Volume-based pattern confirmation | Volume is used in existing volume signals. Pattern signals focus on price action. Volume confirmation can be composed via strategy rules (1 TRIGGER + 1 FILTER). |

### 1.3 TA-Lib Removal

All references to TA-Lib must be removed from MangroveKnowledgeBase. Current references:

| File | Content | Action |
|------|---------|--------|
| `knowledge-base/07-chart-patterns.md` (lines ~665-695) | Section 7.4 listing 61 TA-Lib CDL functions with `import talib` code example | Replace with reference to MangroveKnowledgeBase's own pattern detection library |
| `knowledge-base/00-table-of-contents.md` (lines ~476-478) | "References TA-Lib candlestick functions" in section description; `TA-Lib` tag | Rewrite to reference MangroveKnowledgeBase pattern indicators; remove TA-Lib tag |

TA-Lib references in MangroveAI and MangroveAI-Research are copies of the KB content and will be updated when those copies are refreshed. The `MangroveResearch/ta-lib-python-master/` directory is a standalone reference library and is not modified.

### 1.4 Consumers

| Consumer | Use Case |
|----------|----------|
| **MangroveAI Strategy Engine** | Pattern signals used as TRIGGER or FILTER in strategies (1 TRIGGER + 1 FILTER constraint) |
| **MangroveAI Backtester** | Vectorized pattern indicators evaluated across historical data for trade generation |
| **MangroveAI AI Copilot** | Recommends pattern-based signals via intent-aware matching; docstring metadata enables discovery |
| **MCP Server (planned)** | Exposes pattern signal metadata and indicator specs to external agents |
| **Signal Explorer Notebook** | Interactive visualization of pattern detection across sample datasets |
| **MangroveKnowledgeBase KB Server** | Updated documentation searchable via FTS5 |

### 1.5 Design Constraints

These are non-negotiable, inherited from the existing architecture:

1. **Indicators are stateless classmethod-based classes** inheriting from `IndicatorInterface` with `_data`, `_params`, `_outputs`, and `_compute()`
2. **Signals are boolean-returning functions** decorated with `@RuleRegistry.register("signal_name")`
3. **Docstrings are the single source of truth** for signal metadata (Type, Requires, Args with Range/Default)
4. **No external dependencies beyond NumPy and Pandas** (the only two runtime dependencies in `pyproject.toml`)
5. **Pattern indicators must return `pd.Series`** (vectorized over the full DataFrame) to be compatible with backtesting
6. **Signals must follow the TRIGGER/FILTER classification** -- TRIGGER for event-based detection ("pattern just appeared"), FILTER for state-based conditions ("pattern appeared within N bars")
7. **Parameter naming follows existing conventions** -- `window` for lookback periods, `threshold` for comparison values
8. **All code goes in MangroveKnowledgeBase**, not MangroveAI

### 1.6 Success Criteria

- [ ] 33 candlestick/multi-bar pattern indicator classes implemented and tested
- [ ] 30-40 pattern signal functions registered in RuleRegistry with full docstring metadata
- [ ] All signals parseable by existing `docstring_parser.py` without modifications
- [ ] All TA-Lib references removed from MangroveKnowledgeBase
- [ ] `knowledge-base/07-chart-patterns.md` updated to reference the new library
- [ ] Existing tests pass; new pattern-specific tests added
- [ ] Signal explorer notebook updated with pattern detection examples
- [ ] MangroveAI can consume pattern signals via `USE_EXTERNAL_KB` toggle with zero changes to strategy engine, backtester, or AI copilot

---

## 2. Specification

### 2.1 Pattern Indicator Return Values

Pattern indicators differ from traditional indicators (RSI returns a continuous series 0-100). Pattern indicators return a categorical series:

| Value | Meaning |
|-------|---------|
| `1` | Bullish pattern detected at this bar |
| `-1` | Bearish pattern detected at this bar |
| `0` | No pattern detected at this bar |

For patterns that are inherently one-directional (e.g., `BullishEngulfing` is always bullish), the output is `1` (detected) or `0` (not detected).

For patterns that have both directions (e.g., `Engulfing` can be bullish or bearish), the indicator returns separate outputs for each direction, or a combined output using the 1/-1/0 convention.

The 1/-1/0 convention is clean and consistent with our existing indicator outputs which return normalized values.

### 2.2 Pattern Indicator Specifications

#### 2.2.1 Single-Candle Pattern Indicators

**Doji**
```
Class: Doji
References: [NISON], [KB-07], [CM45T3R], [LUXALGO], [LINNSOFT]
_data: ["open", "high", "low", "close"]
_params: ["body_threshold"]
_outputs: ["doji"]

body_threshold: Maximum body-to-range ratio to qualify as doji.
  Type: float, Range: 0.01-0.3, Default: 0.1

Detection:
  body = |Close - Open|
  range = High - Low
  doji = 1 if (range > 0 and body <= range * body_threshold) else 0

Output: 1 = doji detected, 0 = no doji

Notes:
  - [NISON] defines doji as "open and close virtually equal" -- qualitative.
  - [KB-07] quantifies as |Close - Open| <= (High - Low) * 0.1 (10% of range).
  - [CM45T3R] uses body < 10% of range -- matches our default.
  - [LUXALGO] uses stricter 5% threshold.
  - [LINNSOFT] uses a different metric: |Close - Open| < 0.50% of min(Close, Open).
  - 10% of range is the balanced default. Stricter markets can use 0.05.
```

**LongLeggedDoji**
```
Class: LongLeggedDoji
References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["body_threshold", "wick_threshold"]
_outputs: ["long_legged_doji"]

body_threshold: Maximum body-to-range ratio. Type: float, Range: 0.01-0.3, Default: 0.1
wick_threshold: Minimum wick-to-range ratio for both wicks. Type: float, Range: 0.1-0.5, Default: 0.25

Detection:
  Is doji AND both upper and lower wicks >= range * wick_threshold

Notes:
  - [STOCKCHARTS]: "long upper and lower shadows with the Doji in the middle".
  - [TRENDSPIDER]: "short real body" with "very long upper and lower shadow".
  - 25% wick threshold ensures both shadows are substantial relative to range.
```

**DragonflyDoji**
```
Class: DragonflyDoji
References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["body_threshold", "upper_wick_max"]
_outputs: ["dragonfly_doji"]

body_threshold: Maximum body-to-range ratio. Type: float, Range: 0.01-0.3, Default: 0.1
upper_wick_max: Maximum upper wick-to-range ratio. Type: float, Range: 0.01-0.2, Default: 0.1

Detection:
  Is doji AND upper_wick <= range * upper_wick_max AND lower_wick > body

Notes:
  - [STOCKCHARTS]: "Open and close at the day's high" -- open/close at top, long lower shadow.
  - [TRENDSPIDER]: "No or very short upper shadow" -- our upper_wick_max enforces this.
  - Bullish signal especially at support or after downtrend [NISON].
```

**GravestoneDoji**
```
Class: GravestoneDoji
References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["body_threshold", "lower_wick_max"]
_outputs: ["gravestone_doji"]

body_threshold: Maximum body-to-range ratio. Type: float, Range: 0.01-0.3, Default: 0.1
lower_wick_max: Maximum lower wick-to-range ratio. Type: float, Range: 0.01-0.2, Default: 0.1

Detection:
  Is doji AND lower_wick <= range * lower_wick_max AND upper_wick > body

Notes:
  - [STOCKCHARTS]: "Doji is at, or very near, the low of the day" -- open/close at bottom, long upper shadow.
  - [TRENDSPIDER]: "long upper shadow" with open/close near low.
  - Bearish signal especially at resistance or after uptrend [NISON].
```

**Hammer**
```
Class: Hammer
References: [NISON], [KB-07], [CM45T3R], [LUXALGO], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["wick_ratio", "upper_wick_max"]
_outputs: ["hammer"]

wick_ratio: Minimum lower wick to body ratio. Type: float, Range: 1.5-5.0, Default: 2.0
upper_wick_max: Maximum upper wick to body ratio. Type: float, Range: 0.01-0.5, Default: 0.1

Detection:
  body = |Close - Open|
  lower_wick = min(Open, Close) - Low
  upper_wick = High - max(Open, Close)
  hammer = 1 if (body > 0 and lower_wick >= body * wick_ratio and upper_wick <= body * upper_wick_max) else 0

Notes:
  - [NISON]: Small body at upper end, long lower shadow, little or no upper shadow.
  - [KB-07]: Lower_Wick >= 2 * Body, Upper_Wick <= Body * 0.1, Body in upper 25% of range.
  - [CM45T3R]: body < 1/3 of range, lower shadow >= 2x body.
  - [LUXALGO]: lower shadow "at least twice the length of the body".
  - [STOCKCHARTS]: "moves significantly lower after the open but rallies to close well above the intraday low".
  - [TRENDSPIDER]: "small body positioned at candle highs" with "long lower shadow, minimal upper shadow".
  - Hammer is structurally identical to Hanging Man. The distinction is context
    (Hammer appears after downtrend, Hanging Man after uptrend) [NISON].
    The indicator detects the shape; the signal applies context.
```

**HangingMan**
```
Class: HangingMan
References: [NISON], [STOCKCHARTS]
_data: ["open", "high", "low", "close"]
_params: ["wick_ratio", "upper_wick_max"]
_outputs: ["hanging_man"]

Same shape detection as Hammer. Context applied at the signal level.

Notes:
  - [STOCKCHARTS]: Same structure as Hammer but appears during advances;
    "square lollipop with a long stick".
  - [NISON]: Bearish warning signal when appearing after uptrend.
```

**InvertedHammer**
```
Class: InvertedHammer
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["wick_ratio", "lower_wick_max"]
_outputs: ["inverted_hammer"]

wick_ratio: Minimum upper wick to body ratio. Type: float, Range: 1.5-5.0, Default: 2.0
lower_wick_max: Maximum lower wick to body ratio. Type: float, Range: 0.01-0.5, Default: 0.1

Detection:
  upper_wick >= body * wick_ratio AND lower_wick <= body * lower_wick_max

Notes:
  - [KB-07]: Upper_Wick >= 2 * Body, Lower_Wick <= Body * 0.1, Body in lower 25% of range.
  - [STOCKCHARTS]: "open is lower, then it trades higher, but closes near its open".
  - [TRENDSPIDER]: "small body, long upper shadow, minimal lower shadow" with "gap down".
  - Less reliable than hammer [NISON]; needs confirmation.
```

**ShootingStar**
```
Class: ShootingStar
References: [NISON], [STOCKCHARTS]
_data: ["open", "high", "low", "close"]
_params: ["wick_ratio", "lower_wick_max"]
_outputs: ["shooting_star"]

Same shape detection as InvertedHammer. Context applied at the signal level.

Notes:
  - [STOCKCHARTS]: "opens higher, trades much higher, and then closes near its open".
  - [TRENDSPIDER]: requires uptrend context, "gap up" from previous close.
  - [NISON]: Bearish reversal after uptrend.
  - [KB-07] reliability: ~60%, needs confirmation.
```

**Marubozu**
```
Class: Marubozu
References: [NISON], [KB-07], [CM45T3R], [STOCKCHARTS]
_data: ["open", "high", "low", "close"]
_params: ["wick_tolerance"]
_outputs: ["marubozu"]

wick_tolerance: Maximum wick-to-range ratio for either wick. Type: float, Range: 0.0-0.1, Default: 0.05

Detection:
  range = High - Low
  upper_wick = High - max(Open, Close)
  lower_wick = min(Open, Close) - Low
  bullish = Close > Open and upper_wick <= range * wick_tolerance and lower_wick <= range * wick_tolerance
  bearish = Close < Open and upper_wick <= range * wick_tolerance and lower_wick <= range * wick_tolerance
  Output: 1 (bullish), -1 (bearish), 0 (neither)

Notes:
  - [STOCKCHARTS]: "no shadow extending from the body at the open, close, or both".
  - [CM45T3R]: body >= 70% of range, shadows < 10% of body.
  - [KB-07]: Upper_Wick <= Range * 0.05 and Lower_Wick <= Range * 0.05.
  - Pure marubozu (zero wicks) are rare; 5% tolerance is practical [NISON].
```

**SpinningTop**
```
Class: SpinningTop
References: [NISON], [CM45T3R], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["body_max", "wick_min"]
_outputs: ["spinning_top"]

body_max: Maximum body-to-range ratio. Type: float, Range: 0.1-0.5, Default: 0.3
wick_min: Minimum wick-to-range ratio for both wicks. Type: float, Range: 0.1-0.5, Default: 0.2

Detection:
  Small body (body <= range * body_max) with significant wicks on both sides
  (upper_wick >= range * wick_min and lower_wick >= range * wick_min)
  Differs from Doji in that body can be larger (up to 30% vs 10% of range)

Notes:
  - [STOCKCHARTS]: "small bodies with upper and lower shadows that exceed the length of the body".
  - [CM45T3R]: body < 30% of range, both wicks > 20% of range.
  - [TRENDSPIDER]: "small real body" with "shadows longer than the real body".
  - Signals indecision, less significant than doji [NISON].
```

#### 2.2.2 Two-Candle Pattern Indicators

**Engulfing**
```
Class: Engulfing
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER], [LUXALGO]
_data: ["open", "close"]
_params: []
_outputs: ["engulfing"]

Detection (vectorized, comparing bar[i] to bar[i-1]):
  Bullish Engulfing (output = 1):
    Close[i-1] < Open[i-1]  (previous candle bearish)
    Close[i] > Open[i]      (current candle bullish)
    Open[i] < Close[i-1]    (current opens below prev close)
    Close[i] > Open[i-1]    (current closes above prev open)

  Bearish Engulfing (output = -1):
    Close[i-1] > Open[i-1]  (previous candle bullish)
    Close[i] < Open[i]      (current candle bearish)
    Open[i] > Close[i-1]    (current opens above prev close)
    Close[i] < Open[i-1]    (current closes below prev open)

Output: 1 (bullish), -1 (bearish), 0 (neither)

Notes:
  - [STOCKCHARTS]: second body "completely engulfs the previous day's body".
  - [NISON]: "does not require the entire range (high and low) to be engulfed, just the open and close".
  - [TRENDSPIDER]: second candle's body range must fully contain first candle's body range.
  - [LUXALGO]: most reliable with 2-3x average volume (volume is a signal-level concern, not indicator-level).
  - [KB-07] reliability: 60-65%, context dependent.
```

**Harami**
```
Class: Harami
References: [NISON], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "close"]
_params: []
_outputs: ["harami"]

Detection:
  Bullish Harami (output = 1):
    Close[i-1] < Open[i-1]  (previous candle bearish)
    Close[i] > Open[i]      (current candle bullish)
    Open[i] > Close[i-1]    (current body inside previous body)
    Close[i] < Open[i-1]

  Bearish Harami (output = -1):
    Close[i-1] > Open[i-1]  (previous candle bullish)
    Close[i] < Open[i]      (current candle bearish)
    Open[i] < Close[i-1]    (current body inside previous body)
    Close[i] > Open[i-1]

Output: 1 (bullish), -1 (bearish), 0 (neither)

Notes:
  - [NISON]: "small real body holds within the prior session's unusually large real body".
    Most often the second body is the opposite color of the first.
  - [STOCKCHARTS]: "small body day completely contained within the range of the previous body,
    and is the opposite color".
  - [TRENDSPIDER]: scoring system -- 100 if bodies match both ends, 80 if match one end.
    We use binary detection (inside or not) for simplicity.
  - Less strong reversal signal than engulfing [NISON].
```

**PiercingLine**
```
Class: PiercingLine
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["min_penetration"]
_outputs: ["piercing_line"]

min_penetration: Minimum penetration into previous body. Type: float, Range: 0.3-0.8, Default: 0.5

Detection:
  Close[i-1] < Open[i-1]                    (previous candle bearish)
  Close[i] > Open[i]                        (current candle bullish)
  Open[i] < Low[i-1]                        (gaps below previous low)
  Close[i] > Close[i-1] + (Open[i-1] - Close[i-1]) * min_penetration
                                             (closes above midpoint of previous body)

Output: 1 (detected), 0 (not detected)

Notes:
  - [STOCKCHARTS]: "closes above the midpoint of the body of the first day".
  - [TRENDSPIDER]: "long white opening below prior low, closing >= 50% into first body".
  - [NISON]: first candle must be "long black body" -- we enforce this via the gap-down
    requirement (Open[i] < Low[i-1]) which implies the first candle was substantial.
  - 50% penetration is the universally accepted minimum [NISON], [STOCKCHARTS], [TRENDSPIDER].
```

**DarkCloudCover**
```
Class: DarkCloudCover
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["min_penetration"]
_outputs: ["dark_cloud_cover"]

min_penetration: Minimum penetration into previous body. Type: float, Range: 0.3-0.8, Default: 0.5

Detection:
  Close[i-1] > Open[i-1]                    (previous candle bullish)
  Close[i] < Open[i]                        (current candle bearish)
  Open[i] > High[i-1]                       (gaps above previous high)
  Close[i] < Close[i-1] - (Close[i-1] - Open[i-1]) * min_penetration
                                             (closes below midpoint of previous body)

Output: -1 (detected), 0 (not detected)

Notes:
  - [STOCKCHARTS]: "opens at new high then closes below midpoint of first day's body".
  - [TRENDSPIDER]: "Greg Morris prefers close below midpoint" -- matches our 50% default.
  - [NISON]: Mirror of piercing line. "Bearish counterpart of the piercing pattern".
  - One Japanese author requires open above prior close, not just prior high [NISON] --
    our criterion (Open > High[i-1]) is stricter and subsumes this.
```

**TweezerTops**
```
Class: TweezerTops
References: [NISON], [CM45T3R], [STOCKCHARTS]
_data: ["open", "high", "low", "close"]
_params: ["tolerance"]
_outputs: ["tweezer_tops"]

tolerance: Maximum high-to-high difference as fraction of range. Type: float, Range: 0.001-0.05, Default: 0.01

Detection:
  |High[i] - High[i-1]| <= avg_range * tolerance  (highs approximately equal)
  Close[i-1] > Open[i-1]                          (first candle bullish)
  Close[i] < Open[i]                              (second candle bearish)

Output: -1 (bearish signal), 0 (not detected)

Notes:
  - [NISON]: "same highs or lows are tested on back-to-back sessions". Minor reversal
    signals that gain importance when combined with other patterns.
  - [CM45T3R]: 1% tolerance for matching highs/lows -- matches our default.
  - [STOCKCHARTS]: identifies matching extremes as resistance confirmation.
```

**TweezerBottoms**
```
Class: TweezerBottoms
References: [NISON], [CM45T3R], [STOCKCHARTS]
_data: ["open", "high", "low", "close"]
_params: ["tolerance"]
_outputs: ["tweezer_bottoms"]

tolerance: Maximum low-to-low difference as fraction of range. Type: float, Range: 0.001-0.05, Default: 0.01

Detection:
  |Low[i] - Low[i-1]| <= avg_range * tolerance    (lows approximately equal)
  Close[i-1] < Open[i-1]                          (first candle bearish)
  Close[i] > Open[i]                              (second candle bullish)

Output: 1 (bullish signal), 0 (not detected)

Notes:
  - Mirror of TweezerTops. Same tolerance and matching logic applied to lows.
  - [NISON]: bullish reversal when matching lows appear after downtrend.
```

#### 2.2.3 Three-Candle Pattern Indicators

**MorningStar**
```
Class: MorningStar
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER], [BABYPIPS]
_data: ["open", "high", "low", "close"]
_params: ["body_threshold"]
_outputs: ["morning_star"]

body_threshold: Maximum body-to-range ratio for middle candle. Type: float, Range: 0.1-0.5, Default: 0.3

Detection (comparing bars [i-2], [i-1], [i]):
  Close[i-2] < Open[i-2]                      (first candle bearish)
  |Close[i-1] - Open[i-1]| <= range[i-1] * body_threshold  (middle candle small body)
  Close[i] > Open[i]                          (third candle bullish)
  Close[i] > (Open[i-2] + Close[i-2]) / 2     (third closes above midpoint of first)

Output: 1 (detected), 0 (not detected)

Notes:
  - [NISON]: "long black real body, small real body that gaps lower, white candlestick
    that closes well into the first session's black real body".
  - [TRENDSPIDER]: third candle must penetrate >50% of first candle's body -- our midpoint
    check enforces this.
  - [STOCKCHARTS]: "long black body, gapped-down small middle candle, long white body
    gapping up and closing above first day's midpoint".
  - Classical definition requires gaps between candles [NISON]. In crypto/forex markets
    where gaps are rare, we relax the gap requirement and focus on the body size and
    penetration criteria. The gap adds confirmation but is not structurally necessary.
```

**EveningStar**
```
Class: EveningStar
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER], [BABYPIPS]
_data: ["open", "high", "low", "close"]
_params: ["body_threshold"]
_outputs: ["evening_star"]

body_threshold: Maximum body-to-range ratio for middle candle. Type: float, Range: 0.1-0.5, Default: 0.3

Detection:
  Close[i-2] > Open[i-2]                      (first candle bullish)
  |Close[i-1] - Open[i-1]| <= range[i-1] * body_threshold  (middle candle small body)
  Close[i] < Open[i]                          (third candle bearish)
  Close[i] < (Open[i-2] + Close[i-2]) / 2     (third closes below midpoint of first)

Output: -1 (detected), 0 (not detected)

Notes:
  - Mirror of morning star. [NISON]: "tall white real body, small real body that gaps
    above, black candlestick that closes well into the first session's white real body".
  - [TRENDSPIDER]: "more reliable if the first candlestick's size is smaller than the third one".
  - Same gap relaxation as MorningStar for crypto/forex markets.
```

**ThreeWhiteSoldiers**
```
Class: ThreeWhiteSoldiers
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER], [BABYPIPS]
_data: ["open", "high", "low", "close"]
_params: ["min_body_ratio"]
_outputs: ["three_white_soldiers"]

min_body_ratio: Minimum body-to-range ratio per candle. Type: float, Range: 0.3-0.8, Default: 0.5

Detection:
  All three candles bullish (Close > Open)
  Each close higher than previous close
  Each open within previous body (Open[i] >= Open[i-1] and Open[i] <= Close[i-1])
  Each body >= range * min_body_ratio (strong bodies, not spinning tops)

Output: 1 (detected), 0 (not detected)

Notes:
  - [STOCKCHARTS]: "three consecutive long white bodies"; each opens within previous body,
    closes near day's high.
  - [TRENDSPIDER]: "no dramatic size reduction between candles", "no or very short upper shadow".
    We enforce body size but not shadow length -- shadow constraints would be too restrictive
    for crypto markets.
  - [NISON]: "considered one of the most potent bullish signals, especially when it occurs
    after an extended downtrend".
  - 50% body-to-range ensures strong-bodied candles, filtering out spinning tops and dojis.
```

**ThreeBlackCrows**
```
Class: ThreeBlackCrows
References: [NISON], [KB-07], [STOCKCHARTS], [TRENDSPIDER]
_data: ["open", "high", "low", "close"]
_params: ["min_body_ratio"]
_outputs: ["three_black_crows"]

min_body_ratio: Minimum body-to-range ratio per candle. Type: float, Range: 0.3-0.8, Default: 0.5

Detection:
  All three candles bearish (Close < Open)
  Each close lower than previous close
  Each open within previous body (Open[i] <= Open[i-1] and Open[i] >= Close[i-1])
  Each body >= range * min_body_ratio

Output: -1 (detected), 0 (not detected)

Notes:
  - [STOCKCHARTS]: "three consecutive long black bodies where each day closes at or near
    its low and opens within the body of the previous day".
  - [TRENDSPIDER]: opens within prior body, closes at or near low, "no or very short
    lower shadow".
  - Mirror of three white soldiers. Same body ratio rationale.
```

**ThreeInsideUp**
```
Class: ThreeInsideUp
References: [NISON], [KB-07], [TRENDSPIDER]
_data: ["open", "close"]
_params: []
_outputs: ["three_inside_up"]

Detection:
  Bar[i-2]: Bearish (Close < Open)
  Bar[i-1]: Bullish Harami of bar[i-2] (body inside previous body)
  Bar[i]: Bullish, closes above Open of bar[i-2]

Output: 1 (detected), 0 (not detected)

Notes:
  - [KB-07]: "Bearish candle, bullish candle that forms inside bar, bullish candle
    that closes above first candle's high".
  - Confirmation pattern: the harami (bar 2) suggests reversal, bar 3 confirms it.
  - [TRENDSPIDER]: classified as bullish reversal.
```

**ThreeInsideDown**
```
Class: ThreeInsideDown
References: [NISON], [KB-07], [TRENDSPIDER]
_data: ["open", "close"]
_params: []
_outputs: ["three_inside_down"]

Detection:
  Bar[i-2]: Bullish (Close > Open)
  Bar[i-1]: Bearish Harami of bar[i-2] (body inside previous body)
  Bar[i]: Bearish, closes below Open of bar[i-2]

Output: -1 (detected), 0 (not detected)

Notes:
  - Mirror of ThreeInsideUp.
  - [KB-07]: "Bullish candle, bearish candle that forms inside bar, bearish candle
    that closes below first candle's low".
```

#### 2.2.4 Multi-Bar Pattern Indicators

**InsideBar**
```
Class: InsideBar
References: [KB-07], [TSR], [NETPICKS], [INVESTOPEDIA-PA]
_data: ["high", "low"]
_params: []
_outputs: ["inside_bar"]

Detection:
  High[i] < High[i-1] AND Low[i] > Low[i-1]

Output: 1 (detected), 0 (not detected)

Notes:
  - [TSR]: "second bar must have a lower high and a higher low".
  - [KB-07]: "A bar whose entire range is contained within the previous bar's range".
  - [NETPICKS]: inside bar + NR combination (ID/NR) signals "low-volatility phase
    that may precede a strong breakout".
  - Strict containment: uses < and > (not <= and >=) to exclude equal highs/lows.
```

**OutsideBar**
```
Class: OutsideBar
References: [KB-07], [TSR]
_data: ["high", "low"]
_params: []
_outputs: ["outside_bar"]

Detection:
  High[i] > High[i-1] AND Low[i] < Low[i-1]

Output: 1 (detected), 0 (not detected)

Notes:
  - [TSR]: "higher high and a lower low" than the previous bar.
  - [KB-07]: "A bar whose range completely engulfs the previous bar's range".
  - Differs from Engulfing (body-based) -- OutsideBar compares full range (high/low).
```

**PinBar**
```
Class: PinBar
References: [KB-07], [TSR], [INVESTOPEDIA-PA]
_data: ["open", "high", "low", "close"]
_params: ["wick_ratio", "body_position"]
_outputs: ["pin_bar"]

wick_ratio: Minimum dominant wick to body ratio. Type: float, Range: 1.5-5.0, Default: 2.0
body_position: Maximum body position from the wick end as fraction of range. Type: float, Range: 0.1-0.5, Default: 0.33

Detection:
  Bullish Pin Bar (output = 1):
    Long lower wick (lower_wick >= body * wick_ratio)
    Body in upper third of range (min(Open, Close) > Low + range * (1 - body_position))
  Bearish Pin Bar (output = -1):
    Long upper wick (upper_wick >= body * wick_ratio)
    Body in lower third of range (max(Open, Close) < High - range * (1 - body_position))

Notes:
  - [TSR]: "long and distinct tail" dominates the bar. Bullish at support, bearish
    at resistance.
  - [KB-07]: "long wick (2x+ body)" with "small body in upper/lower portion".
  - Pin bar is a price action concept [INVESTOPEDIA-PA]; similar to hammer/shooting star
    but defined by body position within the range rather than strict wick-to-body ratio.
  - body_position=0.33 means body must be in the upper/lower third of the range.
```

**TwoBarReversal**
```
Class: TwoBarReversal
References: [KB-07], [TSR]
_data: ["open", "high", "low", "close"]
_params: []
_outputs: ["two_bar_reversal"]

Detection:
  Bullish (output = 1):
    Bar[i-1] bearish with close near low
    Bar[i] bullish with close near high
    Bar[i] low <= Bar[i-1] low (takes out the low)
    Bar[i] close > Bar[i-1] open

  Bearish (output = -1):
    Bar[i-1] bullish with close near high
    Bar[i] bearish with close near low
    Bar[i] high >= Bar[i-1] high (takes out the high)
    Bar[i] close < Bar[i-1] open

Notes:
  - [TSR]: "two strong bars closing in opposite directions" showing rejection of
    initial thrust.
  - [KB-07]: "Combined forms a hammer-like structure" (bullish) or
    "shooting star-like structure" (bearish).
  - "Close near high/low" implemented as close in upper/lower 25% of range.
```

**NarrowRange**
```
Class: NarrowRange
References: [KB-07], [CHARTSCHOOL-NR7], [FOREXTRAINING], [NETPICKS], [BULKOWSKI]
_data: ["high", "low"]
_params: ["lookback"]
_outputs: ["narrow_range"]

lookback: Number of bars to compare range against. Type: int, Range: 4-20, Default: 7

Detection (NR7 default, NR4 with lookback=4):
  range[i] = High[i] - Low[i]
  narrow_range = 1 if range[i] < min(range[i-lookback:i]) else 0

Output: 1 (narrowest range in lookback period), 0 (not)

Notes:
  - [CHARTSCHOOL-NR7]: "Narrow Range Day NR7" -- originated by Toby Crabel.
  - [FOREXTRAINING]: range = High - Low for each bar; NR7 = current bar range is
    smallest of last 7 bars.
  - [NETPICKS]: contraction/expansion principle -- "volatility expansion often follows
    a volatility contraction" (analogous to Bollinger Band Squeeze).
  - [KB-07]: Range[0] < min(Range[1], Range[2], ..., Range[6]).
  - NR4 available by setting lookback=4. NR4/ID (inside day + NR4) is a composite
    that can be built from InsideBar + NarrowRange signals.
```

### 2.3 Pattern Signal Specifications

Pattern signals use pattern indicators internally. Each signal returns `bool` and evaluates the **last bar** of the DataFrame (same convention as all existing signals).

#### 2.3.1 Signal Naming Convention

Pattern signals follow the format: `{pattern_name}_{direction}_{type}`

- `pattern_name`: snake_case pattern name (e.g., `engulfing`, `morning_star`, `doji`)
- `direction`: `bullish` or `bearish` (omitted for non-directional patterns like `doji`, `inside_bar`)
- `type`: `trigger` for TRIGGER signals (pattern appeared on current bar), `recent` for FILTER signals (pattern appeared within lookback window)

#### 2.3.2 TRIGGER Signals (Pattern Just Appeared)

These detect the pattern on the **current (last) bar**. Suitable for strategy entry/exit triggers.

| Signal Name | Pattern | Direction | Description |
|-------------|---------|-----------|-------------|
| `doji_trigger` | Doji | Neutral | Doji detected on current bar |
| `dragonfly_doji_trigger` | DragonflyDoji | Bullish | Dragonfly doji detected on current bar |
| `gravestone_doji_trigger` | GravestoneDoji | Bearish | Gravestone doji detected on current bar |
| `hammer_trigger` | Hammer | Bullish | Hammer shape detected on current bar (context: after downtrend) |
| `shooting_star_trigger` | ShootingStar | Bearish | Shooting star shape detected on current bar (context: after uptrend) |
| `bullish_engulfing_trigger` | Engulfing | Bullish | Bullish engulfing pattern completed on current bar |
| `bearish_engulfing_trigger` | Engulfing | Bearish | Bearish engulfing pattern completed on current bar |
| `bullish_harami_trigger` | Harami | Bullish | Bullish harami pattern completed on current bar |
| `bearish_harami_trigger` | Harami | Bearish | Bearish harami pattern completed on current bar |
| `piercing_line_trigger` | PiercingLine | Bullish | Piercing line pattern completed on current bar |
| `dark_cloud_cover_trigger` | DarkCloudCover | Bearish | Dark cloud cover pattern completed on current bar |
| `morning_star_trigger` | MorningStar | Bullish | Morning star pattern completed on current bar |
| `evening_star_trigger` | EveningStar | Bearish | Evening star pattern completed on current bar |
| `three_white_soldiers_trigger` | ThreeWhiteSoldiers | Bullish | Three white soldiers completed on current bar |
| `three_black_crows_trigger` | ThreeBlackCrows | Bearish | Three black crows completed on current bar |
| `three_inside_up_trigger` | ThreeInsideUp | Bullish | Three inside up completed on current bar |
| `three_inside_down_trigger` | ThreeInsideDown | Bearish | Three inside down completed on current bar |
| `inside_bar_trigger` | InsideBar | Neutral | Inside bar detected on current bar |
| `outside_bar_trigger` | OutsideBar | Neutral | Outside bar detected on current bar |
| `bullish_pin_bar_trigger` | PinBar | Bullish | Bullish pin bar detected on current bar |
| `bearish_pin_bar_trigger` | PinBar | Bearish | Bearish pin bar detected on current bar |
| `nr7_trigger` | NarrowRange | Neutral | NR7 (narrowest range in 7 bars) detected on current bar |

**Total TRIGGER signals: 22**

#### 2.3.3 FILTER Signals (Pattern Context)

These check whether a pattern appeared **within a recent lookback window**. Suitable for strategy filters ("only enter if a bullish pattern appeared in the last N bars").

| Signal Name | Description | Extra Params |
|-------------|-------------|--------------|
| `bullish_pattern_recent` | Any bullish candlestick pattern detected within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `bearish_pattern_recent` | Any bearish candlestick pattern detected within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `reversal_pattern_bullish` | Bullish reversal pattern (hammer, engulfing, morning star, piercing line, dragonfly doji) within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `reversal_pattern_bearish` | Bearish reversal pattern (shooting star, engulfing, evening star, dark cloud cover, gravestone doji) within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `continuation_pattern_bullish` | Bullish continuation (three white soldiers, three inside up) within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `continuation_pattern_bearish` | Bearish continuation (three black crows, three inside down) within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `indecision_pattern_recent` | Indecision pattern (doji, spinning top, inside bar, NR7) within lookback | `lookback` (int, Range: 1-20, Default: 5) |
| `strong_body_recent` | Marubozu detected within lookback | `lookback` (int, Range: 1-20, Default: 5) |

**Total FILTER signals: 8**

**Grand total: 30 signals (22 TRIGGER + 8 FILTER)**

### 2.4 Pattern Helper Utilities

Shared computations used by multiple pattern indicators. These are internal helpers, not public API.

```python
# In pattern_utils.py

def candle_body(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Absolute body size: |Close - Open|"""

def candle_range(high_s: pd.Series, low_s: pd.Series) -> pd.Series:
    """Full candle range: High - Low"""

def upper_wick(open_s: pd.Series, high_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Upper wick: High - max(Open, Close)"""

def lower_wick(open_s: pd.Series, low_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Lower wick: min(Open, Close) - Low"""

def is_bullish(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Boolean series: Close > Open"""

def is_bearish(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Boolean series: Close < Open"""

def body_ratio(open_s: pd.Series, high_s: pd.Series, low_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Body as fraction of range: body / range (0 where range is 0)"""
```

---

## 3. Architecture

### 3.1 File Layout

```
mangrove_knowledge_base/
  indicators/
    __init__.py                    # Add pattern indicator exports
    indicator_interface.py         # Unchanged
    momentum_indicators.py         # Unchanged
    trend_indicators.py            # Unchanged
    volume_indicators.py           # Unchanged
    volatility_indicators.py       # Unchanged
    return_indicators.py           # Unchanged
    pattern_indicators.py          # NEW: 25 pattern indicator classes
    pattern_utils.py               # NEW: shared candle geometry helpers
  signals/
    __init__.py                    # Add patterns import
    momentum.py                    # Unchanged
    trend.py                       # Unchanged
    volume.py                      # Unchanged
    volatility.py                  # Unchanged
    patterns.py                    # NEW: 30 pattern signal functions

knowledge-base/
  07-chart-patterns.md             # MODIFIED: replace TA-Lib section with library reference
  00-table-of-contents.md          # MODIFIED: remove TA-Lib references

tests/
  test_docstring_parser.py         # Unchanged (auto-discovers new signals)
  test_pattern_indicators.py       # NEW: unit tests for pattern detection
  test_pattern_signals.py          # NEW: signal integration tests
```

### 3.2 Module Dependencies

```
pattern_utils.py          (no dependencies, pure pandas/numpy)
    ^
    |
pattern_indicators.py     (imports pattern_utils, IndicatorInterface)
    ^
    |
signals/patterns.py       (imports pattern indicators, RuleRegistry)
```

No circular dependencies. Pattern indicators depend only on `IndicatorInterface` and `pattern_utils`. Pattern signals depend only on pattern indicators and `RuleRegistry`.

### 3.3 Indicator Class Organization

All 25 pattern indicator classes live in a single file `pattern_indicators.py` grouped by category:

```python
# mangrove_knowledge_base/indicators/pattern_indicators.py

"""Candlestick and multi-bar pattern indicator classes."""

# --- Single-candle patterns ---
class Doji(IndicatorInterface): ...
class LongLeggedDoji(IndicatorInterface): ...
class DragonflyDoji(IndicatorInterface): ...
class GravestoneDoji(IndicatorInterface): ...
class Hammer(IndicatorInterface): ...
class HangingMan(IndicatorInterface): ...
class InvertedHammer(IndicatorInterface): ...
class ShootingStar(IndicatorInterface): ...
class Marubozu(IndicatorInterface): ...
class SpinningTop(IndicatorInterface): ...

# --- Two-candle patterns ---
class Engulfing(IndicatorInterface): ...
class Harami(IndicatorInterface): ...
class PiercingLine(IndicatorInterface): ...
class DarkCloudCover(IndicatorInterface): ...
class TweezerTops(IndicatorInterface): ...
class TweezerBottoms(IndicatorInterface): ...

# --- Three-candle patterns ---
class MorningStar(IndicatorInterface): ...
class EveningStar(IndicatorInterface): ...
class ThreeWhiteSoldiers(IndicatorInterface): ...
class ThreeBlackCrows(IndicatorInterface): ...
class ThreeInsideUp(IndicatorInterface): ...
class ThreeInsideDown(IndicatorInterface): ...

# --- Multi-bar patterns ---
class InsideBar(IndicatorInterface): ...
class OutsideBar(IndicatorInterface): ...
class PinBar(IndicatorInterface): ...
class TwoBarReversal(IndicatorInterface): ...
class NarrowRange(IndicatorInterface): ...
```

### 3.4 Signal Organization

All 30 pattern signals live in a single file `signals/patterns.py`:

```python
# mangrove_knowledge_base/signals/patterns.py

"""Candlestick and multi-bar pattern signal functions."""

# --- Single-candle TRIGGER signals ---
@RuleRegistry.register("doji_trigger")
def doji_trigger(df, body_threshold=0.1): ...

@RuleRegistry.register("dragonfly_doji_trigger")
def dragonfly_doji_trigger(df, body_threshold=0.1, upper_wick_max=0.1): ...

# ... etc

# --- Two-candle TRIGGER signals ---
@RuleRegistry.register("bullish_engulfing_trigger")
def bullish_engulfing_trigger(df): ...

# ... etc

# --- FILTER signals ---
@RuleRegistry.register("bullish_pattern_recent")
def bullish_pattern_recent(df, lookback=5): ...

# ... etc
```

### 3.5 Integration Points

**MangroveAI integration requires zero changes** to:
- Strategy engine (`strategy.py`) -- pattern signals register in `RuleRegistry` like all others
- Backtester (`backtesting/services.py`) -- evaluates signals by name, agnostic to implementation
- AI Copilot -- discovers signals via docstring metadata, recommends via intent matching
- Signal API (`routes.py`) -- lists/evaluates all registered signals
- Signal validation (`validation.py`) -- validates any registered signal

The only change needed in MangroveAI is updating the `USE_EXTERNAL_KB` toggle files to import the new pattern signals module (same pattern as existing momentum/trend/volume/volatility imports).

### 3.6 Vectorized vs. Last-Bar Evaluation

**Indicators** are vectorized: they compute pattern detection for **every bar** in the DataFrame, returning a full `pd.Series`. This is essential for backtesting, which needs to evaluate signals at every historical bar.

**Signals** evaluate the **last bar** only (returning `bool`). They call the indicator's `compute()` method, then check `result.iloc[-1]`.

This matches the existing architecture exactly. For example:
- `RSI.compute()` returns a full RSI series (indicator)
- `rsi_overbought()` checks if `rsi.iloc[-1] > threshold` (signal)

Pattern indicators follow the same split:
- `Engulfing.compute()` returns a full series of 1/-1/0 values (indicator)
- `bullish_engulfing_trigger()` checks if `engulfing.iloc[-1] == 1` (signal)

---

## 4. Implementation Plan

### 4.1 Phase Breakdown

#### Step 1: Pattern Utilities and Infrastructure

**Files created:**
- `mangrove_knowledge_base/indicators/pattern_utils.py`

**Work:**
1. Implement the 7 helper functions (`candle_body`, `candle_range`, `upper_wick`, `lower_wick`, `is_bullish`, `is_bearish`, `body_ratio`)
2. All functions operate on `pd.Series` and return `pd.Series`
3. Handle edge cases: zero-range candles (High == Low), NaN values

**Testing:** Unit tests for each helper with known OHLCV data.

#### Step 2: Single-Candle Pattern Indicators

**Files created/modified:**
- `mangrove_knowledge_base/indicators/pattern_indicators.py` (create)
- `mangrove_knowledge_base/indicators/__init__.py` (add exports)

**Work:**
1. Implement 10 single-candle indicator classes: Doji, LongLeggedDoji, DragonflyDoji, GravestoneDoji, Hammer, HangingMan, InvertedHammer, ShootingStar, Marubozu, SpinningTop
2. Each follows `IndicatorInterface` with `_data`, `_params`, `_outputs`, `_compute()`
3. All computations vectorized using pandas operations (`.shift()`, boolean masking)

**Testing:** Unit tests with synthetic OHLCV data containing known patterns.

#### Step 3: Two-Candle Pattern Indicators

**Work:**
1. Add 6 two-candle indicator classes to `pattern_indicators.py`: Engulfing, Harami, PiercingLine, DarkCloudCover, TweezerTops, TweezerBottoms
2. Two-candle patterns use `.shift(1)` to compare current bar with previous bar

**Testing:** Unit tests with two-candle pattern scenarios.

#### Step 4: Three-Candle and Multi-Bar Pattern Indicators

**Work:**
1. Add 6 three-candle indicator classes: MorningStar, EveningStar, ThreeWhiteSoldiers, ThreeBlackCrows, ThreeInsideUp, ThreeInsideDown
2. Add 5 multi-bar indicator classes: InsideBar, OutsideBar, PinBar, TwoBarReversal, NarrowRange
3. Three-candle patterns use `.shift(1)` and `.shift(2)`
4. NarrowRange uses `.rolling()` for lookback window comparison

**Testing:** Unit tests with multi-bar pattern scenarios.

#### Step 5: Pattern Signals -- TRIGGER

**Files created/modified:**
- `mangrove_knowledge_base/signals/patterns.py` (create)
- `mangrove_knowledge_base/signals/__init__.py` (add import)

**Work:**
1. Implement 22 TRIGGER signal functions
2. Each follows the exact signal function pattern: `@RuleRegistry.register`, docstring with Type/Requires/Args, returns `bool`
3. Each calls the corresponding indicator's `compute()` method and checks `iloc[-1]`
4. Handle minimum data requirements (return `False` if insufficient bars)

**Testing:** Verify all signals parseable by `docstring_parser.py`. Test signal output matches indicator output for last bar.

#### Step 6: Pattern Signals -- FILTER

**Work:**
1. Implement 8 FILTER signal functions
2. FILTER signals check a window of recent bars: `any(indicator_result.iloc[-lookback:] != 0)`
3. Composite filters (e.g., `bullish_pattern_recent`) run multiple pattern indicators and check for any bullish detection

**Testing:** Verify FILTER signals work with various lookback values.

#### Step 7: TA-Lib Removal and KB Documentation Update

**Files modified:**
- `knowledge-base/07-chart-patterns.md` -- Replace TA-Lib section (7.4) with reference to `mangrove_knowledge_base.indicators.pattern_indicators`
- `knowledge-base/00-table-of-contents.md` -- Remove TA-Lib references and tags

**Work:**
1. Remove TA-Lib CDL function listing and `import talib` code examples
2. Replace with section documenting the MangroveKnowledgeBase pattern detection library
3. Include usage examples showing `Engulfing.compute()` and pattern signal evaluation
4. Update tags: replace `TA-Lib` with `pattern-indicators`

#### Step 8: Test Suite and Validation

**Files created:**
- `tests/test_pattern_indicators.py`
- `tests/test_pattern_signals.py`

**Work:**
1. Pattern indicator tests: verify detection on synthetic data with known patterns
2. Pattern signal tests: verify boolean output, docstring metadata parsing, registry integration
3. Run existing `test_docstring_parser.py` to confirm new signals are discovered and parsed correctly
4. Edge case tests: empty DataFrames, single-bar DataFrames, all-NaN data, zero-range candles

#### Step 9: Integration Verification

**Work:**
1. Verify `from mangrove_knowledge_base.signals.patterns import *` triggers registration
2. Verify `RuleRegistry.evaluate({"name": "bullish_engulfing_trigger"}, df)` works
3. Verify docstring parser extracts correct metadata for all 30 signals
4. Update signal explorer notebook with pattern detection examples
5. Verify signal count: 96 existing + 30 new = 126 total signals

### 4.2 File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `indicators/pattern_utils.py` | CREATE | 7 candle geometry helper functions |
| `indicators/pattern_indicators.py` | CREATE | 27 pattern indicator classes |
| `indicators/__init__.py` | MODIFY | Add pattern indicator exports |
| `signals/patterns.py` | CREATE | 30 pattern signal functions |
| `signals/__init__.py` | MODIFY | Add `from . import patterns` |
| `knowledge-base/07-chart-patterns.md` | MODIFY | Replace TA-Lib section with library reference |
| `knowledge-base/00-table-of-contents.md` | MODIFY | Remove TA-Lib references |
| `tests/test_pattern_indicators.py` | CREATE | Pattern indicator unit tests |
| `tests/test_pattern_signals.py` | CREATE | Pattern signal integration tests |

### 4.3 Estimated Signal Counts After Completion

| Category | TRIGGER | FILTER | Total |
|----------|---------|--------|-------|
| Momentum | 13 | 13 | 26 |
| Trend | 19 | 19 | 38 |
| Volume | 11 | 11 | 22 |
| Volatility | 5 | 5 | 10 |
| **Patterns (new)** | **22** | **8** | **30** |
| **Total** | **70** | **56** | **126** |

### 4.4 Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pattern indicators are computationally heavier than traditional indicators (multiple shifted comparisons per bar) | Slow backtesting on large datasets | Use vectorized pandas operations exclusively; avoid Python loops. Profile with sample data. |
| FILTER signals running multiple indicators per evaluation | Slow composite signal evaluation | Cache indicator results within the signal function call; compute once, check multiple. |
| Docstring parser may not handle new parameter patterns | Signals not discoverable by AI Copilot | Test parser compatibility in Step 5 before proceeding. All params use existing types (int, float). |
| Existing tests may break if signal count validation is hardcoded | CI failure | Check for hardcoded counts in test files and update them. |
| Pattern detection sensitivity varies by market/timeframe | False signals in backtesting | Default parameters are tuned conservatively per the KB documentation. Users can adjust via strategy params. |

---

## 5. References

All detection logic, default thresholds, and pattern definitions are sourced from and cross-referenced against the following materials. Each pattern indicator docstring will cite the specific references that informed its implementation.

### 5.1 Primary References

| ID | Source | Type | Key Contributions |
|----|--------|------|-------------------|
| [NISON] | Steve Nison, *Japanese Candlestick Charting Techniques*, 2nd Edition (Prentice Hall, 2001) | Book (canonical) | Definitive Western reference for Japanese candlestick patterns. Defines all single, two, and three-candle patterns including doji, hammer, engulfing, harami, morning/evening star, three soldiers/crows. Establishes that candlestick patterns are psychology-based and context-dependent. Does not provide exact numeric thresholds -- uses qualitative descriptions ("small body", "long shadow"). |
| [BULKOWSKI] | Thomas Bulkowski, *Encyclopedia of Candlestick Charts* (Wiley, 2008) and thepatternsite.com | Book + website | Empirical reliability statistics for candlestick patterns based on backtesting thousands of historical examples. 103 candlestick patterns ranked by performance. NR7: rank 11/23, 57% win rate in bull/up breakouts (13,391 trades), 46% failure rate. Sample: 1,201 stocks, Jan 1990 - Mar 2013. Also published "Are Three-Bar Patterns Reliable For Stocks" in Stocks & Commodities (Jan 2000). |
| [CRABEL] | Toby Crabel, *Day Trading with Short Term Price Patterns & Opening Range Breakout* (1990, out of print) | Book (seminal) | Original source for NR4 and NR7 narrow range patterns. Defined NR7 as the narrowest range bar in 7 sessions. Established the volatility contraction/expansion principle: "narrow range days mark price contractions that often precede price expansions." Used absolute range (High - Low), not percentage range. Focused on opening range breakout entries following NR patterns. |
| [KB-07] | MangroveKnowledgeBase `knowledge-base/07-chart-patterns.md` | Internal documentation | Detection logic pseudocode for all patterns in scope. Doji threshold (10% body-to-range), hammer wick ratio (2x body), marubozu tolerance (5% range), engulfing/harami/piercing/dark cloud criteria, NR7 algorithm, swing point detection. Reliability statistics table. |

### 5.2 Quantitative Detection References

| ID | Source | Type | Key Contributions |
|----|--------|------|-------------------|
| [LINNSOFT] | Linn Software, "Candlestick Pattern Recognition (CPR)" (linnsoft.com/techind/candlestick-pattern-recognition-cpr) | Software documentation | Precise quantitative thresholds for algorithmic detection. Doji Equal Percent (EP) default 0.50% of price. Long shadow multiplier default 2.0x body. Small shadow multiplier default 1.0x body. Body length classification: "Long" = above average of all candle bodies in chart, "Small" = below average but above doji threshold. |
| [CM45T3R] | cm45t3r/candlestick (github.com/cm45t3r/candlestick) | Open-source library | Python implementation thresholds: Doji body < 10% of range. Hammer body < 1/3 of range, lower shadow >= 2x body. Marubozu body >= 70% of range, shadows < 10% of body. Spinning top body < 30% of range, both wicks > 20% of range. Tweezer tolerance 1% between highs/lows. |
| [TRENDSPIDER] | TrendSpider, "Auto-Recognized Traditional Candlestick Pattern Definitions" (help.trendspider.com) | Software documentation | Comprehensive pattern definitions for 40+ patterns. Morning/evening star: third candle must penetrate >50% of first candle's body. Three soldiers: no dramatic size reduction between candles, no/very short upper shadows. Three black crows: opens within prior body, closes at or near low. Harami scoring: 100 if bodies match both ends, 80 if match one end. Dark cloud cover: Greg Morris prefers close below midpoint. |
| [LUXALGO] | LuxAlgo, "Popular Candlestick Patterns: Key Signals" (luxalgo.com/blog/popular-candlestick-patterns-key-signals/) | Software documentation | Doji body <= 5% of total candle range (stricter than our 10% default). Hammer lower shadow "at least twice the length of the body". Engulfing most reliable with 2-3x average volume. |

### 5.3 Price Action and Context References

| ID | Source | Type | Key Contributions |
|----|--------|------|-------------------|
| [COINCODEX] | CoinCodex, "Candlestick Patterns Cheat Sheet" (coincodex.com/article/35704/candlestick-patterns-cheat-sheet/) | Article | Classification of patterns by reliability and type. Candlestick pattern cheat sheet with bullish/bearish/neutral categorization. Context requirements for each pattern family. |
| [OPTIMUS] | Optimus Futures, "How to Trade Support and Resistance Levels" (optimusfutures.com/blog/trade-support-and-resistance-levels/) | Article | Support/resistance zone definitions by instrument (ES: 5-10 points, CL: $0.50-$1.00). Three-level zone structure (aggressive/neutral/conservative). Candlestick confirmation at S/R: pin bars for rejection, engulfing for momentum shifts, dojis for indecision before breakouts. Stop placement 0.5-1.0 ATR beyond S/R zone. Strong levels require 2-3 touches minimum. |
| [INVESTOPEDIA-PA] | Investopedia, "Introduction to Price Action Trading Strategies" (investopedia.com/articles/active-trading/110714/introduction-price-action-trading-strategies.asp) | Article | Price action trading framework. Inside bar, outside bar, pin bar definitions in price action context. Pattern confirmation rules and multi-bar pattern usage. |
| [TSR] | Trading Setups Review, "10 Price Action Bar Patterns You Must Know" (tradingsetupsreview.com/10-price-action-bar-patterns-must-know/) | Article | Inside bar: "second bar must have a lower high and a higher low". Outside bar: "higher high and a lower low". Pin bar: "long and distinct tail" dominates the bar. Two-bar reversal: "two strong bars closing in opposite directions". NR7: "smallest bar range within the sequence of seven bars". |
| [STOCKCHARTS] | StockCharts, "Candlestick Pattern Dictionary" (chartschool.stockcharts.com) | Reference dictionary | Canonical definitions for all standard candlestick patterns. Hammer: "moves significantly lower after the open but rallies to close well above the intraday low". Marubozu: "no shadow extending from the body at the open, close, or both". Morning star: gap between first and second candle, third closes above first's midpoint. Engulfing: second candle "completely engulfs the previous day's body". |
| [BABYPIPS] | Babypips, "Triple Candlestick Patterns" (babypips.com/learn/forex/triple-candlestick-patterns) | Educational | Three-candle pattern definitions for morning/evening star, three soldiers/crows. Clear structural breakdown with visual descriptions. |
| [PRICEACTION] | PriceAction.com, "Pin Bar Trading Strategy" (priceaction.com/price-action-university/strategies/pin-bar/) | Educational | Pin bar definition as price action concept. Distinction from hammer/shooting star: pin bar is context-aware (must be at support/resistance in a trend). "A pin bar pattern consists of one price bar with a long tail -- the tail is also referred to as a shadow or wick -- and pin bars generally have small real bodies in comparison to their long tails." |
| [DAILYFOREX] | DailyForex, "The 2 Bar Reversal Explained" (dailyforex.com) | Article | Two-bar reversal is structurally "just a pin bar reversal formed over 2 sessions." Psychology is the same: "price goes in one direction before faking traders out and snapping back quickly in the opposite direction." |

### 5.4 Empirical Performance References

| ID | Source | Type | Key Contributions |
|----|--------|------|-------------------|
| [LST] | Liberated Stock Trader, "The 10 Best Candle Patterns Proven With 56,680 Trades" (liberatedstocktrader.com/candle-patterns-reliable-profitable/) | Backtest study | 56,680 trades across daily charts. Inverted hammer: 60% win rate, 1.12% profit/trade (1,702 trades). Bearish marubozu: 56.1%, 0.8% profit (4,994 trades). Gravestone doji: 57%, 0.65% profit (1,553 trades). Bearish engulfing: 57% (4,096 trades). Spinning top: 55.9% (9,894 trades). Doji: tested across 8,029 trades. Patterns predict ~60% of the time, 3-10 day window. |
| [TRADESVIZ] | TradesViz, "Candlestick Pattern Effectiveness Backtesting" (tradesviz.com/blog/candlestick-pattern-effectiveness-backtesting/) | Backtest study | ES futures (15min, May-Oct 2025). Bearish engulfing (long entry): 75.76% win, PF 2.73, 33 trades. Hammer: 71.79% win, 78 trades, PF 1.94. Three white soldiers + RSI filter: 83.33% win, 36 trades. AAPL: Doji 65.98% win (97 trades). Morning star + MA filter: 51.85% (losing strategy). Shows that pattern + indicator filter combinations improve results significantly. |
| [STRIKE] | Strike.money, "Hammer Candlestick Pattern" (strike.money/technical-analysis/hammer-candlestick-pattern) | Analysis | Hammer appears in 8-12% of daily candles; after context filtering drops to 3-5%. Without confirmation: 45-50% reliability. With proper context: 60-70%. Bulkowski's data: 60.3% success rate when confirmed by breakout. Barry D. Moore: 52.1% win rate, 0.18% avg profit, Sharpe ratio -0.05. Lower shadow must be "at least 2-3x the length of the real body." |
| [BULKOWSKI-NR7] | Thomas Bulkowski, "Bulkowski on the NR7 Chart Pattern" (thepatternsite.com/nr7.html) | Backtest study | NR7 rank 11/23 chart patterns. 29,021 total trades at $10K/trade with 7% targets/stops. Bull/up: 57% win (13,391 trades), $78.79 avg net. Bull/down: 45% win (11,208 trades), -$55.52 avg net. Bear/down: 27% failure rate, -12% avg decline. NR7 in downtrends outperformed benchmarks for stocks ($163.84 vs $145.03). Crypto NR7: underperformed with limited 500-trade sample. |
| [AALTO] | Aalto University Master's Thesis, "Candlestick Patterns" (aaltodoc.aalto.fi) | Academic | Systematic review of candlestick pattern profitability studies. Notes that "most candlestick reversal patterns do not generate statistically significant mean returns" in isolation but can be improved with filters. |
| [LUND] | Lund University, "The Predictive Power of Candlestick Patterns" (lup.lub.lu.se) | Academic thesis | Empirical analysis of candlestick predictive power. Findings vary significantly by market and period. Supports the view that patterns work best as filters combined with other signals, not as standalone strategies. |
| [FHSU] | Fort Hays State University, "A Statistical Analysis of the Predictive Power of Japanese Candlestick Patterns" (scholars.fhsu.edu) | Academic paper | Concluded that candlestick charting methods "had no value for trading individual stocks" when used in isolation. Important caveat: patterns tested without any context (trend, S/R level, volume), which contradicts how they are designed to be used [NISON]. |

### 5.5 Algorithmic Implementation References

| ID | Source | Type | Key Contributions |
|----|--------|------|-------------------|
| [MDPI-CRYPTO] | Adamczyk & Nika, "Candlestick Pattern Recognition in Cryptocurrency Price Time-Series Data Using Rule-Based Data Analysis Methods," *Computation* 12(7):132, MDPI (2024) | Academic paper | Rule-based detection for crypto (ETH, BTC, LTC). Distinguishes "objective" criteria (strict OHLC relationships) from "subjective" criteria (LONG-BODY, SHORT-SHADOW requiring thresholds). Compares current candle range to average of last 21 candles to define body size. Uses EDGE_RATIO = 0.1 for shadow significance. Dragonfly doji: upper shadow <= range * 0.1, total range > 3x body. |
| [NETPICKS] | Netpicks, "NR5 and NR7 Inside Bar Trading Guide" (netpicks.com/nr7-inside-bar/) | Article | NR7 + Inside Bar combination (ID/NR pattern). Contraction/expansion principle: volatility expansion often follows volatility contraction (analogous to Bollinger Band Squeeze). |
| [FOREXTRAINING] | Forex Training Group, "Simple Tactics for Trading Narrow Range Bars" (forextraininggroup.com) | Article | NR4, NR7, NR4/ID pattern definitions. Range calculation: High - Low for each bar. NR7 = current bar range is smallest of last 7 bars. Breakout entry: buy above NR bar high, sell below NR bar low. |
| [CHARTSCHOOL-NR7] | StockCharts ChartSchool, "Narrow Range Day NR7" (chartschool.stockcharts.com) | Reference | Formal NR7 definition and trading model. Originated by Toby Crabel. |
| [ATGT] | Above the Green Line, "Inside Bar Trading Strategy" (abovethegreenline.com/inside-bar-trading-strategy/) | Article | Inside bar quality criteria: "forms after a strong directional move or within a clear trend. The mother bar is well-defined and meaningful, not a tiny or random candle. The inside bar is proportionally smaller, showing real compression rather than noise." Context-dependent win rates vary heavily. |

### 5.6 Default Threshold Rationale

The following table documents why each default threshold was chosen, cross-referencing sources:

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| Doji `body_threshold` | 0.10 (10%) | [KB-07] uses 10%. [CM45T3R] uses 10%. [LUXALGO] uses 5%. [LINNSOFT] uses 0.50% of price (different metric). [MDPI-CRYPTO] uses body compared to 21-candle average range. We use 10% of range as a balanced default that catches most dojis without being so strict that valid dojis are missed. Users can tighten to 0.05 for stricter detection. 10% matches the consensus of rule-based implementations. |
| Hammer `wick_ratio` | 2.0 | [KB-07] specifies "2x+ body length". [LUXALGO] specifies "at least twice the length of the body". [CM45T3R] uses 2x body. [NISON] uses qualitative "long lower shadow" -- 2x is the widely accepted quantitative interpretation. |
| Hammer `upper_wick_max` | 0.1 | [KB-07] specifies "Upper_Wick <= Body * 0.1". [CM45T3R] specifies body < 1/3 of range with minimal upper shadow. 10% of body allows for minor upper wicks while maintaining the hammer shape. |
| Marubozu `wick_tolerance` | 0.05 (5%) | [KB-07] specifies "Upper_Wick <= Range * 0.05" and "Lower_Wick <= Range * 0.05". [CM45T3R] uses shadows < 10% of body. [STOCKCHARTS] says "no shadow" but pure marubozu are rare in practice. 5% of range allows for near-perfect marubozu. |
| SpinningTop `body_max` | 0.30 (30%) | [CM45T3R] uses body < 30% of range. Distinguishes from doji (10%) on the small end and normal candles on the large end. [STOCKCHARTS] says "small bodies" without precise threshold. |
| SpinningTop `wick_min` | 0.20 (20%) | [CM45T3R] uses both wicks > 20% of range. Ensures both shadows are significant, distinguishing from hammer/shooting star (one-sided shadow dominance). |
| Engulfing (no params) | N/A | [KB-07], [NISON], [STOCKCHARTS], [TRENDSPIDER] all agree: second body completely contains first body. No threshold needed -- it is a binary structural condition. |
| Harami (no params) | N/A | [NISON], [STOCKCHARTS]: second body completely inside first body. Binary structural condition. [TRENDSPIDER] notes scoring variants (100 if matching both ends, 80 if one) but we use binary detection. |
| PiercingLine `min_penetration` | 0.50 (50%) | [KB-07]: "closes above midpoint of first". [STOCKCHARTS]: "closes above the midpoint of the body of the first day". [TRENDSPIDER]: ">50% of first body". 50% is the universally accepted minimum. |
| DarkCloudCover `min_penetration` | 0.50 (50%) | Mirror of piercing line. [TRENDSPIDER]: "Greg Morris prefers close below midpoint". [STOCKCHARTS]: "closes within first's body". 50% is the standard minimum. |
| TweezerTops/Bottoms `tolerance` | 0.01 (1%) | [CM45T3R] uses "1% tolerance" for matching highs/lows. Exact matches are rare in practice; 1% of average range captures the "approximately equal" criterion from [NISON]. |
| MorningStar/EveningStar `body_threshold` | 0.30 (30%) | The "star" (middle candle) must have a small body. [TRENDSPIDER]: "short body". [KB-07]: "small-bodied candle". 30% of range is generous enough to catch most stars while excluding full-bodied candles. The third candle's midpoint penetration criterion (from [TRENDSPIDER] >50%) provides the primary validation. |
| ThreeWhiteSoldiers/BlackCrows `min_body_ratio` | 0.50 (50%) | [TRENDSPIDER]: "no dramatic size reduction", "no/very short upper shadows". [STOCKCHARTS]: "consecutive long bodies". 50% body-to-range ensures strong-bodied candles, not spinning tops or dojis. |
| PinBar `wick_ratio` | 2.0 | [KB-07]: "2x+ body". [TSR]: "long and distinct tail". Same rationale as hammer -- 2x is the standard minimum for "long wick" classification. |
| PinBar `body_position` | 0.33 (33%) | Body must be in the upper/lower third of the range. [KB-07]: "small body in upper/lower portion". 33% ensures the body is firmly at one end of the candle. |
| NarrowRange `lookback` | 7 | [CHARTSCHOOL-NR7], [FOREXTRAINING], [NETPICKS]: NR7 is the standard. Originated by Toby Crabel. NR4 available by setting lookback=4. |

### 5.7 Empirical Performance Summary

The following table consolidates empirical data from multiple sources to document expected pattern reliability. These are not guarantees -- they inform users about historical performance and help set expectations.

| Pattern | Win Rate | Sample Size | Source | Notes |
|---------|----------|-------------|--------|-------|
| Inverted Hammer | 60% | 1,702 trades | [LST] | Most reliable single pattern in the study. 1.12% profit/trade. |
| Hammer | 52-72% | varies | [STRIKE], [TRADESVIZ] | 52.1% without context [STRIKE], 60.3% with breakout confirmation [BULKOWSKI], 71.79% on ES 15min [TRADESVIZ]. Context matters enormously. |
| Bearish Engulfing | 57-76% | 4,096+ | [LST], [TRADESVIZ] | 57% on daily charts [LST]. 75.76% on ES 15min with volume [TRADESVIZ]. |
| Gravestone Doji | 57% | 1,553 trades | [LST] | 0.65% profit/trade. |
| Bearish Marubozu | 56.1% | 4,994 trades | [LST] | 0.8% profit/trade. |
| Doji | 66% | 8,029+ trades | [LST], [TRADESVIZ] | 65.98% on AAPL [TRADESVIZ]. |
| Spinning Top | 55.9% | 9,894 trades | [LST] | 3.7% avg win. |
| Three White Soldiers + RSI | 83.33% | 36 trades | [TRADESVIZ] | Small sample but shows pattern + indicator filter power. |
| Morning Star + MA | 51.85% | 54 trades | [TRADESVIZ] | Losing strategy on AAPL (-2.41%). Context-dependent. |
| Dark Cloud Cover | ~60% | varies | [BULKOWSKI] | "Depends heavily on market structure, timeframe, and context." |
| NR7 (bull/up breakout) | 57% | 13,391 trades | [BULKOWSKI-NR7] | $78.79 avg net profit at $10K/trade. 46% failure rate (5% move threshold). |
| NR7 (bear/down breakout) | 53% | 352 trades | [BULKOWSKI-NR7] | 27% failure rate but small sample. -12% avg decline. |
| Harami | 72.85% | varies | backtest surveys | Highest among two-day patterns per multiple survey aggregations. |

**Key takeaway from empirical data:** No candlestick pattern reliably exceeds ~60% win rate in isolation on daily charts [AALTO], [LUND], [FHSU]. However, patterns combined with context filters (trend direction, S/R levels, volume, other indicators) can achieve 65-85% win rates [TRADESVIZ]. This validates our architecture: pattern indicators detect shapes (the structural fact), pattern TRIGGER signals fire on detection, and FILTER signals combine with other signals in strategies for context.

### 5.8 Docstring Reference Format

Each pattern indicator and signal docstring will include a `References:` line citing the sources that informed its detection logic. Format:

```
References: [NISON], [KB-07], [CM45T3R]
```

This provides traceability from code to source material without cluttering the docstring with full citations. The full reference table is in this plan document and will also be added to the KB documentation update (Step 7).
