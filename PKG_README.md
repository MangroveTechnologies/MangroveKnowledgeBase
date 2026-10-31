# mangrove-kb

Open-source trading signals and technical indicators for Python. Pure Python, no native dependencies.

```bash
pip install mangrove-kb
```

## What You Get

- **255 trading signals** -- boolean functions that evaluate market conditions on OHLCV DataFrames
- **85 technical indicators** -- stateless `compute()` API returning named Series
- **RuleRegistry** -- evaluate signals by name with parameter dicts (for strategy engines)
- **Docstring parser** -- extract structured metadata (type, params, ranges) from any signal at runtime
- **A knowledge graph of the library itself** -- 735 nodes, 2411 edges, queryable, shipped in the package
- **Search by words or by meaning** -- `find()` matches terms; `ask()` takes a question in ordinary
  words, seeds from two indices and follows the edges out of what it finds. On twenty-five questions
  phrased the way a trader asks them, `find()` answers 5 and `ask()` answers 18.

Dependencies: **numpy, pandas, scipy.** The graph and both search indices ship inside the wheel.

`ask()` answers on the LSA index alone. To get the second index -- the pretrained encoder, which
takes it from 13 of 25 to 18 -- install the extra:

```bash
pip install "mangrove-kb[semantic]"
```

That is `onnxruntime` + `tokenizers`, no torch: the encoder ships as an ONNX export inside the
wheel, so nothing downloads at install time or at query time either.

| | installed size | `ask()` |
|---|---|---|
| `mangrove-kb` | 285 MB | 13/25 |
| `mangrove-kb[semantic]` | 395 MB | 18/25 |
| `mangrove-kb[semantic-torch]` | 5,873 MB | 18/25 (same answers) |
| ...with CPU-only torch first | **1,438 MB** | 18/25 |

The last two rows are a fallback (`mangrove-kb[semantic-torch]`), tried only if the ONNX path
cannot load. It pulls `sentence-transformers`, and pip's default torch wheel bundles the entire
CUDA stack -- 3.4 GB of that is nvidia libraries and triton for a GPU this never uses, since the
node vectors are precomputed and the only inference is one short question per call. For CPU:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "mangrove-kb[semantic-torch]"
```

There is no `torch-cpu` on PyPI and torch publishes no extra for it, so this is an install-time
choice rather than something a dependency can declare.

## Indicators

All indicators use a stateless classmethod API. Pass data and params, get results:

```python
from mangrove_kb.indicators import RSI, MACD, BollingerBands, EMA
from mangrove_kb import sample_ohlcv

df = sample_ohlcv()  # self-contained sample data; or pd.read_csv("your_ohlcv_data.csv")

# RSI
result = RSI.compute(data={"close": df["close"]}, params={"window": 14})
rsi = result["rsi"]  # pd.Series

# MACD
result = MACD.compute(
    data={"close": df["close"]},
    params={"window_fast": 12, "window_slow": 26, "window_sign": 9},
)
macd_line = result["macd"]
signal_line = result["signal"]
histogram = result["histogram"]

# Bollinger Bands
result = BollingerBands.compute(
    data={"close": df["close"]},
    params={"window": 20, "window_dev": 2},
)
upper, middle, lower = result["hband"], result["mavg"], result["lband"]
```

### Available Indicators

**80 classes**, 71 of them modelled in the graph by what they measure:

| Class | Indicators | Signals reading them |
|----------|---------|--------|
| Momentum | 22 | 56 |
| Averaging | 18 | 55 |
| Oscillator | 12 | 34 |
| Volatility | 11 | 27 |
| Flow | 5 | 10 |
| Pattern | 3 | 40 |

The unmodelled classes are deprecated verdict indicators -- SuperTrend, PSAR, ATRTrailingStop and
the like -- whose outputs are verdicts rather than measurements; each but ATRTrailingStop has a
measurement class in the graph in its place. `kg.stats()["classes"]` is the live list.

## Signals

Signals are boolean functions. TRIGGER signals detect events (crossovers, pattern detections). FILTER signals check ongoing state (above/below thresholds).

```python
from mangrove_kb.signals.momentum import rsi_oversold, rsi_overbought
from mangrove_kb.signals.trend import macd_bullish_cross, ema_cross_up
from mangrove_kb.signals.patterns import hammer_trigger, bullish_engulfing_trigger

