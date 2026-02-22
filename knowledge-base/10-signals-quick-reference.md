# 10. Trading Signals Quick Reference

Alphabetical index of all trading signals. For comprehensive documentation, see the indicator section where each signal is documented.

## How to Use This Reference

Each signal is listed with:
- Quick description
- Parent indicator (with link to full documentation)
- Signal category

For detailed parameters, usage examples, and trading strategies, navigate to the parent indicator section in [6. Indicators](06-indicators.md).

## Important Note on Parameters

Where parameter values are provided in this reference, they serve as **examples only**. Optimal parameter values depend on multiple factors including:

- **Signal combinations**: Parameters should complement other signals in your strategy
- **Strategy goals**: Aggressive vs conservative approaches require different settings
- **Asset characteristics**: Bitcoin vs altcoins may need different sensitivity
- **Market conditions**: Trending vs ranging markets favor different parameters
- **Timeframe**: Lower timeframes (5m, 15m) typically react differently to parameter settings than higher timeframes (4h, 1d)
- **Volatility regime**: High volatility periods may require wider thresholds.


---

## Alphabetical Index


### A

**adi_bearish**
- Type: FILTER
- Parent Indicator: ADI (Accumulation/Distribution Index)
- Category: Volume
- Description: Check if ADI (Accumulation/Distribution) is falling

**adi_bullish**
- Type: FILTER
- Parent Indicator: ADI (Accumulation/Distribution Index)
- Category: Volume
- Description: Check if ADI (Accumulation/Distribution) is rising

**adx_bullish_di**
- Type: FILTER
- Parent Indicator: ADX (Average Directional Index)
- Category: Trend
- Description: Check if +DI is greater than -DI (bullish directional movement)

**adx_strong_trend**
- Type: FILTER
- Parent Indicator: ADX (Average Directional Index)
- Category: Trend
- Description: Check if ADX indicates a strong trend (>25)

**ao_bearish**
- Type: FILTER
- Parent Indicator: Awesome Oscillator
- Category: Momentum
- Description: Check if Awesome Oscillator indicates bearish momentum

**ao_bullish**
- Type: FILTER
- Parent Indicator: Awesome Oscillator
- Category: Momentum
- Description: Check if Awesome Oscillator indicates bullish momentum

**ao_zero_cross**
- Type: TRIGGER
- Parent Indicator: Awesome Oscillator
- Category: Momentum
- Description: Check if Awesome Oscillator crosses zero line

**aroon_crossover**
- Type: TRIGGER
- Parent Indicator: Aroon
- Category: Trend
- Description: Check if Aroon lines cross (trend change signal)

**aroon_down_trend**
- Type: FILTER
- Parent Indicator: Aroon
- Category: Trend
- Description: Check if Aroon Down indicates strong downtrend

**aroon_up_trend**
- Type: FILTER
- Parent Indicator: Aroon
- Category: Trend
- Description: Check if Aroon Up indicates strong uptrend

**atr_high_volatility**
- Type: FILTER
- Parent Indicator: ATR (Average True Range)
- Category: Volatility
- Description: Check if ATR indicates high volatility relative to price


### B

**bb_lower_breakout**
- Type: TRIGGER
- Parent Indicator: Bollinger Bands
- Category: Volatility
- Description: Check if price closes below the lower Bollinger Band

**bb_squeeze**
- Type: TRIGGER
- Parent Indicator: Bollinger Bands
- Category: Volatility
- Description: Detect Bollinger Band squeeze (low volatility, potential breakout)

**bb_upper_breakout**
- Type: TRIGGER
- Parent Indicator: Bollinger Bands
- Category: Volatility
- Description: Check if price closes above the upper Bollinger Band


### C

**cci_overbought**
- Type: FILTER
- Parent Indicator: CCI (Commodity Channel Index)
- Category: Trend
- Description: Check if CCI indicates overbought condition

**cci_oversold**
- Type: FILTER
- Parent Indicator: CCI (Commodity Channel Index)
- Category: Trend
- Description: Check if CCI indicates oversold condition

