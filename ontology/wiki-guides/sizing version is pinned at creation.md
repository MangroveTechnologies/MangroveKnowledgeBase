---
kind: fact
source: content/docs/guides/creating-a-strategy.md
---
# sizing version is pinned at creation

## Summary

The position-sizing version a strategy uses is fixed when the strategy is created and cannot be
changed afterwards.

## Explanation

The value is set at creation and is immutable thereafter; an update that tries to change it is
refused, and the value is read from the strategy's own record rather than from a submitted
configuration. Switching sizing math means creating a new strategy.

A partial execution config supplied at creation is merged over the canonical defaults, so omitting a
field keeps its default rather than dropping it -- which is why a strategy created with almost no
configuration still carries the full set the sizing engine reads.

## About

- [[strategy]] -- what the version is pinned to
- [[position sizing]] -- the calculation whose version is fixed at creation
