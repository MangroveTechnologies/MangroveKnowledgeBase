# Chapter Audit Against the Progressive-Disclosure Template

Per-chapter assessment of what the existing markdown has versus what the template requires. The good news: the existing `Definition / Core Principles / Common Use Cases / Examples / Best Practices / Formulas` section pattern is highly consistent across all 8 narrative chapters and maps cleanly to the "body" portion of the section template. The work is **additive**, not a rewrite.

Legend: ✅ present, ⚠ partial, ✗ missing, n/a not applicable

| | YAML front-matter | Chapter TLDR | Triggers | Key concepts (linked) | Prereqs | Section TLDR + trigger | Section body pattern | See-also blocks | References | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **Ch.1 Market Foundations** | ✗ | ⚠ (1 sentence) | ✗ | ✗ | n/a | ✗ | ✅ | ✗ | ✗ | Clean, very consistent. Lowest-risk chapter to pilot. |
| **Ch.2 Instruments** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ✅ | ✗ | ✗ | Mirrors Ch.1 structure exactly. |
| **Ch.3 Core Concepts** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ⚠ | ✗ | ✗ | §3.0 is a discursive framing intro that doesn't follow the `Definition/Principles/...` pattern. Acceptable; treat as a chapter-opening essay. |
| **Ch.4 Strategy Design** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ✅ | ✗ | ✗ | Longest chapter (1,587 lines). Includes archetype tables and risk-profile summaries, convert to LaTeX `tabularx` / `longtable`. |
| **Ch.5 Risk Management** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ⚠ | ✗ | ✗ | §5.0 is framing essay (parallel to §3.0). Heavy table use, review for column widths. |
| **Ch.6 Indicators** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ⚠ | ✗ | ✗ | Preamble defines TRIGGER vs FILTER classification. Each indicator block deviates from the standard section pattern, has its own sub-structure (formula / API ref / related signals). Document as a Ch.6-specific template variant. |
| **Ch.7 Chart Patterns** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ✅ | ✗ | ✗ | Standard pattern. |
| **Ch.8 Quantitative Analysis** | ✗ | ⚠ | ✗ | ✗ | n/a | ✗ | ✅ | ✗ | ✗ | Standard pattern. Will need careful BibTeX work, heavy academic references expected (GARCH, cointegration, factor investing). |

## Sizes

| Chapter | Lines | Estimated PDF pages (10pt memoir, 1.2x leading) |
|---|---:|---:|
| 1 | 624 | ~18 |
| 2 | 670 | ~20 |
| 3 | 1,013 | ~30 |
| 4 | 1,587 | ~46 |
| 5 | 977 | ~28 |
| 6 | 1,763 | ~52 |
| 7 | 990 | ~28 |
| 8 | 1,168 | ~34 |
| **Body total** | **8,792** | **~256 pages** |
| 9 Glossary | 140 | ~6 |
| 10 Signals Appendix | 931 | ~20 (compact tables) |
| **Grand total** | **9,863** | **~280 pages** |

## Per-chapter restructuring effort

For each chapter, "restructure" = add YAML front-matter, write chapter-level TLDR + triggers + key-concepts list, add section-level TLDR/trigger callouts, add see-also blocks, research and add a References section.

| Chapter | Restructuring effort | Notes |
|---|---|---|
| 1 | Light | Cleanest source; ideal POC. |
| 2 | Light | Same shape as Ch.1. |
| 3 | Medium | §3.0 framing essay needs its own mini-TLDR treatment. |
| 4 | Heavy | Large; archetype tables need LaTeX styling decisions. |
| 5 | Medium | §5.0 essay; risk-dimension table is central, preserve verbatim. |
| 6 | Heavy | Per-indicator block has its own sub-template (formula/API/signals), needs a Ch.6-specific variant of the section template. |
| 7 | Light-Medium | Standard pattern, but pattern reliability data needs care. |
| 8 | Medium-Heavy | Quant chapter, needs heavy BibTeX (Engle GARCH, Engle-Granger cointegration, Jegadeesh-Titman momentum, etc.). |

## Phase 0 decisions (need approval now)

Only one Phase 0 decision is needed before Chapter 1 work begins, beyond the templates and skill themselves: confirming the references requirement.

1. **References per chapter:** zero exist today. All 8 chapters need 6 to 12 references researched, verified, and entered as BibTeX. Pre-electronic-era citations get a one-line historical context annotation per `feedback-references-historical-context`. This is the largest piece of new authoring per chapter.

## Deferred observations (revisit at the relevant chapter gate)

These are real quirks worth recording, but they belong to their own chapter or back-matter gate. Do not block Chapter 1 on them.

- **Ch.3 §3.0 and Ch.5 §5.0 are discursive framing essays.** They do not fit the strict `Definition / Core Principles / ...` body pattern. Treatment will be decided at the Ch.3 and Ch.5 gates. Likely path: keep their shape, add only a TLDR/trigger callout on top.
- **Ch.6 indicator blocks have a distinct sub-structure.** Each indicator already follows Educational / API Reference / Related Signals. Whether to formalize this as a Ch.6 variant or restructure will be decided at the Ch.6 gate.
- **Ch.4 archetype tables and Ch.5 risk-dimension tables.** Column widths and `longtable` vs `tabularx` choices will be settled at the respective chapter gates.
- **Ch.9 (Glossary) format.** Likely path: memoir `glossaries` package, agents query via `kb_glossary_lookup`. Decision deferred to the Ch.9 gate.
- **Ch.10 promoted to Appendix A (Signal Reference).** Likely path: `longtable` in the appendix, skill exposes via `kb_get_signal_quick_reference`. Decision deferred to the Appendix A gate.

## Recommended chapter order for conversion

Pilot Chapter 1 (lowest risk, cleanest source), then proceed in numerical order. Defer Ch.6 to last among the narrative chapters because its section variant adds template work.

Order: **1 → 2 → 3 → 4 → 5 → 7 → 8 → 6 → 9 (glossary) → Appendix A (signals) → front matter / polish.**
