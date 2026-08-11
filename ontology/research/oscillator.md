# Research: oscillator indicators

Literature research for the `oscillator` class, gathered by three web-research subagents on
2026-08-05, **plus verification of every claim against our own `_compute`**. Design context:
MangroveTechnologies/MangroveAI#1012. Method and rationale: see `volatility.md`.

This class mattered most because its definition -- *"bounded output where absolute thresholds are
meaningful"* -- is a claim about `range`, so until `range` was authored the class could not be
checked against declared data at all.

**Headline result: 11 of 12 members are hard-bounded; CCI is not, and is the one member whose class
membership the evidence does not support.**

---

## The bounds table -- hard vs conventional

The single most valuable distinction here. A bound that follows from the arithmetic is a fact about
the series; a "typical range" is a fact about its distribution, and consumers must not treat them
alike. Every row verified by execution over 3,000 bars.

| indicator | output | range | hard or conventional | our observed |
|---|---|---|---|---|
| RSI | `rsi` | `[0, 100]` | **hard** -- ratio non-negative | 17.3 .. 81.3 |
| StochasticOscillator | `stoch_k`, `stoch_d` | `[0, 100]` | **hard** -- close lies inside the window range | 0.1 .. 99.8 |
| StochRSI | `stochrsi`, `_k`, `_d` | `[0, 1]` | **hard** -- min-max normalisation | 0.000 .. 1.000 |
| WilliamsR | `wr` | `[-100, 0]` | **hard** -- the `x -100` is canonical | -99.9 .. -0.15 |
| CMO | `cmo` | `[-100, 100]` | **hard** -- \|Su-Sd\| <= Su+Sd | -90.2 .. 91.0 |
| TSI | `tsi` | `[-100, 100]` | **hard** -- triangle inequality through both EMAs | -56.7 .. 54.7 |
| UltimateOscillator | `ultimate_oscillator` | `[0, 100]` | **hard** -- 0 <= BP <= TR per bar | 26.6 .. 71.0 |
| BOP | `bop` | `[-1, 1]` | **hard** -- open and close inside the bar | -0.97 .. 0.99 |
| **CCI** | `cci` | **unbounded** | **CONVENTIONAL ONLY** | **-320 .. +327** |
| STC | `stc` | `[0, 100]` | **hard** -- normalise then convex-smooth | 0.000 .. 100.000 |
| MFI | `mfi` | `[0, 100]` | **hard** -- RSI form | 8.5 .. 93.3 |
| CMF | `cmf` | `[-1, 1]` | **hard**; practical range ~ +/-0.5 | -0.48 .. 0.36 |

All threshold levels in the literature -- 70/30, 80/20, +/-50, 25/75, -20/-80 -- are **conventional**,
without exception. None is a bound.

## CCI does not satisfy the class definition

StockCharts: *"Theoretically, there are no upside or downside limits."* Fidelity: an *"unbound
oscillator."* Lambert's 0.015 constant was chosen so that *"approximately 70 to 80 percent of CCI
values would fall between -100 and +100"* -- so a fifth to a quarter of readings sit outside the
familiar band **by design**. On our data 43.2% fell outside +/-100, and the observed range reached
+/-320.

The `oscillator` class is defined as bounded output where absolute thresholds are meaningful. CCI's
`range` is `[null, null]`. **This is a live question for the class axis, not a documentation
detail** -- either the definition widens, or CCI moves. Recorded rather than resolved.

## VERIFIED: our CCI is more correct than most libraries

Our `_compute` calculates a **true rolling mean absolute deviation** -- for each window, deviations
are measured against that window's *own* mean, which is exactly the published formula
`MD = (1/n) * SUM |TP_i - SMA_TP|`. The widespread library shortcut instead rolling-averages
`|tp - rolling_mean|`, using each bar's own rolling mean as its reference point.

Reconstructed both on identical data:

```
ours == literature mean-deviation form : True
ours == common library shortcut        : False
max divergence between the two forms   : 154.01 CCI points
```

A 154-point divergence on an indicator whose conventional band is +/-100. Worth stating plainly in
the node, because anyone reconciling our CCI against pandas-ta or a charting platform will see a
difference and assume we are wrong.

## VERIFIED: `%R = %K - 100` exactly

Wikipedia states Williams %R is *"arithmetically exactly equivalent to the %K stochastic oscillator,
mirrored at the 0%-line."* Confirmed against our two implementations: max difference `1.42e-14`,
i.e. floating-point noise. Both read the same measurement on different scales.

The negative sign is **canonical, not cosmetic** -- all four sources agree, and an implementation
returning `0..+100` is computing Stochastic %K under the wrong name. Ours is correctly negative.

## VERIFIED: our StochRSI is on the 0..1 scale

Genuinely contested in the literature. StockCharts (*"fluctuates between 0 and 1"*) and TradingView's
support docs say 0..1; Fidelity says 0..100; GoCharting states outright that it is
platform-dependent. TradingView is internally inconsistent -- its docs say 0..1 and its plotted
indicator renders 0..100.

