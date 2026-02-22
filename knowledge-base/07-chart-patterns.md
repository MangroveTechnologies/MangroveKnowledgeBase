# 7. Chart Patterns

This document provides a comprehensive reference for technical chart patterns used in trading, including candlestick patterns, multi-bar formations, and classical chart patterns. Pattern recognition is a core skill for discretionary and systematic traders alike.

---

## 7.1 Candlestick Patterns

### Definition

Candlestick patterns are formations created by one or more candlesticks that provide visual insight into market sentiment and potential price direction. Originating from Japanese rice traders in the 18th century, they remain one of the most widely used technical analysis tools.

### Core Principles

- **Psychology Reflection**: Candlesticks show the battle between buyers and sellers
- **Context Dependency**: Patterns mean different things in different contexts
- **Confirmation Required**: Most patterns require confirmation from subsequent price action
- **Location Matters**: Patterns at key levels (support/resistance) are more significant
- **Timeframe Relevance**: Higher timeframe patterns carry more weight

### Common Use Cases

- Identifying potential reversal points
- Confirming trend continuation
- Timing entries and exits
- Reading short-term sentiment shifts
- Filtering trade signals

---

### Single Candlestick Patterns

#### Doji
**Structure:** Open and close at nearly the same price, forming a cross or plus sign.

**Variations:**
- **Standard Doji**: Equal upper and lower wicks
- **Long-Legged Doji**: Very long upper and lower wicks
- **Dragonfly Doji**: Long lower wick, no upper wick (bullish at support)
- **Gravestone Doji**: Long upper wick, no lower wick (bearish at resistance)

**Interpretation:** Indecision between buyers and sellers. At trend extremes, signals potential reversal.

**Detection Logic:**
```
Doji = |Close - Open| <= (High - Low) * 0.1
```

---

#### Hammer / Hanging Man
**Structure:** Small body at upper end, long lower wick (2x+ body length), little or no upper wick.

**Hammer (Bullish):**
- Appears after a downtrend
- Long lower wick shows rejection of lower prices
- Bullish reversal signal

**Hanging Man (Bearish):**
- Appears after an uptrend
- Same structure as hammer but bearish context
- Warning of potential top

**Detection Logic:**
```
Lower_Wick >= 2 * Body
Upper_Wick <= Body * 0.1
Body in upper 25% of range
```

---

#### Inverted Hammer / Shooting Star
**Structure:** Small body at lower end, long upper wick (2x+ body length), little or no lower wick.

**Inverted Hammer (Bullish):**
- Appears after a downtrend
- Shows buying attempt; needs confirmation
- Less reliable than hammer

**Shooting Star (Bearish):**
- Appears after an uptrend
- Long upper wick shows rejection of higher prices
- Bearish reversal signal

**Detection Logic:**
```
Upper_Wick >= 2 * Body
Lower_Wick <= Body * 0.1
Body in lower 25% of range
```

---

#### Marubozu
**Structure:** Full body candle with no wicks (or very small wicks).

**Bullish Marubozu:** Opens at low, closes at high. Strong buying pressure.
**Bearish Marubozu:** Opens at high, closes at low. Strong selling pressure.

**Interpretation:** Extreme conviction in direction. Often signals continuation.

**Detection Logic:**
```
Upper_Wick <= Range * 0.05
Lower_Wick <= Range * 0.05
```

---

#### Spinning Top
**Structure:** Small body with upper and lower wicks of similar length.

**Interpretation:** Indecision, similar to doji but with a small body. Less significant than doji.

---

### Two-Candlestick Patterns

#### Engulfing Pattern
**Structure:** Second candle completely engulfs the body of the first candle.

**Bullish Engulfing:**
- First candle: bearish (red/black)
- Second candle: bullish (green/white) that engulfs first
- Appears at support / after downtrend
- Strong reversal signal

**Bearish Engulfing:**
- First candle: bullish
- Second candle: bearish that engulfs first
- Appears at resistance / after uptrend
- Strong reversal signal

**Detection Logic:**
```
Bullish_Engulfing:
  Close[1] < Open[1]  // First candle bearish
  Close[0] > Open[0]  // Second candle bullish
  Open[0] < Close[1]  // Opens below first close
  Close[0] > Open[1]  // Closes above first open
```

