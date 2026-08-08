"""Trading signal functions.

Signals are boolean-returning functions that evaluate market conditions
using technical indicators. Each signal is registered with the RuleRegistry
and can be evaluated by name.

Files are named for the ontology CLASS of the signals they hold -- the class of the indicator each
signal reads -- so a signal's location agrees with its position in the graph. Files not yet
reorganised keep their old use-case names.

Signal Categories:
    - oscillator: RSI, Stochastic, StochRSI, Williams %R, CMO, TSI, BOP, Ultimate Oscillator
    - momentum: MACD line, ROC, MOM, PPO, PVO, Awesome Oscillator
    - averaging: KAMA crossings
    - pattern: Doji, Hammer, Engulfing, MorningStar, InsideBar, NR7, etc.
    - trend: SMA, EMA, MACD, ADX, Aroon, Ichimoku, PSAR, etc.
    - volume: OBV, CMF, MFI, VWAP, ADI, Force Index, etc.
    - volatility: Bollinger Bands, ATR, Keltner Channel, Donchian, etc.
    - onchain: smart-money flows, exchange flows, whale activity, holder concentration
    - defi_pro: token-unlock pressure, perp funding regime, ETF-flow momentum,
      treasury accumulation, lending-rate spread (DeFiLlama Pro)
"""

# Import all signal modules to trigger registration with RuleRegistry
from mangrove_kb.signals import momentum
from mangrove_kb.signals import trend
from mangrove_kb.signals import volume
from mangrove_kb.signals import volatility
from mangrove_kb.signals import pattern
from mangrove_kb.signals import oscillator
from mangrove_kb.signals import averaging
from mangrove_kb.signals import onchain
from mangrove_kb.signals import defi_pro
