"""mangrove-kb: Open-source trading signals and technical indicators library.

Provides a comprehensive library of trading signals and technical indicators
for quantitative finance and algorithmic trading.

Signal Categories:
    - Momentum signals (RSI, Stochastic, KAMA, ROC, Williams %R, etc.)
    - Trend signals (SMA, EMA, MACD, ADX, Aroon, Ichimoku, PSAR, etc.)
    - Volume signals (OBV, MFI, CMF, VWAP, ADI, etc.)
    - Volatility signals (Bollinger Bands, ATR, Keltner Channel, Donchian, etc.)

Indicator Categories:
    - Momentum indicators
    - Trend indicators
    - Volume indicators
    - Volatility indicators
    - Return indicators
"""

from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("mangrove-kb")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

from mangrove_kb.registry import RuleRegistry
from mangrove_kb import indicators
from mangrove_kb import signals
