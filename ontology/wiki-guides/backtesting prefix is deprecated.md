---
kind: fact
source: documentation
---
# backtesting prefix is deprecated

## Summary

The /api/v1/backtesting/backtest routes are retained for back-compat; /api/v1/backtests is the
canonical surface.

## Explanation

The two behave identically, so nothing breaks by staying on the older prefix, and nothing is gained
either. New integrations use the canonical prefix, and asynchronous runs use the v2 backtests
surface. Documentation that teaches the deprecated path is teaching the shape of an old deployment.

## About

- [[backtesting]] -- the surface both prefixes reach
- [[sync backtest transport budget]] -- why the async surface exists beside the synchronous one
