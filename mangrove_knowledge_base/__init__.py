"""mangrove-knowledge-base: Open-source trading signals and technical indicators library.

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

__version__ = "0.1.0"

from mangrove_knowledge_base.registry import RuleRegistry
from mangrove_knowledge_base import indicators
from mangrove_knowledge_base import signals
