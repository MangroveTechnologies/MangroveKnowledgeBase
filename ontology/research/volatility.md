# Research: volatility indicators

Literature research for the `volatility` class of the signal/indicator ontology, gathered by two
web-research subagents on 2026-08-05, **plus the verification of each claim against our own
`_compute`**. Design context: MangroveTechnologies/MangroveAI#1012.

Why this file exists: the research is the input to the authored node properties, and the
disagreements it surfaced are the reason several of our nodes can state a convention at all. Without
it recorded, the next session re-runs the same searches and loses the verification verdicts.

## Method, and why both halves are needed

The literature says what an indicator **should** do. Only the code says what **ours** does. Those
coincide most of the time, and the value is in the delta -- so research supplies the hypothesis and
execution decides.

This matters concretely: we only knew to check ATR's seeding because a source flagged that
implementations disagree. Research is also how a deviation becomes *visible* -- the literature is
unanimous that warmup is undefined, which is what makes our zero-filled ATR warmup detectable as a
departure rather than looking normal.

Every "verified" line below was produced by running the code, not by reading it.

---

## ATR

- **Abbreviation** `ATR`. **Canonical output name** "Average True Range". Single output series.
- **Formula (Wilder, 1978).** `TR_t = max(H-L, |H - C_prev|, |L - C_prev|)`; seed `ATR_n = mean(TR_1..TR_n)`,
  then `ATR_t = (ATR_{t-1}*(n-1) + TR_t) / n`.
- **Sources disagreed on two points**, both of which our code settles:
  - *Smoothing.* Wilder's is a modified EMA at `alpha = 1/n` (RMA/SMMA); many libraries ship SMA or an
    ordinary EMA at `alpha = 2/(n+1)` under the same name.
    **VERIFIED: ours is `ewm(alpha=1/window, adjust=False)` -- Wilder's.**
  - *Seeding.* Wikipedia/StockCharts seed with the SMA of the first `n` TR values; others seed with `TR_1`.
    **VERIFIED: `ATR[13] == nanmean(TR[0:14])` exactly -- the SMA-seed convention.**
- **VERIFIED, not in any source -- our deviation.** Warmup bars `0..window-2` are filled with literal
  `0.0`, not NaN (`np.zeros(n)`). Observed first five values `[0. 0. 0. 0. 0.]`. A zero here means "not
  yet computed", and is indistinguishable from a genuine zero-volatility reading.
- **VERIFIED, code defect.** ATR's own inline comment claims *"tr[0] is NaN so it's really mean of
  window-1 valid values"*. False: `true_range` uses `np.fmax`, which ignores NaN and falls back to
  `H-L`, so `TR[0]` is finite and the seed is a true `window`-value mean.

Sources: Wilder, *New Concepts in Technical Trading Systems* (1978);
<https://en.wikipedia.org/wiki/Average_true_range>;
<https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-true-range-atr>

## TrueRange

- **Abbreviation** `TR`. **Canonical output name** "True Range". Single output series.
- **Formula.** `max(H-L, |H - C_prev|, |L - C_prev|)` -- the gap-inclusive replacement for `H-L`.
- **Source uncertainty.** No agreement on the first bar, which has no prior close; the common
  convention is `TR_1 = H_1 - L_1`, but that is implementation practice rather than a stated rule.
  **VERIFIED: ours falls back to `H-L`** (`TR[0] = 0.1875 = High[0] - Low[0]`), matching the common
  convention. Not NaN.

Sources: Wilder (1978); <https://en.wikipedia.org/wiki/Average_true_range>;
<https://help.ctrader.com/knowledge-base/indicators/volatility/true-range/>

## NATR

- **Abbreviation** `NATR`. **Canonical output name** "Normalized Average True Range"; some sources use
  "Average True Range Percent" (ATRP) interchangeably, others treat it as distinct -- unresolved.
- **Sources genuinely disagree on the definition:**
  - *Definition A* (TA-Lib, Tulip, QuantConnect): `100 * ATR(n) / Close`. The dominant convention.
  - *Definition B* (argued by Macroption): normalize each bar's true range by its reference close
    first, then average. Not equal to A; B is claimed to avoid overstating volatility in downtrends.
  - **VERIFIED: ours is Definition A** -- `100.0 * atr / close`, ATR computed first.
- **VERIFIED, inconsistent with ATR.** NATR masks its warmup to `NaN` while ATR fills the same region
  with `0.0`. Two conventions in one dependency chain.
- No primary publication located; NATR appears as a derived library indicator. Attribution to John
  Forman is secondhand and unverified.

Sources: <https://tulipindicators.org/natr>;
<https://ta-lib.github.io/ta-lib-python/func_groups/volatility_indicators.html>;
<https://www.macroption.com/normalized-atr/>

## UlcerIndex

- **Abbreviation** `UI`. **Canonical output name** "Ulcer Index".
- **Two different formulas share the name**, and this is the substantive disagreement:
  - *Martin's original (1987/1989)*: retracement measured against the **running maximum** close over
    the whole sample -- a risk statistic over a series.
  - *Charting form (StockCharts, most TA libraries)*: **rolling `n`-period** max close and rolling
    mean, default n=14 -- a time-series indicator. These produce different values.
  - **VERIFIED: ours is the charting rolling-max form.** Reconstructed both; rolling matched
    (`True`), running-peak did not (`False`).
