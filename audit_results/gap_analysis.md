# Gap Analysis: MangroveKnowledgeBase vs Reference Libraries

**Generated**: 2026-04-15 22:39
**Our library**: 70 indicators, 136 signals

## Summary Statistics

| Library | Their Total | Our Coverage | Coverage % | Notes |
|---------|-----------|-------------|-----------|-------|
| Bukosabino `ta` | 43 | 43/43 matched | 100% | Full coverage of this library |
| TA-Lib (trading) | 135 | 42/70 of ours map to TA-Lib | 60% | Excludes 26 math/utility functions |
| TA-Lib (all) | 161 | -- | -- | Includes math transforms, operators |
| stock-indicators-python | 82 | 36/70 of ours map | 51% | Largest reference with 82 indicators |

**Missing indicator count by priority**:
- Priority A (should add): 25
- Priority B (nice to have): 30
- Priority C (skip): 96

## Coverage Matrix

Our indicators and which reference libraries have an equivalent:

| # | Indicator | Category | Bukosabino ta | TA-Lib | stock-indicators |
|---|-----------|----------|:---:|:---:|:---:|
| 1 | AwesomeOscillator | Momentum | Y | - | Y |
| 2 | KAMA | Momentum | Y | Y | Y |
| 3 | PPO | Momentum | Y | Y | - |
| 4 | PVO | Momentum | Y | - | Y |
| 5 | ROC | Momentum | Y | Y | Y |
| 6 | RSI | Momentum | Y | Y | Y |
| 7 | StochRSI | Momentum | Y | Y | Y |
| 8 | StochasticOscillator | Momentum | Y | Y | Y |
| 9 | TSI | Momentum | Y | - | Y |
| 10 | UltimateOscillator | Momentum | Y | Y | Y |
| 11 | WilliamsR | Momentum | Y | Y | Y |
| 12 | DarkCloudCover | Pattern | - | Y | - |
| 13 | Doji | Pattern | - | Y | Y |
| 14 | DragonflyDoji | Pattern | - | Y | - |
| 15 | Engulfing | Pattern | - | Y | - |
| 16 | EveningStar | Pattern | - | Y | - |
| 17 | GravestoneDoji | Pattern | - | Y | - |
| 18 | Hammer | Pattern | - | Y | - |
| 19 | HangingMan | Pattern | - | Y | - |
| 20 | Harami | Pattern | - | Y | - |
| 21 | InsideBar | Pattern | - | - | - |
| 22 | InvertedHammer | Pattern | - | Y | - |
| 23 | LongLeggedDoji | Pattern | - | Y | - |
| 24 | Marubozu | Pattern | - | Y | Y |
| 25 | MorningStar | Pattern | - | Y | - |
| 26 | NarrowRange | Pattern | - | - | - |
| 27 | OutsideBar | Pattern | - | - | - |
| 28 | PiercingLine | Pattern | - | Y | - |
| 29 | PinBar | Pattern | - | - | - |
| 30 | ShootingStar | Pattern | - | Y | - |
| 31 | SpinningTop | Pattern | - | Y | - |
| 32 | ThreeBlackCrows | Pattern | - | Y | - |
| 33 | ThreeInsideDown | Pattern | - | Y | - |
| 34 | ThreeInsideUp | Pattern | - | Y | - |
| 35 | ThreeWhiteSoldiers | Pattern | - | Y | - |
| 36 | TweezerBottoms | Pattern | - | - | - |
| 37 | TweezerTops | Pattern | - | - | - |
| 38 | TwoBarReversal | Pattern | - | - | - |
| 39 | CumulativeReturn | Return | Y | - | - |
| 40 | DailyLogReturn | Return | Y | - | - |
| 41 | DailyReturn | Return | Y | - | - |
| 42 | ADX | Trend | Y | Y | Y |
| 43 | Aroon | Trend | Y | Y | Y |
| 44 | CCI | Trend | Y | Y | Y |
| 45 | DPO | Trend | Y | - | Y |
| 46 | EMA | Trend | Y | Y | Y |
| 47 | Ichimoku | Trend | Y | - | Y |
| 48 | KST | Trend | Y | - | - |
| 49 | MACD | Trend | Y | Y | Y |
| 50 | MassIndex | Trend | Y | - | - |
| 51 | PSAR | Trend | Y | Y | Y |
| 52 | SMA | Trend | Y | Y | Y |
| 53 | STC | Trend | Y | - | Y |
| 54 | TRIX | Trend | Y | Y | Y |
| 55 | Vortex | Trend | Y | - | Y |
| 56 | WMA | Trend | Y | Y | Y |
| 57 | ATR | Volatility | Y | Y | Y |
| 58 | BollingerBands | Volatility | Y | Y | Y |
| 59 | DonchianChannel | Volatility | Y | - | Y |
| 60 | KeltnerChannel | Volatility | Y | - | Y |
| 61 | UlcerIndex | Volatility | Y | - | Y |
| 62 | ADI | Volume | Y | Y | Y |
| 63 | CMF | Volume | Y | - | Y |
| 64 | EaseOfMovement | Volume | Y | - | - |
| 65 | ForceIndex | Volume | Y | - | Y |
| 66 | MFI | Volume | Y | Y | Y |
| 67 | NVI | Volume | Y | - | - |
| 68 | OBV | Volume | Y | Y | Y |
| 69 | VPT | Volume | Y | - | - |
| 70 | VWAP | Volume | Y | - | Y |