---

#### Harami (Inside Bar)
**Structure:** Second candle's body is completely contained within the first candle's body.

**Bullish Harami:**
- Large bearish candle followed by small bullish candle inside
- Potential bullish reversal

**Bearish Harami:**
- Large bullish candle followed by small bearish candle inside
- Potential bearish reversal

**Interpretation:** Decreasing momentum; potential trend change. Less strong than engulfing.

---

#### Piercing Line / Dark Cloud Cover
**Piercing Line (Bullish):**
- First candle: bearish
- Second candle: opens below first's low, closes above midpoint of first
- Bullish reversal at support

**Dark Cloud Cover (Bearish):**
- First candle: bullish
- Second candle: opens above first's high, closes below midpoint of first
- Bearish reversal at resistance

---

#### Tweezer Tops / Bottoms
**Structure:** Two or more candles with matching highs (tops) or lows (bottoms).

**Tweezer Top:** Matching highs after uptrend - bearish reversal
**Tweezer Bottom:** Matching lows after downtrend - bullish reversal

**Interpretation:** Price rejection at same level twice indicates strong support/resistance.

---

### Three-Candlestick Patterns

#### Morning Star / Evening Star
**Morning Star (Bullish):**
1. Large bearish candle
2. Small-bodied candle (star) that gaps down
3. Large bullish candle that closes above midpoint of first candle

**Evening Star (Bearish):**
1. Large bullish candle
2. Small-bodied candle (star) that gaps up
3. Large bearish candle that closes below midpoint of first candle

**Interpretation:** Strong reversal patterns. More significant with gap between star and surrounding candles.

---

#### Three White Soldiers / Three Black Crows
**Three White Soldiers (Bullish):**
- Three consecutive bullish candles
- Each opens within previous body, closes near high
- Strong bullish momentum / reversal

**Three Black Crows (Bearish):**
- Three consecutive bearish candles
- Each opens within previous body, closes near low
- Strong bearish momentum / reversal

---

#### Three Inside Up / Down
**Three Inside Up (Bullish):**
1. Bearish candle
2. Bullish candle that forms inside bar
3. Bullish candle that closes above first candle's high

**Three Inside Down (Bearish):**
1. Bullish candle
2. Bearish candle that forms inside bar
3. Bearish candle that closes below first candle's low

---

### Best Practices for Candlestick Patterns

- Always consider the preceding trend and context
- Look for patterns at key support/resistance levels
- Require confirmation before acting (next candle)
- Higher timeframe patterns are more reliable
- Combine with volume analysis for confirmation
- Don't trade patterns in isolation; use confluence

---

## 7.2 Multi-Bar Patterns

### Definition

Multi-bar patterns are price formations spanning multiple candlesticks that reveal consolidation, momentum shifts, and potential breakout setups beyond traditional candlestick patterns.

### Core Principles

- **Consolidation**: Multiple bars often indicate pauses before continuation or reversal
- **Energy Building**: Tight consolidations store energy for subsequent moves
- **Breakout Direction**: Often (but not always) continues prior trend
- **Volume Significance**: Volume patterns within consolidations provide clues

---

### Inside Bar

**Structure:** A bar whose entire range (high to low) is contained within the previous bar's range.

**Interpretation:**
- Consolidation / pause in trend
- Decreasing volatility
- Breakout expected in either direction
- Often traded as breakout setup

**Trading Application:**
- Entry: Break of inside bar high (long) or low (short)
- Stop: Opposite side of inside bar
- Target: Measured move or next support/resistance

**Detection Logic:**
```
Inside_Bar:
  High[0] < High[1]
  Low[0] > Low[1]
```

---

### Outside Bar (Engulfing Bar)

**Structure:** A bar whose range completely engulfs the previous bar's range.

**Interpretation:**
- Increased volatility
- Potential reversal or strong continuation
- Direction often determined by close

**Trading Application:**
- Bullish: Close near high, at support
- Bearish: Close near low, at resistance

**Detection Logic:**
```
Outside_Bar:
  High[0] > High[1]
  Low[0] < Low[1]
```

