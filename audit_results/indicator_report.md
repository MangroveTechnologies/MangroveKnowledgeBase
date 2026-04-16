# Indicator Audit Report

**Date**: 2026-04-15
**Data**: BTC/USD Daily, 1,294 bars (2022-08-01 to 2026-02-14)
**Reference**: Bukosabino `ta` v0.11.0 (primary)
**Framework**: `scripts/audit/` -- reproducible via `python scripts/audit/run_all.py`

## Overall Status: 70/70 Indicators PASS, 136/136 Signals PASS

### Indicator Audit

| Category | Total | Pass | Fail | Audit Method |
|----------|-------|------|------|-------------|
| Momentum | 11 | 11 | 0 | Numerical comparison vs Bukosabino `ta` (0.00e+00 max error) |
| Trend | 15 | 15 | 0 | Numerical comparison vs Bukosabino `ta` (0.00e+00 max error) |
| Volatility | 5 | 5 | 0 | Numerical comparison vs Bukosabino `ta` (0.00e+00 max error) |
| Volume | 9 | 9 | 0 | Numerical comparison vs Bukosabino `ta` (0.00e+00 max error) |
| Returns | 3 | 3 | 0 | Numerical comparison vs Bukosabino `ta` (0.00e+00 max error) |
| Patterns | 27 | 27 | 0 | Synthetic candlestick tests (54/54 pass) + BTC detection rate validation |
| **Total** | **70** | **70** | **0** | |

All 43 non-pattern indicators produce **bit-identical** output (0.00e+00 error) to the Bukosabino `ta` reference. All 27 pattern indicators pass synthetic positive/negative tests and show plausible detection rates on BTC daily data.

### Signal Audit

| Test | Scope | Result |
|------|-------|--------|
| Smoke test (runs without error, returns bool) | 136/136 signals | PASS |
| TRIGGER crossover accuracy (fires at correct bars) | 10 key crossover signals | 100% match (0 false positives, 0 false negatives) |
| MACD crossover deep-dive (known suspect) | macd_bullish_cross, macd_bearish_cross | **CLEARED** -- fires correctly on all 47 crossover bars |
| FILTER code review (iloc[-1], NaN handling) | 70 FILTER signals | PASS |

### Gap Analysis

| Reference Library | Their Total | Our Coverage | Gap |
|-------------------|-----------|-------------|-----|
| Bukosabino `ta` | 43 | **100%** | 0 |
| TA-Lib | 135 | 60% | 25 Priority A, 30 Priority B, 96 Priority C |
| stock-indicators-python | 82 | 51% | (overlaps with TA-Lib gaps) |

**25 Priority A missing indicators**: DEMA, TEMA, T3, TRIMA, HMA, ALMA, SMMA, VWMA, MAMA, EPMA, SuperTrend, Chandelier Exit, Williams Alligator, Heikin-Ashi, BOP, CMO, MOM, APO, NATR, True Range, ATR Trailing Stop, STARC Bands, Volatility Stop, ADOSC, KVO

**4 high-impact missing signal patterns**: Divergence Detection, Multi-Timeframe Confirmation, Moving Average Ribbon, Volatility Squeeze/Expansion (TTM Squeeze)

## Known Issues (for _v2 reimplementation)

1. **PSAR `psar_down_indicator` copy-paste bug** (`trend_indicators.py:706`): Uses `psar_up.where(...)` instead of `psar_down.where(...)`. This bug exists in BOTH our code and the Bukosabino reference. Core PSAR outputs (psar, psar_up, psar_down) are correct; only the `psar_down_indicator` convenience output is affected.

2. **fill_value lookahead pattern** (TRIX:203, KST:326-340, DPO:378, Vortex:589): Uses `fill_value=series.mean()` in shift operations. This is non-standard (introduces lookahead bias from future data). However, the Bukosabino reference uses the identical pattern, so our implementation matches. Worth fixing in _v2 for correctness.

3. **PSAR indexing inconsistency** (`trend_indicators.py:690`): `psar[i]` vs `psar.iloc[i]` used everywhere else. Works only with default RangeIndex. Not a bug in current usage but fragile.

