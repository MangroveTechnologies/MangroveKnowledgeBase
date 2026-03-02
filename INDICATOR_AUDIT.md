# Indicator Accuracy Audit

**Status:** TODO -- delegate to agent team
**Priority:** Before PyPI publish

## Objective

Verify that all 70 indicator implementations produce mathematically correct output by comparing against reference implementations on real data.

## Scope

- 70 indicator classes across 6 categories (Momentum, Trend, Volume, Volatility, Patterns, Returns)
- Compare each indicator's output against pandas-ta or manual calculation on BTC daily data
- Flag any discrepancies with bar-level diffs
- Known issue reported: MACD crossover signal may fire at wrong bars (investigate)
- Already fixed: Donchian Channel breakout signals were using offset=0 (now offset=1)

## Approach

- Create notebooks/indicator_audit.ipynb
- For each indicator: compute with our implementation, compute with reference, plot both, report max absolute error
- Can be parallelized: each indicator is independent, delegate one per agent
- Agents need: the indicator class source, reference formula, BTC daily data

## Reference Implementations

- pandas-ta (pip install pandas-ta) for most standard indicators
- Manual numpy calculation for pattern indicators (no external reference exists)
- TA-Lib (optional, C-based, harder to install but gold standard)

## Output

- Pass/fail per indicator with max error tolerance (1e-10 for exact match indicators, 1e-6 for floating point)
- Summary table: indicator name, category, max error, pass/fail
- Any failing indicators get fixed before PyPI publish