---

### Pin Bar

**Structure:** A bar with a long wick (tail) representing rejection of a price level, with a small body opposite the wick.

**Bullish Pin Bar:**
- Long lower wick (2x+ body)
- Small body in upper portion
- Close above midpoint of range
- Found at support

**Bearish Pin Bar:**
- Long upper wick (2x+ body)
- Small body in lower portion
- Close below midpoint of range
- Found at resistance

**Trading Application:**
- Entry: Break of pin bar in direction of signal
- Stop: Beyond the wick
- High probability at key levels with trend

---

### Two-Bar Reversal

**Structure:** Two consecutive bars forming a reversal pattern at an extreme.

**Bullish Two-Bar Reversal:**
- First bar: Strong bearish close
- Second bar: Strong bullish close, closes above first bar's open
- Combined forms a hammer-like structure

**Bearish Two-Bar Reversal:**
- First bar: Strong bullish close
- Second bar: Strong bearish close, closes below first bar's open
- Combined forms a shooting star-like structure

---

### NR4 / NR7 (Narrow Range)

**Structure:** 
- NR4: Narrowest range of the last 4 bars
- NR7: Narrowest range of the last 7 bars

**Interpretation:**
- Volatility compression
- Breakout imminent
- Direction unknown until breakout

**Trading Application:**
- Trade breakout of NR bar's range
- Often combined with trend filter for direction bias

**Detection Logic:**
```
NR7:
  Range[0] < min(Range[1], Range[2], ..., Range[6])
```

---

### Best Practices for Multi-Bar Patterns

- Combine with trend direction for higher probability
- Use at key support/resistance levels
- Wait for confirmation break before entry
- Size stops based on pattern structure
- Note that inside bars after strong moves often continue

---

## 7.3 Chart Patterns

### Definition

Chart patterns are recognizable price formations that develop over multiple bars or candles, representing periods of consolidation, accumulation, distribution, or continuation. They provide structure for entries, stops, and targets.

### Core Principles

- **Psychology Mapping**: Patterns reflect collective trader psychology
- **Measured Moves**: Most patterns have target projections
- **Failure Mode**: Failed patterns often lead to strong moves opposite
- **Volume Profile**: Volume typically decreases during formation, expands on breakout
- **Time Proportionality**: Pattern duration often relates to subsequent move duration

---

### Head and Shoulders

**Structure:**
- Left Shoulder: Rally and decline
- Head: Higher rally and decline to similar level (neckline)
- Right Shoulder: Lower rally and decline
- Neckline: Connect the lows after each shoulder

**Interpretation:** Distribution pattern; bearish reversal after uptrend.

**Trading Application:**
- Entry: Break below neckline
- Stop: Above right shoulder
- Target: Measured move (head to neckline distance projected down)

**Detection Logic:**
```
Head > Left_Shoulder > Neckline
Head > Right_Shoulder > Neckline
Right_Shoulder approximately equals Left_Shoulder height
Both shoulders retrace to approximately same neckline level
```

---

### Inverse Head and Shoulders

**Structure:** Mirror image of head and shoulders.
- Left Shoulder: Decline and rally
- Head: Lower decline and rally
- Right Shoulder: Higher decline and rally
- Neckline: Connect the highs

**Interpretation:** Accumulation pattern; bullish reversal after downtrend.

**Trading Application:**
- Entry: Break above neckline
- Stop: Below right shoulder
- Target: Measured move (head to neckline distance projected up)

---

### Double Top / Double Bottom

**Double Top (Bearish):**
- Two peaks at approximately the same price level
- Valley between peaks (neckline)
- Failure to exceed first peak indicates weakening
- Entry: Break below valley
- Target: Distance from peaks to valley projected down

**Double Bottom (Bullish):**
- Two troughs at approximately the same price level
- Peak between troughs (neckline)
- Failure to break first low indicates support
- Entry: Break above peak
- Target: Distance from troughs to peak projected up

**Detection Logic:**
```
Double_Top:
  |High_Peak1 - High_Peak2| < threshold
  Valley_Low < both Peak_Highs
  Confirmation: Close below Valley_Low
```

---

