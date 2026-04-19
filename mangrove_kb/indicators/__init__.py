"""
Indicators domain - Technical analysis indicator library.

Provides a comprehensive library of technical analysis indicators:
- Momentum indicators (RSI, Stochastic, KAMA, ROC, WilliamsR, TSI, UltimateOscillator, etc.)
- Volatility indicators (ATR, BollingerBands, KeltnerChannel, DonchianChannel, UlcerIndex, etc.)
- Trend indicators (MACD, EMA, SMA, ADX, Aroon, Ichimoku, PSAR, TRIX, CCI, etc.)
- Volume indicators (OBV, MFI, CMF, ForceIndex, VWAP, ADI, EaseOfMovement, VPT, NVI, etc.)
- Return indicators (DailyReturn, DailyLogReturn, CumulativeReturn)
- Pattern indicators (Doji, Hammer, Engulfing, MorningStar, InsideBar, NarrowRange, etc.)

All indicators inherit from IndicatorInterface and use a stateless classmethod-based API.
"""

# Indicator interface
from .indicator_interface import IndicatorInterface

# Utilities
from .utils import true_range, get_min_max

# Momentum indicators
from .momentum_indicators import (
    RSI,
    TSI,
    UltimateOscillator,
    StochasticOscillator,
    KAMA,
    ROC,
    AwesomeOscillator,
    WilliamsR,
    StochRSI,
    PPO,
    PVO,
)

# Volatility indicators
from .volatility_indicators import (
    ATR,
    BollingerBands,
    KeltnerChannel,
    DonchianChannel,
    UlcerIndex,
)

# Trend indicators
from .trend_indicators import (
    SMA,
    EMA,
    WMA,
    DEMA,
    TEMA,
    TRIMA,
    SMMA,
    EPMA,
    HMA,
    ALMA,
    T3,
    MAMA,
    MACD,
    Aroon,
    TRIX,
    MassIndex,
    Ichimoku,
    KST,
    DPO,
    CCI,
    ADX,
    Vortex,
    PSAR,
    STC,
)

# Volume indicators
from .volume_indicators import (
    ADI,
    OBV,
    CMF,
    ForceIndex,
    EaseOfMovement,
    VPT,
    NVI,
    MFI,
    VWAP,
    VWMA,
)

# Return indicators
from .return_indicators import (
    DailyReturn,
    DailyLogReturn,
    CumulativeReturn,
)

# Pattern indicators
from .pattern_indicators import (
    Doji,
    LongLeggedDoji,
    DragonflyDoji,
    GravestoneDoji,
    Hammer,
    HangingMan,
    InvertedHammer,
    ShootingStar,
    Marubozu,
    SpinningTop,
    Engulfing,
    Harami,
    PiercingLine,
    DarkCloudCover,
    TweezerTops,
    TweezerBottoms,
    MorningStar,
    EveningStar,
    ThreeWhiteSoldiers,
    ThreeBlackCrows,
    ThreeInsideUp,
    ThreeInsideDown,
    InsideBar,
    OutsideBar,
    PinBar,
    TwoBarReversal,
    NarrowRange,
)

__all__ = [
    # Interface
    "IndicatorInterface",
    # Utilities
    "true_range",
    "get_min_max",
    # Momentum indicators
    "RSI",
    "TSI",
    "UltimateOscillator",
    "StochasticOscillator",
    "KAMA",
    "ROC",
    "AwesomeOscillator",
    "WilliamsR",
    "StochRSI",
    "PPO",
    "PVO",
    # Volatility indicators
    "ATR",
    "BollingerBands",
    "KeltnerChannel",
    "DonchianChannel",
    "UlcerIndex",
    # Trend indicators
    "SMA",
    "EMA",
    "WMA",
    "DEMA",
    "TEMA",
    "TRIMA",
    "SMMA",
    "EPMA",
    "HMA",
    "ALMA",
    "T3",
    "MAMA",
    "MACD",
    "Aroon",
    "TRIX",
    "MassIndex",
    "Ichimoku",
    "KST",
    "DPO",
    "CCI",
    "ADX",
    "Vortex",
    "PSAR",
    "STC",
    # Volume indicators
    "ADI",
    "OBV",
    "CMF",
    "ForceIndex",
    "EaseOfMovement",
    "VPT",
    "NVI",
    "MFI",
    "VWAP",
    "VWMA",
    # Return indicators
    "DailyReturn",
    "DailyLogReturn",
    "CumulativeReturn",
    # Pattern indicators
    "Doji",
    "LongLeggedDoji",
    "DragonflyDoji",
    "GravestoneDoji",
    "Hammer",
    "HangingMan",
    "InvertedHammer",
    "ShootingStar",
    "Marubozu",
    "SpinningTop",
    "Engulfing",
    "Harami",
    "PiercingLine",
    "DarkCloudCover",
    "TweezerTops",
    "TweezerBottoms",
    "MorningStar",
    "EveningStar",
    "ThreeWhiteSoldiers",
    "ThreeBlackCrows",
    "ThreeInsideUp",
    "ThreeInsideDown",
    "InsideBar",
    "OutsideBar",
    "PinBar",
    "TwoBarReversal",
    "NarrowRange",
]
