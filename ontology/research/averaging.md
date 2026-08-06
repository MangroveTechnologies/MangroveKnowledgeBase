# Research: averaging indicators

Literature research for the `averaging` class, gathered by four web-research subagents on 2026-08-05,
**plus verification of every claim against our own `_compute`**. Design context:
MangroveTechnologies/MangroveAI#1012. Method and rationale: see `volatility.md`.

Unusually good source coverage for this class: primary author documents were obtained for T3
(Tillson), MAMA (Ehlers) and HMA (Hull's own MetaStock listing). ALMA is the weak spot -- no primary
publication exists that could be located.

---

## The overshoot split -- the finding that matters most for consumers

Four of these can print **outside the price range they are averaging**, which is not what a reader
expects from something called an average. Measured over a step-change series, counting bars printing
outside the trailing window's own high-low range:

| convex combination (cannot overshoot) | negative coefficients (can) |
|---|---|
| `SMA` 0, `WMA` 0, `TRIMA` 0, `ALMA` 0, `VWMA`, `KAMA`, `MAMA`, `FAMA` | `DEMA` 53, `TEMA` 57, `T3` 50, `HMA` 14 |

Largest excursion measured: `HMA` at 7.64 price units. The mechanism is documented -- the Chart manual
on HMA: *"The average is weighted towards recent prices, and in fact has negative weights for prices
past about N/2 days ago. Those negatives can make the average overshoot actual price action after a
big jump (the same as other lag-reduced averages do)."*

**Two premises of mine were wrong and the research corrected them:**

1. **ALMA cannot overshoot.** Its Gaussian weights are all strictly positive and normalised, so it is
   a convex combination. Measured 0 excursions. I had assumed the weighting scheme allowed it.
2. **Tillson claims T3 does not overshoot** -- it is his stated achievement over DEMA-cubed: *"we cure
   the multiple DEMA overshoot problem... a new, smoother moving average T3 that does not overshoot
   the data."* Our measurement found 50 bars outside the trailing window's range at his default
   v=0.7. These are **not the same test** -- his figures compare ringing against the underlying data,
   ours against a rolling window. **RESOLVED by running his own test** -- ringing past the data after
   a clean step:

   ```
   DEMA                       overshoot past the new level:  +3.667
   DEMA^3 (his target)        overshoot past the new level: +10.824
   T3 at his default v=0.7    overshoot past the new level:  +4.285
   ```

   His **comparative** claim holds: T3 cuts DEMA-cubed's ringing by ~60%, precisely the problem he set
   out to cure. His **absolute** phrasing does not -- T3 still overshoots by 4.29, marginally more
   than a plain DEMA. The author overstated a real result. Our coefficients match his expansion term
   for term, so this is a limitation of the claim, not of the code.

## Verified exact matches

- **`DEMA` = `2*EMA - EMA(EMA)`** and **`TEMA` = `3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))`** -- ours match,
  four sources agree, no disagreement found. Note TEMA's name is a misnomer: it is a composite of
  single, double and triple EMAs, not a thrice-smoothed EMA. Mulloy said so himself.
- **`TRIMA`'s even/odd window rule.** Odd n uses `(n+1)/2` twice; even n uses `n/2` then `n/2+1`.
  Ours reproduces the canonical kernels exactly -- n=7 gives `1,2,3,4,3,2,1`, n=4 gives `1,2,2,1`,
  n=9 gives `1,2,3,4,5,4,3,2,1`, matching TA-Lib, Tulip and QuantConnect verbatim. **This is the field
  the research flagged as commonly got wrong:** a widely-copied alternative applies `(n+1)/2` twice
  for all n, which is internally inconsistent with its own published weight examples.
- **`WMA` weights** are the canonical linear ramp normalised by the triangle number `n(n+1)/2`.
- **`ALMA` weights** are algebraically identical to the published Gaussian spec --
  `exp(-0.5*((sigma/n)*(i-k))^2)` is `exp(-(i-m)^2/(2*s^2))` with `s = n/sigma`.
- **`T3` coefficients** match Tillson's expansion term for term, including the six-EMA chain and the
  0.7 default volume factor.

## `SMMA` -- the naming knot, resolved

Four names denote one series: **SMMA** (Smoothed), **RMA** (Running), **MMA** (Modified) and
**Wilder's Smoothing**. All are `alpha = 1/n`.

- TradingView's Pine reference is decisive: `ta.rma` is *"the exponentially weighted moving average
  with alpha = 1 / length"* and *"Moving average used in RSI"*, against `ta.ema` at `alpha = 2/(n+1)`.
- It **is** what Wilder used: StockCharts' RSI page gives `Average Gain = [(previous Average Gain) x
  13 + current Gain] / 14`, which is exactly this recursion at n=14. Same for ATR.
- **`SMMA(n)` = `EMA(2n-1)`:** exact in the coefficient, since `2/(N+1) = 1/n` at `N = 2n-1`. Sources
  split between "equivalent" (Tulip, AnyChart) and "approximately" (Macroption, which also offers
  `2n`). The hedge is a **seeding artifact** -- SMMA is documented as SMA-seeded while EMA seeding
  varies.
  - **VERIFIED: in our implementation the identity is EXACT.** `max|SMMA(n) - EMA(2n-1)| = 0.000000`
    at both n=10 and n=14, because ours seeds both from the first observation. Worth recording so the
    agreement is not later "fixed" as a coincidence.

Source gap: **StockCharts has no SMMA page and no WMA page** -- verified against its full
documentation index. The Wilder recursion appears only inside its RSI and ATR pages, so StockCharts
corroborates the maths but not the name.

## `EMA` seeding -- sources genuinely split

- *Trading-platform convention*: seed with an SMA of the first n values. StockCharts: *"a simple
  moving average is used as the previous period's EMA in the first calculation."* TradingView and
  Fidelity agree.
- *Statistics convention*: seed with the first observation, `s_0 = x_0` (Wikipedia, exponential
  smoothing) -- which also documents the SMA seed as the remedy for its drawback.
- **VERIFIED: ours seeds from the first observation.** At the first valid bar ours reads 99.7083
  against an SMA-seeded 99.7771, a difference of 0.069; by bar 100 the difference is exactly zero.
  Warmup-only, decays completely. Both camps agree the choice fades given enough history.

## `VWAP` -- the rolling window is the correct form for a 24/7 market

**An earlier draft of this research called this "the clearest defect in this class." That was wrong,
and it is corrected here.**

The literature defines VWAP as **anchored**: it accumulates from the session open and resets each
session. StockCharts: *"VWAP calculations start fresh at the open and end at the close."* Wikipedia:
*"VWAP resets at the start of each session."* Ours rolls a fixed `window` instead.

The error was treating that as a divergence. **Anchoring presupposes a session boundary, and a 24/7
market does not have one.** There is no open to accumulate from and no close to reset at, so the
anchored definition has no referent here -- it is not that we implement it loosely, it is that the
quantity is undefined. A rolling window is the coherent way to express the same idea, and it is a
deliberate design choice rather than an approximation of one.

The measurements still stand, and remain useful for anyone reconciling against a session-based
platform. Against a synthetic session-anchored VWAP over five simulated sessions: mean absolute
difference 0.7610, max 4.0016, up to **3.882% of price**. And ours is **exactly equal to `VWMA`
computed on typical price** (`allclose` -> True) -- expected, since a volume-weighted rolling window
of typical price is precisely that.

The one caveat worth keeping: a consumer applying this to a session-based instrument such as an
equity is not getting the institutional execution benchmark, because that benchmark is defined by
the session it anchors to.

Attribution, sharpened: no single originator, but there is a documented first use (James Elkins, Abel
Noser, 1984, for the Ford pension fund) and an academic formalisation (Berkowitz, Logue and Noser,
*Journal of Finance*, 1988).

Attribution, sharpened: no single originator, but there is a documented first use (James Elkins, Abel
Noser, 1984, for the Ford pension fund) and an academic formalisation (Berkowitz, Logue and Noser,
*Journal of Finance*, 1988).

## `MAMA` -- closest to primary, two divergences

Ehlers' own paper was read verbatim, including his EasyLanguage. Ours tracks it closely: the Hilbert
FIR coefficients, the `[6, 50]` period clamp, the `[0.67x, 1.5x]` rate limit, the `DeltaPhase` floor
of 1, the 0.5/0.05 alpha limits, and the two canonical output names.

- **`MAMA` and `FAMA` confirmed as canonical names** -- the paper plots `Plot1(MAMA, "MAMA")` and
  `Plot2(FAMA, "FAMA")`. FAMA expands to *Following Adaptive Moving Average*.
- **Adapts to cycle PHASE RATE OF CHANGE, not volatility.** Ehlers draws the contrast himself: *"The
  Kaufman Adaptive Moving Average (KAMA) and the Variable Index Dynamic Average (VIDYA) use the
  variation in prices, or volatility, as the basis of their adaptations. The concept of MAMA is to
  relate the phase rate of change to the EMA alpha."* This is the cleanest distinction in the class.
- **DIVERGENCE: input.** Ehlers specifies `Price = (H+L)/2`; ours consumes close. KB#104 finding 15.
- **DIVERGENCE: warmup.** Both recursions start from zero and only 6 bars are masked, so ~10 further
  bars publish while still converging -- bar 6 measured 50% below price. Appears faithful to Ehlers'
  own code, so the fix is a longer mask, not a changed recursion. KB#104 finding 16.

## "Adaptive" means three different things here

Worth separating, because the class groups them:

| indicator | what adapts | driven by |
|---|---|---|
| `KAMA` | smoothing constant, per bar | **efficiency ratio** -- net move over path length |
| `MAMA` | alpha, per bar | **cycle phase rate of change** via Hilbert transform |
| `ALMA` | nothing at runtime | user-set `offset`/`sigma`, fixed at configuration |
| `T3` | nothing at runtime | user-set volume factor; Tillson calls it adaptive in a filter-theory sense |

Only KAMA and MAMA measure market state. Ehlers' own survey names KAMA and VIDYA as the adaptive
family, not ALMA or T3.

## `MARibbon` is a generic technique, not a canonical indicator

StockCharts defines it only as *"a graphical representation of multiple moving averages with varying
look-back periods."* **No canonical period set, no canonical count, no canonical average type, and
the literature does not name individual ribbon lines at all.** StockCharts' 10 SMAs from 20 to 65 is
documented explicitly as a platform default. No originator attribution exists.

Consequence for the graph: our three boolean outputs (`ribbon_bullish` / `ribbon_bearish` /
`ribbon_tangled`) are **our construction, not literature**, and are labelled as such in the node.

## `WilliamsAlligator` -- confirmed in full

Jaw/Teeth/Lips confirmed by four independent sources, with periods and shifts 13/8, 8/5, 5/3 on
**median price (H+L)/2**, smoothed with **SMMA** (not SMA or EMA), coloured blue/red/green. Williams'
collective term is **Balance Lines**. Periods are Fibonacci numbers.

Our `.shift(+offset)` looks like a lag but reproduces the canonical relative alignment: canonical
plots `SMMA(t)` at bar `t+k`, ours stores `SMMA(t-k)` at bar `t` -- the same series, and lookahead-free.

**Attribution correction:** the common "Trading Chaos, 1995" citation is not well supported. Sources
that name a book point to *New Trading Dimensions* (1998); Trading Chaos (1995) is more consistently
tied to Fractals and the Awesome Oscillator. StockCharts, TradingView and MetaTrader name no book at
all. Safe wording: attributed to Bill Williams, described in *New Trading Dimensions* (1998).

## Coverage honesty

- **MAMA** strongest -- full primary paper with the author's own code and defaults.
- **T3** strong -- full primary Tillson document including the coefficient expansion.
- **KAMA, DEMA, TEMA, HMA, SMA, EMA, WMA** strong -- multiple independent references agreeing.
- **ALMA weakest by a wide margin** -- **no primary author publication could be located**. The 2009
  date and even the co-author's surname spelling (Kouzis-Loukas vs Douzis-Loukas) rest on secondary
  sources that disagree with each other. Do not treat ALMA's provenance as settled.
- **MARibbon** -- generic technique, no attribution exists to find.

## Sources

StockCharts ChartSchool (SMA/EMA, DEMA, TEMA, HMA, KAMA, VWAP, MA Ribbon, Alligator, RSI, ATR);
Wikipedia (moving average, exponential smoothing, DEMA, TEMA, VWAP); Tulip Indicators (dema, tema,
trima, hma, wilders); TradingView (Pine reference for `ta.ema`/`ta.rma`/`ta.wma`, plus VWMA, ALMA,
KAMA, Alligator, Rolling VWAP); Fidelity (SMA, EMA, HMA); MetaTrader 5 (MA, TEMA, Alligator); MQL5
(Alligator/Balance Lines); QuantConnect (TRIMA); Chart manual (DEMA/TEMA, HMA, T3); Macroption (ATR
smoothing); AnyChart (MMA); alanhull.com (HMA, primary); mesasoftware.com (MAMA, primary);
Tillson "Better Moving Averages" (primary); TrendSpider, ProRealCode, LuxAlgo (ALMA, secondary only).

Primary texts NOT obtained: Mulloy's TASC articles (Jan/Feb 1994), Kaufman's *Smarter Trading*,
Legoux's ALMA paper (may not exist publicly), Williams' books.

Fetch notes: `chartschool.stockcharts.com` works and appending `.md` to any page returns clean
markdown; `school.stockcharts.com` is dead (TLS). Investopedia blocked throughout. TradingView's Pine
reference is JS-rendered and needs a text proxy.
