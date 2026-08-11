# Research: flow indicators

Literature research for the `flow` class, gathered by two web-research subagents on 2026-08-06,
**plus verification of every claim against our own `_compute`**. Design context:
MangroveTechnologies/MangroveAI#1012. Method and rationale: see `volatility.md`.

Smallest class: 5 indicators, 6 outputs. Also the most internally uniform -- every member is a
running cumulative total, which makes the class definition ("running accumulation whose level is
arbitrary but whose direction carries meaning") almost a description of the arithmetic.

---

## The class property, and how unevenly it is sourced

All five carry a level that is an artefact of where the data begins. Only shape and direction are
meaningful, and **the zero crossing is not a signal**. But the sourcing is not uniform, and it is
worth being honest about that rather than asserting it across the board:

| indicator | is the "level is meaningless" claim sourced? |
|---|---|
| `OBV` | **Yes, by StockCharts** (primary): *"The absolute value of OBV is not important."* Also *"The scale of OBV is not relevant, and is not even shown on SharpCharts."* Wikipedia adds the start-date dependence explicitly. |
| `VPT` | **Wikipedia only** -- *"the zero point is arbitrary. Only the shape of the resulting indicator is used, not the actual level of the total."* **There is no ChartSchool page for VPT at all.** |
| `ADI` | **Wikipedia only.** StockCharts' ADL page contains no such sentence and no start-date caveat -- checked directly, not inferred from a keyword search. |
| `NVI` | Meaningless for a different reason: the level is set by an arbitrary seed. TradingView states the seed *"defines the scale of the NVI, but it does not affect the indicator's behavior."* |
| `CumulativeReturn` | Rebased by the caller's slice -- it divides by `close[0]` of whatever series is passed. |

## What actually separates OBV, ADI and VPT

They are the same construction -- a running sum of volume -- differing only in the weight applied
per bar. That one difference produces sharply different behaviour:

| | weight on Volume[t] | prior close? | intrabar H/L? | weight bounded? |
|---|---|---|---|---|
| `OBV` | `sign(close - prior close)` in {-1, 0, +1} | yes | no | yes |
| `ADI` | `((C-L)-(H-C))/(H-L)` | **no** | yes | **yes, hard [-1, +1]** |
| `VPT` | `(close - prior close) / prior close` | yes | no | **no** |

- **ADI's weight is hard-bounded**, verified from the definitions: since `L <= C <= H`, both `(C-L)`
  and `(H-C)` are non-negative and sum to exactly `(H-L)`, so the ratio cannot leave `[-1, +1]`.
  StockCharts states it too: *"The Money Flow Multiplier fluctuates between +1 and -1."* Consequence:
  **a bar can never move ADI further than its own volume.**
- **VPT has no such cap.** A bar that doubles in price contributes twice its volume.
- **ADI never looks at the prior close.** This is the sharpest behavioural difference in the class,
  and StockCharts gives the consequence directly: a security can *"gap down and close significantly
  lower, but the Accumulation Distribution Line would rise if the close were above the midpoint of
  the high-low range."* Neither OBV nor VPT can do that. Anyone "fixing" ADI to consider the prior
  close would be reimplementing OBV.

## VERIFIED defect: `OBV` mishandles unchanged closes

Granville's rule is **three-way**. StockCharts, verbatim: *"If the closing prices equals the prior
close price then: Current OBV = Previous OBV (no change)."*

Ours branches two ways -- `np.where(close < close.shift(1), -volume, volume)` -- so a flat close
lands in the `+volume` branch:

```
close : [100, 100, 100, 101, 100, 100]
ours  : [1000, 2000, 3000, 4000, 3000, 4000]
canon : [   0,    0,    0, 1000,    0,    0]
```

The error accumulates monotonically. Since OBV is read by its *direction*, a spurious upward drift is
precisely the failure mode that matters, and it bites hardest exactly where OBV is already weakest --
illiquid instruments, coarse tick sizes, resampled series. Filed as KB#104 finding 22.

## VERIFIED defect: `VPT`'s `dropnans` changes the series length

`dropnans=True` returns 45 rows from a 50-bar input, starting at index 5. Every other indicator in the
corpus returns a full-length series aligned to the input index, and `IndicatorInterface.compute_frame`
explicitly promises that outputs *"outer-join cleanly into a feature matrix"* because they share the
input index. KB#104 finding 23.

## `NVI` -- four genuine source disagreements, and where ours lands

The best-documented indicator in the class, and also the one with the most cross-source conflict:

1. **Additive vs multiplicative recursion.** StockCharts' prose says *"Add the Percentage Price
   Change"* but it never shows an equation. Incredible Charts and cTrader both write the
   **multiplicative** form explicitly: `NVI += ((P - P_prev)/P_prev) * NVI_prev`.
   **VERIFIED: ours compounds** (`cumprod` of `1 + pct_change` on volume-decrease bars), matching the
   two sources that commit to notation.
2. **Seed.** 1000 is dominant (StockCharts, daytrading.com, CFI), but TradingView lists 1000/100/1
   and cTrader defaults to 1. **VERIFIED: ours seeds at 1000.** All sources agree the seed is a pure
   scale choice with no behavioural effect.
3. **Signal period.** 255 is the strong majority (StockCharts, Incredible Charts, Fidelity); CFI says
   250. Ours takes it as a parameter and applies an EMA.
4. **Fosback's probabilities.** 96% bull / 53% bear is the dominant figure (StockCharts, Fidelity,
   daytrading.com); Incredible Charts reports 95% / 50%. The primary text of *Stock Market Logic*
   could not be reached to adjudicate.

