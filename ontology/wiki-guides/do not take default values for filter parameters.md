---
kind: judgment
source: documentation
---
# do not take default values for filter parameters

## Summary

A filter confirms that conditions are right; it is not there to be selective. Where a filter has a
parameterised threshold, its documented default is usually graded for a signal rather than a gate,
and taking it unchanged is how a strategy ends up unable to fire.

## Explanation

A default threshold marks a notable condition -- the value at which the indicator is saying
something. That is what an event wants. A filter is asked a different question: are conditions
right to act. Choose a less selective value than the default.

Two thresholds, each defaulted, compound the problem: the entry needs both to hold at the moment the
trigger fires.

## About

- [[role filter]] -- confirming conditions is the role a threshold should be chosen for
- [[prefer fewer filters]] -- the same failure reached by adding filters rather than by tightening one
