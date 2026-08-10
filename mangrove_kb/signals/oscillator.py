"""Oscillator signals.

Signals whose class is `oscillator` -- the class of the indicator each one reads. The file name is the
class, so a signal's location and its position in the ontology graph agree. Registered names are
unchanged; only the file moved.
"""

import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import zero_cross
from mangrove_kb.indicators import (
    BOP,
    CCI,
    CMF,
    CMO,
    MFI,
    RSI,
    STC,
    StochRSI,
    StochasticOscillator,
    TSI,
    UltimateOscillator,
    WilliamsR,
)

logger = logging.getLogger(__name__)


@RuleRegistry.register("rsi_overbought")
def rsi_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 70.0) -> bool:
    """Signal: rsi_overbought

    Check if RSI is above the overbought threshold. RSI values above 70 typically indicate
    overbought conditions, suggesting the asset may be due for a pullback. In crypto markets,
    consider higher thresholds (80/20) during strong trends.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: window

    Formula:
        rsi[t] > threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: RSI calculation window
        threshold [default=70.0, min=50.0, max=100.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if RSI > threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold. Range: 50-100. Default: 70.0.

    Returns:
        bool: True if RSI > threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']
    if pd.isna(rsi.iloc[-1]):
        return False

    return float(rsi.iloc[-1]) > threshold


@RuleRegistry.register("rsi_oversold")
def rsi_oversold(df: pd.DataFrame, window: int = 14, threshold: float = 30.0) -> bool:
    """Signal: rsi_oversold

    Check if RSI is below the oversold threshold. RSI values below 30 typically indicate oversold
    conditions, suggesting the asset may be due for a bounce. In crypto markets, consider higher
    thresholds (80/20) during strong trends.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: window

    Formula:
        rsi[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: RSI calculation window
        threshold [default=30.0, min=0.0, max=50.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if RSI < threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Oversold threshold. Range: 0-50. Default: 30.0.

    Returns:
        bool: True if RSI < threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']
    if pd.isna(rsi.iloc[-1]):
        return False

    return float(rsi.iloc[-1]) < threshold


@RuleRegistry.register("rsi_cross_up")
def rsi_cross_up(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """Signal: rsi_cross_up

    Check if RSI crosses above a threshold level. Returns True when RSI was at or below the
    threshold in the previous bar and is now above the threshold in the current bar. In crypto
    markets, consider higher thresholds (80/20) during strong trends.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: window

    Formula:
        rsi[t-1] <= threshold and rsi[t] > threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: RSI calculation window
        threshold [default=50.0, min=0.0, max=100.0]: Threshold level to cross above

    Outputs:
        fired [boolean, 0..1]:
            True if RSI crosses above threshold, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Threshold level to cross above. Range: 0-100. Default: 50.0.

    Returns:
        bool: True if RSI crosses above threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']

    if len(rsi) < 2:
        return False

    prev_rsi = rsi.iloc[-2]
    curr_rsi = rsi.iloc[-1]

    if pd.isna(prev_rsi) or pd.isna(curr_rsi):
        return False

    # Check for crossover: RSI was below/equal to threshold, now above
    return prev_rsi <= threshold and curr_rsi > threshold


@RuleRegistry.register("rsi_cross_down")
def rsi_cross_down(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """Signal: rsi_cross_down

    Check if RSI crosses below a threshold level. Returns True when RSI was at or above the
    threshold in the previous bar and is now below the threshold in the current bar. In crypto
    markets, consider higher thresholds (80/20) during strong trends.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Warmup: window

    Formula:
        rsi[t-1] >= threshold and rsi[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: RSI calculation window
        threshold [default=50.0, min=0.0, max=100.0]: Threshold level to cross below

    Outputs:
        fired [boolean, 0..1]:
            True if RSI crosses below threshold, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Threshold level to cross below. Range: 0-100. Default: 50.0.

    Returns:
        bool: True if RSI crosses below threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False

    result = RSI.compute(data={'close': closes}, params={'window': window})
    rsi = result['rsi']

    if len(rsi) < 2:
        return False

    prev_rsi = rsi.iloc[-2]
    curr_rsi = rsi.iloc[-1]

    if pd.isna(prev_rsi) or pd.isna(curr_rsi):
        return False

    # Check for crossover: RSI was above/equal to threshold, now below
    return prev_rsi >= threshold and curr_rsi < threshold


@RuleRegistry.register("stoch_overbought")
def stoch_overbought(
    df: pd.DataFrame, window: int = 14, smooth_window: int = 3, threshold: float = 80.0
) -> bool:
    """Signal: stoch_overbought

    Check if Stochastic %K is above the overbought threshold.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochastic-oscillator-fast-slow-and-full
    Warmup: window - 1

    Formula:
        stoch_k[t] > threshold -- the FAST %K, unsmoothed

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: %K period
        smooth_window [default=3, min=1, max=10]: %K smoothing period
        threshold [default=80.0, min=70.0, max=100.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if %K > threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): %K period. Range: 5-50. Default: 14.
        smooth_window (int): %K smoothing period. Range: 1-10. Default: 3.
        threshold (float): Overbought threshold. Range: 70-100. Default: 80.0.

    Returns:
        bool: True if %K > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = StochasticOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'smooth_window': smooth_window}
    )
    stoch_k = result['stoch_k']

    if pd.isna(stoch_k.iloc[-1]):
        return False

    return float(stoch_k.iloc[-1]) > threshold


@RuleRegistry.register("stoch_oversold")
def stoch_oversold(
    df: pd.DataFrame, window: int = 14, smooth_window: int = 3, threshold: float = 20.0
) -> bool:
    """Signal: stoch_oversold

    Check if Stochastic %K is below the oversold threshold.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochastic-oscillator-fast-slow-and-full
    Warmup: window - 1

    Formula:
        stoch_k[t] < threshold -- the FAST %K, unsmoothed

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: %K period
        smooth_window [default=3, min=1, max=10]: %K smoothing period
        threshold [default=20.0, min=0.0, max=30.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if %K < threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): %K period. Range: 5-50. Default: 14.
        smooth_window (int): %K smoothing period. Range: 1-10. Default: 3.
        threshold (float): Oversold threshold. Range: 0-30. Default: 20.0.

    Returns:
        bool: True if %K < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = StochasticOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'smooth_window': smooth_window}
    )
    stoch_k = result['stoch_k']

    if pd.isna(stoch_k.iloc[-1]):
        return False

    return float(stoch_k.iloc[-1]) < threshold


@RuleRegistry.register("stochrsi_overbought")
def stochrsi_overbought(df: pd.DataFrame, window: int = 14, smooth1: int = 3, smooth2: int = 3, threshold: float = 0.8) -> bool:
    """Signal: stochrsi_overbought

    Check if Stochastic RSI indicates overbought condition. In crypto markets, consider adjusting
    thresholds during strong trends.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochrsi
    Warmup: window + smooth1 + smooth2 - 1

    Formula:
        stochrsi[t] > threshold -- StochRSI is on the 0..1 scale, so the conventional 80 level is 0.80 here

    Inputs:
        close: closing price

    Params:
        window [default=14, min=5, max=30]: RSI period
        smooth1 [default=3, min=1, max=10]: Stochastic %K smoothing
        smooth2 [default=3, min=1, max=10]: Stochastic %D smoothing
        threshold [default=0.8, min=0.6]: Overbought threshold (0-1 scale)

    Outputs:
        fired [boolean, 0..1]:
            True if StochRSI > threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI period. Range: 5-30. Default: 14.
        smooth1 (int): Stochastic %K smoothing. Range: 1-10. Default: 3.
        smooth2 (int): Stochastic %D smoothing. Range: 1-10. Default: 3.
        threshold (float): Overbought threshold (0-1 scale). Range: 0.6-1.0. Default: 0.8.

    Returns:
        bool: True if StochRSI > threshold, False otherwise.
    """
    if len(df) < window + smooth1 + smooth2:
        return False

    result = StochRSI.compute(
        data={'close': df["Close"]},
        params={'window': window, 'smooth1': smooth1, 'smooth2': smooth2}
    )
    stochrsi = result['stochrsi']

    if pd.isna(stochrsi.iloc[-1]):
        return False

    return float(stochrsi.iloc[-1]) > threshold


@RuleRegistry.register("stochrsi_oversold")
def stochrsi_oversold(df: pd.DataFrame, window: int = 14, smooth1: int = 3, smooth2: int = 3, threshold: float = 0.2) -> bool:
    """Signal: stochrsi_oversold

    Check if Stochastic RSI indicates oversold condition. In crypto markets, consider adjusting
    thresholds during strong trends.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochrsi
    Warmup: window + smooth1 + smooth2 - 1

    Formula:
        stochrsi[t] < threshold -- 0..1 scale, so the conventional 20 level is 0.20

    Inputs:
        close: closing price

    Params:
        window [default=14, min=5, max=30]: RSI period
        smooth1 [default=3, min=1, max=10]: Stochastic %K smoothing
        smooth2 [default=3, min=1, max=10]: Stochastic %D smoothing
        threshold [default=0.2, min=0.0]: Oversold threshold (0-1 scale)

    Outputs:
        fired [boolean, 0..1]:
            True if StochRSI < threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): RSI period. Range: 5-30. Default: 14.
        smooth1 (int): Stochastic %K smoothing. Range: 1-10. Default: 3.
        smooth2 (int): Stochastic %D smoothing. Range: 1-10. Default: 3.
        threshold (float): Oversold threshold (0-1 scale). Range: 0.0-0.4. Default: 0.2.

    Returns:
        bool: True if StochRSI < threshold, False otherwise.
    """
    if len(df) < window + smooth1 + smooth2:
        return False

    result = StochRSI.compute(
        data={'close': df["Close"]},
        params={'window': window, 'smooth1': smooth1, 'smooth2': smooth2}
    )
    stochrsi = result['stochrsi']

    if pd.isna(stochrsi.iloc[-1]):
        return False

    return float(stochrsi.iloc[-1]) < threshold


@RuleRegistry.register("williams_r_overbought")
def williams_r_overbought(df: pd.DataFrame, window: int = 14, threshold: float = -20.0) -> bool:
    """Signal: williams_r_overbought

    Check if Williams %R is above the overbought threshold. Williams %R ranges from -100 to 0.
    Values above -20 indicate overbought.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r
    Warmup: window - 1

    Formula:
        wr[t] > threshold -- Williams %R is NEGATIVE, so overbought is the band nearest zero and the default threshold is -20

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: Lookback window
        threshold [default=-20.0, min=-30.0, max=0.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Williams %R > threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback window. Range: 5-50. Default: 14.
        threshold (float): Overbought threshold. Range: -30-0. Default: -20.0.

    Returns:
        bool: True if Williams %R > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = WilliamsR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    wr = result['wr']

    if pd.isna(wr.iloc[-1]):
        return False

    return float(wr.iloc[-1]) > threshold


@RuleRegistry.register("williams_r_oversold")
def williams_r_oversold(df: pd.DataFrame, window: int = 14, threshold: float = -80.0) -> bool:
    """Signal: williams_r_oversold

    Check if Williams %R is below the oversold threshold. Williams %R ranges from -100 to 0. Values
    below -80 indicate oversold.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r
    Warmup: window - 1

    Formula:
        wr[t] < threshold -- negative scale, so oversold is the default -80

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: Lookback window
        threshold [default=-80.0, min=-100.0, max=-70.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if Williams %R < threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback window. Range: 5-50. Default: 14.
        threshold (float): Oversold threshold. Range: -100--70. Default: -80.0.

    Returns:
        bool: True if Williams %R < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = WilliamsR.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window}
    )
    wr = result['wr']

    if pd.isna(wr.iloc[-1]):
        return False

    return float(wr.iloc[-1]) < threshold


@RuleRegistry.register("cmo_overbought")
def cmo_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """Signal: cmo_overbought

    Check if Chande Momentum Oscillator is above the overbought threshold. CMO ranges from -100 to
    +100; default threshold of +50 is standard (analogous to RSI 70).

    Warmup: window

    Formula:
        cmo[t] >= threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: CMO lookback
        threshold [default=50.0, min=20.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if CMO >= threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold. Range: 20.0-90.0. Default: 50.0.

    Returns:
        bool: True if CMO >= threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if pd.isna(cmo.iloc[-1]):
        return False
    return bool(cmo.iloc[-1] >= threshold)


@RuleRegistry.register("cmo_oversold")
def cmo_oversold(df: pd.DataFrame, window: int = 14, threshold: float = -50.0) -> bool:
    """Signal: cmo_oversold

    Check if Chande Momentum Oscillator is below the oversold threshold. Default threshold of -50 is
    standard (analogous to RSI 30).

    Warmup: window

    Formula:
        cmo[t] <= threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: CMO lookback
        threshold [default=-50.0, min=-90.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if CMO <= threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Oversold threshold. Range: -90.0--20.0. Default: -50.0.

    Returns:
        bool: True if CMO <= threshold, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window + 1:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if pd.isna(cmo.iloc[-1]):
        return False
    return bool(cmo.iloc[-1] <= threshold)


@RuleRegistry.register("cmo_cross_up")
def cmo_cross_up(df: pd.DataFrame, window: int = 14, threshold: float = -50.0) -> bool:
    """Signal: cmo_cross_up

    Detect CMO crossing above the oversold threshold (bullish momentum return). Analogous to RSI
    crossing above 30.

    Warmup: window + 1

    Formula:
        cmo[t-1] <= threshold and cmo[t] > threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: CMO lookback
        threshold [default=-50.0, min=-90.0]: Oversold threshold to cross above

    Outputs:
        fired [boolean, 0..1]:
            True if CMO crosses above threshold on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Oversold threshold to cross above. Range: -90.0--20.0. Default: -50.0.

    Returns:
        bool: True if CMO crosses above threshold on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window + 2:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if len(cmo) < 2 or pd.isna(cmo.iloc[-1]) or pd.isna(cmo.iloc[-2]):
        return False
    return bool(cmo.iloc[-2] <= threshold < cmo.iloc[-1])


@RuleRegistry.register("cmo_cross_down")
def cmo_cross_down(df: pd.DataFrame, window: int = 14, threshold: float = 50.0) -> bool:
    """Signal: cmo_cross_down

    Detect CMO crossing below the overbought threshold (bearish momentum onset). Analogous to RSI
    crossing below 70.

    Warmup: window + 1

    Formula:
        cmo[t-1] >= threshold and cmo[t] < threshold

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: CMO lookback
        threshold [default=50.0, min=20.0]: Overbought threshold to cross below

    Outputs:
        fired [boolean, 0..1]:
            True if CMO crosses below threshold on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CMO lookback. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold to cross below. Range: 20.0-90.0. Default: 50.0.

    Returns:
        bool: True if CMO crosses below threshold on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window + 2:
        return False
    cmo = CMO.compute(data={'close': closes}, params={'window': window})['cmo']
    if len(cmo) < 2 or pd.isna(cmo.iloc[-1]) or pd.isna(cmo.iloc[-2]):
        return False
    return bool(cmo.iloc[-2] >= threshold > cmo.iloc[-1])


@RuleRegistry.register("tsi_bullish")
def tsi_bullish(df: pd.DataFrame, window_slow: int = 25, window_fast: int = 13, threshold: float = 0.0) -> bool:
    """Signal: tsi_bullish

    Check if True Strength Index indicates bullish momentum. TSI above zero indicates bullish
    momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/true-strength-index
    Warmup: window_slow + window_fast - 1

    Formula:
        tsi[t] > threshold

    Inputs:
        close: closing price

    Params:
        window_slow [default=25, min=10, max=50]: Slow EMA period
        window_fast [default=13, min=5, max=25]: Fast EMA period
        threshold [default=0.0, min=-50.0, max=50.0]: Bullish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if TSI > threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 10-50. Default: 25.
        window_fast (int): Fast EMA period. Range: 5-25. Default: 13.
        threshold (float): Bullish threshold. Range: -50-50. Default: 0.0.

    Returns:
        bool: True if TSI > threshold, False otherwise.
    """
    if len(df) < window_slow + window_fast:
        return False

    result = TSI.compute(
        data={'close': df["Close"]},
        params={'window_slow': window_slow, 'window_fast': window_fast}
    )
    tsi = result['tsi']

    if pd.isna(tsi.iloc[-1]):
        return False

    return float(tsi.iloc[-1]) > threshold


@RuleRegistry.register("tsi_bearish")
def tsi_bearish(df: pd.DataFrame, window_slow: int = 25, window_fast: int = 13, threshold: float = 0.0) -> bool:
    """Signal: tsi_bearish

    Check if True Strength Index indicates bearish momentum. TSI below zero indicates bearish
    momentum.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/true-strength-index
    Warmup: window_slow + window_fast - 1

    Formula:
        tsi[t] < threshold

    Inputs:
        close: closing price

    Params:
        window_slow [default=25, min=10, max=50]: Slow EMA period
        window_fast [default=13, min=5, max=25]: Fast EMA period
        threshold [default=0.0, min=-50.0, max=50.0]: Bearish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if TSI < threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 10-50. Default: 25.
        window_fast (int): Fast EMA period. Range: 5-25. Default: 13.
        threshold (float): Bearish threshold. Range: -50-50. Default: 0.0.

    Returns:
        bool: True if TSI < threshold, False otherwise.
    """
    if len(df) < window_slow + window_fast:
        return False

    result = TSI.compute(
        data={'close': df["Close"]},
        params={'window_slow': window_slow, 'window_fast': window_fast}
    )
    tsi = result['tsi']

    if pd.isna(tsi.iloc[-1]):
        return False

    return float(tsi.iloc[-1]) < threshold


@RuleRegistry.register("bop_bullish")
def bop_bullish(df: pd.DataFrame) -> bool:
    """Signal: bop_bullish

    Check if Balance of Power indicates buyers in control on the current bar. BOP = (close - open) /
    (high - low). Positive = buyers dominated the bar.

    Reference: https://www.tradingview.com/support/solutions/43000589100-balance-of-power-bop/
    Warmup: 0

    Formula:
        bop[t] > 0

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if BOP > 0, False otherwise (including NaN when high==low)

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP > 0, False otherwise (including NaN when high==low).
    """
    if len(df) < 1:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    if pd.isna(bop.iloc[-1]):
        return False
    return bool(bop.iloc[-1] > 0)


@RuleRegistry.register("bop_bearish")
def bop_bearish(df: pd.DataFrame) -> bool:
    """Signal: bop_bearish

    Check if Balance of Power indicates sellers in control on the current bar.

    Reference: https://www.tradingview.com/support/solutions/43000589100-balance-of-power-bop/
    Warmup: 0

    Formula:
        bop[t] < 0

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if BOP < 0, False otherwise

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP < 0, False otherwise.
    """
    if len(df) < 1:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    if pd.isna(bop.iloc[-1]):
        return False
    return bool(bop.iloc[-1] < 0)


@RuleRegistry.register("bop_cross_up")
def bop_cross_up(df: pd.DataFrame) -> bool:
    """Signal: bop_cross_up

    Detect Balance of Power crossing above zero (sellers -> buyers).

    Reference: https://www.tradingview.com/support/solutions/43000589100-balance-of-power-bop/
    Warmup: 1

    Formula:
        bop[t-1] <= 0 and bop[t] > 0

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if BOP crosses above zero on the current bar

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP crosses above zero on the current bar.
    """
    if len(df) < 2:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    return zero_cross(bop, "up")


@RuleRegistry.register("bop_cross_down")
def bop_cross_down(df: pd.DataFrame) -> bool:
    """Signal: bop_cross_down

    Detect Balance of Power crossing below zero (buyers -> sellers).

    Reference: https://www.tradingview.com/support/solutions/43000589100-balance-of-power-bop/
    Warmup: 1

    Formula:
        bop[t-1] >= 0 and bop[t] < 0

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if BOP crosses below zero on the current bar

    Type: TRIGGER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if BOP crosses below zero on the current bar.
    """
    if len(df) < 2:
        return False
    bop = BOP.compute(
        data={'open': df['Open'], 'high': df['High'], 'low': df['Low'], 'close': df['Close']},
        params={},
    )['bop']
    return zero_cross(bop, "down")


@RuleRegistry.register("uo_overbought")
def uo_overbought(df: pd.DataFrame, window_short: int = 7, window_medium: int = 14, window_long: int = 28, threshold: float = 70.0) -> bool:
    """Signal: uo_overbought

    Check if Ultimate Oscillator indicates overbought condition.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ultimate-oscillator
    Warmup: window_long - 1

    Formula:
        ultimate_oscillator[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window_short [default=7, min=3, max=20]: Short window
        window_medium [default=14, min=7, max=30]: Medium window
        window_long [default=28, min=14, max=50]: Long window
        threshold [default=70.0, min=60.0, max=90.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if UO > threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_short (int): Short window. Range: 3-20. Default: 7.
        window_medium (int): Medium window. Range: 7-30. Default: 14.
        window_long (int): Long window. Range: 14-50. Default: 28.
        threshold (float): Overbought threshold. Range: 60-90. Default: 70.0.

    Returns:
        bool: True if UO > threshold, False otherwise.
    """
    if len(df) < window_long:
        return False

    result = UltimateOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window1': window_short, 'window2': window_medium, 'window3': window_long,
                'weight1': 4.0, 'weight2': 2.0, 'weight3': 1.0}
    )
    uo = result['ultimate_oscillator']

    if pd.isna(uo.iloc[-1]):
        return False

    return float(uo.iloc[-1]) > threshold


