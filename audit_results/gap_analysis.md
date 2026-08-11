# Gap Analysis: MangroveKnowledgeBase vs Reference Libraries

**Generated**: 2026-08-10 21:01
**Our library**: 79 indicators, 249 signals

## Summary Statistics

| Library | Their Total | Our Coverage | Coverage % | Notes |
|---------|-----------|-------------|-----------|-------|
| Bukosabino `ta` | 43 | 43/43 matched | 100% | Full coverage of this library |
| TA-Lib (trading) | 135 | 32/79 of ours map to TA-Lib | 41% | Excludes 26 math/utility functions |
| TA-Lib (all) | 161 | -- | -- | Includes math transforms, operators |
| stock-indicators-python | 82 | 50/79 of ours map | 63% | Largest reference with 82 indicators |

**Missing indicator count by priority**:
- Priority A (should add): 5
- Priority B (nice to have): 30
- Priority C (skip): 96

## Coverage Matrix

Our indicators and which reference libraries have an equivalent:

| # | Indicator | Category | Bukosabino ta | TA-Lib | stock-indicators |
|---|-----------|----------|:---:|:---:|:---:|
| 1 | AwesomeOscillator | Momentum | Y | - | Y |
| 2 | BOP | Momentum | - | Y | Y |
| 3 | CMO | Momentum | - | Y | Y |
| 4 | KAMA | Momentum | Y | Y | Y |
| 5 | MOM | Momentum | - | Y | - |
| 6 | PPO | Momentum | Y | Y | - |
| 7 | PVO | Momentum | Y | - | Y |
| 8 | ROC | Momentum | Y | Y | Y |
| 9 | RSI | Momentum | Y | Y | Y |
| 10 | StochRSI | Momentum | Y | Y | Y |
| 11 | StochasticOscillator | Momentum | Y | Y | Y |
| 12 | TSI | Momentum | Y | - | Y |
| 13 | UltimateOscillator | Momentum | Y | Y | Y |
| 14 | WilliamsR | Momentum | Y | Y | Y |
| 15 | CandleGeometry | Pattern | - | - | - |
| 16 | CandleRaw | Pattern | - | - | - |
| 17 | CandleRelation | Pattern | - | - | - |
| 18 | CumulativeReturn | Return | Y | - | - |
| 19 | DailyLogReturn | Return | Y | - | - |
| 20 | DailyReturn | Return | Y | - | - |
| 21 | ADX | Trend | Y | Y | Y |
| 22 | ALMA | Trend | - | - | Y |
| 23 | Aroon | Trend | Y | Y | Y |
| 24 | CCI | Trend | Y | Y | Y |
| 25 | DEMA | Trend | - | Y | Y |
| 26 | DPO | Trend | Y | - | Y |
| 27 | Divergence | Trend | - | - | - |
| 28 | EMA | Trend | Y | Y | Y |
| 29 | EPMA | Trend | - | - | Y |
| 30 | HMA | Trend | - | - | Y |
| 31 | HeikinAshi | Trend | - | - | Y |
| 32 | Ichimoku | Trend | Y | - | Y |
| 33 | KST | Trend | Y | - | - |
| 34 | MACD | Trend | Y | Y | Y |
| 35 | MAMA | Trend | - | Y | Y |
| 36 | MassIndex | Trend | Y | - | - |
| 37 | MultiTFSlope | Trend | - | - | - |
| 38 | MultiTFTrend | Trend | - | - | - |
| 39 | PSAR | Trend | Y | Y | Y |
| 40 | SMA | Trend | Y | Y | Y |
| 41 | SMMA | Trend | - | - | Y |
| 42 | STC | Trend | Y | - | Y |
| 43 | SuperTrend | Trend | - | - | Y |
| 44 | SwingDelta | Trend | - | - | - |
| 45 | T3 | Trend | - | Y | Y |
| 46 | TEMA | Trend | - | Y | Y |
| 47 | TRIMA | Trend | - | Y | - |
| 48 | TRIX | Trend | Y | Y | Y |
| 49 | Vortex | Trend | Y | - | Y |
| 50 | WMA | Trend | Y | Y | Y |
| 51 | WilliamsAlligator | Trend | - | - | - |
| 52 | ATR | Volatility | Y | Y | Y |
| 53 | ATRTrailingStop | Volatility | - | - | - |
| 54 | BollingerBands | Volatility | Y | Y | Y |
| 55 | ChandelierExit | Volatility | - | - | - |
| 56 | ChandelierLevels | Volatility | - | - | - |
| 57 | DonchianChannel | Volatility | Y | - | Y |
| 58 | KeltnerChannel | Volatility | Y | - | Y |
| 59 | NATR | Volatility | - | Y | - |
| 60 | STARCBands | Volatility | - | - | Y |
| 61 | SqueezeDepth | Volatility | - | - | - |
| 62 | TTMSqueeze | Volatility | - | - | - |
| 63 | TrueRange | Volatility | - | - | - |
| 64 | UlcerIndex | Volatility | Y | - | Y |
| 65 | VolatilityEnvelope | Volatility | - | - | - |
| 66 | VolatilityStop | Volatility | - | - | Y |
| 67 | ADI | Volume | Y | Y | Y |
| 68 | ADOSC | Volume | - | Y | - |
| 69 | CMF | Volume | Y | - | Y |
| 70 | EaseOfMovement | Volume | Y | - | - |
| 71 | ForceIndex | Volume | Y | - | Y |
| 72 | KVO | Volume | - | - | Y |
| 73 | KlingerVolumeOscillator | Volume | - | - | - |
| 74 | MFI | Volume | Y | Y | Y |
| 75 | NVI | Volume | Y | - | - |
| 76 | OBV | Volume | Y | Y | Y |
| 77 | VPT | Volume | Y | - | - |
| 78 | VWAP | Volume | Y | - | Y |
| 79 | VWMA | Volume | - | - | Y |

