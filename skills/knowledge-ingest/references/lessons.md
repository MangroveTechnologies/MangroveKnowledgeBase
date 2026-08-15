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

## About the merge

**Measure lossiness; do not assert it.** A transform claimed to be clean was dropping sixteen
formulas, sixteen typed I/O blocks, ten worked examples and nine use-case lists. Count what went in
and what came out, per kind of content, before saying anything about fidelity.

**Outer join with dedupe, never a choice.** Two sources describing the same node contribute both
statements: materially different wordings sit side by side (`source_wording`, `chapter_variants`),
near-identical ones collapse. Choosing between them destroys information no reviewer asked to lose.

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

## About working

**Present the node list before the edges.** Feedback on a list is cheap. Edge work on a wrong list is
wasted twice — once building it, once unpicking it.

**One substep, then stop.** Read, declare, table, review. Merge, verify. Wire, verify. Each has an
output someone can judge; a chapter delivered whole is a chapter reviewed at the end, when the
declarations that produced it are no longer in anyone's head.
