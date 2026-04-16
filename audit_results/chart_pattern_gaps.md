# Chart Pattern Gap Analysis

**Date**: 2026-04-15

## What We Have

27 **candlestick patterns** -- all implementations match reference standards (Nison, Bulkowski, KB-07). All thresholds verified against academic sources. All use relative (percentage-based) metrics that work across all markets and timeframes. 25/27 fully parameterized.

## What We're Missing

Our pattern library covers only one category of chart patterns: **single/multi-bar candlestick formations**. There are 7 major categories of chart patterns used in production trading that we don't have.

### Priority A -- High Value, Should Add

**1. Classical Chart Formations**
- Head & Shoulders / Inverse Head & Shoulders
- Double Top / Double Bottom
- Triple Top / Triple Bottom
- Triangles: Ascending, Descending, Symmetrical
- Wedges: Rising, Falling
- Flags / Pennants (Bullish, Bearish)
- Cup & Handle
- Rounding Bottom / Rounding Top
- Rectangle / Channel

Complexity: Medium-high. Requires swing point detection, trendline fitting, pattern region recognition.
Value: Very high. These are institutional bread-and-butter patterns for swing trading.

**2. Support & Resistance**
- Horizontal S/R levels (price clustering detection)
- Trendline S/R (uptrend/downtrend lines)
- Dynamic S/R (MAs acting as support/resistance)
- Pivot Points (daily/weekly/monthly using standard formulas)
- Prior high/low key levels
- Breakout & retest detection

Complexity: Medium. Pivot points are simple formulas. Horizontal S/R needs clustering. Trendlines need line fitting.
Value: Very high. Professional traders confirm patterns at S/R levels.

**3. Pattern Confluence**
- Multiple candlestick patterns confirming same direction
- Pattern + indicator convergence (e.g., hammer + RSI oversold + at support)
- Timeframe confluence (hourly pattern confirmed by daily trend)

Complexity: Low. Infrastructure is already in place. Just need composite signal functions.
Value: Very high. Most professional traders require confluence before entering trades.

### Priority B -- Important, Nice to Have

**4. Fibonacci**
- Retracements (38.2%, 50%, 61.8% levels after trends)
- Extensions (127.2%, 161.8% price targets)

Complexity: Medium. Requires swing point identification and trend measurement.
Value: Medium-high. Very popular in forex/crypto for entry targets.

**5. Harmonic Patterns**
- Gartley, Butterfly, Bat, Crab, Shark, Cypher

Complexity: High. Requires 4-point pattern identification with precise Fibonacci ratio validation.
Value: Medium-high. Devoted following in crypto. Precise entry/exit zones.

**6. Volume Pattern Composites**
- Volume climax (abnormally high volume + directionality)
- Volume dry-up (declining volume during consolidation)
- Pattern + volume confirmation signals

Complexity: Low-medium. We already have 9 volume indicators and 22 volume signals. Need composites.
Value: High. "Volume is God" -- dramatically improves pattern reliability.

### Priority C -- Lower Priority

**7. Price Action Extensions**
- Key reversals, island reversals, gap classification

Complexity: Low-medium. Gap detection is straightforward.
Value: Medium (lower in crypto due to 24/7 trading).

**8. Elliott Wave**
- Wave counts, impulse/correction identification

Complexity: Very high. Probabilistic, not deterministic. Multiple valid interpretations.
Value: Low. Disputed statistical validity. Most quant traders avoid it.

## Implementation Issues Found

### Issue 1: PiercingLine & DarkCloudCover Gap Requirement (Medium Severity)

`pattern_indicators.py:396` and `:425` require `open < prev_low` (gap down) and `open > prev_high` (gap up). In 24/7 crypto markets, gaps are extremely rare. Result: 0 detections on BTC daily data.

**Fix**: Add `require_gap` parameter (default True for backward compat). With `require_gap=False`, relax to `open < prev_close` which still requires bearish/bullish continuation but doesn't need an actual gap.

### Issue 2: TwoBarReversal Hardcoded Quarter (Low Severity)

`pattern_indicators.py:803` hardcodes `quarter = 0.25` for "close near high/low" detection. Should be a configurable parameter for different timeframes.

**Fix**: Add `close_proximity` parameter (default 0.25, range 0.1-0.5).

## Recommendations

1. **Highest ROI next step**: Pattern Confluence signals. Low complexity, very high value. We already have all the building blocks.
2. **Biggest capability gap**: Classical Chart Formations (H&S, triangles, flags). This is what separates a candlestick library from a full chart pattern library. Medium-high complexity but very high institutional value.
3. **Quick win**: Support & Resistance via Pivot Points. Simple formulas, high value, complements existing patterns.
4. **Fix crypto issue**: PiercingLine/DarkCloudCover gap relaxation. 2 patterns affected, medium impact.