### Coverage by Category

| Category | Count | In Bukosabino | In TA-Lib | In stock-indicators |
|----------|-------|:---:|:---:|:---:|
| Momentum | 11 | 11/11 | 8/11 | 10/11 |
| Pattern | 27 | 0/27 | 20/27 | 2/27 |
| Return | 3 | 3/3 | 0/3 | 0/3 |
| Trend | 15 | 15/15 | 9/15 | 13/15 |
| Volatility | 5 | 5/5 | 2/5 | 5/5 |
| Volume | 9 | 9/9 | 3/9 | 6/9 |

## Missing Indicators by Priority

### Priority A -- Should Add

Standard indicators widely used in production trading systems.

| # | Indicator | Description | Found In |
|---|-----------|-------------|----------|
| 1 | **ADOSC** | A/D Oscillator (Chaikin) | TA-Lib |
| 2 | **APO** | Absolute Price Oscillator | TA-Lib |
| 3 | **BOP** | Balance of Power | TA-Lib, stock-indicators-python |
| 4 | **CMO** | Chande Momentum Oscillator | TA-Lib, stock-indicators-python |
| 5 | **DEMA** | Double EMA | TA-Lib, stock-indicators-python |
| 6 | **MAMA** | MESA Adaptive MA | TA-Lib, stock-indicators-python |
| 7 | **MOM** | Momentum | TA-Lib |
| 8 | **NATR** | Normalized ATR | TA-Lib |
| 9 | **T3** | Triple EMA (T3) | TA-Lib, stock-indicators-python |
| 10 | **TEMA** | Triple EMA | TA-Lib, stock-indicators-python |
| 11 | **TRANGE** | True Range | TA-Lib, stock-indicators-python |
| 12 | **TRIMA** | Triangular MA | TA-Lib |
| 13 | **alligator** | Williams Alligator (SMMA-based trend) | stock-indicators-python |
| 14 | **alma** | Arnaud Legoux Moving Average | stock-indicators-python |
| 15 | **atr_stop** | ATR Trailing Stop | stock-indicators-python |
| 16 | **chandelier** | Chandelier Exit | stock-indicators-python |
| 17 | **epma** | Endpoint Moving Average | stock-indicators-python |
| 18 | **heikin_ashi** | Heikin-Ashi Candles | stock-indicators-python |
| 19 | **hma** | Hull Moving Average | stock-indicators-python |
| 20 | **kvo** | Klinger Volume Oscillator | stock-indicators-python |
| 21 | **smma** | Smoothed Moving Average (SMMA/RMA) | stock-indicators-python |
| 22 | **starc_bands** | STARC Bands | stock-indicators-python |
| 23 | **super_trend** | SuperTrend | stock-indicators-python |
| 24 | **volatility_stop** | Volatility Stop | stock-indicators-python |
| 25 | **vwma** | Volume Weighted Moving Average | stock-indicators-python |

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
| Momentum | KAMA | 2 | `kama_cross_down`, `kama_cross_up` |
| Momentum | PPO | 2 | `ppo_bearish_cross`, `ppo_bullish_cross` |
| Momentum | PVO | 2 | `pvo_bearish_cross`, `pvo_bullish_cross` |
| Momentum | ROC | 3 | `roc_momentum_shift`, `roc_negative`, `roc_positive` |
| Momentum | RSI | 4 | `rsi_cross_down`, `rsi_cross_up`, `rsi_overbought`, `rsi_oversold` |
| Momentum | StochRSI | 2 | `stochrsi_overbought`, `stochrsi_oversold` |
| Momentum | StochasticOscillator | 2 | `stoch_overbought`, `stoch_oversold` |
| Momentum | TSI | 2 | `tsi_bearish`, `tsi_bullish` |
| Momentum | UltimateOscillator | 2 | `uo_overbought`, `uo_oversold` |
| Momentum | WilliamsR | 2 | `williams_r_overbought`, `williams_r_oversold` |
| Return | CumulativeReturn | 2 | `cumulative_return_positive`, `cumulative_return_target` |
| Return | DailyLogReturn | 0 | *none* |
| Return | DailyReturn | 2 | `daily_return_negative`, `daily_return_positive` |
| Trend | ADX | 2 | `adx_bullish_di`, `adx_strong_trend` |
| Trend | Aroon | 3 | `aroon_crossover`, `aroon_down_trend`, `aroon_up_trend` |
| Trend | CCI | 2 | `cci_overbought`, `cci_oversold` |
| Trend | DPO | 2 | `dpo_negative`, `dpo_positive` |
| Trend | EMA | 4 | `ema_cross_down`, `ema_cross_up`, `ema_crossover`, `price_above_ema` |
| Trend | Ichimoku | 3 | `ichimoku_bearish`, `ichimoku_bullish`, `ichimoku_tk_cross` |
| Trend | KST | 2 | `kst_bearish_cross`, `kst_bullish_cross` |
| Trend | MACD | 3 | `macd_bearish_cross`, `macd_bullish_cross`, `macd_positive` |
| Trend | MassIndex | 1 | `mass_reversal_signal` |
| Trend | PSAR | 3 | `psar_bearish`, `psar_bullish`, `psar_reversal` |
| Trend | SMA | 4 | `is_above_sma`, `sma_cross_down`, `sma_cross_up`, `sma_crossover` |
| Trend | STC | 2 | `stc_overbought`, `stc_oversold` |
| Trend | TRIX | 2 | `trix_bearish`, `trix_bullish` |
| Trend | Vortex | 3 | `vortex_bearish`, `vortex_bullish`, `vortex_crossover` |
| Trend | WMA | 2 | `wma_cross_down`, `wma_cross_up` |
| Volatility | ATR | 1 | `atr_high_volatility` |
| Volatility | BollingerBands | 3 | `bb_lower_breakout`, `bb_squeeze`, `bb_upper_breakout` |
| Volatility | DonchianChannel | 2 | `dc_lower_breakout`, `dc_upper_breakout` |
| Volatility | KeltnerChannel | 2 | `kc_lower_breakout`, `kc_upper_breakout` |
| Volatility | UlcerIndex | 2 | `ulcer_high_risk`, `ulcer_low_risk` |
| Volume | ADI | 2 | `adi_bearish`, `adi_bullish` |
| Volume | CMF | 2 | `cmf_bearish`, `cmf_bullish` |
| Volume | EaseOfMovement | 2 | `eom_bearish`, `eom_bullish` |
| Volume | ForceIndex | 2 | `force_bearish`, `force_bullish` |
| Volume | MFI | 2 | `mfi_overbought`, `mfi_oversold` |
| Volume | NVI | 2 | `nvi_bearish`, `nvi_bullish` |
| Volume | OBV | 2 | `obv_bearish`, `obv_bullish` |
| Volume | VPT | 2 | `vpt_bearish`, `vpt_bullish` |
| Volume | VWAP | 2 | `vwap_above`, `vwap_below` |

### Indicators with No Signal Coverage

- **DailyLogReturn**

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

Add these 25 indicators to reach parity with standard trading libraries:

- **Moving Averages**: DEMA, MAMA, T3, TEMA, TRIMA, alma, epma, hma, smma, vwma
- **Trend**: alligator, chandelier, heikin_ashi, super_trend
- **Momentum**: APO, BOP, CMO, MOM
- **Volatility**: NATR, TRANGE, atr_stop, starc_bands, volatility_stop
- **Volume**: ADOSC, kvo

### High-Impact Signal Patterns

These signal patterns would significantly increase the library's value:

1. **Divergence Detection** -- RSI/MACD/OBV divergence from price (bullish/bearish).
1. **Multi-Timeframe Confirmation** -- Signal on one timeframe confirmed by same or related signal on higher timeframe.
1. **Moving Average Ribbon** -- Multiple MAs (e.
1. **Volatility Squeeze / Expansion** -- Bollinger Bands inside Keltner Channel (squeeze) then expansion breakout.