### Coverage by Category

| Category | Count | In Bukosabino | In TA-Lib | In stock-indicators |
|----------|-------|:---:|:---:|:---:|
| Momentum | 14 | 11/14 | 11/14 | 12/14 |
| Pattern | 3 | 0/3 | 0/3 | 0/3 |
| Return | 3 | 3/3 | 0/3 | 0/3 |
| Trend | 31 | 15/31 | 14/31 | 23/31 |
| Volatility | 15 | 5/15 | 3/15 | 7/15 |
| Volume | 13 | 9/13 | 4/13 | 8/13 |

## Missing Indicators by Priority

### Priority A -- Should Add

Standard indicators widely used in production trading systems.

| # | Indicator | Description | Found In |
|---|-----------|-------------|----------|
| 1 | **APO** | Absolute Price Oscillator | TA-Lib |
| 2 | **TRANGE** | True Range | TA-Lib, stock-indicators-python |
| 3 | **alligator** | Williams Alligator (SMMA-based trend) | stock-indicators-python |
| 4 | **atr_stop** | ATR Trailing Stop | stock-indicators-python |
| 5 | **chandelier** | Chandelier Exit | stock-indicators-python |

### Priority B -- Nice to Have

Niche but useful indicators for specialized strategies.

| # | Indicator | Description | Found In |
|---|-----------|-------------|----------|
| 1 | AROONOSC | Aroon Oscillator | TA-Lib |
| 2 | BETA | Beta | TA-Lib, stock-indicators-python |
| 3 | CORREL | Pearson Correlation | TA-Lib, stock-indicators-python |
| 4 | HT_TRENDLINE | Hilbert Transform - Instantaneous Trendline | TA-Lib, stock-indicators-python |
| 5 | LINEARREG | Linear Regression | TA-Lib |
| 6 | LINEARREG_ANGLE | Linear Regression Angle | TA-Lib |
| 7 | LINEARREG_INTERCEPT | Linear Regression Intercept | TA-Lib |
| 8 | LINEARREG_SLOPE | Linear Regression Slope | TA-Lib, stock-indicators-python |
| 9 | MA | Moving Average (generic) | TA-Lib |
| 10 | STDDEV | Standard Deviation | TA-Lib, stock-indicators-python |
| 11 | chaikin_oscillator | Chaikin Oscillator (A/D Oscillator) | stock-indicators-python |
| 12 | chop | Choppiness Index | stock-indicators-python |
| 13 | connors_rsi | Connors RSI (composite RSI) | stock-indicators-python |
| 14 | dynamic | McGinley Dynamic | stock-indicators-python |
| 15 | elder_ray | Elder Ray Index (Bull/Bear Power) | stock-indicators-python |
| 16 | fcb | Fractal Chaos Bands | stock-indicators-python |
| 17 | fisher_transform | Fisher Transform | stock-indicators-python |
| 18 | fractal | Williams Fractal | stock-indicators-python |
| 19 | gator | Gator Oscillator | stock-indicators-python |
| 20 | hurst | Hurst Exponent | stock-indicators-python |
| 21 | ma_envelopes | Moving Average Envelopes | stock-indicators-python |
| 22 | pivot_points | Pivot Points | stock-indicators-python |
| 23 | pivots | Pivots (Williams Fractal Pivots) | stock-indicators-python |
| 24 | pmo | Price Momentum Oscillator | stock-indicators-python |
| 25 | prs | Price Relative Strength | stock-indicators-python |
| 26 | renko | Renko Charts | stock-indicators-python |
| 27 | rolling_pivots | Rolling Pivot Points | stock-indicators-python |
| 28 | smi | Stochastic Momentum Index | stock-indicators-python |
| 29 | stdev_channels | Standard Deviation Channels | stock-indicators-python |
| 30 | zig_zag | Zig Zag | stock-indicators-python |

