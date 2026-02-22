# mangrove-signals

Open-source trading signals and technical indicators library for quantitative finance and algorithmic trading.

## Overview

`mangrove-signals` provides a comprehensive collection of technical analysis indicators and trading signal functions. All indicators use a stateless classmethod-based API, and all signals are registered with a central `RuleRegistry` for easy evaluation by name.

## Installation

```bash
pip install mangrove-signals
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Using Indicators Directly

```python
import pandas as pd
from mangrove_signals.indicators import RSI, MACD, BollingerBands

# Compute RSI
result = RSI.compute(data={'close': df['Close']}, params={'window': 14})
rsi_values = result['rsi']

# Compute MACD
result = MACD.compute(
    data={'close': df['Close']},
    params={'window_fast': 12, 'window_slow': 26, 'window_sign': 9}
)
macd_line = result['macd']
signal_line = result['signal']
histogram = result['histogram']
```

### Using Signals via RuleRegistry

```python
import pandas as pd
from mangrove_signals import RuleRegistry

# Import signals to register them
import mangrove_signals.signals

# Evaluate a signal by name
rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)

# Or call signal functions directly
from mangrove_signals.signals.momentum import rsi_oversold
is_oversold = rsi_oversold(df, window=14, threshold=30.0)
```

## Available Indicators

### Momentum
RSI, TSI, Stochastic Oscillator, Williams %R, KAMA, ROC, Awesome Oscillator, Stochastic RSI, PPO, PVO, Ultimate Oscillator

### Trend
SMA, EMA, WMA, MACD, ADX, Aroon, TRIX, Mass Index, Ichimoku, KST, DPO, CCI, Vortex, PSAR, STC

### Volume
ADI, OBV, CMF, Force Index, Ease of Movement, VPT, NVI, MFI, VWAP

### Volatility
ATR, Bollinger Bands, Keltner Channel, Donchian Channel, Ulcer Index

### Returns
Daily Return, Daily Log Return, Cumulative Return

## Available Signals

Signals are boolean functions that evaluate market conditions. Each signal is either a **FILTER** (state-based condition) or a **TRIGGER** (event-based crossover detection).

See individual module docstrings for complete signal documentation.

## Architecture

All indicators inherit from `IndicatorInterface` and expose a single `compute()` classmethod:

```python
class MyIndicator(IndicatorInterface):
    _data = ["close"]          # Required input data
    _params = ["window"]       # Required parameters
    _outputs = ["my_value"]    # Output names

    @classmethod
    def _compute(cls, data, params):
        # Implementation
        return {'my_value': pd.Series(...)}
```

## License

MIT
