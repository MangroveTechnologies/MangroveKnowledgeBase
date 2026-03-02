# MangroveKnowledgeBase

Open-source trading signals, technical indicators, and knowledge base for quantitative finance and algorithmic trading.

Part of the [Mangrove](https://github.com/MangroveTechnologies) ecosystem.

**If you find this useful, please star the repo** -- it helps others discover it and keeps the project growing.

## Our Mission

Mangrove is named after the mangrove tree -- an ecosystem where everything is interconnected, resilient, and thriving. In nature, mangroves protect coastlines, nurture marine life, and create conditions where diverse species flourish together.

We believe the same principle applies to trading knowledge. The best strategies, the deepest understanding of markets, and the most reliable tools don't come from hoarding information behind paywalls. They come from a community that openly shares knowledge and experience.

**MangroveKnowledgeBase is for the people, by the people.** Every signal function, every indicator implementation, and every education document in this repository exists because someone chose to share what they know. We invite you to do the same.

Whether you're a quant who can improve an RSI calculation, a trader who spots a missing candlestick pattern, or a student who wants to add to the knowledge base -- your contribution makes the whole ecosystem stronger.

## What This Is

MangroveKnowledgeBase is a standalone repository providing:

- **136 trading signal functions** across momentum, trend, volume, volatility, and pattern categories (66 TRIGGER, 70 FILTER)
- **70 technical indicator classes** with a stateless `compute()` API (including 27 candlestick/multi-bar pattern indicators)
- **A unified server** with dual protocol access (REST API + MCP) serving 11 trading education documents with full-text search, signal/indicator metadata (free), and signal evaluation/indicator computation (x402 gated)
- **Self-describing metadata** -- every signal carries its type, required data columns, and parameter ranges directly in its docstring
- **A docstring parser** that extracts structured metadata from signal functions at runtime
- **A signal explorer notebook** with 7 sample OHLCV datasets for interactive signal visualization

Signals and indicators are designed to be used by trading strategy engines, backtesting frameworks, and AI agents.

## Installation

### Python Package (signals + indicators)

```bash
pip install mangrove-knowledge-base
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
from mangrove_knowledge_base.indicators import RSI, MACD, BollingerBands

# RSI
result = RSI.compute(data={'close': df['Close']}, params={'window': 14})
rsi_values = result['rsi']

# MACD
result = MACD.compute(
    data={'close': df['Close']},
    params={'window_fast': 12, 'window_slow': 26, 'window_sign': 9}
)
macd_line, signal_line = result['macd'], result['signal']
```

### Using Signals

Signals are boolean functions that evaluate market conditions:

```python
from mangrove_knowledge_base.signals.momentum import rsi_oversold
from mangrove_knowledge_base.signals.trend import macd_bullish_cross
from mangrove_knowledge_base.signals.patterns import hammer_trigger

if rsi_oversold(df, window=14, threshold=30.0):
    print("RSI indicates oversold")

if hammer_trigger(df):
    print("Hammer candlestick detected")
```

### Using RuleRegistry

Evaluate signals by name -- useful for strategy engines:

```python
from mangrove_knowledge_base.registry import RuleRegistry
from mangrove_knowledge_base.signals import momentum, trend, volume, volatility, patterns

rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)
```

### Extracting Signal Metadata

The docstring parser extracts structured metadata from signal functions:

```python
from mangrove_knowledge_base.docstring_parser import parse_all_signals
from mangrove_knowledge_base.signals import momentum, trend, volume, volatility, patterns

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
  -d '{"name":"rsi_oversold","ohlcv":{"Close":[100,101,99,98]},"params":{"window":14,"threshold":30}}'
```

## Repository Structure

```
MangroveKnowledgeBase/
  mangrove_knowledge_base/     # Python package (pip install)
    registry.py                # RuleRegistry for signal evaluation by name
    docstring_parser.py        # Extracts structured metadata from docstrings
    signals/                   # 136 signal functions (5 categories)
    indicators/                # 70 indicator classes
  kb_server/                   # Unified server (REST + MCP)
    main.py                    # FastAPI + FastMCP on same port
    services/                  # Search, signals, indicators, cross-refs
    mcp/                       # 16 MCP tools
    x402/                      # Payment middleware and pricing
  knowledge-base/              # 11 trading education markdown documents
  notebooks/                   # Signal explorer + validation notebooks
  data/                        # 7 sample OHLCV datasets (BTC, ETH, SOL, ...)
  tests/                       # 102 tests
```

## Signal Categories

| Category | TRIGGER | FILTER | Total | Examples |
|----------|---------|--------|-------|----------|
| Momentum | 8 | 18 | 26 | RSI, Stochastic, Williams %R, TSI, KAMA, ROC, PPO, PVO |
| Trend | 18 | 20 | 38 | SMA, EMA, MACD, ADX, Aroon, Ichimoku, PSAR, Vortex |
| Volume | 2 | 20 | 22 | OBV, CMF, MFI, VWAP, ADI, Force Index, NVI |
| Volatility | 6 | 4 | 10 | Bollinger Bands, ATR, Keltner, Donchian, Ulcer Index |
| Patterns | 32 | 8 | 40 | Doji, Hammer, Engulfing, MorningStar, NR7, Inside Bar |
| **Total** | **66** | **70** | **136** | |

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
| Signals Quick Reference | Alphabetical index of all 136 signals |

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
flake8 mangrove_knowledge_base/ --max-line-length=120

# Start KB server locally
docker compose up -d mkb-knowledge-base
```

## Links

- [GitHub](https://github.com/MangroveTechnologies/MangroveKnowledgeBase)
- [PyPI Package](https://pypi.org/project/mangrove-knowledge-base/)
- [Documentation](https://docs.mangrovedeveloper.ai)
- [Mangrove](https://mangrove.ai)

## License

[MIT](LICENSE) -- Use it freely. Cite it proudly. Contribute back when you can.