# Direct function calls
if rsi_oversold(df, window=14, threshold=30.0):
    print("RSI below 30 -- oversold")

if hammer_trigger(df):
    print("Hammer candlestick detected on current bar")

if macd_bullish_cross(df, window_fast=12, window_slow=26, window_sign=9):
    print("MACD crossed above signal line")
```

### Using RuleRegistry

Evaluate signals by name -- useful for strategy engines and configuration-driven systems:

```python
from mangrove_kb import RuleRegistry, sample_ohlcv
# Import signal modules to register them
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

df = sample_ohlcv()  # self-contained sample data; or bring your own DataFrame

# Evaluate by name
rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)

# List all registered signals
print(f"Available signals: {len(RuleRegistry._registry)}")
```

### Signal Categories

**255 registered**, 225 modelled in the graph. Every signal carries two independent labels: the
class it is *about* (above) and the **role** it plays -- `trigger` (an event) or `filter` (an ongoing
state). They are different questions, so the graph keeps them apart:

```python
from mangrove_kb.graph import KnowledgeGraph

KnowledgeGraph.load().find(kind="momentum", role="trigger")   # momentum-class signals, used as triggers
```

## Signal Metadata

Every signal carries its metadata in its docstring. Extract it at runtime:

```python
from mangrove_kb.docstring_parser import parse_all_signals
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

metadata = parse_all_signals([momentum, trend, volume, volatility, patterns])

# Example: inspect rsi_oversold
sig = metadata["rsi_oversold"]
print(sig["type"])        # "FILTER"
print(sig["requires"])    # ["close"]
print(sig["params"])      # {"window": {"type": "int", "min": 2, "max": 100, "default": 14}, ...}
```

## Candlesticks

Candlestick **detection** lives in the signal functions; the indicator classes supply the geometry
those signals read.

```python
from mangrove_kb.indicators import CandleGeometry
from mangrove_kb.signals.pattern import hammer_trigger, bullish_engulfing_trigger
from mangrove_kb import sample_ohlcv

df = sample_ohlcv()

# Geometry: the measurements a candlestick rule is written against
g = CandleGeometry.compute(data={k: df[k] for k in ("open", "high", "low", "close")}, params={})
g["body"], g["upper_wick"], g["lower_wick"], g["body_ratio"]

# Detection: a boolean for the current bar
hammer_trigger(df)                # True when the last bar is a hammer
bullish_engulfing_trigger(df)     # ...or engulfs the previous one
```

`CandleRaw`, `CandleGeometry` and `CandleRelation` are the three classes: raw OHLC, single-bar
geometry, and bar-to-bar relations. Ask the graph which signals read them --
`kg.neighbors("procedure:indicator-candlegeometry", relation="uses", direction="in")`.

## Ask the library about itself

`mangrove-kb` ships a knowledge graph with two halves on one schema. One is compiled from this
library's own source -- what each indicator computes, what it consumes and produces, which signals
read which of its outputs, and what part each plays in a strategy -- and is exact, because it is
read from the code rather than extracted from prose. The other is a trading knowledge base: market
structure, instruments, risk, chart patterns, quantitative method, ingested from its chapters.

They are joined, and that is the point: `procedure:atr-based-stop` is a rule the risk chapter states,
and it `uses` an indicator the code defines -- so one query crosses from advice to implementation.

```python
from mangrove_kb.graph import KnowledgeGraph

kg = KnowledgeGraph.load()          # no download, no config -- it is in the package
kg.stats()                          # counts + the full vocabulary every filter accepts

