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
- **Usage Example**: `SMA.compute(data={'close': df['close']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `EMA.compute(data={'close': df['close']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `ADX.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `Ichimoku.compute(data={'high': df['high'], 'low': df['low']}, params={'window_tenkan': value, 'window_kijun': value, 'window_senkou': value, 'visual': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `RSI.compute(data={'close': df['close']}, params={'window': value})`
- **Reference**: https://www.investopedia.com/terms/r/rsi.asp

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `MACD.compute(data={'close': df['close']}, params={'window_slow': value, 'window_fast': value, 'window_sign': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

---

### 6.2.3 Stochastic Oscillator


#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `CCI.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close']}, params={'window': value, 'constant': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `ROC.compute(data={'close': df['close']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

---

### 6.2.6 Williams %R


#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `MFI.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close'], 'volume': df['volume']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Outputs**: `mavg`, `hband`, `lband`, `wband`, `pband`
- **Usage Example**: `BollingerBands.compute(data={'close': df['close']}, params={'window': value, 'window_dev': value})`

`hband_indicator` and `lband_indicator` were removed: a boolean decision over a numeric series the
indicator already emits is a signal, not a measurement. That content is the `bb_above_upper` and
`bb_below_lower` FILTER signals.

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `ATR.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

---

### 6.3.3 Keltner Channels


#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
Upper Channel = Highest High over the n periods PRECEDING the current bar
Lower Channel = Lowest Low over the n periods PRECEDING the current bar
Middle Line = (Upper + Lower) / 2
Width = (Upper - Lower) / Middle * 100
Standard period: 20
```

#### Interpretation
- Price at upper channel: Strong uptrend / potential overbought
- Price at lower channel: Strong downtrend / potential oversold
- Breakouts above upper channel signal long entries
- Breakouts below lower channel signal short entries

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `OBV.compute(data={'close': df['close'], 'volume': df['volume']}, params={})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

---

### 6.4.2 Accumulation/Distribution Line (ADL)


#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
The average price weighted by volume over a rolling window, representing the price at which
most trading has actually occurred. A rolling window is used rather than the session anchor
of the textbook definition: anchoring resets at each session open, and a continuously traded
24/7 market has no session boundary to reset at.

#### Formula
```
VWAP = Rolling_Sum(Typical Price * Volume, window) / Rolling_Sum(Volume, window)
Typical Price = (High + Low + Close) / 3
```

#### Interpretation
- Price above VWAP: Buyers in control
- Price below VWAP: Sellers in control
- VWAP as dynamic support/resistance
- Deviation from VWAP indicates overextension

#### Trading Applications
- Dynamic support and resistance in a continuously traded market
- Volume-weighted trend reference, less sensitive to low-volume bars than a plain moving average
- Entry/exit timing against a volume-aware fair-value estimate
- Mean reversion trading

> **On session-traded instruments** (equities, futures with a defined session) this rolling form
> is not the institutional execution benchmark, since that benchmark is defined by the session it
> anchors to. It is exactly VWMA computed on typical price.

---


#### MangroveAI API Reference

- **Indicator Class**: `VWAP`
- **Category**: Volume
- **Required Data**: `high`, `low`, `close`, `volume`
- **Parameters**:
  - `window`: Parameter for VWAP calculation
- **Outputs**: `vwap`
- **Usage Example**: `VWAP.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close'], 'volume': df['volume']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `CMF.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close'], 'volume': df['volume']}, params={'window': value})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

---

### 6.4.5 Klinger Volume Oscillator

#### Definition
Volume-based oscillator designed to identify long-term money flow trends.

#### Formula
```
tp    = (high + low + close) / 3
trend = +1 if tp > prev_tp else -1        (binary -- no flat branch)
dm    = high - low
cm    = prev_cm + dm   if trend == prev_trend   (accumulate within a trend)
        prev_dm + dm   otherwise                (reset on a trend change)

Volume Force = Volume * |2 * (dm/cm - 1)| * trend * 100
KVO    = EMA(Volume Force, 34) - EMA(Volume Force, 55)
Signal = EMA(KVO, 13)
```

`cm` is a path-dependent accumulator whose reset points are set by the trend series itself, so this
cannot be expressed as a rolling window.

Two incompatible variants circulate under this name. The above is Klinger's original, implemented by
`KlingerVolumeOscillator`. The simplified form implemented by `KVO` signs volume by nothing more than
the direction of the typical price change; on identical data with identical periods the original runs
about 145x larger. Read either by sign, slope and signal-line crossings -- never by level, and never
against each other.

#### Interpretation
- KVO above zero: Bullish volume pressure
- KVO below zero: Bearish volume pressure
- KVO crossing signal line: Potential trade signal
- Divergences with price indicate weakening trends
- The level is scale-arbitrary and roughly 145x the simplified KVO's -- read sign, slope and crossings, never magnitude

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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
- **Usage Example**: `ROC.compute(data={'close': df['close']}, params={'period': 12})`

#### Related Trading Signals

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

See the [Signal Catalog](/signals/catalog) for full parameter details and usage examples.

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

