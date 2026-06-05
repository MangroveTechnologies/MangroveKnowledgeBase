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
    - onchain: smart-money flows, exchange flows, whale activity, holder concentration
"""

# Import all signal modules to trigger registration with RuleRegistry
from mangrove_kb.signals import momentum
from mangrove_kb.signals import trend
from mangrove_kb.signals import volume
from mangrove_kb.signals import volatility
from mangrove_kb.signals import patterns
from mangrove_kb.signals import onchain