### Triple Top / Triple Bottom

**Structure:** Similar to double top/bottom but with three peaks/troughs.

**Interpretation:** Stronger reversal signal than double top/bottom due to additional test.

**Trading Application:** Same as double top/bottom but often more reliable.

---

### Triangles

**Ascending Triangle (Typically Bullish):**
- Horizontal resistance line (flat tops)
- Rising support line (higher lows)
- Buyers becoming more aggressive
- Breakout typically upward (70% of cases)

**Descending Triangle (Typically Bearish):**
- Horizontal support line (flat bottoms)
- Falling resistance line (lower highs)
- Sellers becoming more aggressive
- Breakout typically downward (70% of cases)

**Symmetrical Triangle (Neutral):**
- Converging trend lines
- Lower highs and higher lows
- Consolidation pattern
- Breakout direction determines trend

**Triangle Trading:**
- Entry: Breakout beyond triangle boundary
- Stop: Opposite side of triangle or last swing
- Target: Height of triangle base projected from breakout

**Detection Logic:**
```
Ascending_Triangle:
  High values form horizontal line (within tolerance)
  Low values form upward sloping line
  Lines converging
```

---

### Flags and Pennants

**Bull Flag:**
- Sharp rally (flagpole)
- Consolidation that slopes against trend (parallel channel down)
- Continuation pattern
- Entry: Break above flag resistance
- Target: Flagpole length projected from breakout

**Bear Flag:**
- Sharp decline (flagpole)
- Consolidation that slopes against trend (parallel channel up)
- Continuation pattern
- Entry: Break below flag support
- Target: Flagpole length projected from breakout

**Pennant:**
- Similar to flag but consolidation forms symmetrical triangle
- Very short-term pattern (1-3 weeks typically)
- Strong continuation pattern

---

### Wedges

**Rising Wedge (Bearish):**
- Both support and resistance lines slope upward
- Resistance line has gentler slope
- Lines converge
- Typically bearish regardless of trend context
- Breakout usually downward

**Falling Wedge (Bullish):**
- Both support and resistance lines slope downward
- Support line has gentler slope
- Lines converge
- Typically bullish regardless of trend context
- Breakout usually upward

---

### Channels

**Ascending Channel:**
- Parallel upward sloping lines containing price
- Buy at lower channel line
- Sell at upper channel line
- Channel break can signal acceleration or reversal

**Descending Channel:**
- Parallel downward sloping lines containing price
- Sell at upper channel line
- Cover at lower channel line
- Channel break can signal acceleration or reversal

**Horizontal Channel (Rectangle):**
- Horizontal parallel lines containing price
- Range-bound trading
- Breakout direction determines next trend

---

### Cup and Handle

**Structure:**
- Cup: Rounded bottom formation (U-shape, not V)
- Handle: Small consolidation after cup (slight downward drift)
- Bullish continuation pattern

**Trading Application:**
- Entry: Break above handle resistance / cup rim
- Stop: Below handle low
- Target: Depth of cup projected from breakout

---

### Best Practices for Chart Patterns

- Identify patterns in context of larger trend
- Volume should confirm pattern (decrease during formation, increase on breakout)
- Wait for pattern completion and confirmation
- Calculate risk/reward before entering
- Recognize that 30-40% of breakouts fail; manage risk accordingly
- Failed patterns provide trading opportunities in opposite direction

---

## 7.4 Algorithmic / Programmatic Patterns

### Definition

Algorithmic patterns are price formations that can be systematically detected and traded through programmatic rules, suitable for automated trading systems.

### Core Principles

- **Objective Definition**: Patterns must have precise, programmable criteria
- **Parameter Sensitivity**: Results depend heavily on detection parameters
- **Backtestable**: Patterns should be testable on historical data
- **False Positives**: Algorithms may detect patterns humans would ignore
- **Optimization Risk**: Over-optimization leads to curve fitting

---

### Swing Point Detection