### Priority C -- Skip (Unless Requested)

Redundant variants, math utilities, or very niche patterns.

<details><summary>96 indicators (click to expand)</summary>

| # | Indicator | Description | Found In |
|---|-----------|-------------|----------|
| 1 | ACCBANDS | Acceleration Bands | TA-Lib |
| 2 | ACOS | ACOS | TA-Lib |
| 3 | ADD | ADD | TA-Lib |
| 4 | ADXR | ADX Rating (smoothed ADX) | TA-Lib |
| 5 | ASIN | ASIN | TA-Lib |
| 6 | ATAN | ATAN | TA-Lib |
| 7 | AVGDEV | Average Deviation | TA-Lib |
| 8 | AVGPRICE | Average Price | TA-Lib |
| 9 | CDL2CROWS | CDL2CROWS | TA-Lib |
| 10 | CDL3LINESTRIKE | CDL3LINESTRIKE | TA-Lib |
| 11 | CDL3OUTSIDE | CDL3OUTSIDE | TA-Lib |
| 12 | CDL3STARSINSOUTH | CDL3STARSINSOUTH | TA-Lib |
| 13 | CDLABANDONEDBABY | CDLABANDONEDBABY | TA-Lib |
| 14 | CDLADVANCEBLOCK | CDLADVANCEBLOCK | TA-Lib |
| 15 | CDLBELTHOLD | CDLBELTHOLD | TA-Lib |
| 16 | CDLBREAKAWAY | CDLBREAKAWAY | TA-Lib |
| 17 | CDLCLOSINGMARUBOZU | CDLCLOSINGMARUBOZU | TA-Lib |
| 18 | CDLCONCEALBABYSWALL | CDLCONCEALBABYSWALL | TA-Lib |
| 19 | CDLCOUNTERATTACK | CDLCOUNTERATTACK | TA-Lib |
| 20 | CDLDOJISTAR | CDLDOJISTAR | TA-Lib |
| 21 | CDLEVENINGDOJISTAR | CDLEVENINGDOJISTAR | TA-Lib |
| 22 | CDLGAPSIDESIDEWHITE | CDLGAPSIDESIDEWHITE | TA-Lib |
| 23 | CDLHARAMICROSS | CDLHARAMICROSS | TA-Lib |
| 24 | CDLHIGHWAVE | CDLHIGHWAVE | TA-Lib |
| 25 | CDLHIKKAKE | CDLHIKKAKE | TA-Lib |
| 26 | CDLHIKKAKEMOD | CDLHIKKAKEMOD | TA-Lib |
| 27 | CDLHOMINGPIGEON | CDLHOMINGPIGEON | TA-Lib |
| 28 | CDLIDENTICAL3CROWS | CDLIDENTICAL3CROWS | TA-Lib |
| 29 | CDLINNECK | CDLINNECK | TA-Lib |
| 30 | CDLKICKING | CDLKICKING | TA-Lib |
| 31 | CDLKICKINGBYLENGTH | CDLKICKINGBYLENGTH | TA-Lib |
| 32 | CDLLADDERBOTTOM | CDLLADDERBOTTOM | TA-Lib |
| 33 | CDLLONGLINE | CDLLONGLINE | TA-Lib |
| 34 | CDLMATCHINGLOW | CDLMATCHINGLOW | TA-Lib |
| 35 | CDLMATHOLD | CDLMATHOLD | TA-Lib |
| 36 | CDLMORNINGDOJISTAR | CDLMORNINGDOJISTAR | TA-Lib |
| 37 | CDLONNECK | CDLONNECK | TA-Lib |
| 38 | CDLRICKSHAWMAN | CDLRICKSHAWMAN | TA-Lib |
| 39 | CDLRISEFALL3METHODS | CDLRISEFALL3METHODS | TA-Lib |
| 40 | CDLSEPARATINGLINES | CDLSEPARATINGLINES | TA-Lib |
| 41 | CDLSHORTLINE | CDLSHORTLINE | TA-Lib |
| 42 | CDLSTALLEDPATTERN | CDLSTALLEDPATTERN | TA-Lib |
| 43 | CDLSTICKSANDWICH | CDLSTICKSANDWICH | TA-Lib |
| 44 | CDLTAKURI | CDLTAKURI | TA-Lib |
| 45 | CDLTASUKIGAP | CDLTASUKIGAP | TA-Lib |
| 46 | CDLTHRUSTING | CDLTHRUSTING | TA-Lib |
| 47 | CDLTRISTAR | CDLTRISTAR | TA-Lib |
| 48 | CDLUNIQUE3RIVER | CDLUNIQUE3RIVER | TA-Lib |
| 49 | CDLUPSIDEGAP2CROWS | CDLUPSIDEGAP2CROWS | TA-Lib |
| 50 | CDLXSIDEGAP3METHODS | CDLXSIDEGAP3METHODS | TA-Lib |
| 51 | CEIL | CEIL | TA-Lib |
| 52 | COS | COS | TA-Lib |
| 53 | COSH | COSH | TA-Lib |
| 54 | DIV | DIV | TA-Lib |
| 55 | DX | Directional Movement Index | TA-Lib |
| 56 | EXP | EXP | TA-Lib |
| 57 | FLOOR | FLOOR | TA-Lib |
| 58 | HT_DCPERIOD | Hilbert Transform - Dominant Cycle Period | TA-Lib |
| 59 | HT_DCPHASE | Hilbert Transform - Dominant Cycle Phase | TA-Lib |
| 60 | HT_PHASOR | Hilbert Transform - Phasor Components | TA-Lib |
| 61 | HT_SINE | Hilbert Transform - SineWave | TA-Lib |
| 62 | HT_TRENDMODE | Hilbert Transform - Trend vs Cycle Mode | TA-Lib |
| 63 | IMI | Intraday Momentum Index | TA-Lib |
| 64 | LN | LN | TA-Lib |
| 65 | LOG10 | LOG10 | TA-Lib |
| 66 | MACDEXT | MACD with controllable MA type | TA-Lib |
| 67 | MACDFIX | MACD Fix 12/26 | TA-Lib |
| 68 | MAVP | MA with Variable Period | TA-Lib |
| 69 | MAX | MAX | TA-Lib |
| 70 | MEDPRICE | Median Price | TA-Lib |
| 71 | MIDPOINT | MidPoint over period | TA-Lib |
| 72 | MIDPRICE | Midpoint Price | TA-Lib |
| 73 | MIN | MIN | TA-Lib |
| 74 | MINMAX | MINMAX | TA-Lib |
| 75 | MINUS_DI | Minus Directional Indicator | TA-Lib |
| 76 | MINUS_DM | Minus Directional Movement | TA-Lib |
| 77 | MULT | MULT | TA-Lib |
| 78 | PLUS_DI | Plus Directional Indicator | TA-Lib |
| 79 | PLUS_DM | Plus Directional Movement | TA-Lib |
| 80 | ROCP | ROC Percentage | TA-Lib |
| 81 | ROCR | ROC Ratio | TA-Lib |
| 82 | ROCR100 | ROC Ratio 100 scale | TA-Lib |
| 83 | SAREXT | Parabolic SAR Extended | TA-Lib |
| 84 | SIN | SIN | TA-Lib |
| 85 | SINH | SINH | TA-Lib |
| 86 | SQRT | SQRT | TA-Lib |
| 87 | STOCHF | Stochastic Fast | TA-Lib |
| 88 | SUB | SUB | TA-Lib |
| 89 | SUM | SUM | TA-Lib |
| 90 | TAN | TAN | TA-Lib |
| 91 | TANH | TANH | TA-Lib |
| 92 | TSF | Time Series Forecast | TA-Lib |
| 93 | TYPPRICE | Typical Price | TA-Lib |
| 94 | VAR | Variance | TA-Lib |
| 95 | WCLPRICE | Weighted Close Price | TA-Lib |
| 96 | basic_quotes | Basic Quote Transforms | stock-indicators-python |

