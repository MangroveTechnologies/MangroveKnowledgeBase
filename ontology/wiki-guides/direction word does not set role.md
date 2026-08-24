---
kind: fact
source: documentation
---
# direction word does not set role

## Summary

Words naming a direction -- bullish, bearish -- say which way a signal points, not whether it is a
trigger or a filter.

## Explanation

`macd_bullish_cross` is a trigger and `obv_bullish` is a filter. Both are bullish. What separates
them is that one names a crossing, which happens on a bar, and the other names a state, which
persists. `rsi_bullish_divergence` is a trigger for the same reason and `adx_strong_trend` a filter,
neither of which the direction word predicts.

## About

- [[signal role is declared not inferred]] -- the general form of this trap
- [[signal type]] -- where the answer actually lives
