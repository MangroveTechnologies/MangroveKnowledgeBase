---
name: author-signal-properties
description: Fill the authored (null) property fields on ONE signal node in the signal/indicator ontology graph - the predicate formula and the literature reference. Use when the builder emits nulls on a signal that cannot be lifted from source. Triggers on "author the properties for <signal>", "fill in the nulls for <signal>", "write the formula for <signal>".
---

# Author the null properties for one signal

The builder (`ontology/build_signal_indicator_ontology.py`) lifts everything machine-derivable and
emits `null` for anything a human must write. This skill fills those nulls for **one signal at a
time**.

The signal counterpart of `author-indicator-properties`, and much smaller: a signal has **two**
authored fields against an indicator's ten -- three when the warmup lift is ambiguous -- because
everything else either lifts from the docstring or is reached through the `uses` edge.

Shape and decisions: `ontology/example-bollinger-signals-subgraph.md`.

## The fields

| field | what to write |
|---|---|
| `formula` | the predicate, in domain terms |
| `reference` | the published source for this rule |
| `warmup_bars` | **only when the builder emits null** -- see below |

`abbreviation` is `null` on every signal by convention and is **not** an authoring task. Signals have
no abbreviation; it is held at null for consistency with the indicator layer, which already uses
null for inapplicable. See the worked example.

## Scope - read this before anything else

**ONE signal. Nothing else.** Do not touch the indicator it reads, other signals, the class scheme,
roles, the builder, or the ontology model. If something adjacent looks wrong, note it in one line at
the end and keep going.

## What is already populated - never author these

If you find yourself writing one of these, stop -- it means the builder is broken, and the fix is
there, not here:

| field | source |
|---|---|
| `summary` | the docstring prose above the sections |
| `source_module` | the file the signal lives in |
| `warmup_bars` | the `len(df) < ...` guard, converted to bars-discarded -- *unless null, see below* |
| `usage_example` | generated from the registered name and params |
| `inputs` | the docstring `Requires:` line |
| `params` | the docstring `Args:` block |
| `outputs` | the return annotation and the `Returns:` line |
| the `uses` edge's `inputs` | AST -- the output name and type only |

`interpretation`, `applications` and the signal's **class** are not fields at all. They are reached
by following `uses` to the indicator. Do not add them.

Nor does the `uses` edge carry a description of the output it names. The edge says WHICH output
flows across it; what that output means is authored once on the indicator that emits it.

## `formula` - the predicate in domain terms

Write what the signal decides, using the output names the indicator actually emits and the param
names the signal actually takes. Index bars with `[t]`, and `[t-1]` for the prior bar.

```
bb_above_upper      close[t] > hband[t]
bb_upper_breakout   close[t-1] <= hband[t-1] and close[t] > hband[t]
bb_squeeze          wband[t-1] >= threshold and wband[t] < threshold
```

**Index every bar reference, including on a state signal.** A state and a crossing are both per-bar
predicates; writing the state un-indexed makes the difference look like a change of notation instead
of what it is -- which bars the predicate reads.

**Translate, do not transcribe.** The return expression is mechanically extractable and looks like
`prev_close <= prev_upper and curr_close > curr_upper`. That is local variable names; it means
nothing to a reader of the graph. Read the body, then write the predicate in the names the node
already uses. This is the one field where reading source is required rather than optional.

**Verify by execution, not by eye.** Compute the indicator, evaluate the predicate you wrote against
the signal's actual output over a few hundred bars, and confirm they agree bar for bar. A formula
that disagrees with the code is worse than a null, because a null is honest.

**A signal that never fires verifies nothing.** If the signal returned False on every bar, so did the
formula, and they agree for a reason that has nothing to do with correctness. Check the fire count;
if it is zero, build bars that force the pattern and re-run. Four of the forty pattern signals
(`three_black_crows`, `three_inside_down`, `gravestone_doji`, `continuation_pattern_bearish`) never
fired on a random walk and needed hand-built bars before their check meant anything.

**Read the signal's signature; do not assume its parameters.** The signal exposes a subset of what
its detector takes, and the defaults differ. `tweezer_bottoms_trigger` exposes `tolerance` but not
the detector's `avg_window`; `long_legged_doji_trigger`'s `wick_threshold` defaults to 0.25, not
0.30; `piercing_line_trigger` defaults to `require_gap=True` while the aggregate scanners call the
same detector with False. Four of my first-pass verifications failed on this.

**Run verification scripts with `PYTHONPATH=$PWD`.** Python puts the SCRIPT'S directory on
`sys.path[0]`, not the working directory, so a script in a scratch directory imports the installed
`mangrove_kb` from site-packages rather than this repository -- a different, older API. Assert it
took: `assert "site-packages" not in mangrove_kb.__file__`.

## `warmup_bars` - only when the lift comes back null

The builder converts the `len(df) < N` guard into bars-discarded, but withholds it when a signal has
several guards with different expressions, because then picking one is a judgement. When it is null,
**do not copy the guard** -- the guard is often wrong.

Warmup is set by the DEEPEST-REACHING thing the signal consults, which may be nothing the guard
knows about. All five aggregate scanners guard on `len(df) < 2`, but `bullish_pattern_recent`
consults `morning_star`, `three_white_soldiers` and `three_inside_up`, each of which reaches back two
bars via `.shift(2)` -- so it needs three bars and discards two. `indecision_pattern_recent` guards
the same way but consults `narrow_range(window=7)`, so it discards six.

Find every detector the signal calls, take the deepest `.shift(n)` and the longest rolling window
among them, and use whichever is larger.

## `reference` - the published source

The source that documents **this rule**, not the indicator. `bb_squeeze` cites the BandWidth page
because the Squeeze is its own documented concept; the band-touch signals cite the Bollinger Bands
page because that is where the rule is stated.

**Never invent a URL.** Use one already cited in this repository, or one you have fetched and read.
A plausible-looking URL that 404s is a fabrication.

Where the only source is the indicator's own page, that is what to record -- the `uses` edge tells a
reader which indicator, but not which paragraph of it states this rule.

## If the signal duplicates another

Two signals that compute the same thing are declared, not silently tolerated. Put
`DEPRECATED: identical to \`<canonical_name>\`` in the duplicate's docstring, with the evidence and
the reason it is kept; the builder lifts that one line into both `status: "deprecated"` on the node
and a `supersedes` edge from the canonical signal. Add a runtime `DeprecationWarning` naming the
replacement. Do not delete the signal without checking who reads the name outside this repository --
`hanging_man_trigger` and `shooting_star_trigger` are referenced by MangroveOracle's
`signals_metadata.json`, its strategy cohort files and its experiment outputs.

## Verify before finishing

1. `python3 ontology/build_signal_indicator_ontology.py > /tmp/check.json` and diff against the
   committed graph. **Your authored values must survive the rebuild** -- carry-forward preserves
   them. If one is gone, it is being overwritten by a lift and belongs at that source instead.
2. Run it twice. The second run must be byte-identical: authoring is complete only when the build is
   a fixed point.
3. No new nulls anywhere else in the node. `abbreviation` stays null on every signal by convention;
   nothing else should be.
