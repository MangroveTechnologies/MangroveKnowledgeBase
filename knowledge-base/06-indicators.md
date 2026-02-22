# 6. Indicators

This document provides a comprehensive reference for technical indicators used in trading, organized by category. Each indicator includes its calculation, interpretation, and practical application guidelines.

## Signal Type Classifications

MangroveAI uses two signal types to categorize trading signals:

- **TRIGGER**: Discrete events that occur at specific moments (e.g., crossovers, breakouts). These signals fire once when conditions transition from false to true.
- **FILTER**: Continuous state conditions that remain true while conditions persist (e.g., price above MA, RSI overbought). These signals evaluate to true or false at each bar.

Note: Terms like "Entry" and "Exit" are context-dependent. Any signal can be used for entries, exits, or filters depending on your strategy design.

---

## 6.1 Trend Indicators

Trend indicators are mathematical calculations applied to price data to identify the direction and strength of market trends. They smooth price action to filter noise and reveal underlying directional bias, helping traders align with prevailing market momentum.

**Core Principles:**

- **Lag vs. Smoothing Trade-off**: More smoothing means more lag but cleaner signals
- **Trend Confirmation**: Indicators confirm trend direction, not predict reversals
- **Multiple Timeframe Agreement**: Trend indicators across timeframes should align
- **Trend Following**: Best used in trending markets, not ranges
- **Price Always Leads**: Indicators are derivatives of price; price changes first

**Common Use Cases:**

- Identifying trend direction for trade bias
- Dynamic support/resistance levels
- Entry triggers on pullbacks to moving averages
- Exit signals when trend indicators turn
- Filtering out counter-trend trades

---

### 6.1.1 Simple Moving Average (SMA)

#### Definition

The arithmetic mean of price over a specified number of periods.

#### Formula

```
SMA(n) = (P_1 + P_2 + ... + P_n) / n
```

#### Interpretation

- Price above SMA = Bullish bias
- Price below SMA = Bearish bias
- Slope indicates trend strength
- Common periods: 20 (short-term), 50 (medium), 200 (long-term)

#### Trading Applications

- 200 SMA as major trend filter
- Price crossing SMA as trend change signal
- Multiple SMA crossovers (Golden Cross: 50 crosses above 200; Death Cross: 50 crosses below 200)

---

#### MangroveAI API Reference

- **Indicator Class**: `SMA`
- **Category**: Trend
- **Required Data**: `close`
- **Parameters**:
  - `window`: Parameter for SMA calculation
