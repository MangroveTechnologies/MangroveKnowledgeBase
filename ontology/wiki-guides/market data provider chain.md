---
kind: fact
source: content/docs/guides/backtesting-guide.md
---
# market data provider chain

## Summary

A backtest's bars resolve through a cost-ordered provider chain: internal Mangrove history first,
then kraken_rest, binance_public, coinapi and coingecko.

## Explanation

With no provider pinned, the shared cost-ordered chain decides, and the internal Mangrove market
data -- free, with deep ClickHouse history -- is tried first. Paid CoinAPI sits mid-chain as a
fallback rather than the source anyone reaches for. Results are cached in Redis across workers and
restarts, and a relative window is floored to the day, so two backtests asking the same question
share one cache entry instead of refetching upstream.

## About

- [[backtest takes api or file data]] -- the chain is one of the two places bars come from
- [[data quality]] -- what the chain's ordering trades against