kg.find("divergence")                                # is there already a signal for this?
kg.find(kind="momentum", role="trigger")             # by what it is AND how it is used
kg.find(requires="volume", status="deprecated")      # by what it needs and whether it is current
kg.find(param="window_dev")                          # by a parameter it takes
kg.get("procedure:indicator-rsi")["outputs"]         # typed outputs, with units and range
kg.outputs(bounded=True, kind="oscillator")          # every value you could put on one axis
kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in")   # what would break
kg.path("procedure:signal-adosc-bearish", "concept:momentum")   # why is it classed so

kg.ask("how far away from my entry should the stop go")   # a QUESTION, not a term

kg.find(under="risk management", limit=None)             # 74 nodes, every primitive
kg.find(under="risk management", primitive="Judgment")   # 5 -- what to actually do about it
```

`find()` matches the words you use; `ask()` matches what you mean, then walks one hop along the
edges. Every row it returns carries `reached` -- which result it came from, how many hops, along
which relation, and that edge's own stated reason -- so an answer arrives with its grounds rather
than a score. It is the one call that loads the encoder, and it is right about three times in four:
when a result looks off-topic it usually is, and re-asking with a domain term, or falling back to
`find()`, is the move.

**Read these two before using it** -- they are installed alongside the package at
`mangrove_kb/skills/knowledge-graph/`, and readable here:

- **[SKILL.md](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/blob/main/skills/knowledge-graph/SKILL.md)** -- which call answers which question, and
  the rules of use (results are capped and say so; roles are never types)
- **[GUIDE.md](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/blob/main/skills/knowledge-graph/GUIDE.md)** -- thirteen worked tasks end to end, with real
  output and the trap in each

If you are an agent, load `SKILL.md` -- it is written for you.

### Or look at it

```bash
python -m mangrove_kb.viz > graph.html
```

One self-contained page -- no server, no build step, no network -- with the whole graph in 2D and
3D. Click a node to read what it computes; trim the view to one node's neighbors, ancestors or
descendants; follow an edge to the thing on the other end. The
**[README](https://github.com/MangroveTechnologies/MangroveKnowledgeBase#the-viewer)** walks through
every part of it.

## Data Format

All functions expect a pandas DataFrame with lowercase OHLCV columns:

```
Timestamp  open      high      low       close     volume
2024-01-01 42000.0   42500.0   41800.0   42300.0   15000.0
```

Capitalized columns are accepted too -- signals normalize OHLCV column case at the
registry boundary -- but lowercase is the canonical form, the one `sample_ohlcv()`
produces and the one the knowledge graph publishes for every node.

Required columns depend on the signal/indicator: ask the graph
(`kg.get(id)["inputs"]`, or `kg.find(requires="volume")`), or read `Requires:` in the
docstring.

## Part of the Mangrove Ecosystem

This package is part of [MangroveKnowledgeBase](https://github.com/MangroveTechnologies/MangroveKnowledgeBase) -- an open-source project built on the belief that trading knowledge is stronger when shared openly. Visit the repo to learn about our mission, explore the full knowledge base, and see how you can contribute.

**Star the repo** if you find this useful -- it helps others discover it.

## Links

- [GitHub](https://github.com/MangroveTechnologies/MangroveKnowledgeBase) -- star it, fork it, contribute
- [Documentation](https://mangrove.io/docs)
- [Mangrove](https://mangrove.ai)

## License

Free for noncommercial use under the [PolyForm Noncommercial License 1.0.0](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/blob/main/LICENSE) -- personal study, hobby projects, research, teaching, and use by charitable, educational, public-research and government organizations.

**Commercial use requires a paid license.** Using mangrove-kb in a product or service you sell, or internally in a for-profit business, needs one -- contact **support@mangrove.ai**.

Releases published before this change remain under the MIT license they shipped with.

## Offline knowledge documents

The document catalog is separate from graph node IDs and executable signal names.
It bundles the eleven reviewed knowledge-base chapters and requires no server or
semantic-search dependencies.

```python
from mangrove_kb.documents import get_document_store