**cmf_bearish**
- Type: FILTER
- Parent Indicator: CMF (Chaikin Money Flow)
- Category: Volume
- Description: Check if CMF (Chaikin Money Flow) indicates selling pressure

**cmf_bullish**
- Type: FILTER
- Parent Indicator: CMF (Chaikin Money Flow)
- Category: Volume
- Description: Check if CMF (Chaikin Money Flow) indicates buying pressure

**cumulative_return_positive**
- Type: FILTER
- Parent Indicator: Cumulative Return
- Category: Unknown
- Description: Check if cumulative return from start is positive

**cumulative_return_target**
- Type: FILTER
- Parent Indicator: Cumulative Return
- Category: Unknown
- Description: Check if cumulative return has reached target


### D

**daily_return_negative**
- Type: FILTER
- Parent Indicator: Daily Return
- Category: Unknown
- Description: Check if daily return is negative

**daily_return_positive**
- Type: FILTER
- Parent Indicator: Daily Return
- Category: Unknown
- Description: Check if daily return is positive

**dc_lower_breakout**
- Type: TRIGGER
- Parent Indicator: Donchian Channel
- Category: Volatility
- Description: Check if price breaks below lower Donchian Channel (new low)

**dc_upper_breakout**
- Type: TRIGGER
- Parent Indicator: Donchian Channel
- Category: Volatility
- Description: Check if price breaks above upper Donchian Channel (new high)

**dpo_negative**
- Type: FILTER
- Parent Indicator: DPO (Detrended Price Oscillator)
- Category: Trend
- Description: Check if DPO is negative (price below detrended average)

**dpo_positive**
- Type: FILTER
- Parent Indicator: DPO (Detrended Price Oscillator)
- Category: Trend
- Description: Check if DPO is positive (price above detrended average)


### E

**ema_cross_down**
- Type: TRIGGER
- Parent Indicator: EMA (Exponential Moving Average)
- Category: Trend
- Description: Detect bearish EMA crossover (fast EMA crosses below slow EMA)

**ema_cross_up**
- Type: TRIGGER
- Parent Indicator: EMA (Exponential Moving Average)
- Category: Trend
- Description: Detect bullish EMA crossover (fast EMA crosses above slow EMA)

**ema_crossover**
- Type: TRIGGER
- Parent Indicator: EMA (Exponential Moving Average)
- Category: Trend
- Description: Detect EMA crossover signal with configurable direction (bullish or bearish)

**eom_bearish**
- Type: FILTER
- Parent Indicator: Ease of Movement
- Category: Volume
- Description: Check if Ease of Movement indicates bearish

**eom_bullish**
- Type: FILTER
- Parent Indicator: Ease of Movement
- Category: Volume
- Description: Check if Ease of Movement indicates bullish


### F

**force_bearish**
- Type: FILTER
- Parent Indicator: Force Index
- Category: Unknown
- Description: Check if Force Index indicates bearish momentum

**force_bullish**
- Type: FILTER
- Parent Indicator: Force Index
- Category: Unknown
- Description: Check if Force Index indicates bullish momentum


### I

**ichimoku_bearish**
- Type: FILTER
- Parent Indicator: Ichimoku Cloud
- Category: Trend
- Description: Check if Ichimoku indicates bearish signal (price below cloud)

**ichimoku_bullish**
- Type: FILTER
- Parent Indicator: Ichimoku Cloud
- Category: Trend
- Description: Check if Ichimoku indicates bullish signal (price above cloud)

**ichimoku_tk_cross**
- Type: TRIGGER
- Parent Indicator: Ichimoku Cloud
- Category: Trend
- Description: Check if Tenkan-sen crosses Kijun-sen (TK cross)

**is_above_sma**
- Type: FILTER
- Parent Indicator: SMA (Simple Moving Average)
- Category: Unknown
- Description: Check if current price is above Simple Moving Average


### K

**kama_cross_down**
- Type: TRIGGER
- Parent Indicator: KAMA (Kaufman Adaptive Moving Average)
- Category: Momentum
- Description: Check if price crosses below KAMA (bearish signal)

