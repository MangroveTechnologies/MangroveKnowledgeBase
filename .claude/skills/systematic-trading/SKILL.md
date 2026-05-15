---
name: systematic-trading
description: Use this skill to read or quote "An Agent's Guide to Systematic Trading" by Timothy Darrah, PhD. Trigger when the user asks about systematic trading, technical indicators (RSI, MACD, ADX, Bollinger Bands, etc.), trading signals, chart patterns, strategy archetypes (trend following, momentum, mean reversion, breakout, carry), backtesting, walk-forward optimization, risk management (position sizing, stop-loss, Kelly criterion, risk of ruin), market microstructure, order types, slippage, futures, options Greeks, perpetual swaps, quantitative trading methods (GARCH, cointegration, pairs trading, seasonality), or when the user asks "what does the book say about X". Do not trigger for general finance questions unrelated to systematic trading methodology.
---

# Skill: Read "An Agent's Guide to Systematic Trading"

This skill teaches agents how to consume the book progressively: scan cheap metadata first, load specific sections only when needed. The book is large (~280 PDF pages, ~10,500 source lines of markdown) and slurping whole chapters into context is wasteful.

## When to use this skill

Trigger when the user asks about systematic trading methodology. Match against:

- Indicators: RSI, MACD, ADX, Bollinger Bands, ATR, OBV, VWAP, Ichimoku, Parabolic SAR, CCI, Williams %R, MFI, Stochastic, Keltner Channels, etc.
- Signal concepts: TRIGGER vs FILTER, signal categories (momentum, trend, volume, volatility, patterns), crossover signals, divergence, breakout, mean reversion.
- Strategy concepts: trend following, momentum, breakout, mean reversion, carry, event-driven, scalping, day trading, swing trading, position trading.
- Risk concepts: position sizing, Kelly criterion, stop-loss engineering, drawdown control, risk-reward ratios, risk of ruin, expected shortfall, VaR, portfolio risk.
- Market mechanics: microstructure, order types, market makers, HFT, liquidity, slippage, spread, price discovery, futures, options Greeks, perpetual swaps, funding rate, leverage, margin, FX.
- Quant methods: GARCH, cointegration, pairs trading, seasonality, time-series momentum, cross-sectional momentum, autocorrelation, machine learning features.
- Chart patterns: candlestick patterns (Doji, Hammer, Engulfing), Head and Shoulders, Double Top/Bottom, triangles, flags, wedges, channels.

Do NOT trigger for general personal-finance questions, equity research on specific tickers, or trading advice. This skill returns book content, not recommendations.

## Progressive disclosure: how to load the book

The book lives in two forms:

1. **Markdown source** at `knowledge-base/01-…10-*.md` in the MangroveKnowledgeBase repo. Authoritative source for both the printed book and the agent-readable form.
2. **PDF** at `book/book.pdf` (built from the same source). For human reading; do not parse for agent queries.

When the KB server is running (`http://localhost:8081` locally, `https://kb.mangrovedeveloper.ai` in prod), prefer its query API. When offline, fall back to reading the markdown directly.

### Recommended access pattern

Follow this loading order. Each step is cheap; only escalate when the prior step did not yield enough context.

**Step 1: Discover the relevant chapter.**

Read the chapter index by listing the front-matter of all 10 chapters. Each chapter file begins with a YAML block containing `slug`, `title`, `tldr`, `triggers`, `tags`, `key_concepts`. Total cost across all 10 chapters is approximately 2,000 tokens.

If the KB server is reachable:

```
kb_list_documents(limit=20)
```

Offline fallback: read lines 1, 30 of each `knowledge-base/NN-*.md` to extract front-matter.

**Step 2: Match the user's question against `triggers` and `tags`.**

Pick at most two chapters. If the question spans more, list candidate chapters with their TLDRs to the user and ask which.

**Step 3: Load the chapter-level TLDR, "When to read this", and section headings.**

If the KB server is reachable:

```
kb_get_document(slug="04-strategy-design-modeling", max_chars=2000)
```

Use the resulting outline to choose specific sections.

**Step 4: Load only the relevant section(s).**

If the KB server is reachable:

```
kb_get_sections(slug="04-strategy-design-modeling", anchors=["4.2", "4.5"], max_chars_per_section=3000)
```

Offline fallback: open the markdown file, jump to the heading by anchor (e.g., `## 4.2 Strategy Archetypes`), read that section only.

**Step 5: Follow `prerequisites` or `see_also` links only when needed.**

Each section ends with a `### See also` list. Each chapter ends with a chapter-level `## See also` and `## References`. Follow these transitively only if the current section did not answer the question.

### Special cases

- **Glossary terms.** Use `kb_glossary_lookup(term="VWAP")` for one-line definitions. Faster than loading Chapter 9 wholesale.
- **Signal lookup by name.** Use `kb_get_signal_quick_reference()` for the alphabetical index of all 223 signals. Each entry points back to the parent indicator section in Chapter 6.
- **Free-text search across the book.** Use `kb_search(q="momentum divergence", expand=true, limit=5)` when triggers and tags do not produce a clean chapter match.

## How to quote the book

When citing book content in a response, name the chapter and section explicitly:

> Per *An Agent's Guide to Systematic Trading*, Chapter 4, §4.2 (Strategy Archetypes): "Trend Following bets on regime persistence; Momentum bets on near-term acceleration. The two are commonly conflated but have different risk profiles."

Always preserve the section reference so the user can verify. Do not paraphrase formulas, mathematical rules, or risk thresholds. Quote them.

## What this skill does NOT do

- It does not give trading advice. If the user asks "should I buy X" or "what is a good entry for Y", decline and redirect to the relevant chapter.
- It does not execute signals or compute indicators. For computation, use the KB server's `evaluate_signal` and `compute_indicator` endpoints (which are x402-gated and require payment).
- It does not modify book content. If the user wants to edit a chapter, route to the MangroveKnowledgeBase repo's product owner.

## Book metadata

- **Title:** An Agent's Guide to Systematic Trading
- **Author:** Timothy Darrah, PhD
- **License:** MIT
- **Repository:** `MangroveTechnologies/MangroveKnowledgeBase`
- **Source format:** Markdown in `knowledge-base/`, with YAML front-matter and structured headings per `book/TEMPLATE.md`.
- **Print format:** LaTeX (memoir class), built from the same markdown via pandoc.
