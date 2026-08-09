# Changelog

All notable changes to the `mangrove-kb` package will be documented in this file.

This project uses [Semantic Versioning](https://semver.org/).

## [2.0.0] - Unreleased

**A signal/indicator knowledge graph, and the reorganisation it forced.** Every indicator now
carries a class describing what its output tells you about its input, and every modelled signal
carries a formula stating the predicate it computes -- 301 nodes, 732 edges, in
`ontology/signal-indicator-ontology.json`.

Major, because files moved and things were renamed. **No registered signal name changed meaning,
and every old name still evaluates**, so stored strategies are unaffected; the breaks are in import
paths, and all of them are shimmed.

### The rule

Indicators are measurements, never verdicts; signals are verdicts. Applying it changed five
indicators:

- `Divergence` emitted four booleans -- it concluded rather than measured. Replaced by `SwingDelta`,
  which emits the two changes a divergence is drawn from; the four sign comparisons moved into the
  signals.
- `TTMSqueeze` emitted `squeeze_on` / `squeeze_fired` beside a real momentum. Replaced by
  `SqueezeDepth`, which emits how far inside the Keltner Channel the Bollinger Bands sit -- positive
  IS the squeeze, and the magnitude the boolean discarded comes back.
- `MultiTFTrend` emitted a ternary -1/0/+1. Replaced by `MultiTFSlope`, which emits the normalised
  higher-timeframe slope. `slope_threshold` moved to the signals with the verdict.
- `ChandelierExit` and `VolatilityStop` were excluded from the ontology as "stateful policy rules"
  and should not have been -- both are stateless measurements whose names stated a use. Now
  `ChandelierLevels` and `VolatilityEnvelope`, both class `volatility`.

Every split was proven equivalent before landing: reconstructing the old outputs from the new
measurements reproduces them bar-for-bar on a 1,294-bar BTC fixture, and the rewritten signals
disagree with the old implementations on zero expanding-window evaluations.

### Signal files are named for their class

`volume.py` is gone -- there is no `volume` indicator class, and its 33 signals split four ways by
the class of the indicator each reads. `patterns.py` is `pattern.py`. `trend.py` went from 88
signals to 7. Files now: `averaging` 55, `momentum` 56, `oscillator` 30, `volatility` 29,
`pattern` 40, `flow` 10, `trend` 7, `onchain` 10, `defi_pro` 10.

### Nothing breaks

- Retired signal names resolve through a registry alias, evaluate identically, and warn. They are
  excluded from `names()` and the catalogue so no signal is counted twice.
- `mangrove_kb.signals.volume` and `.patterns` survive as shim modules.
- Signals that moved between modules that both still exist resolve through a PEP 562 `__getattr__`,
  so `from mangrove_kb.signals.trend import vortex_bullish` still works.
- `SuperTrend`, `PSAR` and `ATRTrailingStop` are deprecated and out of `__all__`, but importable.

### Fixed

- Every `stockcharts.com/doku.php` reference URL in the indicator docstrings was dead (30 of them);
  ChartSchool moved. All replaced with fetched, title-verified links.
- `sma_crossover` guarded on `len < window_slow` when a crossing needs the prior bar too, so the
  lifted warmup understated by one.
- `RuleRegistry` gained `names()`, `has()`, `alias()` and `resolve()`.
- Five `defi_pro` signals can never fire with the data their provider actually returns, and the
  on-chain window arithmetic counts observations rather than bars -- documented in
  [#109](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/109), not yet fixed.

### Known gaps

216 of 247 signals are modelled. The 20 `onchain` / `defi_pro` signals read provider feeds rather
than indicator outputs and have no class; 11 read a verdict and never will. All 31 still evaluate.

## [1.0.0] - Unreleased

Comprehensive expansion to 99 indicators and 223 signals. This release adds 29 standard
indicators (Priority A from the v0.4.0 gap analysis plus four signal-pattern indicators)
and 87 signals, bringing the library to feature parity with production trading platforms.
All new indicators follow the vectorization discipline established in prior optimization
waves: no `.rolling().apply(python_callback)`, cached per-window constants,
`np.fmax`/`sliding_window_view` where appropriate, stateless classmethods.

Every new indicator is audited for numerical correctness against `pandas-ta` (indicator
audit) and every new signal is verified bar-by-bar against a sliding-window ground truth
(zero false positives, zero false negatives on a 1294-bar BTC daily fixture). Every
indicator is benchmarked on the same fixture and tier-classified
(fast < 0.5 ms, moderate 0.5-2 ms, slow 2-20 ms).

### Added (Wave A -- Simple Moving Averages)
- **DEMA** (Double Exponential Moving Average). Reference: Patrick Mulloy, *Technical Analysis of Stocks & Commodities*, Jan 1994.
- **TEMA** (Triple Exponential Moving Average). Same Mulloy paper.
- **TRIMA** (Triangular Moving Average). Double-smoothed SMA with TA-Lib even/odd window convention.
- **SMMA** (Smoothed Moving Average / Wilder's / RMA). `ewm(alpha=1/n)`. Reference: Wilder 1978.
- **VWMA** (Volume-Weighted Moving Average). `sum(close*vol)/sum(vol)` over window.
- **EPMA** (End Point Moving Average / LSMA). Linear regression endpoint; implemented as FIR filter with cached weights via `np.convolve`.
- 18 new signals: `is_above_<ma>`, `<ma>_cross_up`, `<ma>_cross_down` for each new MA.

### Added (Wave B -- Complex Moving Averages)
- **HMA** (Hull Moving Average). Formula: `WMA(2*WMA(n/2) - WMA(n), sqrt(n))`. Reuses our vectorized WMA. Reference: Alan Hull, 2005.
- **ALMA** (Arnaud Legoux Moving Average). Gaussian-weighted FIR filter with `@lru_cache(maxsize=256)` keyed on `(window, offset, sigma)`, applied via `np.convolve`. Reference: Legoux & Kouzis-Loukas, 2009.
- **T3** (Tillson T3). Six chained EMAs combined via Tillson's volume-factor formula `T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3`. Reference: Tim Tillson, *Technical Analysis of Stocks & Commodities*, Jan 1998.
- **MAMA** (MESA Adaptive Moving Average). Hilbert-transform-adaptive MA with FAMA follower output. Genuinely sequential (per-bar Hilbert phase/period state); pure-Python loop documented as state-dependent. Reference: John F. Ehlers, *Technical Analysis of Stocks & Commodities*, Sept 2001.
- 12 new signals: `is_above_hma/alma/t3/mama` (FILTER), `{hma,alma,t3}_cross_up/down` (fast-vs-slow window crossover TRIGGERs), `mama_cross_up/down` (MAMA/FAMA crossover TRIGGERs).

### Added (Wave C -- Momentum)
- **MOM** (Momentum). `close - close.shift(n)`. Absolute price change over lookback. TA-Lib canonical.
- **BOP** (Balance of Power). `(close - open) / (high - low)`. Intrabar buying vs. selling pressure. Reference: Igor Livshin, TA-Lib canonical.
- **APO** (Absolute Price Oscillator). `EMA(fast) - EMA(slow)` -- equivalent to the MACD line. Our implementation uses EMA; pandas-ta defaults to SMA.
- **CMO** (Chande Momentum Oscillator). Rolling-sum variant: `100 * (pos_sum - neg_sum) / (pos_sum + neg_sum)`. Ranges [-100, +100]. Reference: Tushar Chande, *The New Technical Trader* (1994).
- 16 new signals: for each of MOM/BOP/APO (zero-centered): `<ind>_bullish`, `<ind>_bearish` (FILTER), `<ind>_cross_up`, `<ind>_cross_down` (zero-line crossover TRIGGER). For CMO: `cmo_overbought`, `cmo_oversold` (FILTER), `cmo_cross_up`, `cmo_cross_down` (threshold crossover TRIGGER, analogous to RSI).

### Added (Wave F -- Volume)
- **ADOSC** (Chaikin A/D Oscillator). `EMA(AD, fast) - EMA(AD, slow)`. Reuses our ADI indicator for the AD line and our EMA for smoothing. Reference: Marc Chaikin, TA-Lib canonical.
- **KVO** (Klinger Volume Oscillator). Simplified modern form matching pandas-ta/TradingView: `signed_volume = volume * sign(hlc3.diff())`, `KVO = EMA(signed_volume, fast) - EMA(signed_volume, slow)`, plus `KVO_signal = EMA(KVO, signal_window)`. Signed-volume computation is bit-exact vs pandas-ta.
- 8 new signals: `adosc_bullish/bearish` (FILTER), `adosc_cross_up/down` (zero-line TRIGGER), `kvo_bullish/bearish` (vs signal line FILTER), `kvo_bullish_cross/bearish_cross` (signal-line cross TRIGGER).

### Added (Wave E -- Trend)
- **HeikinAshi**. Smoothed candlestick transform: HA_close = (O+H+L+C)/4; HA_open = avg of prev HA_open and HA_close (sequential, state-dependent). HA_high/low fully vectorized with `np.fmax`/`np.fmin`.
- **ChandelierExit** (Chuck LeBeau). `highest_high(n) - k*ATR` (long_stop), `lowest_low(n) + k*ATR` (short_stop). Both always computed; user picks which applies to their position.
- **WilliamsAlligator** (Bill Williams, 1998). Three SMMA lines on median price ((H+L)/2) with forward offsets (Jaw 13+8, Teeth 8+5, Lips 5+3). Offsets applied via `shift(+n)` -- lookahead-free in backtesting (value at bar t is SMMA computed at t-offset).
- **SuperTrend** (Olivier Seban). ATR-scaled bands around hl2 with trend-flip rule: close crosses opposite band -> flip; between flips, active band ratchets. State-dependent loop; matches pandas-ta bit-exact.
- 11 new signals: `heikin_ashi_bullish/bearish` (FILTER), `chandelier_long_stop_hit/short_stop_hit` (FILTER, exit triggers), `alligator_bullish/bearish/sleeping` (regime FILTER), `supertrend_long/short` (regime FILTER), `supertrend_flip_up/flip_down` (TRIGGER).

### Added (Wave D -- Volatility)
- **TrueRange** (standalone Wilder TR). Raw per-bar volatility; building block for ATR/Vortex/UO but useful on its own. Reuses our existing `true_range()` helper. Reference: Wilder 1978.
- **NATR** (Normalized ATR). `100 * ATR / close`. Scale-invariant volatility measure. Uses Wilder (RMA) smoothing -- matches TA-Lib canonical convention; pandas-ta defaults to EMA-smoothing which is non-standard.
- **ATRTrailingStop** (Chuck LeBeau variant). Stateful trailing stop with long/short regimes; stop ratchets in trend direction and flips on opposite-side close cross. Returns trailing stop level and direction (+1/-1). Genuinely sequential (documented). Reference: Chuck LeBeau, popularized in Chande's *Beyond Technical Analysis* (1997).
- **STARCBands** (Stoller Average Range Channels). `SMA +/- multiplier * ATR`, with independent windows for SMA and ATR. Similar to Keltner Channel but with configurable separate windows. Reference: Manning Stoller.
- **VolatilityStop**. Stdev-of-returns envelope centered on prev close -- `prev_close +/- multiplier * stdev(returns) * prev_close`. Distinct from ATR Trailing Stop in both construction (stdev vs TR) and regime (static envelope vs ratcheting stop).
- 10 new signals: `natr_high_volatility`, `natr_low_volatility` (FILTER), `atr_trailing_stop_long/short` (FILTER), `atr_trailing_stop_flip_up/down` (TRIGGER), `starc_upper_breakout`, `starc_lower_breakout` (FILTER), `volatility_stop_upper`, `volatility_stop_lower` (FILTER).

### Added (Wave G -- Signal Patterns)
- **MARibbon**. Generalized moving-average ribbon: computes N SMAs over user-supplied windows and returns three mutually-exclusive regime flags (`ribbon_bullish` = all windows monotonic descending in value, `ribbon_bearish` = monotonic ascending, `ribbon_tangled` = neither). Default windows are the 8-MA Fibonacci ribbon `[5, 8, 13, 21, 34, 55, 89, 144]`; any monotonically-increasing window list is accepted.
- **TTMSqueeze** (John Carter, *Mastering the Trade*, 2005). Detects BB-inside-KC "squeeze" compression, squeeze release (prev bar on, current bar off), and Carter's linear-regression momentum histogram `LR_slope(close - (highest_high + lowest_low)/2 + SMA(close))/2`. Reuses our BollingerBands and KeltnerChannel; momentum via vectorized `sliding_window_view` + closed-form linear regression coefficients.
- **Divergence** (Cardwell / Constance Brown, *Technical Analysis for the Trading Professional*, 2000). Generic four-way divergence detector between price and an arbitrary indicator series (RSI/MACD/OBV/...). Swing points detected via `scipy.signal.argrelextrema`; fire bar is `max(price_swing, indicator_swing) + swing_window` to guarantee lookahead-free evaluation (sliding-window and full-dataset verdicts match bit-exactly).
- **MultiTFTrend**. Higher-timeframe confirmation indicator. Resamples OHLC to a higher timeframe (e.g., `1W`), computes `EMA(window)` slope direction on the higher TF, and forward-fills back to the base-TF index so every bar carries the enclosing higher-TF trend. Requires a DatetimeIndex; returns `0` for bars that cannot be confirmed.
- 12 new signals: `ma_ribbon_bullish/bearish/tangled` (FILTER), `ttm_squeeze_active` (FILTER), `ttm_squeeze_fired_bullish/bearish` (TRIGGER), `rsi_bullish_divergence/bearish_divergence/hidden_bullish_divergence/hidden_bearish_divergence` (TRIGGER), `multi_tf_trend_bullish/bearish` (FILTER).

## [0.4.0] - 2026-04-16

### Fixed
- **PSAR `psar_down_indicator` copy-paste bug**: Convenience output `psar_down_indicator` was computed from `psar_up` instead of `psar_down`. Core PSAR outputs (psar, psar_up, psar_down) were unaffected. Bug existed in upstream reference (Bukosabino ta) as well.
- **PSAR indexing inconsistency**: Changed `psar[i]` to `psar.iloc[i]` for index-safety in the PSAR computation loop.
- **TRIX, KST, DPO, Vortex fill_value lookahead**: Removed `fill_value=series.mean()` from shift operations in TRIX, KST (4 shifts), DPO, and Vortex indicators. The mean of the entire series introduced subtle lookahead bias into early warmup bars. Shifted positions now produce NaN (standard behavior). Post-warmup values are unchanged.

### Added
- **PiercingLine `require_gap` parameter**: New boolean parameter (default `True`). When `False`, relaxes the gap requirement from "open below previous low" to "open below previous close", making the pattern detectable in 24/7 crypto/forex markets where price gaps are rare.
- **DarkCloudCover `require_gap` parameter**: Same as PiercingLine. When `False`, relaxes from "open above previous high" to "open above previous close".
- **TwoBarReversal `close_proximity` parameter**: New float parameter (default `0.25`, range `0.1-0.5`). Controls how close the close must be to the high/low for reversal detection. Previously hardcoded at `0.25`.
- **Indicator audit framework** at `scripts/audit/` -- reproducible accuracy verification for all 70 indicators and 136 signals against Bukosabino `ta` reference library.
- **Audit reports** at `audit_results/` -- indicator, signal, pattern, and gap analysis reports.

### Documentation
- Updated KB document 07-chart-patterns.md with notes on `require_gap` and `close_proximity` parameters
- Updated signals quick reference with new parameter documentation

## [0.3.0] - 2026-04-01

### Fixed
- Capped all window-type signal parameters at max 200 to prevent excessive computation
- Docker build with setuptools-scm (pass version via build arg)

### Added
- CODEOWNERS file
- CodeQL security scanning
- Dependabot configuration

## [0.2.0] - 2026-03-12

### Breaking Changes
- `IndicatorInterface.inputs` and `IndicatorInterface.outputs` are now classmethods (call with `()`)

### Added
- 40 pattern signals (Doji variants, Hammer, Engulfing, Stars, Three White Soldiers, etc.)
- 27 pattern indicators with candlestick geometry detection
- Automated PyPI release workflow via GitHub Actions (`workflow_dispatch`)
- `CHANGELOG.md`

### Fixed
- Standardized all signal parameters to `window` (from `lookback`, `period`, `length`)
- Pattern signal names in quick reference now match `RuleRegistry`
- KB documentation signal counts updated to reflect actual 136 signals
- Pydantic V2 compatibility (migrated from deprecated `class Config` pattern)
- Removed dead code (`indicator_utils.py`)

### Improved
- KB server concurrency: sync routes, WAL mode, N+1 query fix, 2 workers
- Developer docs portal (Mintlify) with Docker build support

## [0.1.1] - 2025-12-15

### Fixed
- Publish script now bumps `__version__` in `__init__.py`
- Renamed old package references to `mangrove_kb`

## [0.1.0] - 2025-12-01

### Added
- Initial release
- 96 trading signals (Momentum, Trend, Volume, Volatility)
- 43 technical indicators
- RuleRegistry with decorator-based signal registration
- Docstring parser for signal metadata extraction
- KB server with REST + MCP dual protocol
- SQLite FTS5 full-text search
- 11 trading education documents
- x402 payment gating
