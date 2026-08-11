# Research: momentum indicators

Literature research for the `momentum` class, gathered by five web-research subagents on 2026-08-05,
**plus verification of every claim against our own `_compute`**. Design context:
MangroveTechnologies/MangroveAI#1012. Method and rationale: see `volatility.md`.

Largest class in the corpus: 21 indicators, 37 outputs. This class is where the ontology's `momentum`
definition does the most work, because it absorbed the directional-strength indicators (ADX, Aroon,
Vortex, MultiTFTrend) that a use-case taxonomy would have filed under "trend".

---

## The bounds picture -- not uniform, and that is the point

| indicator | output | range | hard or conventional |
|---|---|---|---|
| ADX | `adx`, `adx_pos`, `adx_neg` | `[0, 100]` | **hard** -- `+DM <= TR` per bar, so each DI ratio cannot exceed 1 |
| Aroon | `aroon_up`, `aroon_down` | `[0, 100]` | **hard** -- rescaling of a counter confined to `[0, window]` |
| Aroon | `aroon_indicator` | `[-100, 100]` | **hard** -- difference of two `[0,100]` series |
| ROC, DailyReturn | -- | `[-100, inf)` | **hard** -- price cannot fall below zero |
| PVO | `pvo`, `pvo_signal` | `[-100, inf)` | **hard** -- volumes are non-negative |
| Vortex | `+VI`, `-VI` | `[0, inf)` | **hard floor, NO ceiling** -- see below |
| MassIndex | `mass_index` | `(0, inf)` | **hard** -- sum of positive ratios |
| MultiTFTrend | `higher_tf_trend` | `[-1, 1]` | **hard** -- ternary by construction |
| MACD, APO, AO, MOM, DPO | -- | unbounded | **hard**, and in PRICE UNITS |
| PPO, TRIX, KST | -- | unbounded | **hard**, but percent-normalised |
| ForceIndex, EOM, ADOSC, KVO | -- | unbounded | **hard**, volume-scaled, arbitrary level |

**Vortex is the one most likely to be got wrong.** `+VI` and `-VI` look like they belong in `[0, 2]`
because they "oscillate around 1", and the 0.90 / 1.10 signal levels reinforce that. They do not: the
numerator `|high - prior low|` spans *across* bars while the denominator (true range) is a
within-bar measure, so a gap drives the ratio past 1 without limit. Those threshold levels are
explicitly presented as *adjustable*, which is only coherent if the values move freely past them.

**DailyReturn vs DailyLogReturn is a real structural difference**, not a cosmetic one. The simple
return's hard `-100` floor is mapped by `ln(1+R)` to `-infinity`, so the log return is unbounded in
**both** directions. That is exactly why log returns are the modelling default -- along with
time-additivity and symmetry -- and it is why these two near-identical-looking indicators carry
different `range` values.

## Verified exact matches

- **`MACD`** = fast EMA - slow EMA, signal = EMA(macd, 9), histogram = macd - signal. Canonical
  output names confirmed: **MACD Line**, **Signal Line**, **MACD Histogram**.
- **`PPO`** divides by the **slow** EMA -- confirmed verbatim against ChartSchool.
- **`TRIX`** is the 1-period percent change **of** the triple-smoothed EMA, in that order. Verified
  against a hand-reconstructed chain.
- **`KST`** matches Pring's construction: ROC periods 10/15/20/30, smoothing 10/10/10/15, weights
  1/2/3/4, signal a 9-period **SMA** (not EMA). Ours computes ROC as a fraction and scales the
  weighted sum by 100 -- algebraically identical to the percent form.
- **`Aroon`** = `((N - days_since) / N) * 100`, verified numerically against a hand implementation.
- **`AwesomeOscillator`** uses **median price** `(H+L)/2`, not close, with 5/34 SMAs.
- **`MassIndex`** matches the canonical four-step construction; 27 / 26.5 are conventional signal
  levels, and ~25 is the neutral resting value because each of the 25 ratios sits near 1.
- **`ADOSC`** = EMA(ADL, 3) - EMA(ADL, 10), matching both ChartSchool and TA-Lib's defaults.
- **`EaseOfMovement`** smoothing is an **SMA**, which is correct -- and easy to "fix" wrongly, since
  every neighbouring indicator here smooths with an EMA. Our scaling also checks out algebraically:
  `(H.diff + L.diff) * (H-L) / (2*vol)` is the canonical midpoint-move form with the `/2` folded in.

## `DPO` -- two standard alignments, and ours is the causal one

The most consequential finding for consumers. Both of these are "the standard DPO":

1. **Centred** (what charting platforms plot): value at bar `t` is `Close[t] - SMA(t + n/2 + 1)`.
   This reaches `n/2 + 1` bars into the **future**, which is why the plotted DPO does not extend to
   the last date.
