# MangroveKnowledgeBase

Open-source trading signals, technical indicators, and knowledge base for quantitative finance and algorithmic trading.

Part of the [Mangrove](https://github.com/MangroveTechnologies) ecosystem.

## What This Is

MangroveKnowledgeBase is a standalone repository providing:

- **96 trading signal functions** across momentum, trend, volume, and volatility categories (34 TRIGGER, 62 FILTER)
- **40+ technical indicator classes** with a stateless `compute()` API
- **A Knowledge Base server** (FastAPI + SQLite FTS5) serving 11 trading education documents with full-text search, synonym expansion, glossary, cross-references, and tagging
- **Self-describing metadata** -- every signal carries its type, required data columns, and parameter ranges directly in its docstring
- **A docstring parser** that extracts structured metadata from signal functions at runtime
- **A signal explorer notebook** with 7 sample OHLCV datasets for interactive signal visualization

MangroveAI consumes this package as a pip dependency (`mangrove-knowledge-base`). Signals and indicators are designed to be used by trading strategy engines, backtesting frameworks, and AI agents.

## Repository Structure

```
MangroveKnowledgeBase/
  mangrove_knowledge_base/     # Python package (pip install)
    registry.py                # RuleRegistry for signal evaluation by name
    docstring_parser.py        # Extracts structured metadata from docstrings
    signals/                   # 96 signal functions (4 categories)
      momentum.py              # RSI, Stochastic, KAMA, ROC, PPO, PVO, ...
      trend.py                 # SMA, EMA, MACD, ADX, Ichimoku, PSAR, ...
      volume.py                # OBV, CMF, MFI, VWAP, ADI, VPT, NVI, ...
      volatility.py            # Bollinger Bands, ATR, Keltner, Donchian, ...
    indicators/                # 40+ indicator classes
      momentum_indicators.py
      trend_indicators.py
      volume_indicators.py
      volatility_indicators.py
      return_indicators.py
  kb_server/                   # Knowledge Base FastAPI server
    main.py                    # FastAPI app with 13 API endpoints
    routers/                   # API and UI routes
    services/                  # Search engine, document loader, synonyms
    templates/                 # Jinja2 HTML templates
    API.md                     # Full API endpoint documentation
  knowledge-base/              # 11 trading education markdown documents
  notebooks/                   # Signal explorer notebook
  data/                        # 7 sample OHLCV datasets (BTC, ETH, SOL, ...)
  tests/                       # Docstring parser validation (27 tests)
  findings/                    # Planning docs and session notes
```

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
docker compose up -d knowledge-base
# KB server available at http://localhost:8080
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
from mangrove_knowledge_base.signals.momentum import rsi_oversold, stoch_overbought
from mangrove_knowledge_base.signals.trend import macd_bullish_cross

if rsi_oversold(df, window=14, threshold=30.0):
    print("RSI indicates oversold")

if macd_bullish_cross(df, window_fast=12, window_slow=26, window_sign=9):
    print("MACD bullish crossover detected")
```

### Using RuleRegistry

Evaluate signals by name -- useful for strategy engines:

```python
from mangrove_knowledge_base.registry import RuleRegistry
from mangrove_knowledge_base.signals import momentum, trend, volume, volatility

rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)
```

### Extracting Signal Metadata

The docstring parser extracts structured metadata from signal functions:

```python
from mangrove_knowledge_base.docstring_parser import parse_all_signals
from mangrove_knowledge_base.signals import momentum, trend, volume, volatility

metadata = parse_all_signals([momentum, trend, volume, volatility])
# Returns: {signal_name: {type, requires, params: {name: {type, min, max, default}}}}
```

### Knowledge Base Search

```bash
# Search for trading concepts
curl "http://localhost:8080/api/search?q=RSI+overbought&limit=5"

# Get a document
curl "http://localhost:8080/api/documents/6-indicators"

# Look up a glossary term
curl "http://localhost:8080/api/glossary/RSI"
```

## Signal Categories

### Momentum (26 signals)

RSI, Stochastic, Williams %R, TSI, Ultimate Oscillator, KAMA, ROC, Awesome Oscillator, Stochastic RSI, PPO, PVO

### Trend (38 signals)

SMA, EMA, WMA, MACD, ADX, Aroon, TRIX, Mass Index, Ichimoku, KST, DPO, CCI, Vortex, PSAR, STC

### Volume (22 signals)

ADI, OBV, CMF, Force Index, EOM, VPT, NVI, MFI, VWAP, Daily Return, Cumulative Return

### Volatility (10 signals)

Bollinger Bands, ATR, Keltner Channel, Donchian Channel, Ulcer Index

## Signal Types

- **FILTER** (62 signals): State-based conditions evaluated every bar (e.g., "RSI > 70")
- **TRIGGER** (34 signals): Event-based crossovers that fire once per event (e.g., "MACD crosses above signal line")

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
| Signals Quick Reference | Alphabetical index of all 96 signals |

## MangroveAI Integration

MangroveAI consumes this package via pip. It supports both external (this package) and internal (local fallback) implementations, controlled by the `USE_EXTERNAL_KB` environment variable:

- `USE_EXTERNAL_KB=false` (default): MangroveAI uses its own local signal/indicator implementations
- `USE_EXTERNAL_KB=true`: MangroveAI imports from this package

All MangroveAI code uses the same import paths regardless of mode (`from MangroveAI.domains.signals.registry import RuleRegistry`). The toggle is transparent to consuming code.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
flake8 mangrove_knowledge_base/ --max-line-length=120

# Format
black mangrove_knowledge_base/ tests/

# Start KB server locally
docker compose up -d knowledge-base
```

## License

MIT
