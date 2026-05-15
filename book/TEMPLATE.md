# Book Structure Template

This is the structural contract for *An Agent's Guide to Systematic Trading*. Every chapter and every section conforms to this template so that:

1. **AI agents** can scan TLDRs, match triggers, and load only the sections they need (progressive disclosure).
2. **Human readers** get a coherent, well-paced narrative with consistent rhythm.
3. **The KB server** (`kb_search`, `kb_get_sections`) and the **`systematic-trading` skill** can derive structured metadata from a single source of truth, the markdown itself, without sidecar files.

Source of truth: `knowledge-base/NN-chapter.md`. The LaTeX book and the skill both derive from this. No drift.

---

## Chapter-level template

Every chapter file begins with YAML front-matter, then a fixed sequence of top-level headings before the body sections.

````markdown
---
slug: 01-market-foundations
chapter: 1
title: Market Foundations
tldr: >
  How markets actually work at the mechanical level, order types, participants,
  liquidity, regimes, venues, spreads, and price discovery. Read this before any
  chapter that assumes you can "just execute a trade."
triggers:
  - "how do markets work"
  - "what is a limit order vs a market order"
  - "what is slippage"
  - "what is market microstructure"
prerequisites: []
key_concepts:
  - {term: "microstructure", section: "1.1", glossary: "market-microstructure"}
  - {term: "limit order",    section: "1.2", glossary: "limit-order"}
  - {term: "slippage",       section: "1.4", glossary: "slippage"}
estimated_read_time_min: 25
tags: [market-structure, microstructure, order-types, execution, liquidity, volatility]
---

# 1. Market Foundations

## TLDR

(50-100 words. Self-contained chapter summary. An agent should be able to decide
from this paragraph alone whether to load the rest of the chapter.)

## When to read this

(Bullet list of concrete trigger phrases. Match what an agent or human would
actually ask, not abstract topic labels.)

- If you need to choose between a market order and a limit order
- If you are estimating execution cost for a strategy
- If you need to understand why your backtest results disagree with live fills

## Key concepts

(One-line definitions, with section anchors. Mirrors the YAML `key_concepts`
list in human-readable form. Each term links to its section and to the glossary.)

- **Microstructure** (§1.1), the mechanics of order flow and price formation
- **Limit order** (§1.2), an order that fills only at a specified price or better
- ...

## Prerequisites

(Other chapters/sections that should be read first. Empty list is fine for
foundational chapters.)

None. This is a foundational chapter.

---

## 1.1 Section title

(Section body. See section-level template below.)

## 1.2 Section title

...

---

## References

(6-12 entries. Mix of seminal academic works and practitioner texts. BibTeX
keys live in `book/bib/ch01.bib` and are cited inline using `[@key]` syntax
that pandoc converts to LaTeX `\cite{}`.)

1. Harris, L. (2002). *Trading and Exchanges: Market Microstructure for Practitioners*. Oxford University Press. [@harris2002trading]
2. O'Hara, M. (1995). *Market Microstructure Theory*. Blackwell. [@ohara1995microstructure]
3. Kyle, A. S. (1985). "Continuous Auctions and Insider Trading." *Econometrica*, 53(6), 1315–1335. [@kyle1985continuous]
4. ...

## See also

- Chapter 2 (Instruments & Market Mechanics): for derivative-specific execution
- Chapter 5, §5.4 (Stop-Loss Engineering): applies the slippage concepts here
- Glossary entries: [microstructure], [VWAP], [TWAP]
````

---

## Section-level template

Every numbered section (e.g., §1.1, §3.7) opens with TLDR + trigger before
diving into the existing `Definition / Core Principles / …` body pattern.

````markdown
## 1.1 Market Microstructure

> **TLDR.** (1-2 sentences. Plain prose, no jargon if avoidable.)
>
> **When this matters.** (Single sentence. The concrete situation in which an
> agent or trader needs this section.)

### Definition

(Existing body content; minimal disruption.)

### Core Principles

...

### Common Use Cases

...

### Examples

...

### Best Practices

...

### Mathematical Rules / Formulas

(Optional. Present where applicable.)

### See also

- §1.4 Liquidity, Slippage & Market Impact (for execution cost framing)
- §3.5 Volume & Order Flow (for the analytic side)
````

The existing `Definition / Core Principles / Common Use Cases / Examples / Best Practices / Formulas` pattern is preserved as-is. It is already well-suited as the section body. The change is **additive**: a TLDR/trigger callout at the top and a `See also` list at the bottom.

---

## YAML front-matter schema

