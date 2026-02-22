"""Volume-based trading signals and return signals.

This module contains signal functions based on volume indicators and return calculations:

Volume Indicators:
- ADI (Accumulation/Distribution Index)
- OBV (On-Balance Volume)
- CMF (Chaikin Money Flow)
- Force Index
- EOM (Ease of Movement)
- VPT (Volume Price Trend)
- NVI (Negative Volume Index)
- MFI (Money Flow Index)
- VWAP (Volume Weighted Average Price)

Return Indicators:
- Daily Return
- Cumulative Return
"""

import logging

import pandas as pd

from mangrove_signals.registry import RuleRegistry

# Import volume and return indicator classes
from mangrove_signals.indicators import (
    ADI,
    OBV,
    CMF,
    ForceIndex,
    EaseOfMovement,
    VPT,
    NVI,
    MFI,
    VWAP,
    DailyReturn,
    DailyLogReturn,
    CumulativeReturn,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Volume Indicator Signals
# =============================================================================

@RuleRegistry.register("adi_bullish")
def adi_bullish(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if ADI (Accumulation/Distribution) is rising (bullish volume).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if ADI trending up, False otherwise.
    """
    if len(df) < window:
        return False

    result = ADI.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"],
    }, params={})
    adi = result['adi']

    if len(adi) < window or pd.isna(adi.iloc[-1]) or pd.isna(adi.iloc[-window]):
        return False

    return float(adi.iloc[-1]) > float(adi.iloc[-window])


@RuleRegistry.register("adi_bearish")
def adi_bearish(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if ADI (Accumulation/Distribution) is falling (bearish volume).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if ADI trending down, False otherwise.
    """
    if len(df) < window:
        return False

    result = ADI.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"],
    }, params={})
    adi = result['adi']

    if len(adi) < window or pd.isna(adi.iloc[-1]) or pd.isna(adi.iloc[-window]):
        return False

    return float(adi.iloc[-1]) < float(adi.iloc[-window])


