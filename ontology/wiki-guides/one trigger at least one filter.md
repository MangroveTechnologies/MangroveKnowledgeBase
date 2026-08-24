---
kind: fact
source: content/docs/guides/signal-architecture.md
---
# one trigger at least one filter

## Summary

An entry takes exactly one TRIGGER and at least one FILTER; an exit takes at most one TRIGGER, and
may not carry FILTERs without one.

## Explanation

The trigger says when to act and the filter says whether the conditions are right, so an entry needs
both. The counts are one entry trigger with one or two entry filters, and at most one exit trigger
with up to two exit filters; an exit may be left out entirely, and the position then closes on the
stop, the target, or a time-based rule from the execution config.

The API's rule check is narrower than the requirement. It rejects an entry with no TRIGGER and an
entry with two, and an exit carrying FILTERs without a TRIGGER, but it counts no filters at all.

## About

- [[signal type]] -- the count constraint is stated per role
- [[strategy]] -- the shape a strategy's rules must take to be accepted
