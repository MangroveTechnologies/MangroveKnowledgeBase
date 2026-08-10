# MangroveKnowledgeBase

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white&style=for-the-badge)](https://discord.gg/xUcn4R6zJR)
[![PyPI Downloads](https://static.pepy.tech/badge/mangrove-kb)](https://pepy.tech/projects/mangrove-kb)

Open-source trading signals, technical indicators, and knowledge base for quantitative finance and algorithmic trading.

Part of the [Mangrove](https://github.com/MangroveTechnologies) ecosystem. Questions, ideas, or want to contribute? [Join us on Discord](https://discord.gg/xUcn4R6zJR).

**If you find this useful, please star the repo** -- it helps others discover it and keeps the project growing.

## Our Mission

Mangrove is named after the mangrove tree -- an ecosystem where everything is interconnected, resilient, and thriving. In nature, mangroves protect coastlines, nurture marine life, and create conditions where diverse species flourish together.

We believe the same principle applies to trading knowledge. The best strategies, the deepest understanding of markets, and the most reliable tools don't come from hoarding information behind paywalls. They come from a community that openly shares knowledge and experience.

**MangroveKnowledgeBase is for the people, by the people.** Every signal function, every indicator implementation, and every education document in this repository exists because someone chose to share what they know. We invite you to do the same.

Whether you're a quant who can improve an RSI calculation, a trader who spots a missing candlestick pattern, or a student who wants to add to the knowledge base -- your contribution makes the whole ecosystem stronger.

## What This Is

MangroveKnowledgeBase is a standalone repository providing:

- **247 trading signal functions** (117 TRIGGER, 130 FILTER), in files named for the ontology class of the indicator each one reads: `averaging`, `momentum`, `oscillator`, `volatility`, `flow`, `pattern` -- plus `onchain` and `defi_pro`, which read provider feeds rather than price
- **70 technical indicator classes** with a stateless `compute()` API (including 27 candlestick/multi-bar pattern indicators)
- **A signal/indicator knowledge graph** -- 303 nodes and 755 edges giving every indicator a class and every signal a machine-readable formula, verified by execution against real market data
- **A unified server** with dual protocol access (REST API + MCP) serving 11 trading education documents with full-text search, signal/indicator metadata (free), and signal evaluation/indicator computation (x402 gated)
- **Self-describing metadata** -- every signal carries its type, required data columns, and parameter ranges directly in its docstring
- **A docstring parser** that extracts structured metadata from signal functions at runtime
- **A signal explorer notebook** with 7 sample OHLCV datasets for interactive signal visualization

Signals and indicators are designed to be used by trading strategy engines, backtesting frameworks, and AI agents.

## The signal/indicator ontology

Every indicator carries a **class** describing what its output tells you about its input, and every
signal in the graph carries a **formula** stating the predicate it computes. The graph lives in
`ontology/signal-indicator-ontology.json` (303 nodes, 755 edges); the design is in
`ontology/signal-indicator-ontology.md`.

It ships **inside the package**, so it is there after `pip install mangrove-kb` with no checkout and
no configuration:

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()          # finds the packaged copy; a checkout uses ontology/ instead
kg.stats()
```

Query it with `find` / `get` / `outputs` / `neighbors` / `subgraph` / `path`. Two documents explain
how, and both are installed alongside the package at `mangrove_kb/skills/knowledge-graph/`:

- **[SKILL.md](skills/knowledge-graph/SKILL.md)** -- which call answers which question, and the rules
  of use. Written for an agent to load.
- **[GUIDE.md](skills/knowledge-graph/GUIDE.md)** -- thirteen worked tasks end to end, with real output
  and the trap in each.

The seven classes: `averaging`, `momentum`, `oscillator`, `volatility`, `flow`, `pattern`,
`unclassed`. There is deliberately no `trend` class and no `volume` class -- nothing measures trend,
and volume is an input rather than a measurement. Signal files are named for the class they hold, so
a signal's location on disk agrees with its position in the graph.

**One rule governs what may be an indicator: indicators are measurements, never verdicts; signals
are verdicts.** An indicator states what it measured; deciding what that means belongs to the signal.
Applying it moved several things: `Divergence` emitted four booleans and became `SwingDelta`
(the two changes a divergence is drawn from); `TTMSqueeze` became `SqueezeDepth`; `MultiTFTrend`
became `MultiTFSlope`. In each case the measurement stayed in the indicator and the threshold moved
to the signal. The originals are kept, deprecated, and still work.

### What is NOT in the graph, and why

Of 247 registered signals, **216 are modelled**. The other 31 are accounted for:

| | n | reason |
|---|---|---|
| `onchain` + `defi_pro` | 20 | read provider feed columns, not indicator outputs, so they have no class. See [issue #109](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/109) |
| SuperTrend, PSAR, ATRTrailingStop signals | 11 | read a verdict (`direction`, flip flags), or a level defined only relative to a regime the indicator itself decided |

All 31 still register and still evaluate -- they are unmodelled, not unavailable.

### Renames are never breaking

Registered signal names are the contract, because a stored strategy holds one as a string. Where a
signal was renamed or moved, the old name still resolves and evaluates, emitting a
`DeprecationWarning`, and is kept out of the catalogue so it is not counted twice. The same applies
to the modules: `mangrove_kb.signals.volume` and `.patterns` are gone as files but still importable.


## Installation

### Python Package (signals + indicators)

```bash
pip install mangrove-kb
```

Or from source:

```bash
git clone https://github.com/MangroveTechnologies/MangroveKnowledgeBase.git
cd MangroveKnowledgeBase
pip install -e ".[dev]"
```

### Knowledge Base Server

```bash
cd MangroveKnowledgeBase
docker compose up -d mkb-knowledge-base
# KB server available at http://localhost:8081
```

## Quick Start

### Using Indicators

All indicators use a stateless `compute()` classmethod API:

```python
from mangrove_kb.indicators import RSI, MACD, BollingerBands

# RSI
result = RSI.compute(data={'close': df['close']}, params={'window': 14})
rsi_values = result['rsi']

# MACD
result = MACD.compute(
    data={'close': df['close']},
    params={'window_fast': 12, 'window_slow': 26, 'window_sign': 9}
)
macd_line, signal_line = result['macd'], result['signal']
```

### Using Signals

Signals are boolean functions that evaluate market conditions:

```python
from mangrove_kb.signals.oscillator import rsi_oversold
from mangrove_kb.signals.momentum import macd_bullish_cross
from mangrove_kb.signals.pattern import hammer_trigger

if rsi_oversold(df, window=14, threshold=30.0):
    print("RSI indicates oversold")

if hammer_trigger(df):
    print("Hammer candlestick detected")
```

### Using RuleRegistry

Evaluate signals by name -- useful for strategy engines:

```python
from mangrove_kb import RuleRegistry, sample_ohlcv
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

df = sample_ohlcv()  # self-contained sample data; or bring your own DataFrame

rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)
```

### Extracting Signal Metadata

The docstring parser extracts structured metadata from signal functions:

```python
from mangrove_kb.docstring_parser import parse_all_signals
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

metadata = parse_all_signals([momentum, trend, volume, volatility, patterns])
# Returns: {signal_name: {type, requires, params: {name: {type, min, max, default}}}}
```

### Knowledge Base Search

```bash
# Search for trading concepts
curl "http://localhost:8081/api/search?q=RSI+overbought&limit=5"

# Get a document
curl "http://localhost:8081/api/documents/6-indicators"

# Signal metadata (free)
curl "http://localhost:8081/api/signals"

# Evaluate a signal (x402 gated)
curl -X POST http://localhost:8081/api/evaluate \
  -H "Content-Type: application/json" \
  -H "X-402-Payment: proof" \
  -d '{"name":"rsi_oversold","ohlcv":{"close":[100,101,99,98]},"params":{"window":14,"threshold":30}}'
```

## Repository Structure

```
MangroveKnowledgeBase/
  mangrove_kb/     # Python package (pip install)
    registry.py                # RuleRegistry for signal evaluation by name
    docstring_parser.py        # Extracts structured metadata from docstrings
    signals/                   # 223 signal functions (5 categories)
    indicators/                # 99 indicator classes
  kb_server/                   # Unified server (REST + MCP)
    main.py                    # FastAPI + FastMCP on same port
    services/                  # Search, signals, indicators, cross-refs
    mcp/                       # 16 MCP tools
    x402/                      # Payment middleware and pricing
  knowledge-base/              # 11 trading education markdown documents
  notebooks/                   # Signal explorer + validation notebooks
  data/                        # 7 sample OHLCV datasets (BTC, ETH, SOL, ...)
  tests/                       # 87 tests (17 skipped)
```

## Signal Categories

| Category | TRIGGER | FILTER | Total | Examples |
|----------|---------|--------|-------|----------|
| Momentum | 18 | 24 | 42 | RSI, Stochastic, Williams %R, TSI, KAMA, ROC, PPO, PVO, MOM, BOP, APO, CMO |
| Trend | 43 | 45 | 88 | SMA, EMA, MACD, ADX, Aroon, Ichimoku, PSAR, Vortex, DEMA, TEMA, HMA, ALMA, T3, MAMA, SuperTrend, Alligator, HeikinAshi |
| Volume | 6 | 27 | 33 | OBV, CMF, MFI, VWAP, ADI, Force Index, NVI, VWMA, ADOSC, KVO |
| Volatility | 9 | 11 | 20 | Bollinger Bands, ATR, Keltner, Donchian, Ulcer Index, NATR, STARC Bands, ATR Trailing Stop |
| Patterns | 32 | 8 | 40 | Doji, Hammer, Engulfing, MorningStar, NR7, Inside Bar, TTM Squeeze, MA Ribbon, Divergence |
| **Total** | **108** | **115** | **223** | |

## Knowledge Base Content

11 documents covering trading fundamentals:

| Document | Content |
|----------|---------|
| Market Foundations | Market structure, microstructure, order types |
| Instruments and Market Mechanics | Futures, options, crypto derivatives |
| Core Trading Concepts | Price action, support/resistance, multi-timeframe analysis |
| Strategy Design and Modeling | Strategy archetypes, signal composition, backtesting |
| Risk Management | Position sizing, drawdown, portfolio risk |
| Indicators | All indicator and signal documentation with API reference |
| Chart Patterns | Candlestick, reversal, continuation patterns |
| Quantitative Analysis | Statistical methods, mean reversion, momentum |
| Glossary | 135 trading terms with abbreviations and cross-references |
| Signals Quick Reference | Alphabetical index of all 223 signals |

## Contributing

We actively welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add signals, indicators, and knowledge base content.

The best way to contribute:
- Add a signal or indicator you use in your own trading
- Improve the accuracy of an existing implementation
- Add educational content to the knowledge base
- Report bugs or suggest improvements via [GitHub Issues](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (102 tests)
pytest tests/ -v

# Lint
flake8 mangrove_kb/ --max-line-length=120

# Start KB server locally
docker compose up -d mkb-knowledge-base
```

## Links

- [GitHub](https://github.com/MangroveTechnologies/MangroveKnowledgeBase)
- [PyPI Package](https://pypi.org/project/mangrove-kb/)
- [Documentation](https://mangrove.io/docs)
- [Mangrove](https://mangrove.ai)

## License

[MIT](LICENSE) -- Use it freely. Cite it proudly. Contribute back when you can.