## Audit Completion

- [x] Phase 0: Framework setup (compare.py, config.py, report.py)
- [x] Phase 1: Returns (3/3 PASS)
- [x] Phase 2: Volatility (5/5 PASS)
- [x] Phase 3: Momentum (11/11 PASS)
- [x] Phase 4: Trend (15/15 PASS)
- [x] Phase 5: Volume (9/9 PASS)
- [x] Phase 6: Patterns (27/27 PASS -- synthetic tests)
- [x] Phase 7: Signals (136/136 PASS -- smoke + crossover + code review)
- [x] Phase 8: Gap analysis (25 Priority A gaps identified)

## Detailed Reports

- `audit_results/indicator_report.md` -- this file (consolidated)
- `audit_results/indicator_report.json` -- machine-readable indicator results
- `audit_results/signal_report.md` -- signal audit details
- `audit_results/pattern_report.md` -- pattern indicator details + BTC detection rates
- `audit_results/gap_analysis.md` -- full gap analysis with prioritized missing indicators

## Next Steps (Not In Scope for This Audit)

- [ ] Implement Priority A missing indicators (25) as new classes
- [ ] Implement missing signal patterns (divergence, multi-TF, MA ribbon, squeeze)
- [ ] Fix known issues as _v2 implementations (PSAR bug, fill_value pattern, indexing)
- [ ] Re-audit PiercingLine/DarkCloudCover thresholds for crypto (gap requirement unrealistic for 24/7 markets)

---

## Detailed Results (43 Audited Indicators)

## Detailed Results

### Momentum

**AwesomeOscillator** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `ao`: max_err=0.00e+00, overlap=1261

**KAMA** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `kama`: max_err=0.00e+00, overlap=1285

**PPO** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `ppo`: max_err=0.00e+00, overlap=1269
- `ppo_signal`: max_err=0.00e+00, overlap=1261
- `ppo_hist`: max_err=0.00e+00, overlap=1261

**PVO** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `pvo`: max_err=0.00e+00, overlap=1269
- `pvo_signal`: max_err=0.00e+00, overlap=1261
- `pvo_hist`: max_err=0.00e+00, overlap=1261

**ROC** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `roc`: max_err=0.00e+00, overlap=1282

**RSI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `rsi`: max_err=0.00e+00, overlap=1281

**StochRSI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `stochrsi`: max_err=0.00e+00, overlap=1268
- `stochrsi_k`: max_err=0.00e+00, overlap=1266
- `stochrsi_d`: max_err=0.00e+00, overlap=1264

**StochasticOscillator** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `stoch_k`: max_err=0.00e+00, overlap=1281
- `stoch_d`: max_err=0.00e+00, overlap=1279

**TSI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `tsi`: max_err=0.00e+00, overlap=1257

**UltimateOscillator** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `ultimate_oscillator`: max_err=0.00e+00, overlap=1266

**WilliamsR** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `wr`: max_err=0.00e+00, overlap=1281

### Others

**CumulativeReturn** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `cumulative_return`: max_err=0.00e+00, overlap=1294

**DailyLogReturn** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `daily_log_return`: max_err=0.00e+00, overlap=1293

**DailyReturn** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `daily_return`: max_err=0.00e+00, overlap=1293

### Trend

**ADX** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `adx`: max_err=0.00e+00, overlap=1294
- `adx_pos`: max_err=0.00e+00, overlap=1294
- `adx_neg`: max_err=0.00e+00, overlap=1294
- Notes: Highest complexity indicator -- Wilder smoothing with manual loops

**Aroon** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `aroon_up`: max_err=0.00e+00, overlap=1269
- `aroon_down`: max_err=0.00e+00, overlap=1269
- `aroon_indicator`: max_err=0.00e+00, overlap=1269

**CCI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `cci`: max_err=0.00e+00, overlap=1275

**DPO** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `dpo`: max_err=0.00e+00, overlap=1275
- Notes: Suspected fill_value divergence -- both use fill_value=close.mean()

**EMA** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `ema`: max_err=0.00e+00, overlap=1275