@RuleRegistry.register("obv_bullish")
def obv_bullish(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if OBV is rising (bullish volume confirmation).

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if OBV trending up, False otherwise.
    """
    if len(df) < window:
        return False

    result = OBV.compute(data={'close': df["Close"], 'volume': df["Volume"],
    }, params={})
    obv = result['obv']

    if len(obv) < window or pd.isna(obv.iloc[-1]) or pd.isna(obv.iloc[-window]):
        return False

    return float(obv.iloc[-1]) > float(obv.iloc[-window])


@RuleRegistry.register("obv_bearish")
def obv_bearish(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if OBV is falling (bearish volume confirmation).

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if OBV trending down, False otherwise.
    """
    if len(df) < window:
        return False

    result = OBV.compute(data={'close': df["Close"], 'volume': df["Volume"],
    }, params={})
    obv = result['obv']

    if len(obv) < window or pd.isna(obv.iloc[-1]) or pd.isna(obv.iloc[-window]):
        return False

    return float(obv.iloc[-1]) < float(obv.iloc[-window])


@RuleRegistry.register("cmf_bullish")
def cmf_bullish(df: pd.DataFrame, window: int = 20, threshold: float = 0.0) -> bool:
    """
    Check if CMF (Chaikin Money Flow) indicates buying pressure.

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMF period. Range: 10-50. Default: 20.
        threshold (float): Bullish threshold. Range: -1.0-1.0. Default: 0.0.

    Returns:
        bool: True if CMF > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = CMF.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    cmf = result['cmf']

    if pd.isna(cmf.iloc[-1]):
        return False

    return float(cmf.iloc[-1]) > threshold


@RuleRegistry.register("cmf_bearish")
def cmf_bearish(df: pd.DataFrame, window: int = 20, threshold: float = 0.0) -> bool:
    """
    Check if CMF (Chaikin Money Flow) indicates selling pressure.

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMF period. Range: 10-50. Default: 20.
        threshold (float): Bearish threshold. Range: -1.0-1.0. Default: 0.0.

    Returns:
        bool: True if CMF < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = CMF.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    cmf = result['cmf']

    if pd.isna(cmf.iloc[-1]):
        return False

    return float(cmf.iloc[-1]) < threshold


@RuleRegistry.register("force_bullish")
def force_bullish(df: pd.DataFrame, window: int = 13, threshold: float = 0.0) -> bool:
    """
    Check if Force Index indicates bullish momentum.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for smoothing. Range: 5-30. Default: 13.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if Force Index > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ForceIndex.compute(data={'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    fi = result['fi']

    if pd.isna(fi.iloc[-1]):
        return False

    return float(fi.iloc[-1]) > threshold


@RuleRegistry.register("force_bearish")
def force_bearish(df: pd.DataFrame, window: int = 13, threshold: float = 0.0) -> bool:
    """
    Check if Force Index indicates bearish momentum.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for smoothing. Range: 5-30. Default: 13.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if Force Index < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = ForceIndex.compute(data={'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    fi = result['fi']

    if pd.isna(fi.iloc[-1]):
        return False

    return float(fi.iloc[-1]) < threshold


@RuleRegistry.register("eom_bullish")
def eom_bullish(df: pd.DataFrame, window: int = 14, threshold: float = 0.0) -> bool:
    """
    Check if Ease of Movement indicates bullish (easy upward movement).

    Type: FILTER
    Requires: High, Low, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EOM period. Range: 5-30. Default: 14.
        threshold (float): Bullish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if EOM > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    # IndicatorInterface-style indicators use a stateless compute() API.
    # EaseOfMovement outputs {'eom': ..., 'sma_eom': ...}; we use the raw eom series here.
    result = EaseOfMovement.compute(
        data={"high": df["High"], "low": df["Low"], "volume": df["Volume"]},
        params={"window": window},
    )
    eom = result["eom"]

    if pd.isna(eom.iloc[-1]):
        return False

    return float(eom.iloc[-1]) > threshold


@RuleRegistry.register("eom_bearish")
def eom_bearish(df: pd.DataFrame, window: int = 14, threshold: float = 0.0) -> bool:
    """
    Check if Ease of Movement indicates bearish (easy downward movement).

    Type: FILTER
    Requires: High, Low, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EOM period. Range: 5-30. Default: 14.
        threshold (float): Bearish threshold. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if EOM < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    # IndicatorInterface-style indicators use a stateless compute() API.
    result = EaseOfMovement.compute(
        data={"high": df["High"], "low": df["Low"], "volume": df["Volume"]},
        params={"window": window},
    )
    eom = result["eom"]

    if pd.isna(eom.iloc[-1]):
        return False

    return float(eom.iloc[-1]) < threshold


@RuleRegistry.register("vpt_bullish")
def vpt_bullish(df: pd.DataFrame, lookback: int = 20) -> bool:
    """
    Check if VPT (Volume Price Trend) is rising.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        lookback (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if VPT trending up, False otherwise.
    """
    if len(df) < lookback:
        return False

    result = VPT.compute(data={'close': df["Close"], 'volume': df["Volume"],
    }, params={'smoothing_factor': None, 'dropnans': False})
    vpt = result['vpt']

    if len(vpt) < lookback or pd.isna(vpt.iloc[-1]) or pd.isna(vpt.iloc[-lookback]):
        return False

    return float(vpt.iloc[-1]) > float(vpt.iloc[-lookback])


@RuleRegistry.register("vpt_bearish")
def vpt_bearish(df: pd.DataFrame, lookback: int = 20) -> bool:
    """
    Check if VPT (Volume Price Trend) is falling.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        lookback (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if VPT trending down, False otherwise.
    """
    if len(df) < lookback:
        return False

    result = VPT.compute(data={'close': df["Close"], 'volume': df["Volume"],
    }, params={'smoothing_factor': None, 'dropnans': False})
    vpt = result['vpt']

    if len(vpt) < lookback or pd.isna(vpt.iloc[-1]) or pd.isna(vpt.iloc[-lookback]):
        return False

    return float(vpt.iloc[-1]) < float(vpt.iloc[-lookback])


@RuleRegistry.register("nvi_bullish")
def nvi_bullish(df: pd.DataFrame, window: int = 255) -> bool:
    """
    Check if NVI (Negative Volume Index) indicates smart money buying.

    NVI above its moving average suggests smart money accumulation.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for signal. Range: 100-500. Default: 255.

    Returns:
        bool: True if NVI > NVI EMA, False otherwise.
    """
    if len(df) < window:
        return False

    result = NVI.compute(data={"close": df["Close"], "volume": df["Volume"]}, params={"window": window})
    nvi = result["nvi"]
    nvi_ema = result["nvi_ema"]

    if pd.isna(nvi.iloc[-1]) or pd.isna(nvi_ema.iloc[-1]):
        return False

    return float(nvi.iloc[-1]) > float(nvi_ema.iloc[-1])


@RuleRegistry.register("nvi_bearish")
def nvi_bearish(df: pd.DataFrame, window: int = 255) -> bool:
    """
    Check if NVI (Negative Volume Index) indicates smart money selling.

    NVI below its moving average suggests smart money distribution.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for signal. Range: 100-500. Default: 255.

    Returns:
        bool: True if NVI < NVI EMA, False otherwise.
    """
    if len(df) < window:
        return False

    result = NVI.compute(data={"close": df["Close"], "volume": df["Volume"]}, params={"window": window})
    nvi = result["nvi"]
    nvi_ema = result["nvi_ema"]

    if pd.isna(nvi.iloc[-1]) or pd.isna(nvi_ema.iloc[-1]):
        return False

    return float(nvi.iloc[-1]) < float(nvi_ema.iloc[-1])


@RuleRegistry.register("mfi_overbought")
def mfi_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 80.0) -> bool:
    """
    Check if MFI (Money Flow Index) indicates overbought condition.

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MFI period. Range: 5-30. Default: 14.
        threshold (float): Overbought threshold. Range: 70-95. Default: 80.0.

    Returns:
        bool: True if MFI > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = MFI.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    mfi = result['mfi']

    if pd.isna(mfi.iloc[-1]):
        return False

    return float(mfi.iloc[-1]) > threshold


@RuleRegistry.register("mfi_oversold")
def mfi_oversold(df: pd.DataFrame, window: int = 14, threshold: float = 20.0) -> bool:
    """
    Check if MFI (Money Flow Index) indicates oversold condition.

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): MFI period. Range: 5-30. Default: 14.
        threshold (float): Oversold threshold. Range: 5-30. Default: 20.0.

    Returns:
        bool: True if MFI < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = MFI.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window,
    })
    mfi = result['mfi']

    if pd.isna(mfi.iloc[-1]):
        return False

    return float(mfi.iloc[-1]) < threshold


