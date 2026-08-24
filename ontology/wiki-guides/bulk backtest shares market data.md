---
kind: fact
source: documentation
---
# bulk backtest shares market data

## Summary

A bulk backtest fetches each asset-and-timeframe pair once and reuses it across every strategy that
shares it.

## Explanation

Four strategies on the same asset and the same interval cost one upstream call, and the response
reports how many unique calls were made, so the saving is visible rather than assumed. A bulk request
takes either strategy ids or strategy configurations, never both, and requires both window dates.

## About

- [[backtest window is two dates]] -- the window is shared by every strategy in the batch
- [[sync backtest transport budget]] -- what limits how large a batch can usefully be