**Algorithm:**
```python
def is_swing_high(data, i, lookback=5):
    if i < lookback or i >= len(data) - lookback:
        return False
    high = data['high'][i]
    for j in range(i - lookback, i + lookback + 1):
        if j != i and data['high'][j] >= high:
            return False
    return True

def is_swing_low(data, i, lookback=5):
    if i < lookback or i >= len(data) - lookback:
        return False
    low = data['low'][i]
    for j in range(i - lookback, i + lookback + 1):
        if j != i and data['low'][j] <= low:
            return False
    return True
```

---

### Trend Line Detection

**Algorithm Concept:**
1. Identify swing points (highs and lows)
2. Connect swing points with lines
3. Validate: Minimum touches (typically 3+)
4. Validate: Points approximately collinear (R-squared threshold)
5. Project line forward for support/resistance

---

### Support/Resistance Level Detection

**Algorithm:**
```python
def find_sr_levels(data, window=20, threshold=0.02):
    levels = []
    for i in range(window, len(data) - window):
        if is_swing_high(data, i, window):
            levels.append(('resistance', data['high'][i]))
        if is_swing_low(data, i, window):
            levels.append(('support', data['low'][i]))
    
    # Cluster nearby levels
    clustered = cluster_levels(levels, threshold)
    return clustered
```

---

### Pattern Recognition Libraries

**TA-Lib Patterns (61 candlestick patterns):**
- CDL2CROWS, CDL3BLACKCROWS, CDL3INSIDE, CDL3LINESTRIKE
- CDL3OUTSIDE, CDL3STARSINSOUTH, CDL3WHITESOLDIERS
- CDLABANDONEDBABY, CDLADVANCEBLOCK, CDLBELTHOLD
- CDLBREAKAWAY, CDLCLOSINGMARUBOZU, CDLCONCEALBABYSWALL
- CDLCOUNTERATTACK, CDLDARKCLOUDCOVER, CDLDOJI
- CDLDOJISTAR, CDLDRAGONFLYDOJI, CDLENGULFING
- CDLEVENINGDOJISTAR, CDLEVENINGSTAR, CDLGAPSIDESIDEWHITE
- CDLGRAVESTONEDOJI, CDLHAMMER, CDLHANGINGMAN
- CDLHARAMI, CDLHARAMICROSS, CDLHIGHWAVE
- CDLHIKKAKE, CDLHIKKAKEMOD, CDLHOMINGPIGEON
- CDLIDENTICAL3CROWS, CDLINNECK, CDLINVERTEDHAMMER
- CDLKICKING, CDLKICKINGBYLENGTH, CDLLADDERBOTTOM
- CDLLONGLEGGEDDOJI, CDLLONGLINE, CDLMARUBOZU
- CDLMATCHINGLOW, CDLMATHOLD, CDLMORNINGDOJISTAR
- CDLMORNINGSTAR, CDLONNECK, CDLPIERCING
- CDLRICKSHAWMAN, CDLRISEFALL3METHODS, CDLSEPARATINGLINES
- CDLSHOOTINGSTAR, CDLSHORTLINE, CDLSPINNINGTOP
- CDLSTALLEDPATTERN, CDLSTICKSANDWICH, CDLTAKURI
- CDLTASUKIGAP, CDLTHRUSTING, CDLTRISTAR
- CDLUNIQUE3RIVER, CDLUPSIDEGAP2CROWS, CDLXSIDEGAP3METHODS

**Usage:**
```python
import talib

# Returns: 100 (bullish), -100 (bearish), 0 (no pattern)
pattern = talib.CDLENGULFING(open, high, low, close)
```

---

### Best Practices for Algorithmic Patterns

- Start with simple, well-defined patterns
- Use multiple confirmation filters
- Backtest extensively with out-of-sample data
- Account for transaction costs and slippage
- Avoid over-optimization of pattern parameters
- Combine pattern detection with other filters (trend, volume)

---

## 7.5 Pattern Reliability & Failure Modes

### Definition

Pattern reliability refers to the historical success rate of patterns in predicting subsequent price movement. Failure modes are the ways patterns fail to produce expected outcomes and the trading implications of those failures.

### Core Principles

- **No Pattern is 100%**: All patterns have failure rates
- **Context Affects Success**: Same pattern works differently in different contexts
- **Failed Patterns Signal**: A failed pattern often leads to strong move opposite
- **Confirmation Matters**: Unconfirmed patterns have lower reliability
- **Sample Size**: Published statistics vary; test on your markets

