---
kind: fact
source: documentation
---
# backtest window is two dates

## Summary

A backtest window reaches the engine as two dates; a relative span is resolved before it gets there.

## Explanation

The request carries a start date and an end date, and a bulk request requires both. A phrase like
"the last four months" is a convenience for whoever is choosing the window, and it is converted where
that choice is made -- so the request carries the result rather than the phrasing, and the same
request re-run tomorrow covers the same days instead of sliding forward.

## About

- [[backtesting]] -- the window is the run's first parameter
- [[backtest takes api or file data]] -- the window and the source together decide which bars load