**kama_cross_up**
- Type: TRIGGER
- Parent Indicator: KAMA (Kaufman Adaptive Moving Average)
- Category: Momentum
- Description: Check if price crosses above KAMA (bullish signal)

**kc_lower_breakout**
- Type: TRIGGER
- Parent Indicator: Keltner Channel
- Category: Volatility
- Description: Check if price breaks below lower Keltner Channel band

**kc_upper_breakout**
- Type: TRIGGER
- Parent Indicator: Keltner Channel
- Category: Volatility
- Description: Check if price breaks above upper Keltner Channel band

**kst_bearish_cross**
- Type: TRIGGER
- Parent Indicator: KST (Know Sure Thing)
- Category: Trend
- Description: Check if KST crosses below signal line (bearish)

**kst_bullish_cross**
- Type: TRIGGER
- Parent Indicator: KST (Know Sure Thing)
- Category: Trend
- Description: Check if KST crosses above signal line (bullish)


### M

**macd_bearish_cross**
- Type: TRIGGER
- Parent Indicator: MACD (Moving Average Convergence Divergence)
- Category: Trend
- Description: Detect MACD bearish crossover (MACD line crosses below signal line)

**macd_bullish_cross**
- Type: TRIGGER
- Parent Indicator: MACD (Moving Average Convergence Divergence)
- Category: Trend
- Description: Detect MACD bullish crossover (MACD line crosses above signal line)

**macd_positive**
- Type: FILTER
- Parent Indicator: MACD (Moving Average Convergence Divergence)
- Category: Trend
- Description: Check if MACD histogram is positive (bullish momentum)

**mass_reversal_signal**
- Type: TRIGGER
- Parent Indicator: Mass Index
- Category: Unknown
- Description: Check if Mass Index signals potential reversal (reversal bulge)

**mfi_overbought**
- Type: FILTER
- Parent Indicator: MFI (Money Flow Index)
- Category: Volume
- Description: Check if MFI (Money Flow Index) indicates overbought condition

**mfi_oversold**
- Type: FILTER
- Parent Indicator: MFI (Money Flow Index)
- Category: Volume
- Description: Check if MFI (Money Flow Index) indicates oversold condition


### N

**nvi_bearish**
- Type: FILTER
- Parent Indicator: NVI (Negative Volume Index)
- Category: Volume
- Description: Check if NVI (Negative Volume Index) indicates smart money selling

**nvi_bullish**
- Type: FILTER
- Parent Indicator: NVI (Negative Volume Index)
- Category: Volume
- Description: Check if NVI (Negative Volume Index) indicates smart money buying


### O

**obv_bearish**
- Type: FILTER
- Parent Indicator: OBV (On Balance Volume)
- Category: Volume
- Description: Check if OBV is falling (bearish volume confirmation)

**obv_bullish**
- Type: FILTER
- Parent Indicator: OBV (On Balance Volume)
- Category: Volume
- Description: Check if OBV is rising (bullish volume confirmation)


### P

**ppo_bearish_cross**
- Type: TRIGGER
- Parent Indicator: PPO (Percentage Price Oscillator)
- Category: Momentum
- Description: Check if PPO crosses below signal line (bearish)

**ppo_bullish_cross**
- Type: TRIGGER
- Parent Indicator: PPO (Percentage Price Oscillator)
- Category: Momentum
- Description: Check if PPO crosses above signal line (bullish)

**price_above_ema**
- Type: FILTER
- Parent Indicator: EMA (Exponential Moving Average)
- Category: Unknown
- Description: Check if price is above the EMA

**psar_bearish**
- Type: FILTER
- Parent Indicator: PSAR (Parabolic SAR)
- Category: Trend
- Description: Check if PSAR indicates bearish trend (PSAR above price)

**psar_bullish**
- Type: FILTER
- Parent Indicator: PSAR (Parabolic SAR)
- Category: Trend
- Description: Check if PSAR indicates bullish trend (PSAR below price)