@RuleRegistry.register("uo_oversold")
def uo_oversold(df: pd.DataFrame, window_short: int = 7, window_medium: int = 14, window_long: int = 28, threshold: float = 30.0) -> bool:
    """Signal: uo_oversold

    Check if Ultimate Oscillator indicates oversold condition.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ultimate-oscillator
    Warmup: window_long - 1

    Formula:
        ultimate_oscillator[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window_short [default=7, min=3, max=20]: Short window
        window_medium [default=14, min=7, max=30]: Medium window
        window_long [default=28, min=14, max=50]: Long window
        threshold [default=30.0, min=10.0, max=40.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if UO < threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_short (int): Short window. Range: 3-20. Default: 7.
        window_medium (int): Medium window. Range: 7-30. Default: 14.
        window_long (int): Long window. Range: 14-50. Default: 28.
        threshold (float): Oversold threshold. Range: 10-40. Default: 30.0.

    Returns:
        bool: True if UO < threshold, False otherwise.
    """
    if len(df) < window_long:
        return False

    result = UltimateOscillator.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window1': window_short, 'window2': window_medium, 'window3': window_long,
                'weight1': 4.0, 'weight2': 2.0, 'weight3': 1.0}
    )
    uo = result['ultimate_oscillator']

    if pd.isna(uo.iloc[-1]):
        return False

    return float(uo.iloc[-1]) < threshold


