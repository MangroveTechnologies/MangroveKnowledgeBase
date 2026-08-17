---
name: knowledge-ingest
description: >-
  Turn a knowledge-base chapter into nodes and edges in the mangrove-kb graph. This skill should be
  used when the task is to "add a chapter to the graph", "ingest the knowledge base", "turn these
  docs into nodes", "extend the ontology from the chapters", or when editing
  `ontology/chapter_to_atoms.py`, its `CHAPTERS` declarations, or
  `ontology/signal-indicator-ontology.json`. Covers the extraction pipeline, the per-chapter
  declarations, the review gates, and the failure modes that cost the most when skipped.
---

# Turn a chapter into graph

The knowledge base is eight numbered chapters plus a glossary and a quick reference, held in
`mangrove-platform-frontend-web` at `content/knowledge-base/*.md` on `origin/dev`. Each chapter
becomes nodes and edges in `ontology/signal-indicator-ontology.json`, joining the code-derived nodes
already there; a copy of each ingested chapter lands in `ontology/raw/`.

The requirement is **all the information from a chapter reaches the graph**. The merge is an
**outer join with dedupe**, never a choice between two sources: where the chapter and an authored
definition differ materially both are kept (`source_wording`, `chapter_variants`); where they say the
same thing in different words they collapse.

This file is the reference for **how a chapter is ingested**.
[`references/declarations.md`](references/declarations.md) is the reference for **which declaration
fixes what**, and [`references/lessons.md`](references/lessons.md) for **what goes wrong** — worth
reading before the first chapter rather than after.

## Contents