**psar_reversal**
- Type: TRIGGER
- Parent Indicator: PSAR (Parabolic SAR)
- Category: Trend
- Description: Check if PSAR flips sides (potential reversal)

**pvo_bearish_cross**
- Type: TRIGGER
- Parent Indicator: PVO (Percentage Volume Oscillator)
- Category: Momentum
- Description: Check if PVO crosses below signal line (bearish volume)

**pvo_bullish_cross**
- Type: TRIGGER
- Parent Indicator: PVO (Percentage Volume Oscillator)
- Category: Momentum
- Description: Check if PVO crosses above signal line (bullish volume)


### R

**roc_momentum_shift**
- Type: TRIGGER
- Parent Indicator: ROC (Rate of Change)
- Category: Momentum
- Description: Check if ROC crosses zero (momentum shift)

**roc_negative**
- Type: FILTER
- Parent Indicator: ROC (Rate of Change)
- Category: Momentum
- Description: Check if Rate of Change indicates negative momentum

**roc_positive**
- Type: FILTER
- Parent Indicator: ROC (Rate of Change)
- Category: Momentum
- Description: Check if Rate of Change indicates positive momentum

**rsi_cross_down**
- Type: TRIGGER
- Parent Indicator: RSI (Relative Strength Index)
- Category: Momentum
- Description: Check if RSI crosses below a threshold level

**rsi_cross_up**
- Type: TRIGGER
- Parent Indicator: RSI (Relative Strength Index)
- Category: Momentum
- Description: Check if RSI crosses above a threshold level

**rsi_overbought**
- Type: FILTER
- Parent Indicator: RSI (Relative Strength Index)
- Category: Momentum
- Description: Check if RSI is above the overbought threshold (default 70)

**rsi_oversold**
- Type: FILTER
- Parent Indicator: RSI (Relative Strength Index)
- Category: Momentum
- Description: Check if RSI is below the oversold threshold (default 30)


### S

**sma_cross_down**
- Type: TRIGGER
- Parent Indicator: SMA (Simple Moving Average)
- Category: Trend
- Description: Detect when fast SMA crosses below slow SMA (bearish exit signal)

**sma_cross_up**
- Type: TRIGGER
- Parent Indicator: SMA (Simple Moving Average)
- Category: Trend
- Description: Detect when fast SMA crosses above slow SMA (bullish entry signal)

**sma_crossover**
- Type: TRIGGER
- Parent Indicator: SMA (Simple Moving Average)
- Category: Trend
- Description: Detect SMA crossover signal with configurable direction (bullish or bearish)

**stc_overbought**
- Type: FILTER
- Parent Indicator: STC (Schaff Trend Cycle)
- Category: Trend
- Description: Check if STC indicates overbought condition

**stc_oversold**
- Type: FILTER
- Parent Indicator: STC (Schaff Trend Cycle)
- Category: Trend
- Description: Check if STC indicates oversold condition

**stoch_overbought**
- Type: FILTER
- Parent Indicator: Stochastic Oscillator
- Category: Momentum
- Description: Check if Stochastic %K is above the overbought threshold

**stoch_oversold**
- Type: FILTER
- Parent Indicator: Stochastic Oscillator
- Category: Momentum
- Description: Check if Stochastic %K is below the oversold threshold

**stochrsi_overbought**
- Type: FILTER
- Parent Indicator: Stochastic RSI
- Category: Momentum
- Description: Check if Stochastic RSI indicates overbought condition

**stochrsi_oversold**
- Type: FILTER
- Parent Indicator: Stochastic RSI
- Category: Momentum
- Description: Check if Stochastic RSI indicates oversold condition


### T

**trix_bearish**
- Type: FILTER
- Parent Indicator: TRIX
- Category: Trend
- Description: Check if TRIX indicates bearish momentum

**trix_bullish**
- Type: FILTER
- Parent Indicator: TRIX
- Category: Trend
- Description: Check if TRIX indicates bullish momentum

**tsi_bearish**
- Type: FILTER
- Parent Indicator: TSI (True Strength Index)
- Category: Momentum
- Description: Check if True Strength Index indicates bearish momentum (TSI < threshold)

