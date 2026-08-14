---
kind: concept
chapter: 07-chart-patterns
---

# chart pattern

## Summary

A price formation spanning a variable number of bars, identified from swing highs and lows rather
than over a fixed window.

## Explanation

Multi-bar formations: head and shoulders, double tops and bottoms, triangles, wedges, flags and
pennants, cup and handle, and the necklines and completion criteria that define them. Also pattern
reliability and failure modes, and the context a formation requires to mean anything.

Sibling of the existing pattern class, not a parent of it and not the same thing. That class holds
candlestick geometry -- shapes computable from one bar or a small fixed number of them, which is
why 41 signals implement it. A chart pattern needs a swing structure of unknown length, and no
computation in the library produces swing points, so this class carries no procedures. It is the
first class in the graph that is knowledge without an implementation.

## Kind of

- [[Technical Analysis]] -- a character a computation can read, sibling to the candlestick pattern class