```yaml
slug: string             # filename stem, e.g. "01-market-foundations"
chapter: integer         # chapter number
title: string            # chapter title without the number prefix
tldr: multiline string   # 50-100 words, self-contained
triggers: list[string]   # natural-language phrases an agent might match
prerequisites: list[string]  # slugs of chapters/sections to read first; e.g. ["01-market-foundations", "03-core-trading-concepts#3.5"]
key_concepts:            # list of {term, section, glossary} objects
  - term: string
    section: string      # "1.1", used to anchor links
    glossary: string     # glossary entry slug
estimated_read_time_min: integer
tags: list[string]       # topic tags; reused from existing TOC
```

The schema is intentionally minimal. Anything else (references, see-also, body)
belongs in the prose, not the front-matter.

---

## Glossary, signal reference, and chapter 0

- **Chapter 0 (`00-table-of-contents.md`):** current content is tool-usage notes (`kb_get_document` examples) intended for agents calling the KB server. Drop from the book; keep the file in the repo as agent-facing infrastructure. A real TOC is auto-generated by memoir.
- **Chapter 9 (Glossary):** exported as memoir `glossaries` package entries. The skill exposes glossary lookup via `kb_glossary_lookup`. No prose template needed; it's a flat term list.
- **Chapter 10 (Signals Quick Reference):** promoted to **Appendix A: Signal Reference**. Long-table format (`longtable`). Skill exposes via `kb_get_signal_quick_reference`. No prose template needed.

---

## Voice contract for chapter prose

The book is authored under Timothy Darrah's byline. Every chapter must follow his voice contract, synthesized from his ICAART 2024 paper, his PHM Society 2022 paper, and his Vanderbilt PhD thesis. Authoritative source: `MangroveOracle/reports/tims-voice.md`.

Summary of the voice contract:

1. Open with stakes, not abstraction. The first paragraph of every chapter tells the reader what is lost if the material is not internalized.
2. Define technical terms on first use. Italicize the term, expand acronyms immediately in parens (e.g., *Volume-Weighted Average Price* (VWAP)).
3. Position against the literature explicitly. Use moves like "Typically,", "Most current research does not", "The literature lacks", "Currently, there are no". Each gap is followed by the claim that the chapter addresses it.
4. Tutorial register in technical sections. Walk the reader through methods step by step.
5. First-person plural throughout. "We demonstrate", "our approach", "we show". Active voice.
6. Enumerate contributions explicitly. Numbered or letter-tagged lists, never implicit.
7. Every chapter introduction ends with a "Chapter Organization" subsection that walks through what each section contains. Fixed move, not optional.
8. Flat section transitions. "discussed next", "as described in §X". No throat-clearing.
9. Self-citation matter-of-fact. Cite prior work and build on it without ceremony.
10. Narrate prior work in-prose. "In (Harris, 2002), the author lays out X." The cited work is the subject of a sentence, not a trailing bracket.
11. Hedge on causes, not on claims. Claims are direct. Hedging appears only when explaining *why*.
12. Bold is reserved for the one-sentence claim a section exists to deliver. At most one bold sentence per section.
13. Results presented as facts plus one sentence of interpretation. No caveats stacked in front of findings.
14. No em dashes. Use commas, colons, parentheses, or two separate sentences instead.
15. Prose targets an 8th-grade reading level (Flesch-Kincaid grade ~8.0). Technical passages (formulas, mathematical rules, indicator definitions, signal mechanics, code) stay technical when clarity requires it. The voice traits above are about structure and rhetoric; they coexist with plain vocabulary. Prefer short sentences, common words, concrete subjects, active voice. Split long sentences into two short ones. Replace Latinate words with Anglo-Saxon equivalents where the meaning is preserved.

Reference annotations for pre-electronic-era citations (roughly pre-2000) must include a one-line note situating the work in its historical market context. The book's domain spans markets that were transformed by decimalization in 2001, Reg NMS in 2007, the rise of HFT, dark pools, and the emergence of perpetual swaps and crypto. Pair foundational results (Kyle 1985, Engle 1982, etc.) with modern follow-ups where applicable.

---

## What the skill expects

The `.claude/skills/systematic-trading/` skill instructs agents to:

1. Read the chapter YAML front-matter first (cheap; ~200 tokens per chapter).
2. Match the user's question against `triggers` + `tags` to pick a chapter.
3. Read the chapter-level TLDR and section headings.
4. Use `kb_get_sections(slug, anchors)` to load only the relevant section(s).
5. Follow `prerequisites` / `see_also` links transitively only when needed.

This is the same progressive-disclosure pattern Claude Code skills use internally: small description → SKILL.md → deeper files. The book inherits it.