- **Outputs**: `sma`
- **Usage Example**: `SMA.compute(data={'close': df['Close']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>is_above_sma</strong> — FILTER — Check if current price is above Simple Moving Average</summary>


#### Description
Check if current price is above Simple Moving Average

#### Parameters
- `window` (int, 1-1000, required): SMA window in bars

#### Usage
`{"name": "is_above_sma", "params": {"window": value}}`

</details>

<details markdown="1"><summary><strong>sma_cross_up</strong> — TRIGGER — Detect when fast SMA crosses above slow SMA (bullish entry signal)</summary>


#### Description
Detect when fast SMA crosses above slow SMA (bullish entry signal)

#### Parameters
- `window_fast` (int, 1-500, required): Fast window SMA window in bars
- `window_slow` (int, 1-1000, required): Slow window SMA window in bars

#### Usage
`{"name": "sma_cross_up", "params": {"window_fast": value, "window_slow": value}}`

</details>

<details markdown="1"><summary><strong>sma_cross_down</strong> — TRIGGER — Detect when fast SMA crosses below slow SMA (bearish exit signal)</summary>


#### Description
Detect when fast SMA crosses below slow SMA (bearish exit signal)

#### Parameters
- `window_fast` (int, 1-500, required): Fast window SMA window in bars
- `window_slow` (int, 1-1000, required): Slow window SMA window in bars

#### Usage
`{"name": "sma_cross_down", "params": {"window_fast": value, "window_slow": value}}`

</details>

<details markdown="1"><summary><strong>sma_crossover</strong> — TRIGGER — Detect SMA crossover signal with configurable direction (bullish or bearish)</summary>


#### Description
Detect SMA crossover signal with configurable direction (bullish or bearish)

#### Parameters
- `window_fast` (int, 1-500, required): Fast window SMA window in bars
- `window_slow` (int, 1-1000, required): Slow window SMA window in bars
- `direction` (str, optional, default="bullish"): Crossover direction: 'bullish' or 'bearish'

#### Usage
`{"name": "sma_crossover", "params": {"window_fast": value, "window_slow": value, "direction": value}}`

</details>

---

### 6.1.2 Exponential Moving Average (EMA)

#### Definition
A weighted moving average that gives more weight to recent prices, making it more responsive to new information.

#### Formula
```
EMA_t = (Price_t * k) + (EMA_(t-1) * (1-k))
Where k = 2 / (n + 1)
```

#### Interpretation
- More responsive than SMA to recent price changes
- Less lag but more sensitive to noise
- Popular periods: 8, 12, 21, 50, 200

#### Trading Applications
- Faster trend identification than SMA
- Short-term EMAs (8, 12, 21) for momentum
- EMA ribbons (multiple EMAs) for trend strength visualization

---


#### MangroveAI API Reference

- **Indicator Class**: `EMA`
- **Category**: Trend
- **Required Data**: `close`
- **Parameters**:
  - `window`: Parameter for EMA calculation
- **Outputs**: `ema`
- **Usage Example**: `EMA.compute(data={'close': df['Close']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>ema_cross_down</strong> — TRIGGER — Detect bearish EMA crossover (fast EMA crosses below slow EMA)</summary>


#### Description
Detect bearish EMA crossover (fast EMA crosses below slow EMA)

#### Parameters
- `window_fast` (int, 2-100, optional, default=9): Fast window EMA window
- `window_slow` (int, 5-200, optional, default=21): Slow window EMA window

#### Usage
`{"name": "ema_cross_down", "params": {"window_fast": value, "window_slow": value}}`

</details>

<details markdown="1"><summary><strong>ema_cross_up</strong> — TRIGGER — Detect bullish EMA crossover (fast EMA crosses above slow EMA)</summary>


#### Description
Detect bullish EMA crossover (fast EMA crosses above slow EMA)

#### Parameters
- `window_fast` (int, 2-100, optional, default=9): Fast window EMA window
- `window_slow` (int, 5-200, optional, default=21): Slow window EMA window

#### Usage
`{"name": "ema_cross_up", "params": {"window_fast": value, "window_slow": value}}`

</details>
<details markdown="1"><summary><strong>ema_crossover</strong> — TRIGGER — Detect EMA crossover signal with configurable direction (bullish or bearish) Common periods: 9/21 (short), 50/200 (long). Adjust for crypto's 24/7 markets.</summary>


#### Description
Detect EMA crossover signal with configurable direction (bullish or bearish) Common periods: 9/21 (short), 50/200 (long). Adjust for crypto's 24/7 markets.

#### Parameters
- `window_fast` (int, 1-500, required): Fast window EMA window in bars
- `window_slow` (int, 1-1000, required): Slow window EMA window in bars
- `direction` (str, optional, default="bullish"): Crossover direction: 'bullish' or 'bearish'

#### Usage
`{"name": "ema_crossover", "params": {"window_fast": value, "window_slow": value, "direction": value}}`

</details>


<details markdown="1"><summary><strong>price_above_ema</strong> — FILTER — Check if price is above the EMA</summary>


#### Description
Check if price is above the EMA

#### Parameters
- `window` (int, 2-200, optional, default=20): EMA window

#### Usage
`{"name": "price_above_ema", "params": {"window": value}}`

</details>

---

### 6.1.3 Double Exponential Moving Average (DEMA)

#### Definition
A smoothing indicator that attempts to eliminate lag associated with traditional moving averages by applying EMA calculation twice.

#### Formula
```
DEMA = 2 * EMA(n) - EMA(EMA(n))
```

#### Interpretation
- Less lag than standard EMA
- More responsive to price changes
- Smoother than single EMA

---

### 6.1.4 Triple Exponential Moving Average (TEMA)

#### Definition
Further reduces lag by applying EMA calculation three times.

#### Formula
```
TEMA = 3 * EMA - 3 * EMA(EMA) + EMA(EMA(EMA))
```

#### Interpretation
- Minimal lag among moving average variants
- Highly responsive but may generate more false signals
- Best for shorter-term trend identification

---

### 6.1.5 Average Directional Index (ADX)

#### Definition
Measures trend strength regardless of direction, derived from the Directional Movement Index (DMI) components +DI and -DI.

#### Formula
```
+DI = 100 * EMA(+DM) / ATR
-DI = 100 * EMA(-DM) / ATR
DX = 100 * |+DI - -DI| / (+DI + -DI)
ADX = EMA(DX, n periods, typically 14)
```

#### Interpretation
- ADX > 25: Strong trend
- ADX < 20: Weak trend / ranging
- ADX rising: Trend strengthening
- ADX falling: Trend weakening
- +DI > -DI: Uptrend; -DI > +DI: Downtrend

#### Trading Applications
- Filter trades based on trend strength (only trade when ADX > 25)
- Avoid trend strategies when ADX < 20
- Use DI crossovers for directional signals

---


#### MangroveAI API Reference

- **Indicator Class**: `ADX`
- **Category**: Trend
- **Required Data**: `high`, `low`, `close`
- **Parameters**:
  - `window`: Parameter for ADX calculation
- **Outputs**: `adx`, `adx_pos`, `adx_neg`
- **Usage Example**: `ADX.compute(data={'high': df['High'], 'low': df['Low'], 'close': df['Close']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>adx_bullish_di</strong> — FILTER — Check if +DI is greater than -DI (bullish directional movement)</summary>


#### Description
Check if +DI is greater than -DI (bullish directional movement)

#### Parameters
- `window` (int, 5-50, optional, default=14): ADX period

#### Usage
`{"name": "adx_bullish_di", "params": {"window": value}}`

</details>

<details markdown="1"><summary><strong>adx_strong_trend</strong> — FILTER — Check if ADX indicates a strong trend (above 25)</summary>


#### Description
Check if ADX indicates a strong trend (>25)

#### Parameters
- `window` (int, 5-50, optional, default=14): ADX period
- `threshold` (float, 15-50, optional, default=25.0): Trend strength threshold

#### Usage
`{"name": "adx_strong_trend", "params": {"window": value, "threshold": value}}`

</details>

---

### 6.1.6 Parabolic SAR

#### Definition
Stop and Reverse system that provides potential entry/exit points by plotting dots above or below price, indicating trend direction and potential reversal points.

#### Formula
```
SAR_tomorrow = SAR_today + AF * (EP - SAR_today)

Where:
  AF = Acceleration Factor (starts at 0.02, increments by 0.02, max 0.20)
  EP = Extreme Point (highest high in uptrend, lowest low in downtrend)
```

#### Interpretation
- Dots below price: Uptrend (long)
- Dots above price: Downtrend (short)
- Dot flip signals potential trend reversal

#### Trading Applications
- Trailing stop-loss placement
- Trend direction confirmation
- Entry signals when dots flip
- Best in trending markets; poor in ranges (whipsaws)


#### Related Trading Signals

<details markdown="1"><summary><strong>psar_bullish</strong> — FILTER — Check if PSAR indicates bullish trend (PSAR below price)</summary>


#### Description
Check if PSAR indicates bullish trend (PSAR below price)

#### Parameters
- `step` (float, 0.01-0.1, optional, default=0.02): PSAR acceleration factor step
- `max_step` (float, 0.1-0.5, optional, default=0.2): PSAR max acceleration factor

#### Usage
`{"name": "psar_bullish", "params": {"step": value, "max_step": value}}`

</details>

<details markdown="1"><summary><strong>psar_bearish</strong> — FILTER — Check if PSAR indicates bearish trend (PSAR above price)</summary>


#### Description
Check if PSAR indicates bearish trend (PSAR above price)

#### Parameters
- `step` (float, 0.01-0.1, optional, default=0.02): PSAR acceleration factor step
- `max_step` (float, 0.1-0.5, optional, default=0.2): PSAR max acceleration factor

#### Usage
`{"name": "psar_bearish", "params": {"step": value, "max_step": value}}`

</details>

<details markdown="1"><summary><strong>psar_reversal</strong> — TRIGGER — Check if PSAR flips sides (potential reversal)</summary>


#### Description
Check if PSAR flips sides (potential reversal)

#### Parameters
- `step` (float, 0.01-0.1, optional, default=0.02): PSAR acceleration factor step
- `max_step` (float, 0.1-0.5, optional, default=0.2): PSAR max acceleration factor
- `direction` (str, optional, default="bullish"): Direction: 'bullish' or 'bearish'

#### Usage
`{"name": "psar_reversal", "params": {"step": value, "max_step": value, "direction": value}}`

</details>


---

### 6.1.7 Ichimoku Cloud

#### Definition
A comprehensive indicator system providing support/resistance, trend direction, and momentum through five components.

**Components:**
```
Tenkan-sen (Conversion Line) = (Highest High + Lowest Low) / 2 over 9 periods
Kijun-sen (Base Line) = (Highest High + Lowest Low) / 2 over 26 periods
Senkou Span A (Leading Span A) = (Tenkan + Kijun) / 2, plotted 26 periods ahead
Senkou Span B (Leading Span B) = (Highest High + Lowest Low) / 2 over 52 periods, plotted 26 periods ahead
Chikou Span (Lagging Span) = Current close, plotted 26 periods back
```

#### Interpretation
- Price above cloud: Bullish
- Price below cloud: Bearish
- Price in cloud: Consolidation
- Cloud color change: Trend shift
- Thick cloud: Strong support/resistance
- Thin cloud: Weak support/resistance

#### Trading Applications
- Cloud as dynamic support/resistance
- Tenkan/Kijun cross as entry signal
- Chikou Span for momentum confirmation
- All-time-frame analysis system

---


#### MangroveAI API Reference

- **Indicator Class**: `Ichimoku`
- **Category**: Trend
- **Required Data**: `high`, `low`
- **Parameters**:
  - `window_tenkan`: Tenkan-sen (conversion line) window
  - `window_kijun`: Kijun-sen (base line) window
  - `window_senkou`: Senkou Span B (leading span B) window
  - `visual`: Displacement for cloud projection
- **Outputs**: `conversion_line`, `base_line`, `span_a`, `span_b`
- **Usage Example**: `Ichimoku.compute(data={'high': df['High'], 'low': df['Low']}, params={'window_tenkan': value, 'window_kijun': value, 'window_senkou': value, 'visual': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>ichimoku_bearish</strong> — FILTER — Check if Ichimoku indicates bearish signal (price below cloud)</summary>


#### Description
Check if Ichimoku indicates bearish signal (price below cloud)

#### Parameters
- `window_tenkan` (int, 5-20, optional, default=9): Tenkan-sen (conversion line) window
- `window_kijun` (int, 15-40, optional, default=26): Kijun-sen (base line) window
- `window_senkou` (int, 30-70, optional, default=52): Senkou Span B (leading span B) window

#### Usage
`{"name": "ichimoku_bearish", "params": {"window_tenkan": value, "window_kijun": value, "window_senkou": value}}`

</details>

<details markdown="1"><summary><strong>ichimoku_bullish</strong> — FILTER — Check if Ichimoku indicates bullish signal (price above cloud)</summary>


#### Description
Check if Ichimoku indicates bullish signal (price above cloud)

#### Parameters
- `window_tenkan` (int, 5-20, optional, default=9): Tenkan-sen (conversion line) window
- `window_kijun` (int, 15-40, optional, default=26): Kijun-sen (base line) window
- `window_senkou` (int, 30-70, optional, default=52): Senkou Span B (leading span B) window

#### Usage
`{"name": "ichimoku_bullish", "params": {"window_tenkan": value, "window_kijun": value, "window_senkou": value}}`

</details>

<details markdown="1"><summary><strong>ichimoku_tk_cross</strong> — TRIGGER — Check if Tenkan-sen crosses Kijun-sen (TK cross)</summary>


#### Description
Check if Tenkan-sen crosses Kijun-sen (TK cross)

#### Parameters
- `window_tenkan` (int, 5-20, optional, default=9): Tenkan-sen (conversion line) window
- `window_kijun` (int, 15-40, optional, default=26): Kijun-sen (base line) window
- `window_senkou` (int, 30-70, optional, default=52): Senkou Span B (leading span B) window
- `direction` (str, optional, default="bullish"): Direction: 'bullish' or 'bearish'

#### Usage
`{"name": "ichimoku_tk_cross", "params": {"window_tenkan": value, "window_kijun": value, "window_senkou": value, "direction": value}}`

</details>

---

### 6.1.8 Aroon

#### Definition
The Aroon indicator measures the time elapsed since the highest high and lowest low over a given period, helping identify trend strength and potential reversals.

#### Formula
```
Aroon Up = ((Period - Days Since Highest High) / Period) * 100
Aroon Down = ((Period - Days Since Lowest Low) / Period) * 100
Standard period: 25
```

#### Interpretation
- Aroon Up > 70 and Aroon Down < 30: Strong uptrend
- Aroon Down > 70 and Aroon Up < 30: Strong downtrend
- Both below 50: Consolidation/no clear trend
- Crossovers signal potential trend changes

#### Trading Applications
- Trend identification and confirmation
- Timing entries on trend strength readings
- Detecting consolidation periods

#### Related Trading Signals
<details markdown="1"><summary><strong>aroon_up_trend</strong> — FILTER — Check if Aroon Up indicates strong uptrend</summary>


#### Description
Check if Aroon Up indicates strong uptrend

#### Parameters
- `window` (int, 10-50, optional, default=25): Lookback period
- `threshold` (float, 50-100, optional, default=70.0): Strong trend threshold

#### Usage
`{"name": "aroon_up_trend", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>aroon_down_trend</strong> — FILTER — Check if Aroon Down indicates strong downtrend</summary>


#### Description
Check if Aroon Down indicates strong downtrend

#### Parameters
- `window` (int, 10-50, optional, default=25): Lookback period
- `threshold` (float, 50-100, optional, default=70.0): Strong trend threshold

#### Usage
`{"name": "aroon_down_trend", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>aroon_crossover</strong> — TRIGGER — Check if Aroon lines cross (trend change signal)</summary>


#### Description
Check if Aroon lines cross (trend change signal)

#### Parameters
- `window` (int, 10-50, optional, default=25): Lookback period
- `direction` (str, optional, default="bullish"): Direction: 'bullish' or 'bearish'

#### Usage
`{"name": "aroon_crossover", "params": {"window": value, "direction": value}}`

</details>



---

### 6.1.9 Weighted Moving Average (WMA)

#### Definition
A moving average that assigns more weight to recent prices using a linear weighting scheme.

#### Formula
```
WMA = (P_n * n + P_(n-1) * (n-1) + ... + P_1 * 1) / (n + (n-1) + ... + 1)
Where weights decrease linearly from most recent to oldest
```

#### Interpretation
- More responsive than SMA but smoother than EMA
- Price above WMA suggests bullish bias
- Crossovers between fast and slow WMA signal trend changes

#### Related Trading Signals
<details markdown="1"><summary><strong>wma_cross_up</strong> — TRIGGER — Check if fast WMA crosses above slow WMA (bullish)</summary>


#### Description
Check if fast WMA crosses above slow WMA (bullish)

#### Parameters
- `window_fast` (int, 2-50, optional, default=9): Fast window WMA window
- `window_slow` (int, 10-100, optional, default=21): Slow window WMA window

#### Usage
`{"name": "wma_cross_up", "params": {"window_fast": value, "window_slow": value}}`

</details>


<details markdown="1"><summary><strong>wma_cross_down</strong> — TRIGGER — Check if fast WMA crosses below slow WMA (bearish)</summary>


#### Description
Check if fast WMA crosses below slow WMA (bearish)

#### Parameters
- `window_fast` (int, 2-50, optional, default=9): Fast window WMA window
- `window_slow` (int, 10-100, optional, default=21): Slow window WMA window

#### Usage
`{"name": "wma_cross_down", "params": {"window_fast": value, "window_slow": value}}`

</details>



---

### 6.1.10 KAMA (Kaufman Adaptive Moving Average)

#### Definition
An adaptive moving average that adjusts its smoothing based on market volatility—faster during trends, slower during consolidation.

#### Formula
```
ER = Change / Volatility (Efficiency Ratio)
SC = (ER * (Fast - Slow) + Slow)^2 (Smoothing Constant)
KAMA = Previous KAMA + SC * (Price - Previous KAMA)
```

#### Interpretation
- Adapts to market conditions automatically
- Less whipsaw than traditional MAs in ranging markets
- More responsive during trending periods

#### Related Trading Signals
<details markdown="1"><summary><strong>kama_cross_up</strong> — TRIGGER — Check if price crosses above KAMA (bullish signal)</summary>


#### Description
Check if price crosses above KAMA (bullish signal)

#### Parameters
- `window` (int, 5-30, optional, default=10): Efficiency ratio period
- `pow1` (int, 1-10, optional, default=2): Fast smoothing constant
- `pow2` (int, 10-50, optional, default=30): Slow smoothing constant

#### Usage
`{"name": "kama_cross_up", "params": {"window": value, "pow1": value, "pow2": value}}`

</details>


<details markdown="1"><summary><strong>kama_cross_down</strong> — TRIGGER — Check if price crosses below KAMA (bearish signal)</summary>


#### Description
Check if price crosses below KAMA (bearish signal)

#### Parameters
- `window` (int, 5-30, optional, default=10): Efficiency ratio period
- `pow1` (int, 1-10, optional, default=2): Fast smoothing constant
- `pow2` (int, 10-50, optional, default=30): Slow smoothing constant

#### Usage
`{"name": "kama_cross_down", "params": {"window": value, "pow1": value, "pow2": value}}`

</details>



---

### 6.1.11 TRIX

#### Definition
Triple exponential moving average oscillator that filters out noise and shows the rate of change of a triple-smoothed EMA.

#### Formula
```
EMA1 = EMA(Close, period)
EMA2 = EMA(EMA1, period)
EMA3 = EMA(EMA2, period)
TRIX = (EMA3 - Previous EMA3) / Previous EMA3 * 100
```

#### Interpretation
- Positive TRIX: Bullish momentum
- Negative TRIX: Bearish momentum
- Zero line crossovers signal trend changes
- Very smooth—filters out most noise

#### Related Trading Signals
<details markdown="1"><summary><strong>trix_bullish</strong> — FILTER — Check if TRIX indicates bullish momentum</summary>


#### Description
Check if TRIX indicates bullish momentum

#### Parameters
- `window` (int, 5-30, optional, default=15): TRIX period
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bullish threshold

#### Usage
`{"name": "trix_bullish", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>trix_bearish</strong> — FILTER — Check if TRIX indicates bearish momentum</summary>


#### Description
Check if TRIX indicates bearish momentum

#### Parameters
- `window` (int, 5-30, optional, default=15): TRIX period
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bearish threshold

#### Usage
`{"name": "trix_bearish", "params": {"window": value, "threshold": value}}`

</details>



---

### 6.1.12 Vortex Indicator

#### Definition
Identifies trend direction and strength by comparing positive and negative trend movements.

#### Formula
```
+VM = |High - Previous Low|
-VM = |Low - Previous High|
TR = True Range
+VI = Sum(+VM, n) / Sum(TR, n)
-VI = Sum(-VM, n) / Sum(TR, n)
```

#### Interpretation
- +VI > -VI: Bullish trend
- -VI > +VI: Bearish trend
- Crossovers signal trend reversals
- Wider spread = stronger trend

#### Related Trading Signals
<details markdown="1"><summary><strong>vortex_bullish</strong> — FILTER — Check if Vortex Indicator shows bullish trend (+VI above -VI)</summary>


#### Description
Check if Vortex Indicator shows bullish trend (+VI > -VI)

#### Parameters
- `window` (int, 5-30, optional, default=14): Vortex period

#### Usage
`{"name": "vortex_bullish", "params": {"window": value}}`

</details>


<details markdown="1"><summary><strong>vortex_bearish</strong> — FILTER — Check if Vortex Indicator shows bearish trend (-VI above +VI)</summary>


#### Description
Check if Vortex Indicator shows bearish trend (-VI > +VI)

#### Parameters
- `window` (int, 5-30, optional, default=14): Vortex period

#### Usage
`{"name": "vortex_bearish", "params": {"window": value}}`

</details>


<details markdown="1"><summary><strong>vortex_crossover</strong> — TRIGGER — Check if Vortex lines cross (trend change)</summary>


#### Description
Check if Vortex lines cross (trend change)

#### Parameters
- `window` (int, 5-30, optional, default=14): Vortex period
- `direction` (str, optional, default="bullish"): Direction: 'bullish' or 'bearish'

#### Usage
`{"name": "vortex_crossover", "params": {"window": value, "direction": value}}`

</details>



---

### 6.1.13 DPO (Detrended Price Oscillator)

#### Definition
Removes trend from price to identify cycles and overbought/oversold levels relative to a displaced moving average.

#### Formula
```
DPO = Close - SMA(Close, period) shifted back (period/2 + 1) days
```

#### Interpretation
- Positive DPO: Price above detrended average
- Negative DPO: Price below detrended average
- Helps identify cycle highs and lows
- Not affected by long-term trends

#### Related Trading Signals
<details markdown="1"><summary><strong>dpo_positive</strong> — FILTER — Check if DPO is positive (price above detrended average)</summary>


#### Description
Check if DPO is positive (price above detrended average)

#### Parameters
- `window` (int, 10-50, optional, default=20): DPO period

#### Usage
`{"name": "dpo_positive", "params": {"window": value}}`

</details>


<details markdown="1"><summary><strong>dpo_negative</strong> — FILTER — Check if DPO is negative (price below detrended average)</summary>


#### Description
Check if DPO is negative (price below detrended average)

#### Parameters
- `window` (int, 10-50, optional, default=20): DPO period

#### Usage
`{"name": "dpo_negative", "params": {"window": value}}`

</details>



---

### Best Practices for Trend Indicators

- Use longer-period indicators for trend direction, shorter for entry timing
- Don't fight the trend shown by major moving averages (50, 200)
- Combine trend indicators with oscillators for complete picture
- Adjust periods based on asset volatility and trading timeframe
- Remember that all trend indicators lag; price leads

---

## 6.2 Momentum Indicators

### Definition

Momentum indicators measure the speed or velocity of price changes, helping identify overbought/oversold conditions, divergences, and potential trend reversals. They oscillate around a centerline or within a bounded range.

### Core Principles

- **Overbought/Oversold**: Extreme readings suggest potential reversal but not certainty
- **Divergence**: Momentum diverging from price warns of potential trend change
- **Trend Confirmation**: Momentum should confirm price moves for validity
- **Mean Reversion**: Momentum tends to return to neutral over time
- **Failure Swings**: Momentum failing to reach previous extreme can signal reversal

---

### 6.2.1 Relative Strength Index (RSI)

#### Definition
Oscillator measuring the speed and magnitude of recent price changes to evaluate overbought or oversold conditions, bounded between 0 and 100.

#### Formula
```
RS = Average Gain over n periods / Average Loss over n periods
RSI = 100 - (100 / (1 + RS))

Standard period: 14
```

#### Interpretation
- RSI > 70: Overbought (potential pullback)
- RSI < 30: Oversold (potential bounce)
- RSI 40-60: Neutral zone
- Bullish divergence: Price makes lower low, RSI makes higher low
- Bearish divergence: Price makes higher high, RSI makes lower high

#### Trading Applications
- Overbought/oversold signals in ranging markets
- Divergence signals for reversal warnings
- RSI trend lines and pattern analysis
- Failure swings as reversal confirmation
- Centerline (50) crossovers as trend signals

---


#### MangroveAI API Reference

- **Indicator Class**: `RSI`
- **Category**: Momentum
- **Required Data**: `close`
- **Parameters**:
  - `window`: Parameter for RSI calculation
- **Outputs**: `rsi`
- **Usage Example**: `RSI.compute(data={'close': df['Close']}, params={'window': value})`
- **Reference**: https://www.investopedia.com/terms/r/rsi.asp

#### Related Trading Signals

<details markdown="1"><summary><strong>rsi_overbought</strong> — FILTER — Check if RSI is above the overbought threshold (default 70)</summary>


#### Description
Check if RSI is above the overbought threshold (default 70)

#### Parameters
- `window` (int, 2-100, optional, default=14): RSI calculation window
- `threshold` (float, 50-100, optional, default=70.0): Overbought threshold

#### Usage
`{"name": "rsi_overbought", "params": {"window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>rsi_oversold</strong> — FILTER — Check if RSI is below the oversold threshold (default 30)</summary>


#### Description
Check if RSI is below the oversold threshold (default 30)

#### Parameters
- `window` (int, 2-100, optional, default=14): RSI calculation window
- `threshold` (float, 0-50, optional, default=30.0): Oversold threshold

#### Usage
`{"name": "rsi_oversold", "params": {"window": value, "threshold": value}}`

</details>
<details markdown="1"><summary><strong>rsi_cross_up</strong> — TRIGGER — Check if RSI crosses above a threshold level In crypto markets, consider higher thresholds (80/20) during strong trends.</summary>


#### Description
Check if RSI crosses above a threshold level In crypto markets, consider higher thresholds (80/20) during strong trends.

#### Parameters
- `window` (int, 2-100, optional, default=14): RSI calculation window
- `threshold` (float, 0-100, optional, default=50.0): Threshold level to cross above

#### Usage
`{"name": "rsi_cross_up", "params": {"window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>rsi_cross_down</strong> — TRIGGER — Check if RSI crosses below a threshold level In crypto markets, consider higher thresholds (80/20) during strong trends.</summary>


#### Description
Check if RSI crosses below a threshold level In crypto markets, consider higher thresholds (80/20) during strong trends.

#### Parameters
- `window` (int, 2-100, optional, default=14): RSI calculation window
- `threshold` (float, 0-100, optional, default=50.0): Threshold level to cross below

#### Usage
`{"name": "rsi_cross_down", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>stochrsi_overbought</strong> — FILTER — Check if Stochastic RSI indicates overbought condition</summary>


#### Description
Check if Stochastic RSI indicates overbought condition

#### Parameters
- `window` (int, 5-30, optional, default=14): RSI period
- `smooth1` (int, 1-10, optional, default=3): Stochastic %K smoothing
- `smooth2` (int, 1-10, optional, default=3): Stochastic %D smoothing
- `threshold` (float, 0.6-1.0, optional, default=0.8): Overbought threshold (0-1 scale)

#### Usage
`{"name": "stochrsi_overbought", "params": {"window": value, "smooth1": value, "smooth2": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>stochrsi_oversold</strong> — FILTER — Check if Stochastic RSI indicates oversold condition</summary>


#### Description
Check if Stochastic RSI indicates oversold condition

#### Parameters
- `window` (int, 5-30, optional, default=14): RSI period
- `smooth1` (int, 1-10, optional, default=3): Stochastic %K smoothing
- `smooth2` (int, 1-10, optional, default=3): Stochastic %D smoothing
- `threshold` (float, 0.0-0.4, optional, default=0.2): Oversold threshold (0-1 scale)

#### Usage
`{"name": "stochrsi_oversold", "params": {"window": value, "smooth1": value, "smooth2": value, "threshold": value}}`

</details>

---

### 6.2.2 Moving Average Convergence Divergence (MACD)

#### Definition
Trend-following momentum indicator showing the relationship between two EMAs of price, consisting of MACD line, Signal line, and Histogram.

#### Formula
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

#### Interpretation
- MACD above zero: Bullish momentum
- MACD below zero: Bearish momentum
- MACD crossing Signal Line up: Buy signal
- MACD crossing Signal Line down: Sell signal
- Histogram shows momentum strength and direction

#### Trading Applications
- Signal line crossovers for entries
- Zero line crossovers for trend confirmation
- Histogram divergences for reversal warnings
- MACD in conjunction with price patterns

---


#### MangroveAI API Reference

- **Indicator Class**: `MACD`
- **Category**: Trend
- **Required Data**: `close`
- **Parameters**:
  - `window_slow`: Parameter for MACD calculation
  - `window_fast`: Parameter for MACD calculation
  - `window_sign`: Parameter for MACD calculation
- **Outputs**: `macd`, `signal`, `histogram`
- **Usage Example**: `MACD.compute(data={'close': df['Close']}, params={'window_slow': value, 'window_fast': value, 'window_sign': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>macd_bearish_cross</strong> — TRIGGER — Detect MACD bearish crossover (MACD line crosses below signal line)</summary>


#### Description
Detect MACD bearish crossover (MACD line crosses below signal line)

#### Parameters
- `window_fast` (int, 2-50, optional, default=12): Fast window EMA window
- `window_slow` (int, 10-100, optional, default=26): Slow window EMA window
- `window_sign` (int, 2-50, optional, default=9): Signal line EMA window

#### Usage
`{"name": "macd_bearish_cross", "params": {"window_fast": value, "window_slow": value, "window_sign": value}}`

</details>

<details markdown="1"><summary><strong>macd_bullish_cross</strong> — TRIGGER — Detect MACD bullish crossover (MACD line crosses above signal line)</summary>


#### Description
Detect MACD bullish crossover (MACD line crosses above signal line)

#### Parameters
- `window_fast` (int, 2-50, optional, default=12): Fast window EMA window
- `window_slow` (int, 10-100, optional, default=26): Slow window EMA window
- `window_sign` (int, 2-50, optional, default=9): Signal line EMA window

#### Usage
`{"name": "macd_bullish_cross", "params": {"window_fast": value, "window_slow": value, "window_sign": value}}`

</details>

<details markdown="1"><summary><strong>macd_positive</strong> — FILTER — Check if MACD histogram is positive (bullish momentum)</summary>


#### Description
Check if MACD histogram is positive (bullish momentum)

#### Parameters
- `window_fast` (int, 2-50, optional, default=12): Fast window EMA window
- `window_slow` (int, 10-100, optional, default=26): Slow window EMA window
- `window_sign` (int, 2-50, optional, default=9): Signal line EMA window

#### Usage
`{"name": "macd_positive", "params": {"window_fast": value, "window_slow": value, "window_sign": value}}`

</details>

---

### 6.2.3 Stochastic Oscillator


#### Related Trading Signals

<details markdown="1"><summary><strong>stoch_overbought</strong> — FILTER — Check if Stochastic %K is above the overbought threshold</summary>


#### Description
Check if Stochastic %K is above the overbought threshold

#### Parameters
- `window` (int, 5-50, optional, default=14): %K period
- `smooth_window` (int, 1-10, optional, default=3): %K smoothing period
- `threshold` (float, 70-100, optional, default=80.0): Overbought threshold

#### Usage
`{"name": "stoch_overbought", "params": {"window": value, "smooth_window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>stoch_oversold</strong> — FILTER — Check if Stochastic %K is below the oversold threshold</summary>


#### Description
Check if Stochastic %K is below the oversold threshold

#### Parameters
- `window` (int, 5-50, optional, default=14): %K period
- `smooth_window` (int, 1-10, optional, default=3): %K smoothing period
- `threshold` (float, 0-30, optional, default=20.0): Oversold threshold

#### Usage
`{"name": "stoch_oversold", "params": {"window": value, "smooth_window": value, "threshold": value}}`

</details>


#### Definition
Momentum indicator comparing closing price to price range over a specified period, showing where current price stands relative to recent high-low range.

#### Formula
```
%K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
%D = SMA(%K, 3)

Typical period: 14 for %K
Fast Stochastic: Raw %K and %D
Slow Stochastic: %K smoothed, %D of smoothed %K
```

#### Interpretation
- Above 80: Overbought
- Below 20: Oversold
- %K crossing above %D: Buy signal
- %K crossing below %D: Sell signal
- Divergences with price signal potential reversals

#### Trading Applications
- Overbought/oversold signals
- Crossover signals in trend direction
- Divergence analysis
- Slow stochastic for smoother signals

---

### 6.2.4 Commodity Channel Index (CCI)

#### Definition
Oscillator measuring current price level relative to average price over a given period, designed to identify cyclical trends.

#### Formula
```
Typical Price (TP) = (High + Low + Close) / 3
CCI = (TP - SMA(TP, n)) / (0.015 * Mean Deviation)
Mean Deviation = Average of |TP - SMA(TP)|

Typical period: 20
```

#### Interpretation
- CCI > +100: Strong uptrend / overbought
- CCI < -100: Strong downtrend / oversold
- Zero line crossovers: Trend changes
- Divergences: Potential reversals

#### Trading Applications
- Trend identification and strength
- Overbought/oversold signals
- Breakout confirmation
- Divergence trading

---


#### MangroveAI API Reference

- **Indicator Class**: `CCI`
- **Category**: Trend
- **Required Data**: `high`, `low`, `close`
- **Parameters**:
  - `window`: Parameter for CCI calculation
  - `constant`: Parameter for CCI calculation
- **Outputs**: `cci`
- **Usage Example**: `CCI.compute(data={'high': df['High'], 'low': df['Low'], 'close': df['Close']}, params={'window': value, 'constant': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>cci_overbought</strong> — FILTER — Check if CCI indicates overbought condition</summary>


#### Description
Check if CCI indicates overbought condition

#### Parameters
- `window` (int, 10-50, optional, default=20): CCI period
- `constant` (float, 0.001-0.1, optional, default=0.015): CCI constant
- `threshold` (float, 50-200, optional, default=100.0): Overbought threshold

#### Usage
`{"name": "cci_overbought", "params": {"window": value, "constant": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>cci_oversold</strong> — FILTER — Check if CCI indicates oversold condition</summary>


#### Description
Check if CCI indicates oversold condition

#### Parameters
- `window` (int, 10-50, optional, default=20): CCI period
- `constant` (float, 0.001-0.1, optional, default=0.015): CCI constant
- `threshold` (float, -200--50, optional, default=-100.0): Oversold threshold

#### Usage
`{"name": "cci_oversold", "params": {"window": value, "constant": value, "threshold": value}}`

</details>

---

### 6.2.5 Rate of Change (ROC)

#### Definition
Measures the percentage change in price from one period to another, showing momentum as a percentage.

#### Formula
```
ROC = ((Close - Close_n) / Close_n) * 100

Typical periods: 9, 12, 25
```

#### Interpretation
- ROC > 0: Upward momentum
- ROC < 0: Downward momentum
- Rising ROC: Accelerating momentum
- Falling ROC: Decelerating momentum

---


#### MangroveAI API Reference

- **Indicator Class**: `ROC`
- **Category**: Momentum
- **Required Data**: `close`
- **Parameters**:
  - `window`: Parameter for ROC calculation
- **Outputs**: `roc`
- **Usage Example**: `ROC.compute(data={'close': df['Close']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>roc_momentum_shift</strong> — TRIGGER — Check if ROC crosses zero (momentum shift)</summary>


#### Description
Check if ROC crosses zero (momentum shift)

#### Parameters
- `window` (int, 1-50, optional, default=12): ROC period
- `direction` (str, optional, default="bullish"): Direction: 'bullish' or 'bearish'

#### Usage
`{"name": "roc_momentum_shift", "params": {"window": value, "direction": value}}`

</details>

<details markdown="1"><summary><strong>roc_negative</strong> — FILTER — Check if Rate of Change indicates negative momentum</summary>


#### Description
Check if Rate of Change indicates negative momentum

#### Parameters
- `window` (int, 1-50, optional, default=12): ROC period
- `threshold` (float, -10-10, optional, default=0.0): Negative momentum threshold

#### Usage
`{"name": "roc_negative", "params": {"window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>roc_positive</strong> — FILTER — Check if Rate of Change indicates positive momentum</summary>


#### Description
Check if Rate of Change indicates positive momentum

#### Parameters
- `window` (int, 1-50, optional, default=12): ROC period
- `threshold` (float, -10-10, optional, default=0.0): Positive momentum threshold

#### Usage
`{"name": "roc_positive", "params": {"window": value, "threshold": value}}`

</details>

---

### 6.2.6 Williams %R


#### Related Trading Signals

<details markdown="1"><summary><strong>williams_r_overbought</strong> — FILTER — Check if Williams %R is above the overbought threshold (above -20)</summary>


#### Description
Check if Williams %R is above the overbought threshold (> -20)

#### Parameters
- `window` (int, 5-50, optional, default=14): Lookback window
- `threshold` (float, -30-0, optional, default=-20.0): Overbought threshold

#### Usage
`{"name": "williams_r_overbought", "params": {"window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>williams_r_oversold</strong> — FILTER — Check if Williams %R is below the oversold threshold (below -80)</summary>


#### Description
Check if Williams %R is below the oversold threshold (< -80)

#### Parameters
- `window` (int, 5-50, optional, default=14): Lookback window
- `threshold` (float, -100--70, optional, default=-80.0): Oversold threshold

#### Usage
`{"name": "williams_r_oversold", "params": {"window": value, "threshold": value}}`

</details>


#### Definition
Momentum oscillator measuring overbought/oversold levels, similar to stochastic but inverted scale.

#### Formula
```
%R = (Highest High - Close) / (Highest High - Lowest Low) * -100

Typical period: 14
```

#### Interpretation
- -20 to 0: Overbought
- -80 to -100: Oversold
- Note: Scale is inverted (0 at top, -100 at bottom)

---

### 6.2.7 Money Flow Index (MFI)

#### Definition
Volume-weighted RSI that incorporates volume to measure buying and selling pressure.

#### Formula
```
Typical Price = (High + Low + Close) / 3
Raw Money Flow = Typical Price * Volume
Money Flow Ratio = Positive Money Flow / Negative Money Flow
MFI = 100 - (100 / (1 + Money Flow Ratio))

Typical period: 14
```

#### Interpretation
- MFI > 80: Overbought
- MFI < 20: Oversold
- Divergences with price signal reversals
- Volume confirmation of price moves

---


#### MangroveAI API Reference

- **Indicator Class**: `MFI`
- **Category**: Volume
- **Required Data**: `high`, `low`, `close`, `volume`
- **Parameters**:
  - `window`: Parameter for MFI calculation
- **Outputs**: `mfi`
- **Usage Example**: `MFI.compute(data={'high': df['High'], 'low': df['Low'], 'close': df['Close'], 'volume': df['Volume']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>mfi_overbought</strong> — FILTER — Check if MFI (Money Flow Index) indicates overbought condition</summary>


#### Description
Check if MFI (Money Flow Index) indicates overbought condition

#### Parameters
- `window` (int, 5-30, optional, default=14): MFI period
- `threshold` (float, 70-95, optional, default=80.0): Overbought threshold

#### Usage
`{"name": "mfi_overbought", "params": {"window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>mfi_oversold</strong> — FILTER — Check if MFI (Money Flow Index) indicates oversold condition</summary>


#### Description
Check if MFI (Money Flow Index) indicates oversold condition

#### Parameters
- `window` (int, 5-30, optional, default=14): MFI period
- `threshold` (float, 5-30, optional, default=20.0): Oversold threshold

#### Usage
`{"name": "mfi_oversold", "params": {"window": value, "threshold": value}}`

</details>

---

### 6.2.8 Awesome Oscillator (AO)

#### Definition
Momentum indicator that measures market momentum using the difference between a 5-period and 34-period simple moving average of the bar's midpoints.

#### Formula
```
Midpoint = (High + Low) / 2
AO = SMA(Midpoint, 5) - SMA(Midpoint, 34)
```

#### Interpretation
- AO > 0: Bullish momentum
- AO < 0: Bearish momentum
- Zero line crossovers signal momentum shifts
- Twin peaks pattern for divergence analysis

#### Related Trading Signals
<details markdown="1"><summary><strong>ao_bullish</strong> — FILTER — Check if Awesome Oscillator indicates bullish momentum</summary>


#### Description
Check if Awesome Oscillator indicates bullish momentum

#### Parameters
- `window_fast` (int, 2-15, optional, default=5): Fast SMA window
- `window_slow` (int, 20-60, optional, default=34): Slow SMA window
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bullish threshold

#### Usage
`{"name": "ao_bullish", "params": {"window_fast": value, "window_slow": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>ao_bearish</strong> — FILTER — Check if Awesome Oscillator indicates bearish momentum</summary>


#### Description
Check if Awesome Oscillator indicates bearish momentum

#### Parameters
- `window_fast` (int, 2-15, optional, default=5): Fast SMA window
- `window_slow` (int, 20-60, optional, default=34): Slow SMA window
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bearish threshold

#### Usage
`{"name": "ao_bearish", "params": {"window_fast": value, "window_slow": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>ao_zero_cross</strong> — TRIGGER — Check if Awesome Oscillator crosses zero line</summary>


#### Description
Check if Awesome Oscillator crosses zero line

#### Parameters
- `window_fast` (int, 2-15, optional, default=5): Fast SMA window
- `window_slow` (int, 20-60, optional, default=34): Slow SMA window
- `direction` (str, optional, default="bullish"): Direction: 'bullish' or 'bearish'

#### Usage
`{"name": "ao_zero_cross", "params": {"window_fast": value, "window_slow": value, "direction": value}}`

</details>



---

### 6.2.9 Force Index

#### Definition
Combines price change and volume to measure the strength behind price moves.

#### Formula
```
Force Index = (Close - Previous Close) * Volume
Smoothed Force Index = EMA(Force Index, period)
```

#### Interpretation
- Positive Force Index: Bulls in control
- Negative Force Index: Bears in control
- Rising Force Index: Increasing buying pressure
- Falling Force Index: Increasing selling pressure

#### Related Trading Signals
<details markdown="1"><summary><strong>force_bullish</strong> — FILTER — Check if Force Index indicates bullish momentum</summary>


#### Description
Check if Force Index indicates bullish momentum

#### Parameters
- `window` (int, 5-30, optional, default=13): EMA period for smoothing
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bullish threshold

#### Usage
`{"name": "force_bullish", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>force_bearish</strong> — FILTER — Check if Force Index indicates bearish momentum</summary>


#### Description
Check if Force Index indicates bearish momentum

#### Parameters
- `window` (int, 5-30, optional, default=13): EMA period for smoothing
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bearish threshold

#### Usage
`{"name": "force_bearish", "params": {"window": value, "threshold": value}}`

</details>



---

### 6.2.10 KST (Know Sure Thing)

#### Definition
Momentum oscillator based on the smoothed rate-of-change for four different timeframes, combined with weights.

#### Formula
```
ROC1 = SMA(ROC(10), 10)
ROC2 = SMA(ROC(15), 10)
ROC3 = SMA(ROC(20), 10)
ROC4 = SMA(ROC(30), 15)
KST = (ROC1 * 1) + (ROC2 * 2) + (ROC3 * 3) + (ROC4 * 4)
Signal = SMA(KST, 9)
```

#### Interpretation
- KST above Signal: Bullish momentum
- KST below Signal: Bearish momentum
- Crossovers generate trading signals
- Smoothed version reduces whipsaws

#### Related Trading Signals
<details markdown="1"><summary><strong>kst_bullish_cross</strong> — TRIGGER — Check if KST crosses above signal line (bullish)</summary>


#### Description
Check if KST crosses above signal line (bullish)

#### Parameters
- `roc1` (int, 1-1000, optional, default=10): ROC1 period
- `roc2` (int, 1-1000, optional, default=15): ROC2 period
- `roc3` (int, 1-1000, optional, default=20): ROC3 period
- `roc4` (int, 1-1000, optional, default=30): ROC4 period
- `window_sma1` (int, 2-500, optional, default=10): SMA1 smoothing window (for ROC1)
- `window_sma2` (int, 2-500, optional, default=10): SMA2 smoothing window (for ROC2)
- `window_sma3` (int, 2-500, optional, default=10): SMA3 smoothing window (for ROC3)
- `window_sma4` (int, 2-500, optional, default=15): SMA4 smoothing window (for ROC4)
- `nsig` (int, 1-1000, optional, default=9): Signal line period

#### Usage
`{"name": "kst_bullish_cross", "params": {"roc1": value, "roc2": value, "roc3": value, "roc4": value, "window_sma1": value, "window_sma2": value, "window_sma3": value, "window_sma4": value, "nsig": value}}`

</details>


<details markdown="1"><summary><strong>kst_bearish_cross</strong> — TRIGGER — Check if KST crosses below signal line (bearish)</summary>


#### Description
Check if KST crosses below signal line (bearish)

#### Parameters
- `roc1` (int, 1-1000, optional, default=10): ROC1 period
- `roc2` (int, 1-1000, optional, default=15): ROC2 period
- `roc3` (int, 1-1000, optional, default=20): ROC3 period
- `roc4` (int, 1-1000, optional, default=30): ROC4 period
- `window_sma1` (int, 2-500, optional, default=10): SMA1 smoothing window (for ROC1)
- `window_sma2` (int, 2-500, optional, default=10): SMA2 smoothing window (for ROC2)
- `window_sma3` (int, 2-500, optional, default=10): SMA3 smoothing window (for ROC3)
- `window_sma4` (int, 2-500, optional, default=15): SMA4 smoothing window (for ROC4)
- `nsig` (int, 1-1000, optional, default=9): Signal line period

#### Usage
`{"name": "kst_bearish_cross", "params": {"roc1": value, "roc2": value, "roc3": value, "roc4": value, "window_sma1": value, "window_sma2": value, "window_sma3": value, "window_sma4": value, "nsig": value}}`

</details>



---

### 6.2.11 PPO (Percentage Price Oscillator)

#### Definition
Momentum oscillator showing the percentage difference between two EMAs, similar to MACD but normalized.

#### Formula
```
PPO = ((EMA(12) - EMA(26)) / EMA(26)) * 100
Signal Line = EMA(PPO, 9)
```

#### Interpretation
- Positive PPO: Short-term momentum above long-term
- Negative PPO: Short-term momentum below long-term
- Normalized for comparison across different price levels
- Signal line crossovers for timing

#### Related Trading Signals
<details markdown="1"><summary><strong>ppo_bullish_cross</strong> — TRIGGER — Check if PPO crosses above signal line (bullish)</summary>


#### Description
Check if PPO crosses above signal line (bullish)

#### Parameters
- `window_slow` (int, 15-50, optional, default=26): Slow EMA period
- `window_fast` (int, 5-20, optional, default=12): Fast EMA period
- `window_sign` (int, 3-15, optional, default=9): Signal line period

#### Usage
`{"name": "ppo_bullish_cross", "params": {"window_slow": value, "window_fast": value, "window_sign": value}}`

</details>


<details markdown="1"><summary><strong>ppo_bearish_cross</strong> — TRIGGER — Check if PPO crosses below signal line (bearish)</summary>


#### Description
Check if PPO crosses below signal line (bearish)

#### Parameters
- `window_slow` (int, 15-50, optional, default=26): Slow EMA period
- `window_fast` (int, 5-20, optional, default=12): Fast EMA period
- `window_sign` (int, 3-15, optional, default=9): Signal line period

#### Usage
`{"name": "ppo_bearish_cross", "params": {"window_slow": value, "window_fast": value, "window_sign": value}}`

</details>



---

### 6.2.12 STC (Schaff Trend Cycle)

#### Definition
Combines MACD with a stochastic calculation to create a faster, smoother oscillator.

#### Formula
```
MACD Line = EMA(23) - EMA(50)
%K of MACD = Stochastic of MACD Line
STC = Double smoothed %K
```

#### Interpretation
- STC > 75: Overbought
- STC < 25: Oversold
- Faster signals than traditional MACD
- Good for identifying trend changes early

#### Related Trading Signals
<details markdown="1"><summary><strong>stc_oversold</strong> — FILTER — Check if STC indicates oversold condition</summary>


#### Description
Check if STC indicates oversold condition

#### Parameters
- `window_slow` (int, 2-500, optional, default=50): Slow EMA period
- `window_fast` (int, 2-500, optional, default=23): Fast EMA period
- `cycle` (int, 1-1000, optional, default=10): Cycle period
- `smooth1` (int, 1-1000, optional, default=3): Smoothing 1
- `smooth2` (int, 1-1000, optional, default=3): Smoothing 2
- `threshold` (float, 0.0-100.0, optional, default=25.0): Oversold threshold

#### Usage
`{"name": "stc_oversold", "params": {"window_slow": value, "window_fast": value, "cycle": value, "smooth1": value, "smooth2": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>stc_overbought</strong> — FILTER — Check if STC indicates overbought condition</summary>


#### Description
Check if STC indicates overbought condition

#### Parameters
- `window_slow` (int, 2-500, optional, default=50): Slow EMA period
- `window_fast` (int, 2-500, optional, default=23): Fast EMA period
- `cycle` (int, 1-1000, optional, default=10): Cycle period
- `smooth1` (int, 1-1000, optional, default=3): Smoothing 1
- `smooth2` (int, 1-1000, optional, default=3): Smoothing 2
- `threshold` (float, 0.0-100.0, optional, default=75.0): Overbought threshold

#### Usage
`{"name": "stc_overbought", "params": {"window_slow": value, "window_fast": value, "cycle": value, "smooth1": value, "smooth2": value, "threshold": value}}`

</details>



---

### 6.2.13 TSI (True Strength Index)

#### Definition
Double-smoothed momentum indicator that shows both trend direction and overbought/oversold conditions.

#### Formula
```
PC = Close - Previous Close
Double Smoothed PC = EMA(EMA(PC, 25), 13)
Double Smoothed Absolute PC = EMA(EMA(|PC|, 25), 13)
TSI = (Double Smoothed PC / Double Smoothed Absolute PC) * 100
```

#### Interpretation
- TSI > 0: Bullish momentum
- TSI < 0: Bearish momentum
- Extreme readings suggest overbought/oversold
- Less noise than RSI due to double smoothing

#### Related Trading Signals
<details markdown="1"><summary><strong>tsi_bullish</strong> — FILTER — Check if True Strength Index indicates bullish momentum (TSI above threshold)</summary>


#### Description
Check if True Strength Index indicates bullish momentum (TSI > threshold)

#### Parameters
- `window_slow` (int, 10-50, optional, default=25): Slow EMA period
- `window_fast` (int, 5-25, optional, default=13): Fast EMA period
- `threshold` (float, -50-50, optional, default=0.0): Bullish threshold

#### Usage
`{"name": "tsi_bullish", "params": {"window_slow": value, "window_fast": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>tsi_bearish</strong> — FILTER — Check if True Strength Index indicates bearish momentum (TSI below threshold)</summary>


#### Description
Check if True Strength Index indicates bearish momentum (TSI < threshold)

#### Parameters
- `window_slow` (int, 10-50, optional, default=25): Slow EMA period
- `window_fast` (int, 5-25, optional, default=13): Fast EMA period
- `threshold` (float, -50-50, optional, default=0.0): Bearish threshold

#### Usage
`{"name": "tsi_bearish", "params": {"window_slow": value, "window_fast": value, "threshold": value}}`

</details>



---

### 6.2.14 Ultimate Oscillator

#### Definition
Momentum oscillator that combines short, intermediate, and long timeframes to reduce false signals.

#### Formula
```
BP = Close - Min(Low, Previous Close)
TR = Max(High, Previous Close) - Min(Low, Previous Close)
Average7 = Sum(BP, 7) / Sum(TR, 7)
Average14 = Sum(BP, 14) / Sum(TR, 14)
Average28 = Sum(BP, 28) / Sum(TR, 28)
UO = 100 * ((4 * Average7) + (2 * Average14) + Average28) / 7
```

#### Interpretation
- UO > 70: Overbought
- UO < 30: Oversold
- Multi-timeframe reduces whipsaws
- Divergences with price signal reversals

#### Related Trading Signals
<details markdown="1"><summary><strong>uo_oversold</strong> — FILTER — Check if Ultimate Oscillator indicates oversold condition</summary>


#### Description
Check if Ultimate Oscillator indicates oversold condition

#### Parameters
- `window_short` (int, 3-20, optional, default=7): Short window
- `window_medium` (int, 7-30, optional, default=14): Medium window
- `window_long` (int, 14-50, optional, default=28): Long window
- `threshold` (float, 10-40, optional, default=30.0): Oversold threshold

#### Usage
`{"name": "uo_oversold", "params": {"window_short": value, "window_medium": value, "window_long": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>uo_overbought</strong> — FILTER — Check if Ultimate Oscillator indicates overbought condition</summary>


#### Description
Check if Ultimate Oscillator indicates overbought condition

#### Parameters
- `window_short` (int, 3-20, optional, default=7): Short window
- `window_medium` (int, 7-30, optional, default=14): Medium window
- `window_long` (int, 14-50, optional, default=28): Long window
- `threshold` (float, 60-90, optional, default=70.0): Overbought threshold

#### Usage
`{"name": "uo_overbought", "params": {"window_short": value, "window_medium": value, "window_long": value, "threshold": value}}`

</details>



---

### Best Practices for Momentum Indicators

- Don't rely solely on overbought/oversold signals in strong trends
- Look for divergences as early warning, not immediate signals
- Combine momentum with trend indicators for confirmation
- Adjust overbought/oversold thresholds based on market conditions
- Use multiple momentum indicators for confluence

---

## 6.3 Volatility Indicators

### Definition

Volatility indicators measure the degree of price variation over time, helping traders assess risk, set stop-losses, determine position sizes, and identify potential breakout conditions.

### Core Principles

- **Volatility Cycles**: Markets alternate between high and low volatility periods
- **Volatility Clustering**: High volatility tends to follow high volatility
- **Mean Reversion**: Extreme volatility tends to revert to average
- **Breakout Potential**: Low volatility often precedes significant moves
- **Risk Adjustment**: Volatility should influence position sizing and stops

---

### 6.3.1 Bollinger Bands

#### Definition
Volatility bands placed above and below a moving average, with width determined by standard deviation.

#### Formula
```
Middle Band = SMA(Close, 20)
Upper Band = SMA + (2 * Standard Deviation)
Lower Band = SMA - (2 * Standard Deviation)

Bandwidth = (Upper - Lower) / Middle * 100
%B = (Close - Lower) / (Upper - Lower)
```

#### Interpretation
- Price at upper band: Potentially overbought / strong trend
- Price at lower band: Potentially oversold / strong trend
- Band squeeze (narrow bands): Low volatility, breakout potential
- Band expansion: High volatility, trend in progress
- %B > 1: Above upper band; %B < 0: Below lower band

#### Trading Applications
- Mean reversion trades at bands in ranges
- Trend trades with band walking in trends
- Squeeze detection for breakout anticipation
- Volatility assessment for position sizing

---


#### MangroveAI API Reference

- **Indicator Class**: `BollingerBands`
- **Category**: Volatility
- **Required Data**: `close`
- **Parameters**:
  - `window`: Parameter for BollingerBands calculation
  - `window_dev`: Parameter for BollingerBands calculation
- **Outputs**: `mavg`, `hband`, `lband`, `wband`, `pband`, `hband_indicator`, `lband_indicator`
- **Usage Example**: `BollingerBands.compute(data={'close': df['Close']}, params={'window': value, 'window_dev': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>bb_lower_breakout</strong> — TRIGGER — Check if price closes below the lower Bollinger Band</summary>


#### Description
Check if price closes below the lower Bollinger Band

#### Parameters
- `window` (int, 5-100, optional, default=20): MA period for center band
- `window_dev` (int, 1-5, optional, default=2): Standard deviation multiplier

#### Usage
`{"name": "bb_lower_breakout", "params": {"window": value, "window_dev": value}}`

</details>

<details markdown="1"><summary><strong>bb_squeeze</strong> — TRIGGER — Detect Bollinger Band squeeze (low volatility, potential breakout)</summary>


#### Description
Detect Bollinger Band squeeze (low volatility, potential breakout)

#### Parameters
- `window` (int, 5-100, optional, default=20): MA period for center band
- `window_dev` (int, 1-5, optional, default=2): Standard deviation multiplier
- `threshold` (float, 1-20, optional, default=5.0): Band width percentage threshold

#### Usage
`{"name": "bb_squeeze", "params": {"window": value, "window_dev": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>bb_upper_breakout</strong> — TRIGGER — Check if price closes above the upper Bollinger Band</summary>


#### Description
Check if price closes above the upper Bollinger Band

#### Parameters
- `window` (int, 5-100, optional, default=20): MA period for center band
- `window_dev` (int, 1-5, optional, default=2): Standard deviation multiplier

#### Usage
`{"name": "bb_upper_breakout", "params": {"window": value, "window_dev": value}}`

</details>

---

### 6.3.2 Average True Range (ATR)

#### Definition
Measures market volatility by calculating the average range of price movement, accounting for gaps.

#### Formula
```
True Range = max(
  High - Low,
  |High - Previous Close|,
  |Low - Previous Close|
)
ATR = EMA(True Range, n periods)

Typical period: 14
```

#### Interpretation
- Higher ATR: More volatility
- Lower ATR: Less volatility
- Rising ATR: Volatility expanding
- Falling ATR: Volatility contracting

#### Trading Applications
- Stop-loss placement (e.g., 2 * ATR from entry)
- Position sizing (smaller positions when ATR high)
- Profit target setting
- Volatility breakout detection
- Normalizing across different assets

---


#### MangroveAI API Reference

- **Indicator Class**: `ATR`
- **Category**: Volatility
- **Required Data**: `high`, `low`, `close`
- **Parameters**:
  - `window`: Parameter for ATR calculation
- **Outputs**: `atr`
- **Usage Example**: `ATR.compute(data={'high': df['High'], 'low': df['Low'], 'close': df['Close']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>atr_high_volatility</strong> — FILTER — Check if ATR indicates high volatility relative to price</summary>


#### Description
Check if ATR indicates high volatility relative to price

#### Parameters
- `window` (int, 5-50, optional, default=14): ATR period
- `threshold_pct` (float, 0.5-10, optional, default=3.0): ATR as percentage of close threshold

#### Usage
`{"name": "atr_high_volatility", "params": {"window": value, "threshold_pct": value}}`

</details>

---

### 6.3.3 Keltner Channels


#### Related Trading Signals

<details markdown="1"><summary><strong>kc_upper_breakout</strong> — TRIGGER — Check if price breaks above upper Keltner Channel band</summary>


#### Description
Check if price breaks above upper Keltner Channel band

#### Parameters
- `window` (int, 10-50, optional, default=20): EMA period
- `window_atr` (int, 5-30, optional, default=10): ATR period
- `multiplier` (float, 0.5-5.0, optional, default=2.0): ATR multiplier for band width
- `original_version` (bool, optional, default=False): Use original Keltner Channel formula

#### Usage
`{"name": "kc_upper_breakout", "params": {"window": value, "window_atr": value, "multiplier": value, "original_version": value}}`

</details>

<details markdown="1"><summary><strong>kc_lower_breakout</strong> — TRIGGER — Check if price breaks below lower Keltner Channel band</summary>


#### Description
Check if price breaks below lower Keltner Channel band

#### Parameters
- `window` (int, 10-50, optional, default=20): EMA period
- `window_atr` (int, 5-30, optional, default=10): ATR period
- `multiplier` (float, 0.5-5.0, optional, default=2.0): ATR multiplier for band width
- `original_version` (bool, optional, default=False): Use original Keltner Channel formula

#### Usage
`{"name": "kc_lower_breakout", "params": {"window": value, "window_atr": value, "multiplier": value, "original_version": value}}`

</details>


#### Definition
Volatility-based bands using ATR instead of standard deviation, typically around an EMA.

#### Formula
```
Middle Line = EMA(Close, 20)
Upper Channel = EMA + (2 * ATR)
Lower Channel = EMA - (2 * ATR)
```

#### Interpretation
- Similar to Bollinger Bands but uses ATR for width
- Less sensitive to sudden price spikes
- Squeeze occurs when Bollinger Bands move inside Keltner Channels


#### Related Trading Signals




#### Trading Applications
- Combined with Bollinger Bands for squeeze detection
- Trend direction and strength
- Dynamic support/resistance

---

### 6.3.4 Standard Deviation

#### Definition
Statistical measure of the dispersion of returns around the mean.

#### Formula
```
Variance = Sum((x_i - mean)^2) / (n-1)
Standard Deviation = sqrt(Variance)

Annualized Vol = Daily Std Dev * sqrt(252)
```

#### Interpretation
- Higher std dev: More volatile
- Lower std dev: Less volatile
- Used to normalize comparisons across assets

---

### 6.3.5 Volatility Index (VIX)

#### Definition
Market expectation of near-term volatility implied by S&P 500 index option prices.

#### Interpretation
- VIX < 15: Low volatility / complacency
- VIX 15-20: Normal volatility
- VIX 20-30: Elevated volatility / uncertainty
- VIX > 30: High volatility / fear
- VIX spikes often coincide with market bottoms

#### Trading Applications
- Market sentiment gauge
- Regime classification
- Volatility trading strategies
- Portfolio hedging timing

---

### 6.3.6 Donchian Channels

#### Definition
Price channels formed by the highest high and lowest low over a specified period, used in the famous Turtle Trading system.

#### Formula
```
Upper Channel = Highest High over n periods
Lower Channel = Lowest Low over n periods
Middle Line = (Upper + Lower) / 2
Standard period: 20
```

#### Interpretation
- Price at upper channel: Strong uptrend / potential overbought
- Price at lower channel: Strong downtrend / potential oversold
- Breakouts above upper channel signal long entries
- Breakouts below lower channel signal short entries

#### Related Trading Signals
<details markdown="1"><summary><strong>dc_upper_breakout</strong> — TRIGGER — Check if price breaks above upper Donchian Channel (new high)</summary>


#### Description
Check if price breaks above upper Donchian Channel (new high)

#### Parameters
- `window` (int, 5-100, optional, default=20): Lookback period

#### Usage
`{"name": "dc_upper_breakout", "params": {"window": value}}`

</details>


<details markdown="1"><summary><strong>dc_lower_breakout</strong> — TRIGGER — Check if price breaks below lower Donchian Channel (new low)</summary>


#### Description
Check if price breaks below lower Donchian Channel (new low)

#### Parameters
- `window` (int, 5-100, optional, default=20): Lookback period

#### Usage
`{"name": "dc_lower_breakout", "params": {"window": value}}`

</details>



---

### 6.3.7 Mass Index

#### Definition
Identifies trend reversals by measuring the range between high and low prices, looking for range expansion followed by contraction.

#### Formula
```
Single EMA = EMA(High - Low, 9)
Double EMA = EMA(Single EMA, 9)
Mass Index = Sum(Single EMA / Double EMA, 25)
```

#### Interpretation
- Mass Index > 27 then < 26.5: "Reversal bulge" pattern
- Signals that current trend may be exhausted
- Best combined with trend indicators for direction
- Identifies volatility cycle changes

#### Related Trading Signals
<details markdown="1"><summary><strong>mass_reversal_signal</strong> — TRIGGER — Check if Mass Index signals potential reversal (reversal bulge)</summary>


#### Description
Check if Mass Index signals potential reversal (reversal bulge)

#### Parameters
- `window_fast` (int, 5-15, optional, default=9): Fast EMA period
- `window_slow` (int, 15-40, optional, default=25): Sum period
- `threshold_high` (float, 25-30, optional, default=27.0): Upper threshold
- `threshold_low` (float, 24-27, optional, default=26.5): Lower threshold

#### Usage
`{"name": "mass_reversal_signal", "params": {"window_fast": value, "window_slow": value, "threshold_high": value, "threshold_low": value}}`

</details>



---

### 6.3.8 Ulcer Index

#### Definition
Measures downside risk and volatility by focusing only on drawdowns from recent highs.

#### Formula
```
Percentage Drawdown = ((Close - 14-period High Close) / 14-period High Close) * 100
Ulcer Index = Square Root of Mean of Squared Drawdowns
```

#### Interpretation
- Low Ulcer Index: Low downside risk
- High Ulcer Index: High downside risk
- Focus on downside volatility only
- Useful for risk-adjusted performance (Martin Ratio)

#### Related Trading Signals
<details markdown="1"><summary><strong>ulcer_low_risk</strong> — FILTER — Check if Ulcer Index indicates low downside risk</summary>


#### Description
Check if Ulcer Index indicates low downside risk

#### Parameters
- `window` (int, 5-50, optional, default=14): Lookback period
- `threshold` (float, 1-15, optional, default=5.0): Low risk threshold

#### Usage
`{"name": "ulcer_low_risk", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>ulcer_high_risk</strong> — FILTER — Check if Ulcer Index indicates high downside risk</summary>


#### Description
Check if Ulcer Index indicates high downside risk

#### Parameters
- `window` (int, 5-50, optional, default=14): Lookback period
- `threshold` (float, 5-30, optional, default=10.0): High risk threshold

#### Usage
`{"name": "ulcer_high_risk", "params": {"window": value, "threshold": value}}`

</details>



---

### Best Practices for Volatility Indicators

- Use ATR for stop-loss and position sizing calculations
- Watch for volatility compression as setup for breakouts
- Reduce position size during high volatility periods
- Normalize volatility when comparing different assets
- Remember that volatility is mean-reverting over time

---

## 6.4 Volume & Order Flow Indicators

### Definition

Volume indicators analyze trading volume to confirm price movements, identify accumulation/distribution, and provide insight into the strength of market participation.

### Core Principles

- **Volume Confirms Price**: Strong moves should be accompanied by strong volume
- **Volume Precedes Price**: Volume changes often lead price changes
- **Climactic Volume**: Extreme volume often occurs at turning points
- **Dry Up Warning**: Decreasing volume in a move suggests weakening
- **Effort vs. Result**: Compare volume (effort) to price movement (result)

---

### 6.4.1 On-Balance Volume (OBV)

#### Definition
Cumulative volume indicator that adds volume on up days and subtracts on down days.

#### Formula
```
If Close > Previous Close: OBV = Previous OBV + Volume
If Close < Previous Close: OBV = Previous OBV - Volume
If Close = Previous Close: OBV = Previous OBV
```

#### Interpretation
- Rising OBV: Accumulation (buying pressure)
- Falling OBV: Distribution (selling pressure)
- OBV divergence from price: Potential reversal warning
- OBV breakouts can precede price breakouts

---


#### MangroveAI API Reference

- **Indicator Class**: `OBV`
- **Category**: Volume
- **Required Data**: `close`, `volume`
- **Outputs**: `obv`
- **Usage Example**: `OBV.compute(data={'close': df['Close'], 'volume': df['Volume']}, params={})`

#### Related Trading Signals

<details markdown="1"><summary><strong>obv_bearish</strong> — FILTER — Check if OBV is falling (bearish volume confirmation)</summary>


#### Description
Check if OBV is falling (bearish volume confirmation)

#### Parameters
- `window` (int, 5-50, optional, default=20): Lookback for trend

#### Usage
`{"name": "obv_bearish", "params": {"window": value}}`

</details>

<details markdown="1"><summary><strong>obv_bullish</strong> — FILTER — Check if OBV is rising (bullish volume confirmation)</summary>


#### Description
Check if OBV is rising (bullish volume confirmation)

#### Parameters
- `window` (int, 5-50, optional, default=20): Lookback for trend

#### Usage
`{"name": "obv_bullish", "params": {"window": value}}`

</details>

---

### 6.4.2 Accumulation/Distribution Line (ADL)


#### Related Trading Signals

<details markdown="1"><summary><strong>adi_bullish</strong> — FILTER — Check if ADI (Accumulation/Distribution) is rising</summary>


#### Description
Check if ADI (Accumulation/Distribution) is rising

#### Parameters
- `window` (int, 5-50, optional, default=20): Lookback for trend

#### Usage
`{"name": "adi_bullish", "params": {"window": value}}`

</details>

<details markdown="1"><summary><strong>adi_bearish</strong> — FILTER — Check if ADI (Accumulation/Distribution) is falling</summary>


#### Description
Check if ADI (Accumulation/Distribution) is falling

#### Parameters
- `window` (int, 5-50, optional, default=20): Lookback for trend

#### Usage
`{"name": "adi_bearish", "params": {"window": value}}`

</details>


#### Definition
Volume-based indicator measuring the cumulative flow of money into and out of a security.

#### Formula
```
Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
Money Flow Volume = Money Flow Multiplier * Volume
ADL = Previous ADL + Money Flow Volume
```

#### Interpretation
- Rising ADL: Accumulation
- Falling ADL: Distribution
- ADL confirming price: Trend likely to continue
- ADL diverging from price: Potential reversal

---

### 6.4.3 Volume Weighted Average Price (VWAP)

#### Definition
The average price weighted by volume, representing the average price a security has traded at throughout the day.

#### Formula
```
VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
Typical Price = (High + Low + Close) / 3
```

#### Interpretation
- Price above VWAP: Buyers in control
- Price below VWAP: Sellers in control
- VWAP as dynamic support/resistance
- Deviation from VWAP indicates overextension

#### Trading Applications
- Institutional benchmark for execution quality
- Intraday support/resistance
- Entry/exit timing
- Mean reversion trading

---


#### MangroveAI API Reference

- **Indicator Class**: `VWAP`
- **Category**: Volume
- **Required Data**: `high`, `low`, `close`, `volume`
- **Parameters**:
  - `window`: Parameter for VWAP calculation
- **Outputs**: `vwap`
- **Usage Example**: `VWAP.compute(data={'high': df['High'], 'low': df['Low'], 'close': df['Close'], 'volume': df['Volume']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>vwap_above</strong> — FILTER — Check if price is above VWAP (bullish bias)</summary>


#### Description
Check if price is above VWAP (bullish bias)

#### Parameters
- `window` (int, 5-50, optional, default=14): VWAP period

#### Usage
`{"name": "vwap_above", "params": {"window": value}}`

</details>

<details markdown="1"><summary><strong>vwap_below</strong> — FILTER — Check if price is below VWAP (bearish bias)</summary>


#### Description
Check if price is below VWAP (bearish bias)

#### Parameters
- `window` (int, 5-50, optional, default=14): VWAP period

#### Usage
`{"name": "vwap_below", "params": {"window": value}}`

</details>

---

### 6.4.4 Chaikin Money Flow (CMF)

#### Definition
Measures the amount of Money Flow Volume over a specific period.

#### Formula
```
CMF = Sum(Money Flow Volume, n) / Sum(Volume, n)

Typical period: 20
```

#### Interpretation
- CMF > 0: Buying pressure
- CMF < 0: Selling pressure
- Rising CMF: Increasing buying pressure
- Falling CMF: Increasing selling pressure

---


#### MangroveAI API Reference

- **Indicator Class**: `CMF`
- **Category**: Volume
- **Required Data**: `high`, `low`, `close`, `volume`
- **Parameters**:
  - `window`: Parameter for CMF calculation
- **Outputs**: `cmf`
- **Usage Example**: `CMF.compute(data={'high': df['High'], 'low': df['Low'], 'close': df['Close'], 'volume': df['Volume']}, params={'window': value})`

#### Related Trading Signals

<details markdown="1"><summary><strong>cmf_bearish</strong> — FILTER — Check if CMF (Chaikin Money Flow) indicates selling pressure</summary>


#### Description
Check if CMF (Chaikin Money Flow) indicates selling pressure

#### Parameters
- `window` (int, 10-50, optional, default=20): CMF period
- `threshold` (float, -1.0-1.0, optional, default=0.0): Bearish threshold

#### Usage
`{"name": "cmf_bearish", "params": {"window": value, "threshold": value}}`

</details>

<details markdown="1"><summary><strong>cmf_bullish</strong> — FILTER — Check if CMF (Chaikin Money Flow) indicates buying pressure</summary>


#### Description
Check if CMF (Chaikin Money Flow) indicates buying pressure

#### Parameters
- `window` (int, 10-50, optional, default=20): CMF period
- `threshold` (float, -1.0-1.0, optional, default=0.0): Bullish threshold

#### Usage
`{"name": "cmf_bullish", "params": {"window": value, "threshold": value}}`

</details>

---

### 6.4.5 Klinger Volume Oscillator

#### Definition
Volume-based oscillator designed to identify long-term money flow trends.

#### Formula
```
Volume Force = Volume * |2 * (dm/cm) - 1| * trend * 100
KVO = EMA(Volume Force, 34) - EMA(Volume Force, 55)
Signal = EMA(KVO, 13)
```

#### Interpretation
- KVO above zero: Bullish volume pressure
- KVO below zero: Bearish volume pressure
- KVO crossing signal line: Potential trade signal
- Divergences with price indicate weakening trends

---

### 6.4.6 Ease of Movement (EMV)

#### Definition
Volume-based oscillator that relates price change to volume, showing how easily price moves.

#### Formula
```
Distance Moved = ((High + Low) / 2) - ((Previous High + Previous Low) / 2)
Box Ratio = (Volume / 10000) / (High - Low)
EMV = Distance Moved / Box Ratio
EMV SMA = SMA(EMV, 14)
```

#### Interpretation
- Positive EMV: Price rising easily with volume
- Negative EMV: Price falling easily with volume
- High values: Easy price movement
- Low values: Difficult price movement

#### Related Trading Signals
<details markdown="1"><summary><strong>eom_bullish</strong> — FILTER — Check if Ease of Movement indicates bullish</summary>


#### Description
Check if Ease of Movement indicates bullish

#### Parameters
- `window` (int, 5-30, optional, default=14): EOM period
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bullish threshold

#### Usage
`{"name": "eom_bullish", "params": {"window": value, "threshold": value}}`

</details>


<details markdown="1"><summary><strong>eom_bearish</strong> — FILTER — Check if Ease of Movement indicates bearish</summary>


#### Description
Check if Ease of Movement indicates bearish

#### Parameters
- `window` (int, 5-30, optional, default=14): EOM period
- `threshold` (float, 0.0-100.0, optional, default=0.0): Bearish threshold

#### Usage
`{"name": "eom_bearish", "params": {"window": value, "threshold": value}}`

</details>



---

### 6.4.7 NVI (Negative Volume Index)

#### Definition
Tracks price changes on days when volume decreases from the previous day, thought to track "smart money" activity.

#### Formula
```
If Volume < Previous Volume:
  NVI = Previous NVI + ((Close - Previous Close) / Previous Close) * Previous NVI
Else:
  NVI = Previous NVI
```

#### Interpretation
- Rising NVI on down volume: Smart money accumulating
- Falling NVI on down volume: Smart money distributing
- Compare to 255-day EMA for trend
- Less noise than volume-inclusive indicators

#### Related Trading Signals
<details markdown="1"><summary><strong>nvi_bullish</strong> — FILTER — Check if NVI (Negative Volume Index) indicates smart money buying</summary>


#### Description
Check if NVI (Negative Volume Index) indicates smart money buying

#### Parameters
- `window` (int, 100-500, optional, default=255): EMA period for signal

#### Usage
`{"name": "nvi_bullish", "params": {"window": value}}`

</details>


<details markdown="1"><summary><strong>nvi_bearish</strong> — FILTER — Check if NVI (Negative Volume Index) indicates smart money selling</summary>


#### Description
Check if NVI (Negative Volume Index) indicates smart money selling

#### Parameters
- `window` (int, 100-500, optional, default=255): EMA period for signal

#### Usage
`{"name": "nvi_bearish", "params": {"window": value}}`

</details>



---

### 6.4.8 PVO (Percentage Volume Oscillator)

#### Definition
Momentum oscillator for volume, showing the percentage difference between two volume EMAs.

#### Formula
```
PVO = ((EMA(Volume, 12) - EMA(Volume, 26)) / EMA(Volume, 26)) * 100
Signal Line = EMA(PVO, 9)
```

#### Interpretation
- Positive PVO: Short-term volume above average
- Negative PVO: Short-term volume below average
- Crossovers indicate volume momentum shifts
- Confirms price breakouts with volume expansion

#### Related Trading Signals
<details markdown="1"><summary><strong>pvo_bullish_cross</strong> — TRIGGER — Check if PVO crosses above signal line (bullish volume)</summary>


#### Description
Check if PVO crosses above signal line (bullish volume)

#### Parameters
- `window_slow` (int, 15-50, optional, default=26): Slow EMA period
- `window_fast` (int, 5-20, optional, default=12): Fast EMA period
- `window_sign` (int, 3-15, optional, default=9): Signal line period

#### Usage
`{"name": "pvo_bullish_cross", "params": {"window_slow": value, "window_fast": value, "window_sign": value}}`

</details>


<details markdown="1"><summary><strong>pvo_bearish_cross</strong> — TRIGGER — Check if PVO crosses below signal line (bearish volume)</summary>


#### Description
Check if PVO crosses below signal line (bearish volume)

#### Parameters
- `window_slow` (int, 15-50, optional, default=26): Slow EMA period
- `window_fast` (int, 5-20, optional, default=12): Fast EMA period
- `window_sign` (int, 3-15, optional, default=9): Signal line period

#### Usage
`{"name": "pvo_bearish_cross", "params": {"window_slow": value, "window_fast": value, "window_sign": value}}`

</details>



---

### 6.4.9 VPT (Volume Price Trend)

#### Definition
Cumulative indicator that adds or subtracts a portion of volume based on the percentage change in price.

#### Formula
```
VPT = Previous VPT + Volume * ((Close - Previous Close) / Previous Close)
```

#### Interpretation
- Rising VPT: Accumulation / bullish volume-price relationship
- Falling VPT: Distribution / bearish volume-price relationship
- Divergences with price signal potential reversals
- More sensitive than OBV to price magnitude

#### Related Trading Signals
<details markdown="1"><summary><strong>vpt_bullish</strong> — FILTER — Check if VPT (Volume Price Trend) is rising</summary>


#### Description
Check if VPT (Volume Price Trend) is rising

#### Parameters
- `lookback` (int, 5-50, optional, default=20): Lookback for trend

#### Usage
`{"name": "vpt_bullish", "params": {"lookback": value}}`

</details>


<details markdown="1"><summary><strong>vpt_bearish</strong> — FILTER — Check if VPT (Volume Price Trend) is falling</summary>


#### Description
Check if VPT (Volume Price Trend) is falling

#### Parameters
- `lookback` (int, 5-50, optional, default=20): Lookback for trend

#### Usage
`{"name": "vpt_bearish", "params": {"lookback": value}}`

</details>



---

### Best Practices for Volume Indicators

- Always confirm price breakouts with volume
- Watch for volume divergences as early warnings
- Use VWAP for intraday trading reference
- Note that volume patterns differ by asset class
- Consider relative volume (vs. average) not just absolute

---

## 6.5 Breadth & Market Health

### Definition

Market breadth indicators measure the participation and health of the overall market by analyzing the number of advancing vs. declining stocks, new highs/lows, and other internal market metrics.

### Core Principles

- **Confirmation**: Healthy rallies should have broad participation
- **Divergence Warning**: Narrow rallies (few stocks leading) are suspect
- **Extremes**: Extreme breadth readings often precede reversals
- **Internal vs. External**: Breadth reveals what indices may hide
- **Cumulative Analysis**: Track breadth trends over time

---

### 6.5.1 Advance-Decline Line

#### Definition
Cumulative measure of the difference between advancing and declining stocks.

#### Formula
```
Daily A/D = Advancing Stocks - Declining Stocks
A/D Line = Cumulative sum of Daily A/D
```

#### Interpretation
- Rising A/D Line: Broad participation, healthy market
- Falling A/D Line: Narrow participation, weak market
- A/D divergence from index: Warning signal
- A/D making new highs with index: Confirms strength

---

### 6.5.2 McClellan Oscillator

#### Definition
Market breadth oscillator based on the difference between 19-day and 39-day EMAs of daily advance-decline data.

#### Formula
```
McClellan Oscillator = EMA(A-D, 19) - EMA(A-D, 39)
```

#### Interpretation
- Oscillator > 0: Bullish breadth
- Oscillator < 0: Bearish breadth
- Extreme positive readings: Overbought
- Extreme negative readings: Oversold
- Divergences with price signal potential reversals

---

### 6.5.3 McClellan Summation Index

#### Definition
Cumulative sum of the McClellan Oscillator, providing a longer-term view of market breadth.

#### Formula
```
Summation Index = Cumulative sum of McClellan Oscillator
```

#### Interpretation
- Rising Summation Index: Bull market environment
- Falling Summation Index: Bear market environment
- Extreme readings indicate potential reversals

---

### 6.5.4 Arms Index (TRIN)

#### Definition
Measures the relationship between advancing/declining stocks and advancing/declining volume.

#### Formula
```
TRIN = (Advancing Issues / Declining Issues) / (Advancing Volume / Declining Volume)
```

#### Interpretation
- TRIN < 1: Bullish (more volume in advancers)
- TRIN > 1: Bearish (more volume in decliners)
- TRIN < 0.5: Extremely bullish
- TRIN > 2.0: Extremely bearish (often contrarian buy signal)

---

### Best Practices for Breadth Indicators

- Use breadth to confirm index moves
- Watch for divergences between breadth and price
- Extreme breadth readings often precede reversals
- Breadth is most useful for equity indices
- Combine multiple breadth indicators for confirmation

---

## 6.6 Oscillators Deep Dive

### Definition

Oscillators are indicators that fluctuate within a bounded range, typically used to identify overbought/oversold conditions and momentum changes. This section provides advanced concepts for oscillator usage.

### Core Principles

- **Bounded Range**: Most oscillators move between fixed values (0-100 or centered on zero)
- **Overbought/Oversold**: Extreme readings don't guarantee reversals
- **Divergence Analysis**: Comparing oscillator to price action
- **Centerline Significance**: Crossing zero or 50 often significant
- **Trend Context**: Interpret oscillators differently in trends vs. ranges

### Advanced Oscillator Concepts

**Hidden Divergence:**
- Bullish Hidden: Price makes higher low, oscillator makes lower low (trend continuation)
- Bearish Hidden: Price makes lower high, oscillator makes higher high (trend continuation)

**Failure Swings:**
- Bullish Failure Swing: Oscillator fails to reach previous low, then breaks above intervening high
- Bearish Failure Swing: Oscillator fails to reach previous high, then breaks below intervening low

**Oscillator Trend Lines:**
- Draw trend lines on oscillator, not just price
- Oscillator trend line breaks can precede price breaks

**Range Shift:**
- In uptrends: RSI tends to oscillate 40-80 instead of 30-70
- In downtrends: RSI tends to oscillate 20-60 instead of 30-70
- Adjust overbought/oversold thresholds based on trend

### Best Practices for Oscillators

- Don't fade strong trends based solely on overbought/oversold
- Use divergence as a warning, not an entry trigger
- Consider trend context when interpreting readings
- Combine oscillator signals with price action confirmation
- Look for failure swings for higher probability signals

---

## 6.7 Moving Average Variants

### Definition

Beyond basic SMA and EMA, numerous moving average variants exist, each with different smoothing characteristics and applications.

### Moving Average Types

**Weighted Moving Average (WMA):**
```
WMA = Sum(Price_i * Weight_i) / Sum(Weight_i)
Where Weight_i = (n - i + 1) for linear weighting
```
- Gives more weight to recent prices linearly
- Less lag than SMA, more than EMA

**Hull Moving Average (HMA):**
```
HMA = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))
```
- Significantly reduces lag while maintaining smoothness
- Faster response than EMA

**Kaufman Adaptive Moving Average (KAMA):**
```
Efficiency Ratio (ER) = Change / Volatility
Smoothing Constant (SC) = (ER * (Fast - Slow) + Slow)^2
KAMA = Previous KAMA + SC * (Price - Previous KAMA)
```
- Adapts to market volatility
- Slow in ranges, fast in trends

**Variable Index Dynamic Average (VIDYA):**
- Volatility-adjusted smoothing
- More responsive during high volatility

**Arnaud Legoux Moving Average (ALMA):**
```
ALMA applies Gaussian distribution weighting
```
- Smooth with minimal lag
- Reduces noise while maintaining responsiveness

### Best Practices for Moving Average Selection

- Use SMA for simplicity and wide recognition (200 SMA)
- Use EMA for faster response to price changes
- Consider HMA or KAMA for reduced lag
- Match MA type to strategy requirements
- Test different variants on historical data

---

## 6.8 Return Indicators

Return indicators measure price changes over time, providing metrics for momentum, performance, and risk-adjusted returns. Unlike oscillators that normalize values, return indicators show actual percentage or absolute changes.

### 6.8.1 Rate of Change (ROC)

#### Definition

ROC measures the percentage price change over a specified lookback period.

#### Formula

```
ROC(n) = ((Close - Close[n]) / Close[n]) * 100
```

Where `n` is the lookback period (typically 12 bars).

#### Interpretation

- **Positive ROC**: Price is rising over the period (bullish momentum)
- **Negative ROC**: Price is falling over the period (bearish momentum)
- **Zero line cross**: Momentum shift from positive to negative or vice versa
- **Extreme values**: Can indicate overbought (high positive) or oversold (high negative) conditions

#### Trading Applications

- **Momentum confirmation**: Positive ROC confirms uptrend, negative ROC confirms downtrend
- **Divergence detection**: ROC making lower highs while price makes higher highs (bearish divergence)
- **Threshold signals**: ROC crossing above/below specific levels (e.g., +10%/-10%)
- **Zero line crosses**: ROC crossing zero indicates momentum direction change

#### Crypto-Specific Considerations

- Crypto markets exhibit higher ROC volatility than traditional assets
- Adjust thresholds higher for crypto (e.g., ±15-20% vs ±5-10% for stocks)
- Shorter periods (6-9 bars) may work better on lower timeframes (5m, 15m)
- Use in conjunction with volume to confirm momentum strength

#### MangroveAI API Reference

- **Indicator Class**: `ROC`
- **Category**: Momentum/Return
- **Required Data**: `close`
- **Parameters**:
  - `period`: Lookback period for ROC calculation (default: 12)
- **Outputs**: `roc` (percentage change)
- **Usage Example**: `ROC.compute(data={'close': df['Close']}, params={'period': 12})`

#### Related Trading Signals




### 6.8.2 Daily and Cumulative Returns

#### Daily Return

Measures the percentage change from the previous bar's close.

**Formula**:
```
Daily Return = ((Close - Close[1]) / Close[1]) * 100
```

**Use Cases**:
- Track short-term performance
- Identify volatility patterns
- Risk management (daily drawdown limits)

#### Cumulative Return

Measures the total percentage change from a starting point.

**Formula**:
```
Cumulative Return = ((Close - Close[start]) / Close[start]) * 100
```

**Use Cases**:
- Strategy performance tracking
- Benchmark comparison
- Target-based exits (e.g., exit at +20% cumulative return)

#### Related Trading Signals

<details markdown="1"><summary><strong>daily_return_positive</strong> — FILTER — Check if daily return is positive</summary>


#### Description
Evaluates to true when the current bar shows a positive return compared to the previous bar

#### Parameters
- `threshold` (float, 0.0-100.0, optional, default=0.0): Minimum return threshold in percent

#### Usage
`{"name": "daily_return_positive", "params": {}}`

</details>

<details markdown="1"><summary><strong>daily_return_negative</strong> — FILTER — Check if daily return is negative</summary>


#### Description
Evaluates to true when the current bar shows a negative return compared to the previous bar

#### Parameters
- `threshold` (float, 0.0-100.0, optional, default=0.0): Maximum return threshold in percent

#### Usage
`{"name": "daily_return_negative", "params": {}}`

</details>

<details markdown="1"><summary><strong>cumulative_return_positive</strong> — FILTER — Check if cumulative return from start is positive</summary>


#### Description
Evaluates to true when the total return from the strategy start point is positive

#### Parameters
- `threshold` (float, 0.0-100.0, optional, default=0.0): Minimum cumulative return in percent

#### Usage
`{"name": "cumulative_return_positive", "params": {}}`

</details>

<details markdown="1"><summary><strong>cumulative_return_target</strong> — FILTER — Check if cumulative return has reached target</summary>


#### Description
Evaluates to true when cumulative return exceeds a specified target threshold

#### Parameters
- `target` (float, 1-100, optional, default=10.0): Target cumulative return in percent

#### Usage
`{"name": "cumulative_return_target", "params": {"target": 20.0}}`

</details>

### Best Practices for Return Indicators

1. **Combine with trend indicators**: ROC confirms trend direction
2. **Use appropriate periods**: Shorter for day trading (6-9), longer for swing trading (12-25)
3. **Adjust for asset volatility**: Crypto needs wider thresholds than stocks
4. **Watch for divergences**: Price and ROC disagreement can signal reversals
5. **Consider timeframe**: Daily returns on 5m bars vs 1d bars have different meanings

---

## Summary

Technical indicators are tools for interpreting market data, not crystal balls for prediction. Effective use requires:

1. **Understanding the math**: Know what each indicator actually measures
2. **Context awareness**: Interpret indicators based on market conditions
3. **Confirmation**: Use multiple indicators from different categories
4. **Price primacy**: Indicators follow price; always consider price action first
5. **Simplicity**: More indicators don't equal better decisions

Select indicators that complement each other (trend + momentum + volume) and match your trading style and timeframe.