</details>

## Signal Gap Analysis

### Signal Coverage per Indicator

| Category | Indicator | Signal Count | Signals |
|----------|-----------|:-----------:|---------|
| Momentum | AwesomeOscillator | 3 | `ao_bearish`, `ao_bullish`, `ao_zero_cross` |
| Momentum | BOP | 0 | *none* |
| Momentum | CMO | 0 | *none* |
| Momentum | KAMA | 2 | `kama_cross_down`, `kama_cross_up` |
| Momentum | MOM | 0 | *none* |
| Momentum | PPO | 2 | `ppo_bearish_cross`, `ppo_bullish_cross` |
| Momentum | PVO | 2 | `pvo_bearish_cross`, `pvo_bullish_cross` |
| Momentum | ROC | 3 | `roc_momentum_shift`, `roc_negative`, `roc_positive` |
| Momentum | RSI | 8 | `rsi_bearish_divergence`, `rsi_bullish_divergence`, `rsi_hidden_bearish_divergence`, `rsi_hidden_bullish_divergence`, `rsi_cross_down`, `rsi_cross_up`, `rsi_overbought`, `rsi_oversold` |
| Momentum | StochRSI | 2 | `stochrsi_overbought`, `stochrsi_oversold` |
| Momentum | StochasticOscillator | 2 | `stoch_overbought`, `stoch_oversold` |
| Momentum | TSI | 2 | `tsi_bearish`, `tsi_bullish` |
| Momentum | UltimateOscillator | 2 | `uo_overbought`, `uo_oversold` |
| Momentum | WilliamsR | 2 | `williams_r_overbought`, `williams_r_oversold` |
| Return | CumulativeReturn | 2 | `cumulative_return_positive`, `cumulative_return_target` |
| Return | DailyLogReturn | 0 | *none* |
| Return | DailyReturn | 2 | `daily_return_negative`, `daily_return_positive` |
| Trend | ADX | 2 | `adx_bullish_di`, `adx_strong_trend` |
| Trend | ALMA | 0 | *none* |
| Trend | Aroon | 3 | `aroon_crossover`, `aroon_down_trend`, `aroon_up_trend` |
| Trend | CCI | 2 | `cci_overbought`, `cci_oversold` |
| Trend | DEMA | 0 | *none* |
| Trend | DPO | 2 | `dpo_negative`, `dpo_positive` |
| Trend | Divergence | 0 | *none* |
| Trend | EMA | 4 | `ema_cross_down`, `ema_cross_up`, `ema_crossover`, `price_above_ema` |
| Trend | EPMA | 0 | *none* |
| Trend | HMA | 0 | *none* |
| Trend | HeikinAshi | 0 | *none* |
| Trend | Ichimoku | 3 | `ichimoku_bearish`, `ichimoku_bullish`, `ichimoku_tk_cross` |
| Trend | KST | 2 | `kst_bearish_cross`, `kst_bullish_cross` |
| Trend | MACD | 7 | `macd_bearish_cross`, `macd_bullish_cross`, `macd_line_cross_down`, `macd_line_cross_up`, `macd_line_negative`, `macd_line_positive`, `macd_positive` |
| Trend | MAMA | 0 | *none* |
| Trend | MassIndex | 1 | `mass_reversal_signal` |
| Trend | MultiTFSlope | 0 | *none* |
| Trend | MultiTFTrend | 0 | *none* |
| Trend | PSAR | 3 | `psar_bearish`, `psar_bullish`, `psar_reversal` |
| Trend | SMA | 4 | `is_above_sma`, `sma_cross_down`, `sma_cross_up`, `sma_crossover` |
| Trend | SMMA | 0 | *none* |
| Trend | STC | 2 | `stc_overbought`, `stc_oversold` |
| Trend | SuperTrend | 0 | *none* |
| Trend | SwingDelta | 0 | *none* |
| Trend | T3 | 0 | *none* |
| Trend | TEMA | 0 | *none* |
| Trend | TRIMA | 0 | *none* |
| Trend | TRIX | 2 | `trix_bearish`, `trix_bullish` |
| Trend | Vortex | 3 | `vortex_bearish`, `vortex_bullish`, `vortex_crossover` |
| Trend | WMA | 2 | `wma_cross_down`, `wma_cross_up` |
| Trend | WilliamsAlligator | 0 | *none* |
| Volatility | ATR | 5 | `atr_high_volatility`, `atr_trailing_stop_flip_down`, `atr_trailing_stop_flip_up`, `atr_trailing_stop_long`, `atr_trailing_stop_short` |
| Volatility | ATRTrailingStop | 0 | *none* |
| Volatility | BollingerBands | 5 | `bb_above_upper`, `bb_below_lower`, `bb_lower_breakout`, `bb_squeeze`, `bb_upper_breakout` |
| Volatility | ChandelierExit | 0 | *none* |
| Volatility | ChandelierLevels | 0 | *none* |
| Volatility | DonchianChannel | 2 | `dc_lower_breakout`, `dc_upper_breakout` |
| Volatility | KeltnerChannel | 4 | `kc_above_upper`, `kc_below_lower`, `kc_lower_breakout`, `kc_upper_breakout` |
| Volatility | NATR | 0 | *none* |
| Volatility | STARCBands | 0 | *none* |
| Volatility | SqueezeDepth | 0 | *none* |
| Volatility | TTMSqueeze | 0 | *none* |
| Volatility | TrueRange | 0 | *none* |
| Volatility | UlcerIndex | 2 | `ulcer_high_risk`, `ulcer_low_risk` |
| Volatility | VolatilityEnvelope | 0 | *none* |
| Volatility | VolatilityStop | 0 | *none* |
| Volume | ADI | 2 | `adi_bearish`, `adi_bullish` |
| Volume | ADOSC | 0 | *none* |
| Volume | CMF | 2 | `cmf_bearish`, `cmf_bullish` |
| Volume | EaseOfMovement | 2 | `eom_bearish`, `eom_bullish` |
| Volume | ForceIndex | 2 | `force_bearish`, `force_bullish` |
| Volume | KVO | 0 | *none* |
| Volume | KlingerVolumeOscillator | 0 | *none* |
| Volume | MFI | 2 | `mfi_overbought`, `mfi_oversold` |
| Volume | NVI | 2 | `nvi_bearish`, `nvi_bullish` |
| Volume | OBV | 2 | `obv_bearish`, `obv_bullish` |
| Volume | VPT | 2 | `vpt_bearish`, `vpt_bullish` |
| Volume | VWAP | 2 | `vwap_above`, `vwap_below` |
| Volume | VWMA | 0 | *none* |

