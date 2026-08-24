---
kind: fact
source: content/docs/guides/backtesting-guide.md
---
# sync backtest transport budget

## Summary

The synchronous backtest surface rides a gateway budget of about fifteen seconds; work that will not
finish inside it belongs on the async surface.

## Explanation

A request that cannot complete within the budget answers 503 with a retry hint and an engine-warming
code, which is an honest answer rather than the opaque gateway error that a bounded read prevents.
Bulk runs are therefore kept to short, warm windows; a long lookback is submitted one strategy at a
time to the asynchronous surface and polled.

## About

- [[bulk backtest shares market data]] -- the batch size this budget bounds
- [[backtesting prefix is deprecated]] -- which prefix the surfaces are reached through
