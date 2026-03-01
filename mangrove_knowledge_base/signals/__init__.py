"""Trading signal functions.

Signals are boolean-returning functions that evaluate market conditions
using technical indicators. Each signal is registered with the RuleRegistry
and can be evaluated by name.

Signal Categories:
    - momentum: RSI, Stochastic, Williams %R, TSI, KAMA, ROC, etc.
    - trend: SMA, EMA, MACD, ADX, Aroon, Ichimoku, PSAR, etc.
    - volume: OBV, CMF, MFI, VWAP, ADI, Force Index, etc.
    - volatility: Bollinger Bands, ATR, Keltner Channel, Donchian, etc.
    - patterns: Doji, Hammer, Engulfing, MorningStar, InsideBar, NR7, etc.
"""

# Import all signal modules to trigger registration with RuleRegistry
from mangrove_knowledge_base.signals import momentum
from mangrove_knowledge_base.signals import trend
from mangrove_knowledge_base.signals import volume
from mangrove_knowledge_base.signals import volatility
from mangrove_knowledge_base.signals import patterns
