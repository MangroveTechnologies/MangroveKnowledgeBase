# Knowledge Base Server - API Reference

Base URL: `http://localhost:8080`

---

## API Endpoints (JSON)

All API endpoints return JSON and are prefixed with `/api`.

### Status

#### `GET /api/status`

Get the current status of the knowledge base server.

**Response:**
```json
{
  "status": "healthy",
  "documents_count": 11,
  "tags_count": 42,
  "terms_registered": 85,
  "kb_path": "/kb",
  "db_path": "/app/kb_server/data/knowledge.db"
}
```

---

### Documents

#### `GET /api/documents`

List all documents in the knowledge base. Returns summaries without full content.

**Response:**
```json
{
  "total": 11,
  "documents": [
    {
      "slug": "1-market-foundations",
      "title": "Market Foundations",
      "summary": "Overview of market structure...",
      "tags": ["market-structure", "order-types"],
      "section_count": 12
    }
  ]
}
```

#### `GET /api/documents/{slug}`

Get a single document by slug, including full content and sections.

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `slug` | string | path | Document slug (e.g., `8-risk-management`) |

**Response:** Full document object with `id`, `slug`, `title`, `filename`, `summary`, `content`, `importance`, `sections[]`, and `tags[]`.

**Errors:**
- `404` - Document not found

#### `GET /api/documents/{slug}/sections`

Get the section tree for a document.

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `slug` | string | path | Document slug |

**Response:**
```json
{
  "document_slug": "8-risk-management",
  "document_title": "Risk Management",
  "sections": [
    {
      "id": 1,
      "anchor": "8-1-position-sizing",
      "title": "8.1 Position Sizing",
      "level": 2,
      "content": "...",
      "parent_anchor": null
    }
  ]
}
```

---

### Search

#### `GET /api/search`

Search the knowledge base with full-text search, synonym expansion, and tag filtering.

**Parameters:**
| Parameter | Type | Location | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | query | *required* | Search query (min 1 char) |
| `tags` | string | query | `null` | Comma-separated tags to filter by |
| `limit` | int | query | `20` | Maximum results (1-100) |
| `expand` | bool | query | `true` | Enable synonym/stem expansion |

**Response:**
```json
{
  "query": "position sizing",
  "expanded_query": null,
  "total_results": 5,
  "results": [
    {
      "document_slug": "8-risk-management",
      "document_title": "Risk Management",
      "section_anchor": "8-2-position-sizing",
      "section_title": "8.2 Position Sizing",
      "snippet": "Position sizing determines how much capital...",
      "relevance_score": 12.5,
      "match_type": "section",
      "tags": ["position-sizing", "risk-management"]
    }
  ],
  "tags_matched": ["position-sizing", "risk-management"],
  "suggestions": []
}
```

**Search Features:**
- Porter stemming (e.g., "trade" matches "trading", "trades")
- Synonym expansion (e.g., "MA" expands to include "moving average")
- BM25 relevance ranking
- Glossary results are prioritized to appear first

---

### Tags

#### `GET /api/tags`

List all tags with their document counts.

**Response:**
```json
{
  "total": 42,
  "tags": [
    {"name": "risk-management", "count": 3},
    {"name": "indicators", "count": 2}
  ]
}
```

#### `GET /api/tags/{tag_name}`

Get all documents with a specific tag.

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `tag_name` | string | path | Tag name |

**Response:**
```json
{
  "tag": "risk-management",
  "total": 3,
  "documents": [
    {
      "slug": "8-risk-management",
      "title": "Risk Management",
      "tags": ["risk-management", "position-sizing"]
    }
  ]
}
```

---

### Glossary

#### `GET /api/glossary`

Get the full glossary with all terms and backlinks.

**Response:**
```json
{
  "total": 85,
  "entries": [
    {
      "term": "VWAP",
      "abbreviation": "VWAP",
      "definition": "Volume Weighted Average Price...",
      "anchor": "vwap",
      "document_slug": "9-glossary",
      "backlinks": [],
      "related_terms": ["Volume", "Average True Range"]
    }
  ]
}
```

#### `GET /api/glossary/{term}`

Get a specific glossary term with backlinks.

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `term` | string | path | Term name (case-insensitive lookup) |

**Response:**
```json
{
  "term": "VWAP",
  "abbreviation": "VWAP",
  "definition": "Volume Weighted Average Price...",
  "anchor": "vwap",
  "document_slug": "9-glossary",
  "backlinks": [
    {
      "term": "VWAP",
      "source_document_slug": "6-indicators",
      "source_anchor": "volume-indicators",
      "source_title": "Indicators"
    }
  ]
}
```

**Errors:**
- `404` - Term not found

---

### Backlinks

#### `GET /api/backlinks/{anchor}`

Get all documents/sections that reference a specific anchor.

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `anchor` | string | path | Target anchor ID |

**Response:**
```json
{
  "target_anchor": "vwap",
  "total": 3,
  "backlinks": [
    {
      "term": "VWAP",
      "source_document_slug": "3-core-trading-concepts",
      "source_anchor": "liquidity",
      "source_title": "Core Trading Concepts"
    }
  ]
}
```

---

### Admin

#### `POST /api/reindex`

Rebuild the search index and cross-references. Use after updating knowledge base files.

**Response:**
```json
{
  "status": "success",
  "documents_indexed": 11,
  "terms_registered": 85
}
```

---

## UI Endpoints (HTML)

These endpoints return rendered HTML pages.

| Route | Method | Description |
|-------|--------|-------------|
| `GET /` | GET | Home page with Table of Contents |
| `GET /doc/{slug}` | GET | Document view with rendered markdown, cross-references, and navigation |
| `GET /search` | GET | Search page with query form and results |
| `GET /search?q={query}&tags={tags}` | GET | Search page with pre-filled query and tag filters |
| `GET /glossary` | GET | Glossary page with alphabetical term listing |
| `GET /tags/{tag_name}` | GET | Tag page showing all documents with a specific tag |

---

## Document Slugs Reference

| Slug | Content |
|------|---------|
| `0-table-of-contents` | Index with summaries and tags |
| `1-market-foundations` | Market structure, order types, participants |
| `2-instruments-market-mechanics` | Futures, options, crypto, margin |
| `3-core-trading-concepts` | Price action, liquidity, support/resistance |
| `4-strategy-design-modeling` | Trading styles, archetypes, signal types |
| `5-risk-management` | Position sizing, drawdown, risk rules |
| `6-indicators` | Technical indicators (RSI, MACD, ATR, etc.) |
| `7-chart-patterns` | Candlestick and chart patterns |
| `8-quantitative-analysis` | Statistics, backtesting, ML |
| `9-glossary` | Alphabetized term definitions |
| `10-signals-quick-reference` | All trading signals with parent indicator links |