---

### Reliability Statistics (General Guidelines)

| Pattern | Direction | Reliability | Notes |
|---------|-----------|-------------|-------|
| Head & Shoulders | Reversal | 70-75% | Higher with volume confirmation |
| Double Top/Bottom | Reversal | 65-70% | Second test often doesn't reach exact level |
| Ascending Triangle | Bullish | 70% | Can break down |
| Descending Triangle | Bearish | 70% | Can break up |
| Symmetrical Triangle | Neutral | 50-55% | Direction unpredictable |
| Bull Flag | Bullish | 65-70% | Best after strong pole |
| Bear Flag | Bearish | 65-70% | Best after strong pole |
| Engulfing (Bullish) | Bullish | 60-65% | Context dependent |
| Engulfing (Bearish) | Bearish | 60-65% | Context dependent |
| Hammer | Bullish | 60% | Needs confirmation |
| Shooting Star | Bearish | 60% | Needs confirmation |

---

### Common Failure Modes

**False Breakout:**
- Pattern completes, price breaks out
- Price quickly reverses back into pattern
- Often leads to move in opposite direction
- Mitigation: Wait for confirmation, use close-based breakouts

**Premature Entry:**
- Entering before pattern completes
- Pattern morphs into different formation
- Mitigation: Wait for completion and confirmation

**Late Entry:**
- Entering long after breakout
- Miss optimal risk/reward
- Chasing leads to poor entries
- Mitigation: Define entry rules; accept missed trades

**Wrong Context:**
- Pattern appears in wrong market context
- E.g., bullish pattern in strong downtrend
- Mitigation: Align patterns with higher timeframe trend

---

### Trading Failed Patterns

**Principle:** A failed pattern often leads to a strong move in the opposite direction.

**Failed Breakout Strategy:**
1. Pattern completes and breaks out
2. Breakout fails (price reverses back into pattern)
3. Enter in direction opposite to failed breakout
4. Stop beyond the false breakout extreme
5. Target: Opposite side of pattern or larger

**Example - Failed Bull Flag:**
- Bull flag forms after rally
- Price breaks above flag (expected bullish breakout)
- Price quickly reverses, breaks below flag
- This is bearish - enter short below flag
- Target: Distance of flagpole projected down

---

### Best Practices for Managing Pattern Risk

- Never risk more than planned regardless of pattern "quality"
- Always define invalidation level before entry
- Use confirmation (close beyond level, volume, follow-through)
- Accept that 30-40% of patterns fail
- Have plan for failed patterns (reverse, stand aside, reassess)
- Track your own statistics for patterns you trade

---

## 7.6 Pattern Context Requirements

### Definition

Pattern context refers to the market conditions and technical environment that must be present for a pattern to be valid and tradeable. Context determines whether a pattern is high probability or should be avoided.

### Core Principles

- **Trend Alignment**: Patterns aligned with trend are more reliable
- **Location**: Patterns at key levels have higher significance
- **Market Regime**: Patterns behave differently in trends vs. ranges
- **Timeframe Hierarchy**: Higher timeframe context overrides lower
- **Confluence**: Multiple supporting factors increase probability

---

### Contextual Requirements by Pattern Type

**Reversal Patterns (Head & Shoulders, Double Top/Bottom, etc.):**
- MUST appear after established trend
- MUST be at significant support/resistance level
- SHOULD have increasing volume on reversal
- SHOULD align with higher timeframe levels
- AVOID in middle of trend with no prior structure

**Continuation Patterns (Flags, Pennants, Triangles):**
- MUST appear within established trend
- MUST be preceded by impulse move
- SHOULD show decreasing volume during formation
- SHOULD break in trend direction
- AVOID if pattern is larger than preceding move

**Candlestick Reversal Patterns:**
- MUST be at support (bullish) or resistance (bearish)
- MUST be at extreme of move (not middle)
- SHOULD have prior trend to reverse
- SHOULD be confirmed by next candle
- AVOID isolated patterns in middle of range

---

### Location-Based Context

