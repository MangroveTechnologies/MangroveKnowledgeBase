# mangrove-kb

Open-source trading signals and technical indicators for Python. Pure Python, no native dependencies.

```bash
pip install mangrove-kb
```

## What You Get

- **249 trading signals** -- boolean functions that evaluate market conditions on OHLCV DataFrames
- **80 technical indicators** -- stateless `compute()` API returning named Series
- **RuleRegistry** -- evaluate signals by name with parameter dicts (for strategy engines)
- **Docstring parser** -- extract structured metadata (type, params, ranges) from any signal at runtime
- **A knowledge graph of the library itself** -- 729 nodes, 2373 edges, queryable, shipped in the package
- **Search by words or by meaning** -- `find()` matches terms; `ask()` takes a question in ordinary
  words, seeds from two indices and follows the edges out of what it finds. On twenty-five questions
  phrased the way a trader asks them, `find()` answers 5 and `ask()` answers 18.

Dependencies: **numpy, pandas, scipy.** The graph and both search indices ship inside the wheel.

`ask()` answers on the LSA index alone. To get the second index -- the pretrained encoder, which
takes it from 13 of 25 to 18 -- install the extra:

```bash
pip install "mangrove-kb[semantic]"
```

**Choose CPU or GPU when you install it**, because nothing in the package can. `sentence-transformers`
pulls torch, and pip's default torch wheel bundles the entire CUDA stack:

| | installed size | `ask()` |
|---|---|---|
| `mangrove-kb` | 373 MB | 13/25 |
| `mangrove-kb[semantic]` | 5,276 MB | 18/25 |
| ...with CPU-only torch first | **1,402 MB** | 18/25 |

3.4 GB of that is nvidia libraries and triton for a GPU this never uses -- the node vectors are
precomputed and the only inference is one short question per call, ~50 ms on a CPU. For CPU:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "mangrove-kb[semantic]"
```

There is no `torch-cpu` on PyPI and torch publishes no extra for it, so this is an install-time
choice rather than something a dependency can declare. The model itself (~90 MB) downloads on first
`ask()` and is cached thereafter.

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

The nine unmodelled classes are stateful policy rules -- SuperTrend, PSAR, ChandelierExit and the
like -- whose outputs are verdicts rather than measurements. `kg.stats()["classes"]` is the live list.

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

**249 registered**, 218 modelled in the graph. Every signal carries two independent labels: the
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