### Indicators with No Signal Coverage

- **ADOSC**
- **ALMA**
- **ATRTrailingStop**
- **BOP**
- **CMO**
- **ChandelierExit**
- **ChandelierLevels**
- **DEMA**
- **DailyLogReturn**
- **Divergence**
- **EPMA**
- **HMA**
- **HeikinAshi**
- **KVO**
- **KlingerVolumeOscillator**
- **MAMA**
- **MOM**
- **MultiTFSlope**
- **MultiTFTrend**
- **NATR**
- **SMMA**
- **STARCBands**
- **SqueezeDepth**
- **SuperTrend**
- **SwingDelta**
- **T3**
- **TEMA**
- **TRIMA**
- **TTMSqueeze**
- **TrueRange**
- **VWMA**
- **VolatilityEnvelope**
- **VolatilityStop**
- **WilliamsAlligator**

### Missing Signal Patterns

Common trading signal patterns not currently implemented:

**1. Divergence Detection** (Priority A)

RSI/MACD/OBV divergence from price (bullish/bearish). Price makes new high but indicator doesn't (bearish divergence), or vice versa. One of the most reliable reversal signals.

Applicable to: RSI, MACD, OBV, StochasticOscillator, CCI, MFI

**2. Multi-Timeframe Confirmation** (Priority A)

