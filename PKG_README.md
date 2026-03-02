# mangrove-kb

Open-source trading signals and technical indicators for Python. Pure Python, no native dependencies.

```bash
pip install mangrove-kb
```

## What You Get

- **136 trading signals** -- boolean functions that evaluate market conditions on OHLCV DataFrames
- **70 technical indicators** -- stateless `compute()` API returning named Series
- **RuleRegistry** -- evaluate signals by name with parameter dicts (for strategy engines)
- **Docstring parser** -- extract structured metadata (type, params, ranges) from any signal at runtime

Dependencies: numpy, pandas. That's it.

## Indicators

All indicators use a stateless classmethod API. Pass data and params, get results:

```python
from mangrove_kb.indicators import RSI, MACD, BollingerBands, EMA
import pandas as pd

df = pd.read_csv("your_ohlcv_data.csv")

# RSI
result = RSI.compute(data={"close": df["Close"]}, params={"window": 14})
rsi = result["rsi"]  # pd.Series

# MACD
result = MACD.compute(
    data={"close": df["Close"]},
    params={"window_fast": 12, "window_slow": 26, "window_sign": 9},
)
macd_line = result["macd"]
signal_line = result["signal"]
histogram = result["histogram"]

# Bollinger Bands
result = BollingerBands.compute(
    data={"close": df["Close"]},
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
from mangrove_kb.registry import RuleRegistry
# Import signal modules to register them
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

# Evaluate by name
rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)

# List all registered signals
print(f"Available signals: {len(RuleRegistry._registry)}")
```

### Signal Categories (136 total)

| Category | TRIGGER | FILTER | Total |
|----------|---------|--------|-------|
| Momentum | 8 | 18 | 26 |
| Trend | 18 | 20 | 38 |
| Volume | 2 | 20 | 22 |
| Volatility | 6 | 4 | 10 |
| Patterns | 32 | 8 | 40 |
| **Total** | **66** | **70** | **136** |

## Signal Metadata

Every signal carries its metadata in its docstring. Extract it at runtime:

```python
from mangrove_kb.docstring_parser import parse_all_signals
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

metadata = parse_all_signals([momentum, trend, volume, volatility, patterns])

# Example: inspect rsi_oversold
sig = metadata["rsi_oversold"]
print(sig["type"])        # "FILTER"
print(sig["requires"])    # ["Close"]
print(sig["params"])      # {"window": {"type": "int", "min": 2, "max": 100, "default": 14}, ...}
```

## Pattern Signals

27 pattern indicator classes detect candlestick and multi-bar patterns:

```python
from mangrove_kb.indicators import Hammer, BullishEngulfing, MorningStar, NR7

# Hammer detection (returns 1 where detected, 0 otherwise)
result = Hammer.compute(
    data={"open": df["Open"], "high": df["High"], "low": df["Low"], "close": df["Close"]},
    params={"wick_ratio": 2.0, "upper_wick_max": 0.1},
)
hammers = result["hammer"]  # pd.Series of 0/1

# NR7 (Narrowest Range of 7 bars)
result = NR7.compute(
    data={"high": df["High"], "low": df["Low"]},
    params={"lookback": 7},
)
nr7_bars = result["nr7"]
```

## Data Format

All functions expect a pandas DataFrame with capitalized OHLCV columns:

```
Timestamp  Open      High      Low       Close     Volume
2024-01-01 42000.0   42500.0   41800.0   42300.0   15000.0
```

Required columns depend on the signal/indicator (check `Requires:` in docstrings or metadata).

## Part of the Mangrove Ecosystem

This package is part of [MangroveKnowledgeBase](https://github.com/MangroveTechnologies/MangroveKnowledgeBase) -- an open-source project built on the belief that trading knowledge is stronger when shared openly. Visit the repo to learn about our mission, explore the full knowledge base, and see how you can contribute.

**Star the repo** if you find this useful -- it helps others discover it.

## Links

- [GitHub](https://github.com/MangroveTechnologies/MangroveKnowledgeBase) -- star it, fork it, contribute
- [Documentation](https://docs.mangrovedeveloper.ai)
- [Contributing Guide](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/blob/main/CONTRIBUTING.md)
- [Mangrove](https://mangrove.ai)

## License

[MIT](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/blob/main/LICENSE) -- Use it freely. Cite it proudly. Contribute back when you can.
