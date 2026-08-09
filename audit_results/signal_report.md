# Signal Audit Report

**Date**: 2026-08-09 13:23
**Data**: BTC/USD Daily, 1294 bars (2022-08-01 to 2026-02-14)

## 1. Smoke Test Summary

**247/247** signals run without error and return bool.

| Metric | Count |
|--------|-------|
| Total signals tested | 247 |
| Passed (no error + returns bool) | 247 |
| Errored (raised exception) | 0 |
| Bad return type (not bool) | 0 |

### Signal Classification

| Type | Count |
|------|-------|
| FILTER | 130 |
| TRIGGER | 117 |
| UNKNOWN | 0 |

### No signals crashed.

### All signals return bool.

## 2. TRIGGER Signal Crossover Accuracy

Ground truth computed from full-dataset indicator values. Signals tested
with sliding window from bar 50 onward.

| Signal | Bars | GT+ | Sig+ | TP | FP | FN | Precision | Recall | Accuracy | Match |
|--------|------|-----|------|----|----|----|-----------|--------|----------|-------|
| `rsi_cross_up` | 1244 | 59 | 59 | 59 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `rsi_cross_down` | 1244 | 59 | 59 | 59 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `sma_crossover (bullish)` | 1244 | 32 | 32 | 32 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `sma_cross_up` | 1244 | 32 | 32 | 32 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `sma_cross_down` | 1244 | 33 | 33 | 33 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `ema_crossover (bullish)` | 1244 | 28 | 28 | 28 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `ema_cross_up` | 1244 | 28 | 28 | 28 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `ema_cross_down` | 1244 | 28 | 28 | 28 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `macd_bullish_cross` | 1244 | 47 | 47 | 47 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |
| `macd_bearish_cross` | 1244 | 47 | 47 | 47 | 0 | 0 | 1.000 | 1.000 | 1.0000 | **PASS** |

### All crossover signals match ground truth perfectly.

## 3. MACD Crossover Deep-Dive

### macd_bullish_cross

- Bars tested: 1244
- Ground-truth crossovers: 47
- Signal fired: 47
- True positives: 47
- False positives: 0
- False negatives: 0
- **Verdict: PASS** -- signal fires at exactly the right bars.

### macd_bearish_cross

- Bars tested: 1244
- Ground-truth crossovers: 47
- Signal fired: 47
- True positives: 47
- False positives: 0
- False negatives: 0
- **Verdict: PASS** -- signal fires at exactly the right bars.

## 4. FILTER Signal Code Review

**109/130** FILTER signals pass code review.

Checks for standard FILTER signals: uses `iloc[-1]`, handles NaN, has early return for insufficient data.

- Standard indicator FILTERs: 101/122 pass
- Pattern scan FILTERs: 8/8 pass

Pattern scan FILTERs (e.g. `bullish_pattern_recent`) check for any pattern within a recent
window of bars using `.iloc[-window:]` and `.any()`. They are architecturally different from
standard indicator FILTERs that read `iloc[-1]` and compare against a threshold.

### FILTER Signals With Issues

| Signal | Type | Issues |
|--------|------|--------|
| `etf_inflow_streak` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `exchange_net_outflow` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `funding_negative_regime` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `holder_concentration_falling` | Standard | No NaN handling detected |
| `holder_concentration_low` | Standard | No NaN handling detected |
| `is_above_dema` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected; No early return False for insufficient data |
| `is_above_epma` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected; No early return False for insufficient data |
| `is_above_hma` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected; No early return False for insufficient data |
| `is_above_mama` | Standard | No NaN handling detected |
| `is_above_smma` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected; No early return False for insufficient data |
| `is_above_tema` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected; No early return False for insufficient data |
| `is_above_trima` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected; No early return False for insufficient data |
| `lending_spread_low` | Standard | No NaN handling detected |
| `ma_ribbon_bearish` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `ma_ribbon_bullish` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `ma_ribbon_tangled` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `smart_money_holdings_rising` | Standard | No NaN handling detected |
| `smart_money_net_positive` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |
| `token_unlock_pressure_low` | Standard | No NaN handling detected |
| `treasury_growing` | Standard | No NaN handling detected |
| `whale_net_accumulation` | Standard | Does not use iloc[-1] -- may not read last bar; No NaN handling detected |

## 5. Conclusion

- **Smoke test**: 247/247 signals pass (no crashes, return bool)
- **Crossover accuracy**: 10/10 tested signals match ground truth
- **FILTER code review**: 109/130 pass static checks