@RuleRegistry.register("vwap_above")
def vwap_above(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if price is above VWAP (bullish bias).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): VWAP period. Range: 5-50. Default: 14.

    Returns:
        bool: True if Close > VWAP, False otherwise.
    """
    if len(df) < window:
        return False

    result = VWAP.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window})
    vwap = result['vwap']

    if pd.isna(vwap.iloc[-1]):
        return False

    return float(df["Close"].iloc[-1]) > float(vwap.iloc[-1])


@RuleRegistry.register("vwap_below")
def vwap_below(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check if price is below VWAP (bearish bias).

    Type: FILTER
    Requires: High, Low, Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): VWAP period. Range: 5-50. Default: 14.

    Returns:
        bool: True if Close < VWAP, False otherwise.
    """
    if len(df) < window:
        return False

    result = VWAP.compute(data={'high': df["High"], 'low': df["Low"], 'close': df["Close"], 'volume': df["Volume"]}, params={'window': window})
    vwap = result['vwap']

    if pd.isna(vwap.iloc[-1]):
        return False

    return float(df["Close"].iloc[-1]) < float(vwap.iloc[-1])


# =============================================================================
# Others (Return) Signals
# =============================================================================

@RuleRegistry.register("daily_return_positive")
def daily_return_positive(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """
    Check if daily return is positive.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Minimum return threshold in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if daily return > threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = DailyReturn.compute(data={'close': df["Close"]}, params={})
    dr = result['daily_return']

    if pd.isna(dr.iloc[-1]):
        return False

    return float(dr.iloc[-1]) > threshold


@RuleRegistry.register("daily_return_negative")
def daily_return_negative(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """
    Check if daily return is negative.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Maximum return threshold in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if daily return < threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = DailyReturn.compute(data={'close': df["Close"]}, params={})
    dr = result['daily_return']

    if pd.isna(dr.iloc[-1]):
        return False

    return float(dr.iloc[-1]) < threshold


@RuleRegistry.register("cumulative_return_positive")
def cumulative_return_positive(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """
    Check if cumulative return from start is positive.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Minimum cumulative return in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if cumulative return > threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = CumulativeReturn.compute(data={'close': df["Close"]}, params={})
    cr = result['cumulative_return']

    if pd.isna(cr.iloc[-1]):
        return False

    return float(cr.iloc[-1]) > threshold


@RuleRegistry.register("cumulative_return_target")
def cumulative_return_target(df: pd.DataFrame, target: float = 10.0) -> bool:
    """
    Check if cumulative return has reached target.

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        target (float): Target cumulative return in percent. Range: 1-100. Default: 10.0.

    Returns:
        bool: True if cumulative return >= target, False otherwise.
    """
    if len(df) < 2:
        return False

    result = CumulativeReturn.compute(data={'close': df["Close"]}, params={})
    cr = result['cumulative_return']

    if pd.isna(cr.iloc[-1]):
        return False

    return float(cr.iloc[-1]) >= target