Signal on one timeframe confirmed by same or related signal on higher timeframe. E.g., RSI oversold on daily AND weekly.

Applicable to: RSI, MACD, SMA, EMA, ADX

**3. Moving Average Ribbon** (Priority A)

Multiple MAs (e.g., 10/20/50/100/200) alignment for trend strength. All MAs in order = strong trend. Tangled = consolidation.

Applicable to: SMA, EMA

**4. Volatility Squeeze / Expansion** (Priority A)

Bollinger Bands inside Keltner Channel (squeeze) then expansion breakout. We have bb_squeeze but not the combined BB+KC squeeze (TTM Squeeze).

Applicable to: BollingerBands, KeltnerChannel

**5. Volume Confirmation** (Priority B)

Price breakout confirmed by above-average volume. Currently signals evaluate volume indicators in isolation.

Applicable to: OBV, ADI, VPT, VWAP

**6. Support/Resistance Levels** (Priority B)

Price at pivot points, round numbers, or historical S/R levels. We have no pivot point indicator or S/R detection.

**7. Mean Reversion** (Priority B)

Price deviation from mean (z-score based) with reversion signals. Bollinger %B is close but explicit z-score signals are absent.

Applicable to: BollingerBands, SMA

**8. Trend Strength Composite** (Priority B)

