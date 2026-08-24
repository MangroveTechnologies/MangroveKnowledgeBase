---
kind: fact
source: content/docs/guides/signal-architecture.md
---
# signal role is declared not inferred

## Summary

A signal's role is read from its declared type, not deduced from its name. Naming patterns correlate
with role but do not determine it.

## Explanation

Event-shaped names -- crossings, breakouts, reversals, squeezes -- are usually triggers, and
state-shaped names -- above, below, oversold, overbought, strong-trend -- are usually filters. The
correlation is strong enough to be a useful guess and weak enough to be wrong: `ttm_squeeze_active`,
`starc_lower_breakout`, `starc_upper_breakout`, `reversal_pattern_bullish` and
`reversal_pattern_bearish` all read as events and all are filters.

The declared type is the answer. Guessing from the name is how a strategy acquires two triggers and
is rejected.

## About

- [[signal type]] -- the declared classification, which is the one that governs
- [[role trigger]] -- one of the two roles a name can only hint at
- [[role filter]] -- the other
