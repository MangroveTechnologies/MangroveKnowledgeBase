---
kind: procedure
source: documentation
---
# backtest execution flow

## Summary

Validate the request, load the bars, walk them once, and compute the metrics after the last one.

## Explanation

Entry signals are evaluated only on bars where no position is open. Where one is open, the exits are
evaluated instead -- signal, stop, target and time-based -- and positions, orders and trades are
recorded as they happen. Nothing is scored while the walk is in progress: the metrics are computed
once, after the final bar.

## About

- [[backtesting]] -- the flow is what running one consists of
- [[backtest metrics set]] -- what the final step produces
