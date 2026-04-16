# Pattern Indicator Audit Report

**Date**: 2026-04-15 22:38
**Data**: BTC/USD Daily, 1294 bars
**Method**: Synthetic OHLC validation + BTC detection-rate plausibility

## Summary: 27/27 PASS, 0 FAIL

| Category | Patterns | Pass | Fail |
|----------|----------|------|------|
| Single-Candle | 10 | 10 | 0 |
| Two-Candle | 6 | 6 | 0 |
| Three-Candle | 6 | 6 | 0 |
| Multi-Bar | 5 | 5 | 0 |

## Detailed Results

| Pattern | Pos | Neg | BTC Detections | Rate | Status | Notes |
|---------|-----|-----|----------------|------|--------|-------|
| Doji | PASS | PASS | 154/1294 | 11.90% | PASS |  |
| LongLeggedDoji | PASS | PASS | 88/1294 | 6.80% | PASS |  |
| DragonflyDoji | PASS | PASS | 6/1294 | 0.46% | PASS |  |
| GravestoneDoji | PASS | PASS | 1/1294 | 0.08% | PASS |  |
| Hammer | PASS | PASS | 26/1294 | 2.01% | PASS |  |
| HangingMan | PASS | PASS | 26/1294 | 2.01% | PASS |  |
| InvertedHammer | PASS | PASS | 2/1294 | 0.15% | PASS |  |
| ShootingStar | PASS | PASS | 2/1294 | 0.15% | PASS |  |
| Marubozu | PASS | PASS | 11/1294 | 0.85% | PASS |  |
| SpinningTop | PASS | PASS | 331/1294 | 25.58% | PASS |  |
| Engulfing | PASS | PASS | 93/1294 | 7.19% | PASS |  |
| Harami | PASS | PASS | 99/1294 | 7.65% | PASS |  |
| PiercingLine | PASS | PASS | 0/1294 | 0.00% | PASS |  |
| DarkCloudCover | PASS | PASS | 0/1294 | 0.00% | PASS |  |
| TweezerTops | PASS | PASS | 10/1294 | 0.77% | PASS |  |
| TweezerBottoms | PASS | PASS | 11/1294 | 0.85% | PASS |  |
| MorningStar | PASS | PASS | 85/1294 | 6.57% | PASS |  |
| EveningStar | PASS | PASS | 69/1294 | 5.33% | PASS |  |
| ThreeWhiteSoldiers | PASS | PASS | 6/1294 | 0.46% | PASS |  |
| ThreeBlackCrows | PASS | PASS | 3/1294 | 0.23% | PASS |  |
| ThreeInsideUp | PASS | PASS | 11/1294 | 0.85% | PASS |  |
| ThreeInsideDown | PASS | PASS | 17/1294 | 1.31% | PASS |  |
| InsideBar | PASS | PASS | 281/1294 | 21.72% | PASS |  |
| OutsideBar | PASS | PASS | 154/1294 | 11.90% | PASS |  |
| PinBar | PASS | PASS | 113/1294 | 8.73% | PASS |  |
| TwoBarReversal | PASS | PASS | 45/1294 | 3.48% | PASS |  |
| NarrowRange | PASS | PASS | 189/1294 | 14.61% | PASS |  |

## BTC Detection Rate Analysis

Expected ranges based on pattern frequency in typical markets:

### Single-Candle

- **Doji**: 154 detections (11.90%) -- expected [2.0%, 30.0%] -- OK
- **LongLeggedDoji**: 88 detections (6.80%) -- expected [1.0%, 15.0%] -- OK
- **DragonflyDoji**: 6 detections (0.46%) -- expected [0.0%, 15.0%] -- OK
- **GravestoneDoji**: 1 detections (0.08%) -- expected [0.0%, 15.0%] -- OK
- **Hammer**: 26 detections (2.01%) -- expected [1.0%, 15.0%] -- OK
- **HangingMan**: 26 detections (2.01%) -- expected [1.0%, 15.0%] -- OK
- **InvertedHammer**: 2 detections (0.15%) -- expected [0.0%, 10.0%] -- OK
- **ShootingStar**: 2 detections (0.15%) -- expected [0.0%, 10.0%] -- OK
- **Marubozu**: 11 detections (0.85%) -- expected [0.1%, 15.0%] -- OK
- **SpinningTop**: 331 detections (25.58%) -- expected [1.0%, 35.0%] -- OK

### Two-Candle

- **Engulfing**: 93 detections (7.19%) -- expected [1.0%, 15.0%] -- OK
- **Harami**: 99 detections (7.65%) -- expected [1.0%, 15.0%] -- OK
- **PiercingLine**: 0 detections (0.00%) -- expected [0.0%, 5.0%] -- OK
- **DarkCloudCover**: 0 detections (0.00%) -- expected [0.0%, 5.0%] -- OK
- **TweezerTops**: 10 detections (0.77%) -- expected [0.0%, 15.0%] -- OK
- **TweezerBottoms**: 11 detections (0.85%) -- expected [0.0%, 15.0%] -- OK

### Three-Candle

- **MorningStar**: 85 detections (6.57%) -- expected [0.1%, 10.0%] -- OK
- **EveningStar**: 69 detections (5.33%) -- expected [0.1%, 10.0%] -- OK
- **ThreeWhiteSoldiers**: 6 detections (0.46%) -- expected [0.0%, 5.0%] -- OK
- **ThreeBlackCrows**: 3 detections (0.23%) -- expected [0.0%, 5.0%] -- OK
- **ThreeInsideUp**: 11 detections (0.85%) -- expected [0.1%, 10.0%] -- OK
- **ThreeInsideDown**: 17 detections (1.31%) -- expected [0.1%, 10.0%] -- OK

### Multi-Bar

- **InsideBar**: 281 detections (21.72%) -- expected [5.0%, 30.0%] -- OK
- **OutsideBar**: 154 detections (11.90%) -- expected [2.0%, 20.0%] -- OK
- **PinBar**: 113 detections (8.73%) -- expected [1.0%, 20.0%] -- OK
- **TwoBarReversal**: 45 detections (3.48%) -- expected [0.1%, 10.0%] -- OK
- **NarrowRange**: 189 detections (14.61%) -- expected [1.0%, 20.0%] -- OK
