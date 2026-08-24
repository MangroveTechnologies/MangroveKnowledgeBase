---
kind: fact
source: documentation
---
# backtest takes api or file data

## Summary

A backtest reads its bars either from the provider chain or from a local CSV.

## Explanation

`data_source="api"` goes through the provider chain. `data_source="file"` reads a CSV, which must
carry timestamp, open, high, low, close and volume. The interval is one of 1m, 5m, 15m, 30m, 1h, 4h
or 1d, and defaults to 1h.

## About

- [[market data provider chain]] -- where the api path gets its bars
- [[backtesting]] -- what the bars are read for