Resolution: the published formula yields `[0, 1]`; the 0..100 form is that value multiplied by 100, a
display convention. **Ours is the canonical 0..1 form** (observed exactly `[0.000, 1.000]`).
Consequence worth flagging to consumers: applying the usual 20/80 thresholds to this series produces
silence -- the equivalent levels are 0.20/0.80.

Also: the `%K`/`%D` names for StochRSI are a platform convention borrowed from the Stochastic
Oscillator, absent from Chande and Kroll's original, which names only a single raw series. Where
platforms expose `%K` it is typically **already smoothed**, so raw StochRSI and `%K` are not
interchangeable. Ours emits all three, correctly distinguished.

## Our Stochastic is the FAST variant

The literature distinguishes Fast (raw %K, 3-SMA %D), Slow (%K itself smoothed) and Full
(user-specified smoothing on both). Ours computes raw `stoch_k` and takes an SMA for `stoch_d` --
that is **Fast Stochastic**. Not stated anywhere in the code or its docstring today.

## Undocumented zero-range behaviour, four indicators

Where a window's high equals its low, the denominator is zero. **No literature source states a
convention.** Verified on a flat series:

| indicator | flat-input result |
|---|---|
| StochasticOscillator | all NaN |
| WilliamsR | all NaN |
| StochRSI | all NaN |
| RSI | **100.0** (explicitly guarded: zero average loss returns 100, the correct limit) |

RSI's guard is right and deliberate. The other three fall through to NaN by accident rather than by
decision -- the same shape as the Keltner/Donchian guard inconsistency in `volatility.md`.

## Per-indicator notes

- **RSI** -- Wilder smoothing at `alpha = 1/window`, matching the original. Default 14. Bull/bear
  regimes shift the traversed range (roughly 40-90 vs 10-60), which is why fixed thresholds
  underperform across regimes.
- **CMO** -- Chande, *The New Technical Trader* (1994). Unsmoothed by design, hence more frequent
  signals than RSI. Default period **contested**: 20 (Fidelity, TradingView) vs 9 (secondary sources).
- **TSI** -- Blau, *S&C* 1991. Bound sourced from Wikipedia (*"bound between +100 and -100"*) and
  TradeStation (*"normalized to be between -100 and 100"*); **StockCharts states no bound at all**.
  Signal-line default is unsettled across sources (7, 8, 12, 13 all appear).
- **UltimateOscillator** -- Larry Williams, *S&C* V.3:4 (1985). Our `true_range` is algebraically
  identical to the article's `max(High, PriorClose) - min(Low, PriorClose)`.
- **BOP** -- Livshin, *S&C* V.19:8 (2001), where it is `BMP`. The published one-line form is an exact
  algebraic simplification of his original six-term construction. **UNCERTAIN:** Livshin writes that
  he *"deliberately developed BMP not to be a range-bound indicator"*, which contradicts the
  arithmetic; the defensible reading is *non-saturating* rather than unbounded, and his charts appear
  to be scaled by 100 though the article never says so. StockCharts misspells him "Levshin".
  Literature normally plots a 14-period SMA of BOP; **ours emits the raw, noisy series**.
- **CMF** -- ChartSchool: *"It would take 20 consecutive closes on the high (low) ... to reach +1
  (-1)."* Ours treats zero-range bars as **zero flow** (`fillna(0.0)`); the literature leaves them
  undefined. The multiplier is intrabar-only and ignores gaps, a known weakness.
- **MFI** -- Quong and Soudack, *S&C* V.7:3, "Volume-weighted RSI: money flow".
- **STC** -- Doug Schaff, 1990s; details published via Twomey, *S&C*. Our EMA smoothing with
  `span=3` is equivalent to the canonical `Factor = 0.5` recursion (`alpha = 2/(3+1) = 0.5`).
  **COVERAGE CAVEAT:** no StockCharts entry exists; Schaff's own 2002 *Chartpoint* article was not
  obtainable. Everything rests on author-adjacent secondary sources. A widely-copied secondary
  formula, `100 * (MACD - %K)/(%D - %K)`, is **garbled and not bounded** -- ignore it.

## Sources

StockCharts ChartSchool (`chartschool.stockcharts.com`) for RSI, Stochastic, StochRSI, Williams %R,
CCI, TSI, Ultimate Oscillator, MFI, CMF, BOP; Wikipedia for RSI, Stochastic, Williams %R, CCI, TSI,
Ultimate Oscillator; Fidelity for RSI, StochRSI, Williams %R, CCI, CMO; TradingView for Williams %R,
StochRSI, CMO, CMF, BOP; Tulip Indicators for CMO; TradeStation for TSI; thinkorswim for STC;
Livshin's original *S&C* PDF for BOP; Twomey's *S&C* PDF for STC.

Primary texts NOT obtained (all attributions secondhand): Lambert 1980 (CCI), Chande 1994 (CMO),
Blau 1991 (TSI), Williams 1985 (Ultimate Oscillator), Schaff 2002 (STC). Larry Williams' original
%R publication year is unresolved -- Wikipedia says 1979, secondary sources 1973.
