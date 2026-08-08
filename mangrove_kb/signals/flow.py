"""Flow signals.

Signals whose class is `flow` -- the class of the indicator each one reads. A flow indicator is a
running accumulation whose absolute level is an artefact of where the series begins, so these
signals read direction or position against an average, never the level itself.

The file name is the class, so a signal's location and its position in the ontology graph agree.
Registered names are unchanged; only the file moved.
"""

import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators import (
    ADI,
    CumulativeReturn,
    NVI,
    OBV,
    VPT,
)

logger = logging.getLogger(__name__)


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


@RuleRegistry.register("nvi_bearish")
def nvi_bearish(df: pd.DataFrame, window: int = 255) -> bool:
    """
    Check if NVI (Negative Volume Index) indicates smart money selling.

    NVI below its moving average suggests smart money distribution.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for signal. Range: 100-200. Default: 255.

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


@RuleRegistry.register("nvi_bullish")
def nvi_bullish(df: pd.DataFrame, window: int = 255) -> bool:
    """
    Check if NVI (Negative Volume Index) indicates smart money buying.

    NVI above its moving average suggests smart money accumulation.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for signal. Range: 100-200. Default: 255.

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


@RuleRegistry.register("vpt_bearish")
def vpt_bearish(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if VPT (Volume Price Trend) is falling.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Window for trend comparison. Range: 5-50. Default: 20.

    Returns:
        bool: True if VPT trending down, False otherwise.
    """
    if len(df) < window:
        return False

    result = VPT.compute(data={'close': df["Close"], 'volume': df["Volume"],
    }, params={'smoothing_factor': None})
    vpt = result['vpt']

    if len(vpt) < window or pd.isna(vpt.iloc[-1]) or pd.isna(vpt.iloc[-window]):
        return False

    return float(vpt.iloc[-1]) < float(vpt.iloc[-window])


@RuleRegistry.register("vpt_bullish")
def vpt_bullish(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Check if VPT (Volume Price Trend) is rising.

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Window for trend comparison. Range: 5-50. Default: 20.

    Returns:
        bool: True if VPT trending up, False otherwise.
    """
    if len(df) < window:
        return False

    result = VPT.compute(data={'close': df["Close"], 'volume': df["Volume"],
    }, params={'smoothing_factor': None})
    vpt = result['vpt']

    if len(vpt) < window or pd.isna(vpt.iloc[-1]) or pd.isna(vpt.iloc[-window]):
        return False

    return float(vpt.iloc[-1]) > float(vpt.iloc[-window])