store = get_document_store()
catalog = store.list_documents()
document = store.get_document("6-indicators", max_chars=2000)
print(document["content"])
print(document["truncated"], document["source"]["artifact_sha256"])
```

Use the exact `slug` returned by the catalog. Listing follows chapter order.
Omit `max_chars` for full content; accepted budgets are integers from zero through
1,000,000. `content_length` is the full character count, `returned_chars` is the
returned count, and `truncated` explicitly identifies an excerpt. Section content
uses the same document prefix, so sections cannot reveal text omitted by the budget.
Sections retain H2/H3 navigation anchors and parent references; code-block headings
are excluded and repeated anchors receive numeric suffixes.

`DocumentNotFoundError` means a valid slug is absent. `ValueError` means invalid
arguments. `DocumentUnavailableError` means the reviewed artifact cannot be read;
a missing or corrupt file never becomes a successful empty or partial catalog.
Responses contain a schema version and artifact hash. Package installations also
report their installed package version; checkout/custom sources are labeled and do
not claim an installed version. The singleton is an immutable process snapshot;
restart consumers after upgrading the package.

### Document search and glossary

`mangrove_kb.document_search.get_document_search().query("RSI", limit=5)` searches
the same reviewed documents using an in-memory FTS5 index, historical synonyms
and glossary-first ranking. `mangrove_kb.document_glossary.get_glossary_entry("RSI")`
uses exact case-insensitive matching followed by a partial match. These modules
require the packaged document artifacts and do not call the retired KB HTTP service.

These additions require a new package release. They are not available in the
backend’s existing 3.7.1 dependency. Search/glossary and cross-repository validation
are pending; earlier document-store checks do not cover these new operations.

Document searches treat input as natural-language text rather than raw FTS syntax.
Search responses include `returned` and `truncated`; `limit` is an upper bound,
and a roughly 24 KB response budget can reduce the number returned. Snippets are
limited to 500 characters. Each result carries at most 16 tags and a
`tags_truncated` flag; `tags_matched` is limited to 64 with its own truncation flag.
Use document retrieval for complete content and document tags.

### Paged document transport (contract version 2)

`DocumentStore.get_document_page(slug, max_chars=None, offset=0, full=False)`
backs the shared backend document and quick-reference tools. It defaults to 6,000
characters, caps page requests at 12,000 characters, and bounds serialized package
responses to 24 KB. `content` is the only text body; `sections` contains overlapping
section metadata with absolute `start_char`/`end_char` offsets. Document tags are
limited to 16 with `tags_truncated` indicating omission.

Continue using `next_offset` as `offset` while `has_more` is true. `max_chars=0`
returns metadata without advancing; use a positive size to continue. `truncated`
indicates that this response is not the entire document. For explicit non-chat
downloads, `full=True` returns all text and section metadata without duplication;
it cannot be combined with an offset or size and is not subject to the page budget.

This changes backend/SDK defaults from full content to paging and removes section
bodies from transport responses. The package's internal `get_document` interface
remains available for search indexing and glossary parsing.

### Overview and section views

The same `get_document_page` operation accepts `view="overview"` to return the
source summary and every section heading/anchor without document text. This view
has no content continuation and does not accept `max_chars`, `offset` or `full`.
Use it for questions about what a guide covers, without reading every page.

For a particular topic, pass `view="section", section_anchor="..."` with an exact
anchor from overview or search. A section includes its nested subsections and stops
before its next sibling. Pagination offsets and `content_length` then refer to the
selected section body; section metadata retains absolute document offsets. Unknown
anchors return not-found, never the full document. `full=True` is only available
with `view="content"`. Existing content-view defaults remain unchanged.

Both backend document tools, the SDK knowledge/document namespaces and agent HTTP
adapters forward these options to this implementation. MCP schemas come from the
backend tool signatures; reconnect clients after deploying a schema change.
