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
    """Signal: adi_bearish

    Check if ADI (Accumulation/Distribution) is falling (bearish volume).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/accumulation-distribution-line
    Warmup: window - 1

    Formula:
        adi[t] < adi[t-window+1] -- a fall over the window; the level itself is meaningless

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=5, max=50]: Lookback for trend

    Outputs:
        fired [boolean, 0..1]:
            True if ADI trending down, False otherwise

    Type: FILTER
    Requires: high, low, close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if ADI trending down, False otherwise.
    """
    if len(df) < window:
        return False

    result = ADI.compute(data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"],
    }, params={})
    adi = result['adi']

    if len(adi) < window or pd.isna(adi.iloc[-1]) or pd.isna(adi.iloc[-window]):
        return False

    return float(adi.iloc[-1]) < float(adi.iloc[-window])


@RuleRegistry.register("adi_bullish")
def adi_bullish(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: adi_bullish

    Check if ADI (Accumulation/Distribution) is rising (bullish volume).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/accumulation-distribution-line
    Warmup: window - 1

    Formula:
        adi[t] > adi[t-window+1] -- ADI is a running total whose absolute level is an artefact of where the series begins, so it is read as a rise over the window

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=5, max=50]: Lookback for trend

    Outputs:
        fired [boolean, 0..1]:
            True if ADI trending up, False otherwise

    Type: FILTER
    Requires: high, low, close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if ADI trending up, False otherwise.
    """
    if len(df) < window:
        return False

    result = ADI.compute(data={'high': df["high"], 'low': df["low"], 'close': df["close"], 'volume': df["volume"],
    }, params={})
    adi = result['adi']

    if len(adi) < window or pd.isna(adi.iloc[-1]) or pd.isna(adi.iloc[-window]):
        return False

    return float(adi.iloc[-1]) > float(adi.iloc[-window])


@RuleRegistry.register("cumulative_return_positive")
def cumulative_return_positive(df: pd.DataFrame, threshold: float = 0.0) -> bool:
    """Signal: cumulative_return_positive

    Check if cumulative return from start is positive.

    Warmup: 1

    Formula:
        cumulative_return[t] > threshold -- rebased by the caller's slice, since CumulativeReturn divides by close[0] of whatever series it is given

    Inputs:
        close: closing price

    Params:
        threshold [default=0.0, min=0.0]: Minimum cumulative return in percent

    Outputs:
        fired [boolean, 0..1]:
            True if cumulative return > threshold, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        threshold (float): Minimum cumulative return in percent. Range: 0.0-100.0. Default: 0.0.

    Returns:
        bool: True if cumulative return > threshold, False otherwise.
    """
    if len(df) < 2:
        return False

    result = CumulativeReturn.compute(data={'close': df["close"]}, params={})
    cr = result['cumulative_return']

    if pd.isna(cr.iloc[-1]):
        return False

    return float(cr.iloc[-1]) > threshold


@RuleRegistry.register("cumulative_return_target")
def cumulative_return_target(df: pd.DataFrame, target: float = 10.0) -> bool:
    """Signal: cumulative_return_target

    Check if cumulative return has reached target.

    Warmup: 1

    Formula:
        cumulative_return[t] >= target -- note >=, unlike the strict > of cumulative_return_positive

    Inputs:
        close: closing price

    Params:
        target [default=10.0, min=1.0, max=100.0]: Target cumulative return in percent

    Outputs:
        fired [boolean, 0..1]:
            True if cumulative return >= target, False otherwise

    Type: FILTER
    Requires: close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        target (float): Target cumulative return in percent. Range: 1-100. Default: 10.0.

    Returns:
        bool: True if cumulative return >= target, False otherwise.
    """
    if len(df) < 2:
        return False

    result = CumulativeReturn.compute(data={'close': df["close"]}, params={})
    cr = result['cumulative_return']

    if pd.isna(cr.iloc[-1]):
        return False

    return float(cr.iloc[-1]) >= target


@RuleRegistry.register("nvi_bearish")
def nvi_bearish(df: pd.DataFrame, window: int = 255) -> bool:
    """Signal: nvi_bearish

    Check if NVI (Negative Volume Index) indicates smart money selling. NVI below its moving average
    suggests smart money distribution.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/negative-volume-index-nvi
    Warmup: window - 1

    Formula:
        nvi[t] < nvi_ema[t] -- same seed-constant caveat as nvi_bullish

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=255, min=100, max=200]: EMA period for signal

    Outputs:
        fired [boolean, 0..1]:
            True if NVI < NVI EMA, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for signal. Range: 100-200. Default: 255.

    Returns:
        bool: True if NVI < NVI EMA, False otherwise.
    """
    if len(df) < window:
        return False

    result = NVI.compute(data={"close": df["close"], "volume": df["volume"]}, params={"window": window})
    nvi = result["nvi"]
    nvi_ema = result["nvi_ema"]

    if pd.isna(nvi.iloc[-1]) or pd.isna(nvi_ema.iloc[-1]):
        return False

    return float(nvi.iloc[-1]) < float(nvi_ema.iloc[-1])


@RuleRegistry.register("nvi_bullish")
def nvi_bullish(df: pd.DataFrame, window: int = 255) -> bool:
    """Signal: nvi_bullish

    Check if NVI (Negative Volume Index) indicates smart money buying. NVI above its moving average
    suggests smart money accumulation.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/negative-volume-index-nvi
    Warmup: window - 1

    Formula:
        nvi[t] > nvi_ema[t] -- NVI's level is set by an arbitrary seed constant, so every documented reading is positional against its own EMA rather than absolute

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=255, min=100, max=200]: EMA period for signal

    Outputs:
        fired [boolean, 0..1]:
            True if NVI > NVI EMA, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA period for signal. Range: 100-200. Default: 255.

    Returns:
        bool: True if NVI > NVI EMA, False otherwise.
    """
    if len(df) < window:
        return False

    result = NVI.compute(data={"close": df["close"], "volume": df["volume"]}, params={"window": window})
    nvi = result["nvi"]
    nvi_ema = result["nvi_ema"]

    if pd.isna(nvi.iloc[-1]) or pd.isna(nvi_ema.iloc[-1]):
        return False

    return float(nvi.iloc[-1]) > float(nvi_ema.iloc[-1])


@RuleRegistry.register("obv_bearish")
def obv_bearish(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: obv_bearish

    Check if OBV is falling (bearish volume confirmation).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/on-balance-volume-obv
    Warmup: window - 1

    Formula:
        obv[t] < obv[t-window+1]

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=5, max=50]: Lookback for trend

    Outputs:
        fired [boolean, 0..1]:
            True if OBV trending down, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if OBV trending down, False otherwise.
    """
    if len(df) < window:
        return False

    result = OBV.compute(data={'close': df["close"], 'volume': df["volume"],
    }, params={})
    obv = result['obv']

    if len(obv) < window or pd.isna(obv.iloc[-1]) or pd.isna(obv.iloc[-window]):
        return False

    return float(obv.iloc[-1]) < float(obv.iloc[-window])