Combine ADX + Aroon + Vortex for composite trend strength scoring. Individual signals exist but no composite.

Applicable to: ADX, Aroon, Vortex

**9. Candlestick + Indicator Confirmation** (Priority B)

Pattern signals confirmed by indicator state (e.g., Hammer at RSI oversold). Currently pattern signals and indicator signals are independent.

Applicable to: Hammer, RSI, StochasticOscillator

**10. Range/Consolidation Detection** (Priority B)

Detect sideways markets using ADX < threshold + narrowing BB + decreasing ATR. Useful as a filter to avoid false breakout signals.

Applicable to: ADX, ATR, BollingerBands

## Recommendations

### Immediate (Priority A Indicators)

Add these 5 indicators to reach parity with standard trading libraries:

- **Trend**: alligator, chandelier
- **Momentum**: APO
- **Volatility**: TRANGE, atr_stop

### High-Impact Signal Patterns

These signal patterns would significantly increase the library's value:

1. **Divergence Detection** -- RSI/MACD/OBV divergence from price (bullish/bearish).
1. **Multi-Timeframe Confirmation** -- Signal on one timeframe confirmed by same or related signal on higher timeframe.
1. **Moving Average Ribbon** -- Multiple MAs (e.
1. **Volatility Squeeze / Expansion** -- Bollinger Bands inside Keltner Channel (squeeze) then expansion breakout.
