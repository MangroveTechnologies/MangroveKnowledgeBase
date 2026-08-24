---
kind: fact
source: documentation
---
# backtest metrics set

## Summary

A backtest reports seventeen metrics, not the handful usually quoted from it.

## Explanation

sharpe_ratio, sortino_ratio, calmar_ratio, irr_annualized, irr_daily, max_drawdown,
max_drawdown_duration, win_rate, total_return, total_trades, avg_daily_return, gain_to_pain_ratio,
max_consecutive_wins, max_consecutive_losses, starting_balance, ending_balance and num_days. A
summary that quotes four of them is a choice about what to show, not the extent of what was measured.

## About

- [[backtest execution flow]] -- the step that computes them
- [[drawdown risk]] -- what two of the seventeen measure
