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
- **A knowledge graph of the library itself** -- 498 nodes, 1539 edges, queryable, shipped in the package
- **Search by words or by meaning** -- `find()` matches terms, `ask()` seeds on a semantic index
  built from the graph and follows the edges out of what it finds

Dependencies: numpy, pandas. That's it.

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

### Available Indicators (70)

| Category | Count | Examples |
|----------|-------|---------|
| Momentum | 13 | RSI, Stochastic, TSI, UltimateOscillator, KAMA, ROC, AwesomeOscillator, StochasticRSI, PPO, PVO |
| Trend | 16 | SMA, EMA, WMA, DEMA, TEMA, MACD, ADX, Aroon, TRIX, MassIndex, Ichimoku, KST, DPO, CCI, Vortex, PSAR, STC |
| Volume | 10 | ADI, OBV, CMF, ForceIndex, EOM, VPT, NVI, MFI, VWAP, DailyReturn, CumulativeReturn |
| Volatility | 4 | BollingerBands, ATR, KeltnerChannel, DonchianChannel, UlcerIndex |
| Patterns | 27 | Doji, Hammer, ShootingStar, Engulfing, Harami, MorningStar, EveningStar, PiercingLine, ThreeWhiteSoldiers, NR7, InsideBar, and more |

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

### Signal Categories (223 total)

| Category | TRIGGER | FILTER | Total |
|----------|---------|--------|-------|
| Momentum | 18 | 24 | 42 |
| Trend | 43 | 45 | 88 |
| Volume | 6 | 27 | 33 |
| Volatility | 9 | 11 | 20 |
| Patterns | 32 | 8 | 40 |
| **Total** | **108** | **115** | **223** |

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

## Pattern Signals

27 pattern indicator classes detect candlestick and multi-bar patterns:

```python
from mangrove_kb.indicators import Hammer, BullishEngulfing, MorningStar, NR7

# Hammer detection (returns 1 where detected, 0 otherwise)
result = Hammer.compute(
    data={"open": df["open"], "high": df["high"], "low": df["low"], "close": df["close"]},
    params={"wick_ratio": 2.0, "upper_wick_max": 0.1},
)
hammers = result["hammer"]  # pd.Series of 0/1

# NR7 (Narrowest Range of 7 bars)
result = NR7.compute(
    data={"high": df["high"], "low": df["low"]},
    params={"window": 7},
)
nr7_bars = result["nr7"]
```

## Ask the library about itself

`mangrove-kb` ships a knowledge graph of its own contents -- what each indicator computes, what it
consumes and produces, which signals read which of its outputs, and what part each signal plays in a
strategy. It is generated from the source, so it is exact: no ranking model, no text extraction.

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
```

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