| Section | What it is for |
|---|---|
| [Two rules](#two-rules-that-account-for-most-of-the-cost) | The two habits that account for most of the wasted work on this task. |
| [The scaffold](#the-scaffold-and-what-is-not-a-node) | The six headings a section carries, what each becomes, and what is deliberately not a node. |
| [Procedure](#procedure) | The eight steps from an unread chapter to a committed, rendered graph. |
| [Pipeline](#pipeline) | The exact commands that rebuild the record, and the dependency that fails silently. |
| [Review gates](#review-gates) | The seven checks to run before committing a chapter, with the code for the additive check. |
| [Writing node prose](#writing-node-prose) | How authored summaries and explanations are written and merged. |
| [Additional resources](#additional-resources) | Where the declaration reference, the failure modes and the query skill live. |

## Two rules that account for most of the cost

**Read the whole chapter before writing a single declaration.** Not a skim, not the headings, not the
first section. Every extraction rule is a claim about what the document contains, and a claim made
without reading gets debugged one defect per turn against parser output. Reading a 4,000-word chapter
takes minutes; learning its contents through build failures takes a day.

**Fix a wrong parse by declaring, never by editing output.** The record is generated. An edit to
`signal-indicator-ontology.json` is erased by the next rebuild, and worse, hides that the extractor
is still wrong. Every correction belongs in `CHAPTERS[<chapter>]` or one of the global tables in
`ontology/chapter_to_atoms.py`.

**See also:** [the scaffold](#the-scaffold-and-what-is-not-a-node) ·
[failure modes](references/lessons.md)

## The scaffold, and what is not a node

Most sections carry six headings, each with a fixed meaning:

```
## N.M <Section title>
### Definition                    -> the Concept(s) the section is about
### Core Principles               -> claims about them        (one Fact node per chapter)
### Common Use Cases              -> `applications` on the subject
### Examples                      -> a taxonomy, or an illustration (declare which)
### Best Practices for Traders    -> what to do about them    (one Judgment node per chapter)
### Mathematical Rules/Formulas   -> Property / Procedure / Fact nodes
```

Not nodes: a heading, a worked example with figures in it, and any claim *about* a thing —
"Liquidity is Dynamic" is something true of liquidity, not a second thing beside it. Core Principles
and Best Practices are each **one** node holding the whole list, not one node per bullet: a bullet
has no name to slug, and naming fifty of them means inventing fifty interpretations.

A chapter is free to break this shape, and every later one does. What has turned up so far, and
what reads it — **check for these at step 1**, because each was found by a build that had already
dropped something:

| shape | first seen | read by |
|---|---|---|
| a section with no `### Definition` | §3.0 | `blocks_as_nodes`, or the build refuses |
| `**Label:**` sub-blocks under a heading | §4.5 | `labelled_nodes` |
| a code fence where a formula block belongs | §4.6 | the docstring becomes the summary, the code the `formula` |
| a different label for the definition | §4.2 | `definition_labels` |
| `#### ` sub-blocks, one scaffold per thing | §6.1.1 | `sub_blocks`, mapping each to a prop or to dropped |
| numbered headings (`### 6.1.1 Simple Moving Average`) | §6.1.1 | stripped before the id is made |
| an unnumbered `## ` section | §6.0 | kept as prose on the chapter |
| a section whose categories contradict the library's | §6.1 | `sections_group_only` |
| `#### ` sub-blocks that are things, not fields | §7.1 | `sub_block_nodes` |
| one block describing a bullish and a bearish form | §7.1 | a dict value in `sub_block_nodes`, splitting it |
| a source whose summaries are better than the chapter's | §7.1 | `keep_summaries` |

Blocks matching no rule are kept on the section's subject under their own name rather than dropped,
and a section with no `### Definition` must declare what its blocks are or the build refuses. Whatever a section says **before** its first
`###`, and whatever its chapter's Summary says outside the numbered list, are kept as `notes` — both
were being dropped, and both carry the thesis in at least one chapter.

Everything emitted is `status: draft`. Promotion is a human act.

**See also:** [declarations](references/declarations.md) · [procedure](#procedure)

## Procedure

**`chapter_to_atoms.py` creates every node. You create none.** Step 4 builds them in memory and
prints them; step 6 is the only one that writes them to a file. Everything hand-written goes into
two places — the `CHAPTERS` declarations and `AUTHORED` prose in `ontology/chapter_to_atoms.py`, and
an anchor page in `ontology/wiki/`. Each step below names the command it runs and what that produces.

1. **Fetch and read the chapter.** `git show origin/dev:content/knowledge-base/<file>.md`. Read it
   end to end. Note which `### Examples` blocks list real kinds rather than worked arithmetic; which
   formulas are quantities, rules or identities; which terms the graph already holds under another
   name; which sections break the scaffold.
   *Produces:* a copy at `ontology/raw/<nn>-<chapter-id>.md`, which is what the replay reads.
2. **Check the chapter has an anchor, and author one only if it does not.** `--parent` names the
   node the chapter hangs off, and it comes from one of two places. Where the library computes the
   subject, the **code builder** creates it and tags it with the chapter —
   `concept:indicator` and `concept:technical-analysis` carry `reference_chapter=[CH_INDICATORS]`,
   so chapter 6 hangs off `concept:indicator` and needs nothing authored. Where nothing in the
   library computes it — market foundations, risk management — a page in `ontology/wiki/` supplies
   it: `kind: concept`, `chapter: <chapter-id>`, a Summary, an Explanation, and `## Part of` →
   `[[Mangrove Knowledge Space]]`; copy `Risk Management.md`. A page is created by the wiki stage,
   so authoring one means **the whole pipeline reruns**, not just the chapter merge.
   `tests/test_chapter_replay_is_reproducible.py` fails if a chapter hangs off an anchor that
   nothing authors.
   *You write:* a markdown page, or nothing. *Produces:* a node, once the wiki stage runs.
3. **Declare.** Add the chapter's entry to `CHAPTERS`. A chapter with no entry raises rather than
   building — building without one emits a graph with no taxonomy and says nothing about it.
   *You write:* a dict literal in `chapter_to_atoms.py`. *Produces:* nothing yet.
4. **Dry-run and stop.** `--table` prints the node list without merging. Review it, and get it
   reviewed. Feedback on a list is cheap; edge work on a wrong list is wasted.
   *Runs:* `chapter_to_atoms.py <raw> --chapter-id <id> --parent <anchor> --ontology <record>
   --table`. *Produces:* the node list on stdout. **Nothing is written.**
5. **Correct through declarations** until the table reads as intended. Boilerplate summaries
   (`The quantity X.`), a worked example standing where a definition belongs, an id like
   `procedure:fvg-fill-statu`, a formula attached to the wrong subject — each has a declaration.
   *You write:* more declarations. *Produces:* a better step 4. Never edit the record.
6. **Merge** with `--merge`, then verify the merge is additive.
   *Runs:* the same command plus `--merge --out build/ch<n>.json`. *Produces:* **the nodes, in a
   file** — the previous record plus this chapter. The record itself is untouched until step 8.
7. **Wire the statements.** The builder resolves every statement that names its node and prints
   what it drew, what it would not draw on one ordinary word, and what it could not place. Read
   that split; declare the residue, the candidates you accept and any wrong pick in `wired`. Both
   lists empty means the chapter is fully connected.
   *Runs:* step 6 again after each edit. *Produces:* edges in place of list entries.
8. **Close the gaps, rebuild the index, then commit.** No node reachable by a single edge, or a
   plain statement of why none exists; rerun `build_semantic_index.py` so retrieval follows the
   graph; update the documented counts; run the suite, commit, re-render, watch CI to green.
   *Runs:* `cp build/ch<n>.json ontology/signal-indicator-ontology.json`, then
   `PYTHONPATH=$PWD python3 ontology/build_semantic_index.py`, `python3 -m pytest tests/ -q`,
   `python3 -m mangrove_kb.viz > <served>/index.html`. *Produces:* the shipped record, the index
   beside it, and the rendered page.

**See also:** [pipeline](#pipeline) · [review gates](#review-gates) ·
[declarations](references/declarations.md)

## Pipeline

Three stages plus one per ingested chapter, each writing to `build/` and copied over the record only
after the diff is checked:

```bash
ONTOLOGY_OUT=build/code.json python3 ontology/build_signal_indicator_ontology.py
python3 -m wiki_to_graph build ontology/wiki -o build/wiki.json \
        --map ontology/wiki-config/map.json --vocab ontology/wiki-config/vocab.json \
        --dag-edges part-of,kind-of,instance-of,supersedes
python3 ontology/wiki_to_atoms.py --wiki ontology/wiki --graph build/wiki.json \
        --ontology build/code.json --out build/r1.json
python3 ontology/chapter_to_atoms.py ontology/raw/01-market-foundations.md \
        --chapter-id market-foundations --parent concept:market-foundations \
        --ontology build/r1.json --merge --out build/ch1.json
# one invocation per chapter, each taking the previous output as --ontology:
#   02 instruments-market-mechanics -> concept:market-mechanics
#   03 core-trading-concepts        -> concept:price-action
#   04 strategy-design              -> concept:strategy-design
cp build/<last>.json ontology/signal-indicator-ontology.json
PYTHONPATH=$PWD python3 ontology/build_semantic_index.py   # the graph changed; the index follows
```

The chain reruns **from the top** whenever a wiki page changes, which includes authoring a new
chapter anchor. `PYTHONPATH` matters for the index build: run as a script, `ontology/` leads
`sys.path` and `import mangrove_kb` resolves to the installed copy in site-packages rather than the
one in the tree.

`build_signal_indicator_ontology.py` writes the code-derived nodes from the library's docstrings and
is authoritative — nothing downstream may overwrite what it wrote. `wiki-to-graph` is a **dev
dependency pinned to a commit** in `pyproject.toml`; the published release lacks `--vocab`, without
which the build silently produces a graph in which every node reports degree 0.

`--parent` is the chapter's subject-area node (`concept:market-foundations`,
`concept:market-mechanics`, `concept:price-action`, …). Those six anchors are authored in
`ontology/wiki/` and exist before any chapter lands.

**See also:** [review gates](#review-gates) · [procedure](#procedure)

## Review gates

Run all seven before committing a chapter.

**Additive.** Only declared folds may touch an existing atom, and no edge may disappear:

```python
import json
old = json.load(open('ontology/signal-indicator-ontology.json'))
new = json.load(open('build/record.json'))
o = {a['id']: a for a in old['atoms']}; n = {a['id']: a for a in new['atoms']}
print('removed', set(o) - set(n), '| modified', [i for i in o if o[i] != n[i]])
ro = {(r['from_id'], r['rel'], r['to_id']) for r in old['relations']}
print('edges removed', ro - {(r['from_id'], r['rel'], r['to_id']) for r in new['relations']})
```

**Degree.** Count edges per node. A node with one is reachable by walking down from its parent and by
no other question — give it the edge the chapter states and never draws, or say plainly why none
exists.

**Statement lists.** `props.principles` and `props.practices` on the chapter's Fact and Judgment
nodes are the progress measure. Empty means the chapter is fully connected.

**The index follows the graph.** `python3 ontology/build_semantic_index.py` after every merge.
`tests/test_semantic.py` compares its checksum against the committed graph, so a chapter merged
without it fails rather than answering yesterday's questions.

**Retrievable.** Pick a term the chapter states **only** in a field it introduced — a comparison
table, a caution, a heading no earlier chapter had — and check `kg.find(term)` returns the node that
holds it. Landing in the record and answering a question are different things, and a chapter can do
the first without the second.

**Parity.** Count how many of the chapter's content lines reach the record, and quote the number.
Six gates passed while four kinds of content were being dropped -- an authored explanation
overwriting the chapter's bullets, a displaced summary falling on the floor, the closing blockquote,
the name of every practice -- and one line-coverage measurement found all four:

```python
raw = pathlib.Path('ontology/raw/<chapter>.md').read_text()
hay = re.sub(r'[^a-z0-9]+', ' ', json.dumps(json.load(open(RECORD))).lower())
for line in raw.split('---', 2)[2].splitlines():
    t = re.sub(r'[^a-z0-9]+', ' ', line.strip().lower()).strip()
    if len(t) >= 12 and not line.strip().startswith(('#', '---', '```')) and t not in hay:
        print('absent:', line)
```

Expect the low nineties: a table row is stored as separate props, a `**Label:**` line keeps its
content and drops the label, and a numbered item loses its number. **Read every absence and say
which kind it is** -- the number alone proves nothing, and the four defects above were hiding among
exactly these.

**Counts and tests.** `python3 -m pytest tests/ -q`. `test_documented_counts.py` pins every node and
edge count quoted in prose; `test_prose_is_not_glued.py` catches wrapped sentences that lost their
spaces; `test_doc_derived_atoms.py` catches document numbering leaking into the graph; `test_chapter_replay_is_reproducible.py` replays the whole pipeline and compares it to the committed record, so an extractor change that quietly alters an earlier chapter fails here rather than in a diff nobody ran.

**See also:** [failure modes](references/lessons.md) · [writing node prose](#writing-node-prose)

## Writing node prose

Authored summaries and explanations go in the `AUTHORED` table, keyed by node id, as
`(summary, explanation)`. The summary says **what the thing is**; the explanation says **why it
matters and what it connects to**, with `[[Wiki Links]]` naming other nodes.

Where the chapter states a real definition it stays as the summary and the authored one is kept
beside it; where the chapter offers only a worked example ("AAPL Call, Strike $180"), the authored
text becomes the summary and the example moves to `examples`. Neither is discarded.

Write each wrapped line with a **trailing space**. Adjacent string literals concatenate with nothing
between them, and a sentence wrapped without it reads "the spreadactually paid" in the published
graph.

**See also:** [declarations · AUTHORED](references/declarations.md) · [review gates](#review-gates)

## Additional resources

- **[`references/declarations.md`](references/declarations.md)** — every declaration key, what it
  does, an example, and the defect it exists to prevent.
- **[`references/lessons.md`](references/lessons.md)** — the failure modes, each with the rule it
  produced.
- **[`../../docs/architecture/README.md`](../../docs/architecture/README.md)** — the build
  pipeline, the node and edge schema and the retrieval machinery, drawn.
- **[`../knowledge-graph/SKILL.md`](../knowledge-graph/SKILL.md)** — querying the result: `find`,
  `under`, `neighbors`, `path`, `all_paths`.

**See also:** [procedure](#procedure) · [two rules](#two-rules-that-account-for-most-of-the-cost)
