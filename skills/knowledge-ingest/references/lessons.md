# Failure modes

Each entry is a defect this work actually produced, and the rule that came out of it. They are here
because every one of them looked correct from the inside: the build was green, the counts moved, and
the graph was wrong.

## About the source

**Read the chapter before writing anything that reads it.** An extractor written over an unread
document is a set of guesses about its contents, debugged one guess per turn: mangled slugs,
primitives inferred from section position, worked examples standing in as definitions, every subject
attached to whichever came first. All of it was discoverable in twenty minutes of reading. The
reading is not preparation for the work; it is the work.

**Read the named references in full.** A README is not the specification. Where an existing tool
covers part of the job, its own documentation states the procedure — including, in this case, that
the model reads the source and writes the entity pages, and the compiler is deterministic.

**Do not assume the next chapter has the shape of the last one.** Chapter 3 introduced a section with
no `### Definition` and no subject, four claims under bare headings, numbered steps where earlier
chapters used bullets, an advice heading worded differently, an ASCII diagram inside an Examples
block, and five headings matching no rule at all. Each was silently dropping content. The parser now
raises on an undeclared block rather than skipping it, which converts that class of loss into a build
failure.

## About corrections

**Do not over-correct.** "Follow the guide" was about how the source gets read. Applied instead to
how the pipeline works, it produced fifty-two hand-written pages that lost every formula, typed
input, worked example and use-case list the chapter states — content the extractor had already
captured correctly. Establish what an instruction is aimed at before discarding work that was not the
problem.

**When the defects are already named, fix them.** A coverage check proposed to detect a list of
problems just enumerated is procrastination wearing a rigour costume. Build the thing that passes the
check; add the check to keep it passing, not to discover what is already known.

**A tool's defaults are not the specification.** The ontology is the specification, and extension
points exist to carry it. Where a default conflicts with the design, the design wins — silently,
without raising it as a question. A question settled in an earlier commit is not a question.

## About what the builder should be doing

**Do not hand-write what the text already says.** A hundred and eighteen statements were about to be
mapped to their nodes by hand, and a third of them name the node outright — "always have a
stop-loss for every position" against a node called `stop order (stop-loss)`. Transcribing what a
document states is where the errors come from; the extractor should read it and print what it could
not place. Declarations are for the residue, the ambiguities and the corrections, not for copying.

**Size a pass by opening three of the items, never by a coverage ratio.** Chapters 1–3 carry
authored prose on 85–90% of their nodes and chapter 4 on 1 of 74, which was read as ~58 nodes of
writing to do. Opening three showed two needed edges rather than prose, and that the comparison was
never valid: chapter 4's nodes carry the chapter's python in a field that is already a search tier.
A ratio describes what earlier work did, not what these items lack.

**A wrong edge is worse than a missing one, so a proposal must be visible.** Matching statements to
node names by frequency alone drew `schema:strategy` from "reveal your strategy to sophisticated
participants": when chapter 1 builds the graph is 310 nodes and `strategy` looks rare, by chapter 4
it is in 98 of 571. Frequency is not enough on a growing corpus — only a compound name or an
abbreviation is a citation, a single ordinary word is a candidate for review, and every resolution
gets printed so it can be refused.

**Do not mint an id inside a namespace something else counts.** `procedure:indicator-*` is one node
per indicator class, and `procedure:indicator-based-entry` made the graph report 73 indicators
where the library has 71. The count test caught it; the builder now raises instead.

**Check which way a new edge points, not just that it exists.** `all_paths` suppresses detours
through a hub by spotting two edges that both point *at* it — the shape every backbone relation
has. Twelve example edges drawn *out* of `concept:signal-type` slipped past that guard and made
twelve signals mutually two hops apart. Same claim, reversed to point up, and the existing
suppression worked again.

## About the merge

**Measure lossiness; do not assert it.** A transform claimed to be clean was dropping sixteen
formulas, sixteen typed I/O blocks, ten worked examples and nine use-case lists. Count what went in
and what came out, per kind of content, before saying anything about fidelity.

**Outer join with dedupe, never a choice.** Two sources describing the same node contribute both
statements: materially different wordings sit side by side (`source_wording`, `chapter_variants`),
near-identical ones collapse. Choosing between them destroys information no reviewer asked to lose.

**Two sources describing one thing is ONE node.** Not two joined by an edge -- that is the same
choice the outer join exists to refuse, made in a different place. Chapter 7 describes the
formations the library already detects, and the first draft made `concept:doji` beside
`procedure:signal-doji-trigger`; folded, the node holds the shape and the predicate that finds it,
and the chapter cost 28 new nodes instead of 43. If the two sources cut the thing differently --
one section for hammer and hanging man where the library has a signal each -- split along the line
the source itself draws, and give both sides what they share.

**Verify a merge is additive.** No atom removed, no atom modified except declared folds, no edge
removed. A fold that quietly replaced a code-derived summary, or a `reference_chapter` that replaced
rather than unioned, is invisible in the totals — the node count is identical either way.

## About the shape of the result