@RuleRegistry.register("cmf_bearish")
def cmf_bearish(df: pd.DataFrame, window: int = 20, threshold: float = 0.0) -> bool:
    """Signal: cmf_bearish

    Check if CMF (Chaikin Money Flow) indicates selling pressure.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-money-flow-cmf
    Warmup: window - 1

    Formula:
        cmf[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=10, max=50]: CMF period
        threshold [default=0.0, min=-1.0]: Bearish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if CMF < threshold, False otherwise

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


@RuleRegistry.register("cmf_bullish")
def cmf_bullish(df: pd.DataFrame, window: int = 20, threshold: float = 0.0) -> bool:
    """Signal: cmf_bullish

    Check if CMF (Chaikin Money Flow) indicates buying pressure.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-money-flow-cmf
    Warmup: window - 1

    Formula:
        cmf[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=10, max=50]: CMF period
        threshold [default=0.0, min=-1.0]: Bullish threshold

    Outputs:
        fired [boolean, 0..1]:
            True if CMF > threshold, False otherwise

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


@RuleRegistry.register("mfi_overbought")
def mfi_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 80.0) -> bool:
    """Signal: mfi_overbought

    Check if MFI (Money Flow Index) indicates overbought condition.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/money-flow-index-mfi
    Warmup: window - 1

    Formula:
        mfi[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=30]: MFI period
        threshold [default=80.0, min=70.0, max=95.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if MFI > threshold, False otherwise

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
    """Signal: mfi_oversold

    Check if MFI (Money Flow Index) indicates oversold condition.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/money-flow-index-mfi
    Warmup: window - 1

    Formula:
        mfi[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=30]: MFI period
        threshold [default=20.0, min=5.0, max=30.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if MFI < threshold, False otherwise

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


# ---------------------------------------------------------------------------
# Moved from trend.py, which held four classes at once.
# Signals whose class is `oscillator` -- the class of the indicator each one reads.
# ---------------------------------------------------------------------------

@RuleRegistry.register("cci_overbought")
def cci_overbought(df: pd.DataFrame, window: int = 20, constant: float = 0.015, threshold: float = 100.0) -> bool:
    """Signal: cci_overbought

    Check if CCI indicates overbought condition.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/commodity-channel-index-cci
    Warmup: window - 1

    Formula:
        cci[t] > threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: CCI period
        constant [default=0.015, min=0.001]: CCI constant
        threshold [default=100.0, min=50.0, max=200.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if CCI > threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CCI period. Range: 10-50. Default: 20.
        constant (float): CCI constant. Range: 0.001-0.1. Default: 0.015.
        threshold (float): Overbought threshold. Range: 50-200. Default: 100.0.

    Returns:
        bool: True if CCI > threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = CCI.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'constant': constant}
    )
    cci = result['cci']

    if pd.isna(cci.iloc[-1]):
        return False

    return float(cci.iloc[-1]) > threshold

@RuleRegistry.register("cci_oversold")
def cci_oversold(df: pd.DataFrame, window: int = 20, constant: float = 0.015, threshold: float = -100.0) -> bool:
    """Signal: cci_oversold

    Check if CCI indicates oversold condition.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/commodity-channel-index-cci
    Warmup: window - 1

    Formula:
        cci[t] < threshold

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: CCI period
        constant [default=0.015, min=0.001]: CCI constant
        threshold [default=-100.0, min=-200.0, max=-50.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if CCI < threshold, False otherwise

    Type: FILTER
    Requires: High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): CCI period. Range: 10-50. Default: 20.
        constant (float): CCI constant. Range: 0.001-0.1. Default: 0.015.
        threshold (float): Oversold threshold. Range: -200--50. Default: -100.0.

    Returns:
        bool: True if CCI < threshold, False otherwise.
    """
    if len(df) < window:
        return False

    result = CCI.compute(
        data={'high': df["High"], 'low': df["Low"], 'close': df["Close"]},
        params={'window': window, 'constant': constant}
    )
    cci = result['cci']

    if pd.isna(cci.iloc[-1]):
        return False

    return float(cci.iloc[-1]) < threshold

@RuleRegistry.register("stc_overbought")
def stc_overbought(df: pd.DataFrame, window_slow: int = 50, window_fast: int = 23, cycle: int = 10, smooth1: int = 3, smooth2: int = 3, threshold: float = 75.0) -> bool:
    """Signal: stc_overbought

    Check if STC indicates overbought condition.

    Warmup: window_slow + cycle - 1

    Formula:
        stc[t] > threshold

    Inputs:
        close: closing price

    Params:
        window_slow [default=50, min=2, max=200]: Slow EMA period
        window_fast [default=23, min=2, max=200]: Fast EMA period
        cycle [default=10, min=1, max=200]: Cycle period
        smooth1 [default=3, min=1, max=200]: First smoothing period
        smooth2 [default=3, min=1, max=200]: Second smoothing period
        threshold [default=75.0, min=0.0]: Overbought threshold

    Outputs:
        fired [boolean, 0..1]:
            True if STC > threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 2-200. Default: 50.
        window_fast (int): Fast EMA period. Range: 2-200. Default: 23.
        cycle (int): Cycle period. Range: 1-200. Default: 10.
        smooth1 (int): First smoothing period. Range: 1-200. Default: 3.
        smooth2 (int): Second smoothing period. Range: 1-200. Default: 3.
        threshold (float): Overbought threshold. Range: 0.0-100.0. Default: 75.0.

    Returns:
        bool: True if STC > threshold, False otherwise.
    """
    if len(df) < window_slow + cycle:
        return False

    result = STC.compute(
        data={'close': df["Close"]},
        params={
            'window_slow': window_slow,
            'window_fast': window_fast,
            'cycle': cycle,
            'smooth1': smooth1,
            'smooth2': smooth2
        }
    )
    stc = result['stc']

    if pd.isna(stc.iloc[-1]):
        return False

    return float(stc.iloc[-1]) > threshold

@RuleRegistry.register("stc_oversold")
def stc_oversold(df: pd.DataFrame, window_slow: int = 50, window_fast: int = 23, cycle: int = 10, smooth1: int = 3, smooth2: int = 3, threshold: float = 25.0) -> bool:
    """Signal: stc_oversold

    Check if STC indicates oversold condition.

    Warmup: window_slow + cycle - 1

    Formula:
        stc[t] < threshold

    Inputs:
        close: closing price

    Params:
        window_slow [default=50, min=2, max=200]: Slow EMA period
        window_fast [default=23, min=2, max=200]: Fast EMA period
        cycle [default=10, min=1, max=200]: Cycle period
        smooth1 [default=3, min=1, max=200]: First smoothing period
        smooth2 [default=3, min=1, max=200]: Second smoothing period
        threshold [default=25.0, min=0.0]: Oversold threshold

    Outputs:
        fired [boolean, 0..1]:
            True if STC < threshold, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_slow (int): Slow EMA period. Range: 2-200. Default: 50.
        window_fast (int): Fast EMA period. Range: 2-200. Default: 23.
        cycle (int): Cycle period. Range: 1-200. Default: 10.
        smooth1 (int): First smoothing period. Range: 1-200. Default: 3.
        smooth2 (int): Second smoothing period. Range: 1-200. Default: 3.
        threshold (float): Oversold threshold. Range: 0.0-100.0. Default: 25.0.

    Returns:
        bool: True if STC < threshold, False otherwise.
    """
    if len(df) < window_slow + cycle:
        return False

    result = STC.compute(
        data={'close': df["Close"]},
        params={
            'window_slow': window_slow,
            'window_fast': window_fast,
            'cycle': cycle,
            'smooth1': smooth1,
            'smooth2': smooth2
        }
    )
    stc = result['stc']

    if pd.isna(stc.iloc[-1]):
        return False

    return float(stc.iloc[-1]) < threshold