- Only downside contributes; squaring penalizes deep drawdowns disproportionately. Approaches zero
  when price makes consecutive new highs within the window.
- Related but distinct metric, NOT an output of this indicator: Ulcer Performance Index / Martin ratio.

Sources: Martin & McCann, *The Investor's Guide to Fidelity Funds* (1989);
<https://en.wikipedia.org/wiki/Ulcer_index>;
<https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index>

## KeltnerChannel

- **Abbreviation** `KC` (platform convention, not Keltner's own).
- **Two variants, both legitimate:**
  - *Variant A -- original (Chester Keltner, 1960)*: `Middle = SMA(TP, 10)`,
    `Upper/Lower = SMA(TP,10) +/- SMA(H-L, 10)`.
  - *Variant B -- modern (Linda Bradford Raschke)*: `Middle = EMA(Close, n)`,
    `Upper/Lower = EMA +/- m * ATR(p)`. Sources disagree on defaults (StockCharts n=20, m=2, ATR(10);
    TradingView m=1.5; others p=n).
  - **VERIFIED: our `original_version=True` is exactly Variant A.** Our code computes
    `SMA((4H-2L+C)/3)`, which expands algebraically to `SMA(TP) + SMA(H-L)`; reconstructed both and
    they match (`True`), as does `mband == SMA(TP)`.
- **VERIFIED, our deviation.** On the `original_version=True` path, `window_atr` and `multiplier` are
  ignored -- two of the four declared parameters do nothing.
- **Canonical output names:** Middle Line (a.k.a. Basis), Upper Channel Line, Lower Channel Line.
  Width and position-within-band series have **no established literature name** -- "Keltner Channel
  %B" exists on some platforms but is a borrowing of Bollinger's naming, absent from Keltner and
  Raschke source material.

Sources: <https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/keltner-channels>;
<https://www.tradingview.com/support/solutions/43000502266-keltner-channels-kc/>

## DonchianChannel

- **Abbreviation** `DC` (less firmly established; StockCharts files it as "Price Channels").
- **Formula.** Upper = highest high over N; Lower = lowest low over N; Middle = midpoint. Default N=20.
- **The window convention -- SETTLED by a dedicated research pass.** The documented convention is
  **unanimous: exclude the current bar.** StockCharts states our exact failure mode as the reason:
  *"The Price Channel formula doesn't include the most recent period... A channel break would not be
  possible if the most recent period was used."* Corroborated by the Original Turtle Trading Rules
  (*"exceeding the high or low of the **preceding** 20 days"*, explicitly attributed to Donchian's
  channel-breakout systems), Donchian's own 4-week rule (*"four **preceding** full calendar weeks"*),
  and TC2000, which defaults to offset 1 -- *"This allows for breakouts."*
  - Sources that include the current bar (pandas-ta, bukosabino/`ta`, Pine's `ta.highest`) are
    **generic rolling-window primitives that make no claim about Donchian convention**. TA-Lib and
    Tulip ship no Donchian function at all. No source argues inclusion is correct.
  - The plot-vs-signal split is NOT the resolution: StockCharts applies the exclusion to the plotted
    channel, for a signal reason. The exclusion belongs in the indicator, not the signal layer.
  - **VERIFIED: our indicator defaults to `offset=0`, i.e. INCLUDES the current bar** -- over 400
    bars, zero closes above the upper band and zero below. Our two Donchian signals pass `offset=1`,
    which restores breakouts (5 above, 9 below), so the standard behaviour exists but is bolted on at
    the call site rather than being the default. Filed as finding 1 on KB#104.
  - Implementation note: the exclusion is a **shift by 1**, not a window of `N-1`, and it costs one
    extra warmup bar.
- **VERIFIED, separate defect.** `pband` is computed from the *unshifted* bands and only then shifted,
  so it never matches the bands actually shipped alongside it (max abs diff 0.344 at `offset=1`) and
  can never leave `[0, 1]` even while those bands are being broken. KB#104 finding 2.
- **VERIFIED, our deviation.** `wband` divides by the rolling mean of **close**, not by its own
  `mband` -- so it is not comparable with the `wband` emitted by BollingerBands or Keltner despite the
  shared name.
- **Canonical output names:** Upper/Lower Channel Line; the middle is "Centerline" (StockCharts) or
  "Middle Channel" -- both well attested, no single dominant term. No literature name for width or
  position series.

Sources: <https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/price-channels>;
<https://en.wikipedia.org/wiki/Donchian_channel>

## STARCBands

- **Abbreviation** `STARC` -- the name *is* the abbreviation (**ST**oller **A**verage **R**ange **C**hannel).
- **Formula.** `Middle = SMA(price, n)`, `Upper/Lower = Middle +/- m * ATR(p)`. Widely repeated
  original parameterization n=6, m=2, p=15.
- **COVERAGE CAVEAT -- weakest evidence in this class.** No StockCharts ChartSchool entry. Attribution
  to Manning Stoller in the early 1980s is **secondary in every source found**; no primary publication
  verified. Platform docs publish no agreed defaults (thinkorswim and devexperts publish none;
  WealthCharts says "5 to 10 periods is common"). The n=6/m=2/p=15 triple was not located in a primary
  Stoller source. Treat developer, date and defaults as reported-but-unverified.
- **VERIFIED, our deviation.** Ours masks ATR's warmup to NaN before forming the bands -- a third
  warmup convention alongside ATR's zeros and the rolling indicators' natural NaNs.
- **Canonical output names:** Middle Band; STARC Band+ ("starc+"); STARC Band- ("starc-"). No width or
  position series exists.

Sources: <https://www.wealthcharts.com/kb/category/charts/indicator-formulas/Stoller-Average-Range-Channel-Bands-STARC-Bands-Indicator-Formula/>;
<https://devexperts.com/dxcharts/kb/docs/stoller-average-range-channel-bands>;
<https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/R-S/STARCBands>

---

## Cross-cutting findings

1. **Three warmup conventions inside one class.** ATR emits literal `0.0`; NATR and STARCBands mask to
   `NaN`; the rolling-window indicators produce `NaN` naturally. No source documents the zero-fill,
   because no source proposes it.
2. **`pband` bounds differ per indicator and cannot be generalised.** BollingerBands is unbounded and
   guarded against zero-width bands; Donchian is bounded `[0, 1]` because its window includes the
   current bar; Keltner is unbounded and **unguarded**. A single "%B is 0..1" claim from the literature
   would be wrong for two of the three.
3. **`wband` is not one measurement.** BollingerBands and Keltner divide by their own middle band;
   Donchian divides by a rolling mean of close. Same name, different quantity.
4. **Bollinger's "Bandwidth"/"%B" have no counterpart in Keltner, Donchian or STARC.** That absence is
   a finding, not a gap -- it must be recorded explicitly rather than left null, since null means
   "not yet authored".

## BollingerBands

Researched last, because its properties had been hand-authored before this research step existed.
That was the right thing to check: one of the two asserted canonical names was **wrong**.

- **Abbreviation** `BB` (also `BBANDS`). **UNCERTAIN:** neither bollingerbands.com nor StockCharts
  states a short form explicitly; "BB" is conventional usage, not a sourced canonical abbreviation.
  Ours comes from our own glossary, which is fine, but the literature does not license it.
  "Bollinger Bands(R)" is a registered trademark of John Bollinger.
- **Canonical output names -- from Bollinger, first person:** *"I created %b, an indicator that
  depicted where price was in relation to the bands, and then I added BandWidth to depict how wide
  the bands were as a function of the middle band."*
  - Width series: **BandWidth** -- one word, capital W. **CORRECTED: we had written "Bandwidth".**
  - Position series: **%b** in Bollinger's own spelling; StockCharts titles the page "%B Indicator".
    Both attested; we use `%B`.
  - **REFUTED:** "%Bandwidth" appears in no source -- the `%` belongs to `%b` alone. "BBW" is
    third-party library shorthand, absent from both primary sources.
- **Formula.** `BandWidth = ((Upper - Lower) / Middle) * 100`; `%B = (Price - Lower) / (Upper - Lower)`.
  Defaults 20 periods and 2 standard deviations, unchanged for 35 years per Bollinger. He recommends
  2.1 for a 50-period SMA and 1.9 for a 10-period.
- **VERIFIED, corroboration rather than deviation.** Bollinger states *"We use the population
  calculation for standard deviation."* Ours is `.std(ddof=0)` -- population. Reconstructed both:
  population matched (`True`), sample `ddof=1` did not (`False`).
- **VERIFIED, and the literature is emphatic.** StockCharts enumerates that `%B` *"is above 1 when
  price is above the upper band"* and *"is below 0 when price is below the lower band"*. Since the
  bands are stated to contain only 88-89% of price action, out-of-range readings are an expected and
  meaningful part of the series. Our `pband` is unclamped, which is correct -- **an implementation
  that clamped it to [0,1] would destroy the signal the literature treats as significant.** Our
  originally authored description said exactly this; it is now sourced rather than asserted.
- **UNCERTAIN:** sources say "price" without specifying close vs typical price, for either the band
  inputs or the `%B` numerator. Not resolvable from these sources. Ours uses close throughout.

Sources: <https://www.bollingerbands.com/bollinger-bands>;
<https://www.bollingerbands.com/bollinger-band-rules>;
<https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands>;
<https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/b-indicator>;
<https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/bollinger-bandwidth>

Note on sourcing: *Bollinger on Bollinger Bands* is cited second-hand via StockCharts, not read
directly. The working ChartSchool path for %B is `.../technical-indicators/b-indicator`; the obvious
path 404s.

## Blocked sources

`school.stockcharts.com` (TLS failure), `investopedia.com` (fetch blocked), `multicharts.com` (403).
The `chartschool.stockcharts.com` mirror served the StockCharts content used above.