**At Support:**
- Bullish reversal patterns are valid
- Bearish patterns are counter-contextual
- Failed breaks below support are bullish

**At Resistance:**
- Bearish reversal patterns are valid
- Bullish patterns are counter-contextual
- Failed breaks above resistance are bearish

**In No Man's Land (Middle of Range):**
- Most patterns have reduced reliability
- Wait for price to reach extremes
- Continuation patterns require clear prior trend

---

### Timeframe Context

**Higher Timeframe Bullish:**
- Trade bullish patterns on lower timeframe
- Be cautious with bearish patterns
- Expect pullbacks to find support

**Higher Timeframe Bearish:**
- Trade bearish patterns on lower timeframe
- Be cautious with bullish patterns
- Expect rallies to find resistance

**Higher Timeframe Ranging:**
- Trade both directions at range extremes
- Expect failed breakouts
- Reduce position size

---

### Best Practices for Pattern Context

- Always check higher timeframe before trading patterns
- Identify key levels and only trade patterns at those levels
- Ensure pattern direction aligns with dominant trend
- Require confluence of at least 2-3 supporting factors
- Document context requirements for patterns you trade

---

## 7.7 Pattern Completion Criteria

### Definition

Pattern completion criteria are the specific conditions that must be met for a pattern to be considered complete and tradeable. Premature trading of incomplete patterns is a common source of losses.

### Core Principles

- **Completion Before Entry**: Don't anticipate; wait for completion
- **Clear Trigger**: Define exact completion trigger in advance
- **Volume Confirmation**: Breakout volume should exceed average
- **Time Element**: Some patterns have time-based components
- **Price Action Quality**: Breakout bar characteristics matter

---

### Completion Criteria by Pattern

**Head and Shoulders:**
- Completion: Close below neckline
- Confirmation: Volume increase on break
- Aggressive: Break of neckline intrabar
- Conservative: Close below neckline AND follow-through

**Double Top/Bottom:**
- Completion: Close beyond neckline (valley/peak)
- Confirmation: Retest of neckline holds
- Minimum depth: At least 10% from peak to valley

**Triangles:**
- Completion: Close beyond triangle boundary
- Timing: Preferably in last third of triangle (before apex)
- Volume: Expansion on breakout
- Note: Breakout within 2/3 of pattern length is ideal

**Flags/Pennants:**
- Completion: Break beyond flag/pennant boundary
- Volume: Decrease during flag, increase on break
- Time: Flag should be brief (5-15 bars typically)

**Cup and Handle:**
- Completion: Break above cup rim / handle high
- Handle depth: Less than 50% of cup depth
- Cup shape: U-shaped, not V-shaped

---

### Breakout Quality Assessment

**High-Quality Breakout:**
- Full candle close beyond pattern boundary
- Volume significantly above average
- Momentum (large-bodied candle)
- Follow-through on next bar

**Low-Quality Breakout:**
- Wick beyond boundary but close inside
- Below-average volume
- Small-bodied or doji candle
- No follow-through

---

### Entry Timing Options

**Aggressive Entry:**
- Enter on intrabar break of pattern boundary
- Tighter stop, larger potential move capture
- Higher failure rate

**Standard Entry:**
- Enter on close beyond pattern boundary
- Balanced approach
- Moderate failure rate

**Conservative Entry:**
- Enter on retest of broken boundary
- Confirmation of role reversal
- May miss some moves but better R:R

---

### Best Practices for Pattern Completion

- Define completion criteria before pattern appears
- Use close-based triggers for most patterns
- Require volume confirmation for breakouts
- Have rules for each entry timing option
- Don't chase if completion criteria weren't met at proper time

---

## Summary

Technical pattern recognition is both an art and a science. Key takeaways:

1. **Context is King**: Patterns mean nothing without proper context
2. **Confirmation Required**: Wait for patterns to complete and confirm
3. **Manage Failures**: Plan for pattern failures; they create opportunities
4. **Combine Methods**: Use patterns with indicators, volume, and structure
5. **Keep Statistics**: Track your success rate with different patterns
6. **Specialize**: Master a few patterns rather than superficially knowing many

Pattern trading success comes from disciplined application of well-defined criteria, not from memorizing hundreds of formations.

