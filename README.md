# mangrove-signals

Open-source trading signals and technical indicators for quantitative finance and algorithmic trading.

Part of the [Mangrove](https://github.com/MangroveTechnologies) ecosystem.

## What This Is

`mangrove-signals` is a standalone Python library providing:

- **40+ technical indicators** across momentum, trend, volume, volatility, and return categories
- **96 trading signal functions** — boolean evaluators for market conditions (TRIGGER and FILTER types)
- **Self-describing metadata** — every signal carries its type, required data columns, and parameter ranges directly in its docstring
- **A docstring parser** that extracts structured metadata from signal functions, eliminating the need for separate JSON/YAML config files
- **A central RuleRegistry** for evaluating signals by name with parameter validation

Signals are designed to be consumed by trading strategy engines, backtesting frameworks, and AI agents.

## Installation

```bash
pip install mangrove-signals
```

Or from source:

```bash
git clone https://github.com/MangroveTechnologies/mangrove-signals.git
cd mangrove-signals
pip install -e ".[dev]"
```

## Quick Start

### Using Indicators

All indicators use a stateless `compute()` classmethod API:

```python
import pandas as pd
from mangrove_signals.indicators import RSI, MACD, BollingerBands

# RSI
result = RSI.compute(data={'close': df['Close']}, params={'window': 14})
rsi_values = result['rsi']

# MACD
result = MACD.compute(
    data={'close': df['Close']},
    params={'window_fast': 12, 'window_slow': 26, 'window_sign': 9}
)
macd_line, signal_line, histogram = result['macd'], result['signal'], result['histogram']

# Bollinger Bands
result = BollingerBands.compute(
    data={'close': df['Close']},
    params={'window': 20, 'window_dev': 2}
)
upper, middle, lower = result['upper'], result['middle'], result['lower']
```

### Using Signals

Signals are boolean functions that evaluate market conditions:

```python
from mangrove_signals.signals.momentum import rsi_oversold, stoch_overbought
from mangrove_signals.signals.trend import macd_bullish_cross, ema_crossover
from mangrove_signals.signals.volatility import bb_squeeze

# Direct function calls
if rsi_oversold(df, window=14, threshold=30.0):
    print("RSI indicates oversold")

if macd_bullish_cross(df, window_fast=12, window_slow=26, window_sign=9):
    print("MACD bullish crossover detected")
```

### Using RuleRegistry

Evaluate signals by name — useful for strategy engines:

```python
from mangrove_signals.registry import RuleRegistry
from mangrove_signals.signals import momentum, trend, volume, volatility  # triggers registration

# Evaluate by name
rule = {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30.0}}
is_oversold = RuleRegistry.evaluate(rule, df)

# List all registered signals
print(list(RuleRegistry._registry.keys()))
```

### Extracting Signal Metadata

The docstring parser extracts structured metadata from signal functions:

```python
from mangrove_signals.docstring_parser import parse_all_signals
from mangrove_signals.signals import momentum, trend, volume, volatility

metadata = parse_all_signals([momentum, trend, volume, volatility])

# Each signal's metadata includes:
# - type: "TRIGGER" or "FILTER"
# - requires: ["Close"] or ["High", "Low", "Close", "Volume"], etc.
# - params: {name: {type, description, min, max, optional, default}}
print(metadata['rsi_overbought'])
```

## Signal Categories

### Momentum (26 signals)

| Indicator | Signals | Requires |
|-----------|---------|----------|
| RSI | `rsi_overbought`, `rsi_oversold`, `rsi_cross_up`, `rsi_cross_down` | Close |
| Stochastic | `stoch_overbought`, `stoch_oversold` | High, Low, Close |
| Williams %R | `williams_r_overbought`, `williams_r_oversold` | High, Low, Close |
| TSI | `tsi_bullish`, `tsi_bearish` | Close |
| Ultimate Oscillator | `uo_overbought`, `uo_oversold` | High, Low, Close |
| KAMA | `kama_cross_up`, `kama_cross_down` | Close |
| ROC | `roc_positive`, `roc_negative`, `roc_momentum_shift` | Close |
| Awesome Oscillator | `ao_bullish`, `ao_bearish`, `ao_zero_cross` | High, Low |
| Stochastic RSI | `stochrsi_overbought`, `stochrsi_oversold` | Close |
| PPO | `ppo_bullish_cross`, `ppo_bearish_cross` | Close |
| PVO | `pvo_bullish_cross`, `pvo_bearish_cross` | Volume |

### Trend (38 signals)

| Indicator | Signals | Requires |
|-----------|---------|----------|
| SMA | `is_above_sma`, `sma_crossover`, `sma_cross_up`, `sma_cross_down` | Close |
| EMA | `ema_cross_up`, `ema_cross_down`, `ema_crossover`, `price_above_ema` | Close |
| MACD | `macd_bullish_cross`, `macd_bearish_cross`, `macd_positive` | Close |
| WMA | `wma_cross_up`, `wma_cross_down` | Close |
| ADX | `adx_strong_trend`, `adx_bullish_di` | High, Low, Close |
| Aroon | `aroon_up_trend`, `aroon_down_trend`, `aroon_crossover` | High, Low |
| TRIX | `trix_bullish`, `trix_bearish` | Close |
| Mass Index | `mass_reversal_signal` | High, Low |
| Ichimoku | `ichimoku_bullish`, `ichimoku_bearish`, `ichimoku_tk_cross` | High, Low |
| KST | `kst_bullish_cross`, `kst_bearish_cross` | Close |
| DPO | `dpo_positive`, `dpo_negative` | Close |
| CCI | `cci_overbought`, `cci_oversold` | High, Low, Close |
| Vortex | `vortex_bullish`, `vortex_bearish`, `vortex_crossover` | High, Low, Close |
| PSAR | `psar_bullish`, `psar_bearish`, `psar_reversal` | High, Low, Close |
| STC | `stc_overbought`, `stc_oversold` | Close |

### Volume (22 signals)

| Indicator | Signals | Requires |
|-----------|---------|----------|
| ADI | `adi_bullish`, `adi_bearish` | High, Low, Close, Volume |
| OBV | `obv_bullish`, `obv_bearish` | Close, Volume |
| CMF | `cmf_bullish`, `cmf_bearish` | High, Low, Close, Volume |
| Force Index | `force_bullish`, `force_bearish` | Close, Volume |
| EOM | `eom_bullish`, `eom_bearish` | High, Low, Volume |
| VPT | `vpt_bullish`, `vpt_bearish` | Close, Volume |
| NVI | `nvi_bullish`, `nvi_bearish` | Close, Volume |
| MFI | `mfi_overbought`, `mfi_oversold` | High, Low, Close, Volume |
| VWAP | `vwap_above`, `vwap_below` | High, Low, Close, Volume |
| Daily Return | `daily_return_positive`, `daily_return_negative` | Close |
| Cumulative Return | `cumulative_return_positive`, `cumulative_return_target` | Close |

### Volatility (10 signals)

| Indicator | Signals | Requires |
|-----------|---------|----------|
| Bollinger Bands | `bb_upper_breakout`, `bb_lower_breakout`, `bb_squeeze` | Close |
| ATR | `atr_high_volatility` | High, Low, Close |
| Keltner Channel | `kc_upper_breakout`, `kc_lower_breakout` | High, Low, Close |
| Donchian Channel | `dc_upper_breakout`, `dc_lower_breakout` | High, Low, Close |
| Ulcer Index | `ulcer_high_risk`, `ulcer_low_risk` | Close |

## Signal Types

- **FILTER** (64 signals): State-based conditions. True when a condition is met (e.g., "RSI > 70"). Evaluated every bar.
- **TRIGGER** (32 signals): Event-based crossovers. True only on the bar where an event occurs (e.g., "MACD crosses above signal line"). Fires once per event.

## Indicator Architecture

All indicators inherit from `IndicatorInterface` and expose a stateless `compute()` classmethod:

```python
class MyIndicator(IndicatorInterface):
    _data = ["close"]          # Required input columns
    _params = ["window"]       # Required parameters
    _outputs = ["my_value"]    # Output series names

    @classmethod
    def _compute(cls, data, params):
        # Pure computation, no side effects
        return {'my_value': pd.Series(...)}
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
flake8 mangrove_signals/ --max-line-length=120

# Format
black mangrove_signals/ tests/
```

## License

MIT