**Ichimoku** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `conversion_line`: max_err=0.00e+00, overlap=1286
- `base_line`: max_err=0.00e+00, overlap=1269
- `span_a`: max_err=0.00e+00, overlap=1269
- `span_b`: max_err=0.00e+00, overlap=1243
- Notes: Ichimoku span_b: ref uses min_periods=0 vs ours uses min_periods=window3

**KST** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `kst`: max_err=0.00e+00, overlap=1280
- `kst_signal`: max_err=0.00e+00, overlap=1272
- `kst_diff`: max_err=0.00e+00, overlap=1272
- Notes: Suspected fill_value divergence; ref uses min_periods=0 for kst_sig rolling

**MACD** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `macd`: max_err=0.00e+00, overlap=1269
- `signal`: max_err=0.00e+00, overlap=1261
- `histogram`: max_err=0.00e+00, overlap=1261

**MassIndex** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `mass_index`: max_err=0.00e+00, overlap=1254

**PSAR** -- PASS
- Reference: Bukosabino ta, Tolerance: RELAXED
- `psar`: max_err=0.00e+00, overlap=1294
- `psar_up`: max_err=0.00e+00, overlap=663
- `psar_down`: max_err=0.00e+00, overlap=629
- Notes: Suspected copy-paste bug on psar_down_indicator (uses psar_up in where clause); comparing psar/psar_up/psar_down only

**SMA** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `sma`: max_err=0.00e+00, overlap=1275

**STC** -- PASS
- Reference: Bukosabino ta, Tolerance: RELAXED
- `stc`: max_err=0.00e+00, overlap=1223
- Notes: State machine -- RELAXED tolerance tier

**TRIX** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `trix`: max_err=0.00e+00, overlap=1251
- Notes: Suspected fill_value divergence in shift -- both use fill_value=ema3.mean()

**Vortex** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `vortex_pos`: max_err=0.00e+00, overlap=1280
- `vortex_neg`: max_err=0.00e+00, overlap=1280
- `vortex_diff`: max_err=0.00e+00, overlap=1280
- Notes: Suspected fill_value divergence in close_shift

**WMA** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `wma`: max_err=0.00e+00, overlap=1286

### Volatility

**ATR** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `atr`: max_err=0.00e+00, overlap=1294

**BollingerBands** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `mavg`: max_err=0.00e+00, overlap=1275
- `hband`: max_err=0.00e+00, overlap=1275
- `lband`: max_err=0.00e+00, overlap=1275

**DonchianChannel** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `dc_hband`: max_err=0.00e+00, overlap=1275
- `dc_lband`: max_err=0.00e+00, overlap=1275
- `dc_mband`: max_err=0.00e+00, overlap=1275

**KeltnerChannel** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `kc_hband`: max_err=0.00e+00, overlap=1275
- `kc_lband`: max_err=0.00e+00, overlap=1275
- `kc_mband`: max_err=0.00e+00, overlap=1275
- Notes: original_version=True

**UlcerIndex** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `ulcer_index`: max_err=0.00e+00, overlap=1281

### Volume

**ADI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `adi`: max_err=0.00e+00, overlap=1294

**CMF** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `cmf`: max_err=0.00e+00, overlap=1275

**EaseOfMovement** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `eom`: max_err=0.00e+00, overlap=1293
- `sma_eom`: max_err=0.00e+00, overlap=1280

**ForceIndex** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `fi`: max_err=0.00e+00, overlap=1281

**MFI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `mfi`: max_err=0.00e+00, overlap=1281

**NVI** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `nvi`: max_err=0.00e+00, overlap=1294
- Notes: comparing nvi only (ref has no nvi_ema output)

**OBV** -- PASS
- Reference: Bukosabino ta, Tolerance: EXACT
- `obv`: max_err=0.00e+00, overlap=1294

**VPT** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `vpt`: max_err=0.00e+00, overlap=1293

**VWAP** -- PASS
- Reference: Bukosabino ta, Tolerance: FLOAT
- `vwap`: max_err=0.00e+00, overlap=1281
