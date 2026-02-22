# AI Copilot Instructions for Knowledge Base

This document provides instructions for AI agents to efficiently query the Trading Knowledge Base for relevant context.

## Starting the Knowledge Base Server

Before querying, ensure the server is running.

### Option 1: Docker (Recommended)

```bash
cd src/MangroveKnowledgeBase
docker compose up -d
```

The database auto-initializes on startup.

### Option 2: Local

```bash
cd src/MangroveKnowledgeBase
conda activate athena
python init_db.py        # First time only
python -m uvicorn MangroveKnowledgeBase.main:app --port 8080
```

## Base URL

```
http://localhost:8080
```

## Workflow

1. Receive user query
2. Identify trading concepts, terms, or topics in the query
3. Search the knowledge base for relevant content
4. Use the retrieved content as context to complete the task

---

## Critical Conceptual Guardrails

When explaining strategy concepts, do not conflate techniques, and be careful about explaining things that are 'safer' or have 'lower risk'. As an example, 
"The Trend Is Your Friend"

Trading WITH the trend (trend following) is structurally safer than trading AGAINST it (mean reversion) because:
- Trends persist longer than expected
- Counter-trend trades have asymmetric risk
- Mean reversion assumes prices will revert, but in strong trends they often don't
   

Apply this type of reasoning to concepts at large.

## API Endpoints for AI Agents

### 1. Search by Query (Primary Method)

Use full-text search to find relevant sections:

```bash
GET /api/search?q={query}&expand=true
```

**Parameters:**
- `q` - Search query (required)
- `expand` - Enable synonym expansion (default: true)
- `tags` - Filter by tags (optional, comma-separated)

**Example:**
```bash
curl "http://localhost:8080/api/search?q=position+sizing+risk+management"
```

**Response:**
```json
{
  "query": "position sizing risk management",
  "total_results": 5,
  "results": [
    {
      "document_slug": "5-risk-management",
      "document_title": "Risk Management",
      "section_anchor": "5-2-position-sizing",
      "section_title": "Position Sizing",
      "snippet": "Position sizing determines how much capital to allocate...",
      "relevance_score": 12.5,
      "match_type": "section",
      "tags": ["position-sizing", "risk-management", "kelly-criterion"]
    }
  ]
}
```

### 2. Search by Tag

Find all sections tagged with a specific topic:

```bash
GET /api/search?q=*&tags={tag}
```

**Example:**
```bash
curl "http://localhost:8080/api/search?q=*&tags=stop-loss"
```

This returns sections from the Table of Contents that have the specified tag.

### 3. Get Specific Document

Retrieve a full document with all sections:

```bash
GET /api/documents/{slug}
```

**Example:**
```bash
curl "http://localhost:8080/api/documents/5-risk-management"
```

### 4. List All Tags

Get available tags to filter searches:

```bash
GET /api/tags
```

### 5. Get Glossary Term

Search for a term definition:

```bash
GET /api/search?q={term}
```

Glossary results are automatically prioritized.

---

## Search Strategy

### Step 1: Extract Key Concepts

From the user query, identify:
- Trading terms (e.g., "stop loss", "ATR", "moving average")
- Strategy concepts (e.g., "momentum", "mean reversion", "trend following")
- Risk concepts (e.g., "position sizing", "drawdown", "skew")

### Step 2: Search

```bash
# For specific terms
curl "http://localhost:8080/api/search?q=average+true+range"

# For concepts
curl "http://localhost:8080/api/search?q=how+to+calculate+position+size"

# For topics via tags
curl "http://localhost:8080/api/search?q=*&tags=backtesting"
```

### Step 3: Use Results

From the search response, extract:
- `snippet` - Summary of the content
- `document_slug` + `section_anchor` - For deep linking
- `tags` - Related topics

If more detail is needed, fetch the full document:
```bash
curl "http://localhost:8080/api/documents/{document_slug}"
```

---

## Common Search Patterns

| User Intent | Search Query |
|-------------|--------------|
| Define a term | `?q={term}` |
| Find strategy archetype info | `?q={archetype}+strategy` or `?q=*&tags=archetypes` |
| Find trend vs momentum | `?q=trend+following+momentum` |
| Find risk profiles | `?q=*&tags=risk-profile` or `?q=skew+win+rate` |
| Find indicator docs | `?q={indicator}+indicator` |
| Find trading signals | `?q={signal_name}` or `?q=*&tags=signals` |
| Find signal types | `?q=signal+types` |
| Find risk rules | `?q=*&tags=risk-management` |
| Find entry/exit logic | `?q=*&tags=entry-logic` or `?q=*&tags=exit-logic` |
| Find backtesting info | `?q=*&tags=backtesting` |
| Find position sizing | `?q=position+sizing` |
| Find regime detection | `?q=regime+detection` |

---

## Strategy Archetypes Reference

The knowledge base now separates archetypes explicitly:

| Archetype | Core Premise | Risk Profile |
|-----------|--------------|--------------|
| **Trend Following** | Markets exhibit persistent directional regimes | Low win rate, positive skew, moderate tail risk |
| **Momentum** | Price movement exhibits short-term persistence | Moderate win rate, neutral skew |
| **Breakouts** | Volatility compression precedes expansion | Moderate win rate, positive skew |
| **Mean Reversion** | Prices revert to equilibrium | High win rate, **negative skew, high tail risk** |
| **Carry** | Earn returns from yield differentials | Very high win rate, **negative skew, high tail risk** |
| **Event-Driven** | Markets respond around discrete events | Varies by event type |

### Archetype Contraindications

| Archetype | DO NOT USE WHEN |
|-----------|-----------------|
| Trend Following | Choppy/range-bound markets |
| Momentum | End of trend / momentum divergence |
| Breakouts | Low volatility / no compression |
| Mean Reversion | **Strong directional trends** |
| Carry | Risk-off regimes / volatility spikes |

---

## Signal Types Reference

The knowledge base defines four signal types used in strategies:

| Type | Purpose | Archetype Mapping | Example |
|------|---------|-------------------|---------|
| **Entry** | Opens a new position | Momentum, Mean Reversion | `rsi_oversold`, `macd_bullish_cross` |
| **Exit** | Closes existing position | Momentum | `rsi_overbought`, `macd_bearish_cross` |
| **Filter** | Gates other signals | Trend Following | `adx_strong_trend`, `is_above_sma` |
| **Confirmation** | Validates signals | Any | `macd_positive`, `bb_squeeze` |

For signal implementation details, search the signals quick reference or indicators document.

---

## Abbreviation Support

The search engine automatically expands common trading abbreviations:

| Abbreviation | Expands To |
|--------------|------------|
| ATR | average true range |
| RSI | relative strength index |
| MACD | moving average convergence divergence |
| EMA | exponential moving average |
| SMA | simple moving average |
| VWAP | volume weighted average price |
| PnL | profit and loss |
| R:R | risk reward ratio |
| HH/HL/LH/LL | higher high, higher low, lower high, lower low |
| BOS | break of structure |
| CHoCH | change of character |
| FVG | fair value gap |

---

## Document Slugs

| Slug | Content |
|------|---------|
| `0-table-of-contents` | Index with summaries and tags |
| `1-market-foundations` | Market structure, order types, participants |
| `2-instruments-market-mechanics` | Futures, options, crypto, margin |
| `3-core-trading-concepts` | Core Market Wisdom, Price action, liquidity, support/resistance |
| `4-strategy-design-modeling` | Trading styles, archetypes (with risk profiles), signal types, entry/exit logic |
| `5-risk-management` | Risk Dimensions, Position sizing, drawdown, risk rules |
| `6-indicators` | Technical indicators (RSI, MACD, ATR, etc.) |
| `7-chart-patterns` | Candlestick and chart patterns |
| `8-quantitative-analysis` | Statistics, backtesting, ML |
| `9-glossary` | Alphabetized term definitions |
| `10-signals-quick-reference` | All trading signals with parent indicator links |

---

## Key Sections to Reference

When users ask about specific topics, these sections are most relevant:

| Topic | Document | Section |
|-------|----------|---------|
| Core market wisdom | 3-core-trading-concepts | 3.0 Core Market Wisdom |
| Win rate vs risk | 3-core-trading-concepts | 3.0 (Win Rate Is Not Risk) |
| Strategy archetypes | 4-strategy-design-modeling | 4.2 Strategy Archetypes |
| Trend vs momentum | 4-strategy-design-modeling | 4.2 (Trend Following, Momentum) |
| Risk profiles by archetype | 4-strategy-design-modeling | 4.2 (Archetype Risk Summary Table) |
| Signal types | 4-strategy-design-modeling | 4.4 Signal Types |
| Risk dimensions | 5-risk-management | 5.0 Risk Dimensions |
| Position sizing | 5-risk-management | 5.2 Position Sizing |

---

## Example: Complete Workflow

**User Query:** "What's the safest trading strategy for a beginner?"

**Agent Actions:**

1. **Recognize the trap:** User is asking about "safest" - need to address win rate vs risk distinction.

2. Search for relevant content:
```bash
curl "http://localhost:8080/api/search?q=risk+profile+archetype+win+rate+skew"
```

3. Key points from KB:
   - Win rate is NOT the same as risk
   - Mean reversion has high win rate but negative skew (dangerous)
   - Trend following has low win rate but positive skew (survivable)

4. Formulate response that:
   - Does NOT say mean reversion is "safer" because of win rate
   - Explains the distinction between win rate and risk
   - Recommends understanding skew and tail risk

---

## Tips

1. **Use specific terms** - "average true range" finds better results than "atr indicator"
2. **Combine with tags** - Add `&tags=` to narrow results by topic
3. **Check glossary first** - For term definitions, glossary results appear first
4. **Use section anchors** - Link users directly to relevant sections with `#{section_anchor}`
5. **Reference archetypes carefully** - Always include risk profile when discussing strategy types
6. **Never conflate win rate with safety** - High win rate strategies can be more dangerous
