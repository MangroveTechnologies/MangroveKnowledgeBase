# Signal Audit Report

**Date**: 2026-04-15 22:37
**Data**: BTC/USD Daily, 1294 bars (2022-08-01 to 2026-02-14)

## 1. Smoke Test Summary

**136/136** signals run without error and return bool.

| Metric | Count |
|--------|-------|
| Total signals tested | 136 |
| Passed (no error + returns bool) | 136 |
| Errored (raised exception) | 0 |
| Bad return type (not bool) | 0 |

### Signal Classification

| Type | Count |
|------|-------|
| FILTER | 70 |
| TRIGGER | 66 |
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

**70/70** FILTER signals pass code review.

Checks for standard FILTER signals: uses `iloc[-1]`, handles NaN, has early return for insufficient data.

- Standard indicator FILTERs: 62/62 pass
- Pattern scan FILTERs: 8/8 pass

Pattern scan FILTERs (e.g. `bullish_pattern_recent`) check for any pattern within a recent
window of bars using `.iloc[-window:]` and `.any()`. They are architecturally different from
standard indicator FILTERs that read `iloc[-1]` and compare against a threshold.

### All FILTER signals pass code review.

## 5. Conclusion

- **Smoke test**: 136/136 signals pass (no crashes, return bool)
- **Crossover accuracy**: 10/10 tested signals match ground truth
- **FILTER code review**: 70/70 pass static checks