The asymmetry in those probabilities is the interesting part: the bullish reading is strong and the
bearish one is barely better than a coin flip, so the indicator is far more informative above its
average than below it.

Attribution confirmed: **Paul Dysart** invented it in the 1930s using Net Advances; **Norman Fosback**
substituted the percentage price change and published the statistics in *Stock Market Logic* (1976).
The signal line is effectively inseparable -- StockCharts lists it as step 4 of the *calculation*, and
Fosback's statistics are defined against it -- but it is not part of the cumulative recursion.

Also noted: our `nvi_ema` carries **no minimum-periods guard**, so its earliest values are dominated
by the seed rather than by data. Not filed, but recorded in the node.

## `CumulativeReturn` is not a technical indicator

Verified by a full grep of the ChartSchool sitemap (368 lines): **no page exists** for cumulative
return, total return, or any return metric. It is an elementary finance quantity, sourced here from
standard finance references. Near-synonyms: total return, holding-period return, compounded return.

Bounds are a **hard `[-100, inf)`**: prices cannot go below zero, and once any `(1 + r)` factor
reaches 0 the product is absorbed there permanently. Ours divides by `close.iloc[0]`, so the entire
series is **rebased by the caller's data slice** -- worth stating in the node, because it is the one
indicator in the corpus whose values change when you change nothing but the start of the window.

Note the contrast with the log-return form: `exp(sum of log returns) - 1` maps an unbounded log-space
sum back into this floored range, which is the standard reason aggregation is done in log space and
exponentiated at the end.

## Sources

StockCharts ChartSchool for OBV, ADL, NVI (and verified ABSENCE of pages for VPT, PVI, and any return
metric); Wikipedia for OBV, accumulation/distribution index, volume-price trend; TradingView for PVT,
NVI, PVI; thinkorswim and Barchart for PVT; cTrader for PVT and NVI; Fidelity, Incredible Charts,
fmlabs, CFI and daytrading.com for NVI; Gundersen and Portfolio Metrics for the return definitions.

Not obtained: Fosback's *Stock Market Logic* primary text (probabilities are all secondary);
Granville's original.
