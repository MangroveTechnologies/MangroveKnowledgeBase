---
kind: judgment
source: content/docs/guides/signal-architecture.md
---
# why one trigger

## Summary

One trigger per entry keeps a strategy explainable: there is exactly one event to point at when
asking why it entered.

## Explanation

The single trigger buys four things. A strategy is easy to state, because it has one entry event
rather than a disjunction of them. It has fewer free parameters, so there is less to curve-fit. The
division of labour is legible -- the trigger says when to act, the filters say whether conditions
are right. And when a backtest disappoints, the entry event is not in question, which leaves the
filters and the parameters as the things to examine.

## About

- [[one trigger at least one filter]] -- the rule this judgment gives the reasons for
- [[overfitting]] -- fewer free parameters is the argument that connects the rule to it
