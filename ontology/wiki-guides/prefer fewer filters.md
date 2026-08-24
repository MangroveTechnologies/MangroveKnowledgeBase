---
kind: judgment
source: content/docs/guides/signal-architecture.md
---
# prefer fewer filters

## Summary

A second filter narrows an entry further than the first; take it only when you can name the entries
it removes.

## Explanation

Filters compose conjunctively -- all of them must hold on the same bar the trigger fires -- so each
one added cuts the set of bars that can produce a trade. One is required and a second is allowed,
and the allowance is not an instruction. Use the filter that confirms the condition the entry
depends on, and add the second only when you can say which entries it removes and why they deserved
removing.

## About

- [[one trigger at least one filter]] -- the counts this judgment chooses within
- [[role filter]] -- what a filter contributes, and what each additional one costs