2. **Causal** (the "shift right" variant): value at `t` is `Close[t - (n/2+1)] - SMA(t)`. Computable
   now, but describes a state `n/2 + 1` bars stale.

**VERIFIED: ours is alignment 2** -- `close.shift(11) - SMA(20)` at the default, past data only, so
it is lookahead-free. Confirmed it matches the formula exactly and that the first valid index is 19.

But note what the sources say about *using* it, in StockCharts' own words: DPO *"is not designed for
momentum signals"*, is *"not well suited for scans"*, and the PPO *"is better suited to identify
overbought and oversold levels"*. Shifting it to be current *"really defeats the purpose of this
indicator, which is to identify cycles."* **Any signal built on DPO is using it against every
primary source.** That belongs in the node description, not in a code change.

## The "Momentum" name collision

Three different quantities travel under the name, with **different centrelines**:

| form | definition | centre |
|---|---|---|
| difference (**ours**) | `close - close[n]` | 0 |
| percent (this corpus's `ROC`) | `(close - close[n]) / close[n] * 100` | 0 |
| ratio (MetaTrader) | `close / close[n] * 100` | **100** |

StockCharts and Fidelity both write that ROC *"is also referred to as Momentum"*, and **StockCharts
has no separate Momentum page at all** -- the collision is structural, not incidental. Our `MOM` is
the difference form; the node says so.

## Defects filed (KB#104 findings 18-21)

1. **`ADX` zero-filled warmup** -- 27 bars of literal `0.0` with no NaN, and 0 is a meaningful ADX
   reading, so warmup is indistinguishable from a flat market. `DX` is also zeroed where undefined.
2. **`TRIX` emits no signal line** -- the series its primary documented signal is built on.
3. **`APO` is byte-identical to the MACD line** (max diff `0.00e+00`). Expected per the literature,
   but the corpus presents them as two independent measurements.
4. **`KVO` is the simplified variant, ~145x off Klinger's original scale.** Measured on identical
   data: ours `[-39,493, 32,593]` against the full form's `[-4,970,310, 5,746,198]`.

## Coverage and source caveats

- **KVO is the weakest-sourced indicator in the class.** StockCharts has no Klinger page; Klinger's
  1997 *S&C* original is behind a Cloudflare challenge and could not be read. Everything rests on
  secondary platform docs (SierraChart, TradingView, CQG, MotiveWave), which is also how the two
  incompatible variants came to circulate under one name.
- **APO** has no StockCharts page either, which is why it is the one indicator in the MACD family
  where sources conflict -- on MA type (EMA-only vs any) and on defaults (12/26 vs 11/21 vs 10/30).
- **`DailyReturn` and `DailyLogReturn` are not named technical indicators.** No ChartSchool entry
  exists for either; they are elementary finance quantities. They sit in `momentum` today.
- **`MultiTFTrend` does not exist in the literature at all** -- it is authored for this corpus. It
  emits a ternary regime flag rather than a measurement, needs a `DatetimeIndex` (returning all-NaN
  without one), and broadcasts by forward-fill so it stays lookahead-free.
- **A negative finding worth recording:** the agent researching the volume-scaled indicators could
  **not** find any source stating that ForceIndex / ADOSC / KVO levels are non-comparable across
  instruments, and checked directly rather than inferring from absence. Only **EaseOfMovement** has a
  citable statement, via its divisor being an explicit per-instrument tuning knob (sources use 1e6,
  1e8 and 1e9 for it). Non-comparability is defensible for all four as a consequence of the units,
  but only EOM can be presented as a sourced claim. The same agent also caught and discarded a
  fabricated quote a summarizer had attributed to the Force Index page.

## Sources

StockCharts ChartSchool for MACD, MACD-Histogram, PPO, TRIX, ROC, DPO, KST, ADX, Aroon, Aroon
Oscillator, Vortex, Mass Index, PVO, Force Index, Ease of Movement, Chaikin Oscillator, ADL, OBV;
Wikipedia for TRIX, Momentum, ADX, Vortex, rate of return; Fidelity for ROC, ADX, APO; TradingView
for TRIX, DPO, KST, Aroon, Vortex, EFI, EOM, Klinger; primary *S&C* citations for Hutson (TRIX,
1983), Pring (KST, V.10:9 1992), Dorsey (Mass Index, V.10:6 1992), Botes & Siepman (Vortex, V.28:1
2010); Wilder 1978 for ADX; Chande 1995 for Aroon; Elder *Trading for a Living* for Force Index;
SierraChart, CQG, MotiveWave, TC2000, QuantShare for KVO; TA-Lib docs for ADOSC; Tsay and Campbell,
Lo & MacKinlay for the return definitions.

Not obtained: Klinger's 1997 original (403), Botes/Siepman full text (403), Investopedia (blocked
throughout).