**tsi_bullish**
- Type: FILTER
- Parent Indicator: TSI (True Strength Index)
- Category: Momentum
- Description: Check if True Strength Index indicates bullish momentum (TSI > threshold)


### U

**ulcer_high_risk**
- Type: FILTER
- Parent Indicator: Ulcer Index
- Category: Unknown
- Description: Check if Ulcer Index indicates high downside risk

**ulcer_low_risk**
- Type: FILTER
- Parent Indicator: Ulcer Index
- Category: Unknown
- Description: Check if Ulcer Index indicates low downside risk

**uo_overbought**
- Type: FILTER
- Parent Indicator: Ultimate Oscillator
- Category: Momentum
- Description: Check if Ultimate Oscillator indicates overbought condition

**uo_oversold**
- Type: FILTER
- Parent Indicator: Ultimate Oscillator
- Category: Momentum
- Description: Check if Ultimate Oscillator indicates oversold condition


### V

**vortex_bearish**
- Type: FILTER
- Parent Indicator: Vortex Indicator
- Category: Trend
- Description: Check if Vortex Indicator shows bearish trend (-VI > +VI)

**vortex_bullish**
- Type: FILTER
- Parent Indicator: Vortex Indicator
- Category: Trend
- Description: Check if Vortex Indicator shows bullish trend (+VI > -VI)

**vortex_crossover**
- Type: TRIGGER
- Parent Indicator: Vortex Indicator
- Category: Trend
- Description: Check if Vortex lines cross (trend change)

**vpt_bearish**
- Type: FILTER
- Parent Indicator: VPT (Volume Price Trend)
- Category: Volume
- Description: Check if VPT (Volume Price Trend) is falling

**vpt_bullish**
- Type: FILTER
- Parent Indicator: VPT (Volume Price Trend)
- Category: Volume
- Description: Check if VPT (Volume Price Trend) is rising

**vwap_above**
- Type: FILTER
- Parent Indicator: VWAP (Volume Weighted Average Price)
- Category: Volume
- Description: Check if price is above VWAP (bullish bias)

**vwap_below**
- Type: FILTER
- Parent Indicator: VWAP (Volume Weighted Average Price)
- Category: Volume
- Description: Check if price is below VWAP (bearish bias)


### W

**williams_r_overbought**
- Type: FILTER
- Parent Indicator: Williams %R
- Category: Momentum
- Description: Check if Williams %R is above the overbought threshold (> -20)

**williams_r_oversold**
- Type: FILTER
- Parent Indicator: Williams %R
- Category: Momentum
- Description: Check if Williams %R is below the oversold threshold (< -80)

**wma_cross_down**
- Type: TRIGGER
- Parent Indicator: WMA (Weighted Moving Average)
- Category: Trend
- Description: Check if fast WMA crosses below slow WMA (bearish)

**wma_cross_up**
- Type: TRIGGER
- Parent Indicator: WMA (Weighted Moving Average)
- Category: Trend
- Description: Check if fast WMA crosses above slow WMA (bullish)


### X

**x_social_sentiment_trigger**
- Type: TRIGGER
- Parent Indicator: X (Twitter) Social Signals
- Category: Unknown
- Description: Fires when social sentiment exceeds threshold

**x_topic_mention_trigger**
- Type: TRIGGER
- Parent Indicator: X (Twitter) Social Signals
- Category: Unknown
- Description: Fires when topic mentioned by enough influential users

**x_topic_sentiment_filter**
- Type: FILTER
- Parent Indicator: X (Twitter) Social Signals
- Category: Unknown
- Description: Checks if topic has sufficient social interest

**x_user_influence_filter**
- Type: FILTER
- Parent Indicator: X (Twitter) Social Signals
- Category: Unknown
- Description: Checks if X user has sufficient influence

**x_user_post_trigger**
- Type: TRIGGER
- Parent Indicator: X (Twitter) Social Signals
- Category: Unknown
- Description: Fires when a specific X user posts about a topic