**A stated line belongs on an edge, not in a list.** Principles and practices start in two list
nodes and move onto the edges they earn, carrying the line as the reason the edge holds. The length
of what remains is the progress measure; empty means the chapter is fully connected. Copies in both
places drift.

**No node reachable by one edge.** A taxonomy member whose only edge is its `kind-of`, or a formula
reachable only from the thing it quantifies, can be found by walking down from its parent and by no
other question. The chapter almost always states the missing relationship in prose without ever
drawing it. Exception, stated rather than papered over: a subject-area anchor whose chapter has not
been read yet has nothing to connect to.

**Do not invent an edge to raise a count.** Where a relationship does not exist, say so. A wrong edge
is worse than a missing one, because it answers a query.

**Watch what a new edge does to existing queries.** An `about` edge into `concept:liquidity` reads as
"what quantifies liquidity", so pointing a venue at it corrupted an answer that was correct. Check
which questions the target node already answers before adding to it.

**A new property is invisible until something reads it.** A chapter that introduces a field —
a comparison table, a caution, a heading nobody anticipated — puts content in the record that the
retrieval surface does not know about. Four claims about strategy risk landed correctly and could
not be found, because search read an allow-list of property names. After merging a chapter, search
for a term that appears **only** in a field the chapter introduced, and check it comes back. The
record being right is not the same as the graph answering.

## About the guards

**A guard that fires on real data is a wrong guard.** The numbering check read a pip (`0.0001`) as a
section number. The fix is to narrow the guard — a section reference wears a section mark or is
followed by the heading it numbers — not to launder the data.

**A test that never sees the artifact proves nothing.** A green suite proves the code runs. It does
not prove the published page renders, the count in the README matches, or the sentence in the graph
is readable. Pin every number quoted in prose to a value derived from the graph.

**Interpreters differ.** An f-string of HTML tokenises as one string before 3.12 and as parts after,
so a source-scanning check passed locally and failed on the oldest supported version. Rules that read
source text have to be right on every version in the matrix.

**Prose defects survive every test that does not read prose.** Adjacent string literals concatenate
with nothing between them; 195 wrapped sentences shipped as "the spreadactually paid" through a green
suite, a review and a published render.

**Count the source lines that reach the record.** Six review gates passed while four kinds of
content were being dropped: an authored explanation overwrote the chapter's own bullets, the loser
of two wordings for one node fell on the floor, the Summary's closing blockquote was thrown away,
and every practice lost the name it was given. One line-coverage measurement found all four in a
single pass. Read the absences rather than the percentage — most are a table row stored as separate
props, and the four real ones were sitting among them.

**A chapter says things outside its blocks.** Three places, all of which were being dropped and all
of which a line-coverage count found: the prose between a section heading and its first `###` (§5.0
states *"risk is multi-dimensional"* there and nowhere else), a Summary's plain statements (chapter
5 closes on *"preserve capital"*, which is neither a blockquote nor a numbered item), and the second
of two list-valued props merging onto one node.

**Watch what a fix does to the merge that follows it.** Keeping a displaced summary created a
`notes` list, and the props merge skipped any key already present — so the block's own notes were
dropped by the very fix that was recovering text. Both list props union now.

**Containment is not sameness.** Collapsing two wordings when one contained the other threw away
the sentence that made it longer: the graph held *"Shows both trend direction and overbought/oversold
conditions"* and the chapter said *"Double-smoothed momentum indicator that shows both…"*. Same rule
lost *"Where `n` is the lookback period"* off a formula. Equality collapses; length decides which of
two unequal wordings wins.

**A chapter may improve a docstring, never a sentence somebody wrote.** *"The indicator provide an
indication of the degree of price volatility"* is not a definition of ATR and the chapter's is, so a
chapter's definition replaces a **code-derived** summary and the builder's is kept as
`source_wording`. Applied without that gate it also replaced `concept:liquidity` — *"the ease with
which an asset can be bought or sold without materially moving its price"* — with a wordier
paragraph, and stripped a `[[ADX]]` link out of another. The record already says which atoms a
chapter or a wiki page wrote: `meta.derived_atom_ids`.

**One chapter can define one node twice.** Chapter 2 gives position P/L an FX formula and a futures
formula; chapter 8 states a volatility breakout in §8.2 and again in §8.4. Both merge paths kept
whichever arrived first and dropped the other without a word — the fold path and the plain-atom path
each needed the same rule, and the second was found only because the parity count listed twenty-four
lines of python that were nowhere in the record. Keep the fuller text, put the other in `notes`.

**Bookkeeping keys are not content.** `_section` survived into that same rule and filed two section
numbers as rival wordings, so a node came out with `notes: ["2.8"]`.

**Replay the whole pipeline, not the stage you changed.** The determinism test rebuilt the
code-derived half and stopped, so four of the five stages were verified only by whoever last ran
them by hand. Every extractor change is a change to chapters already merged.

## About working

**Present the node list before the edges.** Feedback on a list is cheap. Edge work on a wrong list is
wasted twice — once building it, once unpicking it.

**One substep, then stop.** Read, declare, table, review. Merge, verify. Wire, verify. Each has an
output someone can judge; a chapter delivered whole is a chapter reviewed at the end, when the
declarations that produced it are no longer in anyone's head.