@RuleRegistry.register("obv_bullish")
def obv_bullish(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: obv_bullish

    Check if OBV is rising (bullish volume confirmation).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/on-balance-volume-obv
    Warmup: window - 1

    Formula:
        obv[t] > obv[t-window+1] -- a rise over the window; OBV's level is an artefact of where the series begins

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=5, max=50]: Lookback for trend

    Outputs:
        fired [boolean, 0..1]:
            True if OBV trending up, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback for trend. Range: 5-50. Default: 20.

    Returns:
        bool: True if OBV trending up, False otherwise.
    """
    if len(df) < window:
        return False

    result = OBV.compute(data={'close': df["close"], 'volume': df["volume"],
    }, params={})
    obv = result['obv']

    if len(obv) < window or pd.isna(obv.iloc[-1]) or pd.isna(obv.iloc[-window]):
        return False

    return float(obv.iloc[-1]) > float(obv.iloc[-window])


@RuleRegistry.register("vpt_bearish")
def vpt_bearish(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: vpt_bearish

    Check if VPT (Volume Price Trend) is falling.

    Warmup: window - 1

    Formula:
        vpt[t] < vpt[t-window+1]

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=5, max=50]: Window for trend comparison

    Outputs:
        fired [boolean, 0..1]:
            True if VPT trending down, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Window for trend comparison. Range: 5-50. Default: 20.

    Returns:
        bool: True if VPT trending down, False otherwise.
    """
    if len(df) < window:
        return False

    result = VPT.compute(data={'close': df["close"], 'volume': df["volume"],
    }, params={'smoothing_factor': None})
    vpt = result['vpt']

    if len(vpt) < window or pd.isna(vpt.iloc[-1]) or pd.isna(vpt.iloc[-window]):
        return False

    return float(vpt.iloc[-1]) < float(vpt.iloc[-window])


@RuleRegistry.register("vpt_bullish")
def vpt_bullish(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: vpt_bullish

    Check if VPT (Volume Price Trend) is rising.

    Warmup: window - 1

    Formula:
        vpt[t] > vpt[t-window+1] -- a rise over the window; same cumulative-level caveat

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=5, max=50]: Window for trend comparison

    Outputs:
        fired [boolean, 0..1]:
            True if VPT trending up, False otherwise

    Type: FILTER
    Requires: close, volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Window for trend comparison. Range: 5-50. Default: 20.

    Returns:
        bool: True if VPT trending up, False otherwise.
    """
    if len(df) < window:
        return False

    result = VPT.compute(data={'close': df["close"], 'volume': df["volume"],
    }, params={'smoothing_factor': None})
    vpt = result['vpt']

    if len(vpt) < window or pd.isna(vpt.iloc[-1]) or pd.isna(vpt.iloc[-window]):
        return False

    return float(vpt.iloc[-1]) > float(vpt.iloc[-window])
