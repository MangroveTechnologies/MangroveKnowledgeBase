# Tooltip microcopy — what the panel's `?` text has to do

Written 2026-08-14, after the first two passes of the viewer's tooltips were rejected. Both failed
the same way, and the sources below name that failure precisely, which is why this is recorded
rather than left as taste.

## What was wrong

Pass 1 explained my own design decisions: *"Changes the GRAPH, not this node"* — a defence of a
choice nobody had asked about — and *"`unbounded` and `not authored` are different facts"*, which is
a bug I had fixed that morning, not something a reader wants.

Pass 2 over-corrected into fragments that restate the label: `formula` → *"How it is calculated"*,
`action` → *"Show less of the graph"*. The second is worse than the first: it describes the
mechanism of a control that carries scope selection, per-edge-type filtering, and live counts.

## Sources (each fetched and quoted, not summarised from memory)

| Source | What it settles |
| --- | --- |
| [NN/g, *Tooltip Guidelines*](https://www.nngroup.com/articles/tooltip-guidelines/) | Tooltips are *"microcontent — short text fragments intended to be self-sufficient"* carrying *"brief and helpful content"*. Never repeat the label: *"tooltips with obvious or redundant text are not beneficial to users"*, and if you cannot add something, omit the tooltip. Nothing *"vital to task completion"* belongs in one — that must be on screen. |
| [Microsoft Style Guide, *tooltip*](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/t/tooltip) | *"Use them sparingly… Be brief. Make sure that the information is helpful as a tip and doesn't just repeat what a label shows."* Sentence-style capitalisation; a fragment takes no full stop, a sentence does. |
| [Microsoft, *UI Text and Help for Visual Studio* — InfoTips](https://learn.microsoft.com/en-us/visualstudio/extensibility/ux-guidelines/ui-text-and-help-for-visual-studio) | Describes exactly the pattern this panel uses: instructional text that would clutter the surface, parked behind an unobtrusive `?` icon beside the control. *"Write InfoTips as complete sentences… If you are just using different words to restate the main idea, you don't need an InfoTip."* |
| [NN/g, *Microcontent*](https://www.nngroup.com/articles/microcontent-how-to-write-headlines-page-titles-and-subject-lines/) | Front-load the load-bearing words; plain language, *"no puns, no 'cute' or 'clever' wordings"*; vague and wordy are the two failure modes. |

Verified by fetching each page directly on the vendors' own hosts. The Material 3 tooltip page was
also tried and returned no readable guidance, so nothing here rests on it.

## The rule this panel follows

**Every tooltip says what the thing IS and what you would USE IT FOR, in that order, and never
restates its label.**

- Complete sentences, sentence case, plain language. One or two; three only where the control does
  three things (`action`).
- Load-bearing words first — it is read in a glance or not at all.
- Nothing essential lives only here: the panel already shows the data, so a tooltip that vanishes
  costs a reader context, never an answer.
- Relation definitions are **quoted from `SKILL.md`, not paraphrased**. `about` versus `instance-of`
  is a claim the graph makes; a second wording of it in the UI would start disagreeing with it.

Test: read the tooltip with the label hidden. If it still identifies the thing and gives a reason to
care, it passes. `"How it is calculated"` fails — that is the word `formula` with more letters.

## How ours differs

The sources address tooltips on controls whose meaning is merely unfamiliar. Half of this panel's
tooltips explain **ontology**, where the word is not just unfamiliar but load-bearing — `about` and
`instance-of` are different assertions about the same pair of nodes. So the rule above adds a clause
none of the sources need: the definition is quoted from the artefact that defines it, and the UI is
not allowed a second wording. `tests/test_viz.py` fails the build on a relation with no definition,
which keeps the glossary complete as the ontology grows.
