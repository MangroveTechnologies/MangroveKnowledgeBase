"""Averaging signals.

Signals whose class is `averaging` -- the class of the indicator each one reads. The file name is the
class, so a signal's location and its position in the ontology graph agree. Registered names are
unchanged; only the file moved.
"""

import logging

import numpy as np
import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import _ma_crossover, _ma_is_above
from mangrove_kb.indicators import (
    ALMA,
    DEMA,
    EMA,
    EPMA,
    HMA,
    HeikinAshi,
    Ichimoku,
    KAMA,
    MAMA,
    SMA,
    SMMA,
    T3,
    TEMA,
    TRIMA,
    VWAP,
    VWMA,
    WMA,
    WilliamsAlligator,
)

logger = logging.getLogger(__name__)

#: Fibonacci windows -- the ribbon's conventional set. A tuple so the default cannot be mutated.
_DEFAULT_RIBBON_WINDOWS = (5, 8, 13, 21, 34, 55, 89, 144)


@RuleRegistry.register("kama_cross_up")
def kama_cross_up(df: pd.DataFrame, window: int = 10, pow1: int = 2, pow2: int = 30) -> bool:
    """Signal: kama_cross_up

    Check if price crosses above KAMA (bullish signal).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/kaufmans-adaptive-moving-average-kama
    Warmup: window + max(pow1, pow2) - 1

    Formula:
        close[t-1] <= kama[t-1] and close[t] > kama[t]

    Inputs:
        close: closing price

    Params:
        window [default=10, min=5, max=30]: Efficiency ratio period
        pow1 [default=2, min=1, max=10]: Fast smoothing constant
        pow2 [default=30, min=10, max=50]: Slow smoothing constant

    Outputs:
        fired [boolean, 0..1]:
            True if price crosses above KAMA, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Efficiency ratio period. Range: 5-30. Default: 10.
        pow1 (int): Fast smoothing constant. Range: 1-10. Default: 2.
        pow2 (int): Slow smoothing constant. Range: 10-50. Default: 30.

    Returns:
        bool: True if price crosses above KAMA, False otherwise.
    """
    if len(df) < window + max(pow1, pow2):
        return False

    result = KAMA.compute(
        data={'close': df["Close"]},
        params={'window': window, 'pow1': pow1, 'pow2': pow2}
    )
    kama = result['kama']

    if len(kama) < 2 or pd.isna(kama.iloc[-1]) or pd.isna(kama.iloc[-2]):
        return False

    close = df["Close"]
    prev_below = float(close.iloc[-2]) <= float(kama.iloc[-2])
    curr_above = float(close.iloc[-1]) > float(kama.iloc[-1])

    return prev_below and curr_above


@RuleRegistry.register("kama_cross_down")
def kama_cross_down(df: pd.DataFrame, window: int = 10, pow1: int = 2, pow2: int = 30) -> bool:
    """Signal: kama_cross_down

    Check if price crosses below KAMA (bearish signal).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/kaufmans-adaptive-moving-average-kama
    Warmup: window + max(pow1, pow2) - 1

    Formula:
        close[t-1] >= kama[t-1] and close[t] < kama[t]

    Inputs:
        close: closing price

    Params:
        window [default=10, min=5, max=30]: Efficiency ratio period
        pow1 [default=2, min=1, max=10]: Fast smoothing constant
        pow2 [default=30, min=10, max=50]: Slow smoothing constant

    Outputs:
        fired [boolean, 0..1]:
            True if price crosses below KAMA, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Efficiency ratio period. Range: 5-30. Default: 10.
        pow1 (int): Fast smoothing constant. Range: 1-10. Default: 2.
        pow2 (int): Slow smoothing constant. Range: 10-50. Default: 30.

    Returns:
        bool: True if price crosses below KAMA, False otherwise.
    """
    if len(df) < window + max(pow1, pow2):
        return False

    result = KAMA.compute(
        data={'close': df["Close"]},
        params={'window': window, 'pow1': pow1, 'pow2': pow2}
    )
    kama = result['kama']

    if len(kama) < 2 or pd.isna(kama.iloc[-1]) or pd.isna(kama.iloc[-2]):
        return False

    close = df["Close"]
    prev_above = float(close.iloc[-2]) >= float(kama.iloc[-2])
    curr_below = float(close.iloc[-1]) < float(kama.iloc[-1])

    return prev_above and curr_below


@RuleRegistry.register("is_above_vwma")
def is_above_vwma(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: is_above_vwma

    Check if the current price is above the Volume-Weighted Moving Average (VWMA). VWMA weights each
    bar's close by its volume, emphasizing high-participation bars. Useful as a filter that
    incorporates conviction from volume.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window - 1

    Formula:
        close[t] > vwma[t]

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=2, max=200]: VWMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > VWMA, False otherwise

    Type: FILTER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): VWMA window in bars. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > VWMA, False otherwise.
    """
    if len(df) < window:
        return False
    closes = df["Close"]
    volume = df["Volume"]
    result = VWMA.compute(data={'close': closes, 'volume': volume}, params={'window': window})
    vwma = result['vwma']
    if vwma.empty or pd.isna(vwma.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > vwma.iloc[-1])


@RuleRegistry.register("vwap_above")
def vwap_above(df: pd.DataFrame, window: int = 14) -> bool:
    """Signal: vwap_above

    Check if price is above VWAP (bullish bias).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/volume-weighted-average-price-vwap
    Warmup: window - 1

    Formula:
        close[t] > vwap[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=50]: VWAP period

    Outputs:
        fired [boolean, 0..1]:
            True if Close > VWAP, False otherwise

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
    """Signal: vwap_below

    Check if price is below VWAP (bearish bias).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/volume-weighted-average-price-vwap
    Warmup: window - 1

    Formula:
        close[t] < vwap[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=50]: VWAP period

    Outputs:
        fired [boolean, 0..1]:
            True if Close < VWAP, False otherwise

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


@RuleRegistry.register("vwma_cross_down")
def vwma_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: vwma_cross_down

    Detect a bearish VWMA crossover (fast VWMA crosses below slow VWMA). Volume-weighted version of
    the classic SMA death cross.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        vwma(window_fast)[t-1] >= vwma(window_slow)[t-1] and vwma(window_fast)[t] < vwma(window_slow)[t]

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window_fast [default=9, min=2, max=100]: Fast VWMA window
        window_slow [default=21, min=2, max=200]: Slow VWMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish VWMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast VWMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow VWMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bearish VWMA crossover detected on the current bar.
    """
    if len(df) < window_slow + 1:
        return False
    data = {'close': df["Close"], 'volume': df["Volume"]}
    fast = VWMA.compute(data=data, params={'window': window_fast})['vwma']
    slow = VWMA.compute(data=data, params={'window': window_slow})['vwma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


@RuleRegistry.register("vwma_cross_up")
def vwma_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: vwma_cross_up

    Detect a bullish VWMA crossover (fast VWMA crosses above slow VWMA). Volume-weighted version of
    the classic SMA golden cross. High-volume bars carry more weight, so the signal is less
    susceptible to low-volume noise.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        vwma(window_fast)[t-1] <= vwma(window_slow)[t-1] and vwma(window_fast)[t] > vwma(window_slow)[t] -- two VWMAs of different windows, not price against one

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window_fast [default=9, min=2, max=100]: Fast VWMA window
        window_slow [default=21, min=2, max=200]: Slow VWMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish VWMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close, Volume

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast VWMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow VWMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bullish VWMA crossover detected on the current bar.
    """
    if len(df) < window_slow + 1:
        return False
    data = {'close': df["Close"], 'volume': df["Volume"]}
    fast = VWMA.compute(data=data, params={'window': window_fast})['vwma']
    slow = VWMA.compute(data=data, params={'window': window_slow})['vwma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)


# ---------------------------------------------------------------------------
# Moved from trend.py, which held four classes at once.
# Signals whose class is `averaging` -- the class of the indicator each one reads.
# ---------------------------------------------------------------------------

def _alligator_lines(df: pd.DataFrame, jaw: int, teeth: int, lips: int,
                     jaw_offset: int, teeth_offset: int, lips_offset: int):
    """Helper: compute alligator lines, return None if insufficient data."""
    if len(df) < jaw + jaw_offset + 1:
        return None
    out = WilliamsAlligator.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={
            'jaw': jaw, 'teeth': teeth, 'lips': lips,
            'jaw_offset': jaw_offset, 'teeth_offset': teeth_offset, 'lips_offset': lips_offset,
        },
    )
    return out['jaw'], out['teeth'], out['lips']

def _mama_compute(df: pd.DataFrame, fast_limit: float, slow_limit: float, warmup_bars: int = 64):
    """Helper: compute MAMA+FAMA once for signal evaluation.

    MAMA consumes median price per Ehlers. `warmup_bars` is how many leading values are discarded
    as contaminated by the zero seed -- see the indicator docstring for the measurement behind the
    default.
    """
    if len(df) <= warmup_bars:
        return None
    result = MAMA.compute(data={'high': df["High"], 'low': df["Low"]},
                          params={'fast_limit': fast_limit, 'slow_limit': slow_limit,
                                  'warmup_bars': warmup_bars})
    mama, fama = result['mama'], result['fama']
    if len(mama) < 2 or pd.isna(mama.iloc[-1]) or pd.isna(fama.iloc[-1]):
        return None
    return mama, fama

def _ribbon_alignment(closes: pd.Series, windows: list) -> str | None:
    """Classify the ribbon on the latest bar as 'bullish', 'bearish' or 'tangled'.

    Returns None where the alignment is undefined -- any SMA still in warmup on that bar.

    Bullish is strict alignment fastest-above-slowest, i.e. the row of SMAs read shortest window to
    longest is strictly DECREASING. Bearish is the strict opposite. Tangled is defined as neither,
    so the three are mutually exclusive and, wherever alignment is defined, exhaustive.
    """
    if sorted(windows) != windows:
        raise ValueError(f"windows must be strictly increasing; got {windows}")

    mas = np.array([
        SMA.compute({'close': closes}, {'window': w})['sma'].to_numpy(dtype=np.float64)[-1]
        for w in windows
    ])
    if np.isnan(mas).any():
        return None

    diffs = np.diff(mas)
    if np.all(diffs < 0):
        return "bullish"
    if np.all(diffs > 0):
        return "bearish"
    return "tangled"

@RuleRegistry.register("alligator_bearish")
def alligator_bearish(
    df: pd.DataFrame,
    jaw: int = 13, teeth: int = 8, lips: int = 5,
    jaw_offset: int = 8, teeth_offset: int = 5, lips_offset: int = 3,
) -> bool:
    """Signal: alligator_bearish

    Check if Williams Alligator lines are in bearish alignment (lips < teeth < jaw). Strong
    downtrend, all lines spreading downward.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/alligator
    Warmup: jaw + jaw_offset

    Formula:
        lips[t] < teeth[t] < jaw[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        jaw [default=13, min=5, max=50]: Jaw SMMA period
        teeth [default=8, min=3, max=30]: Teeth SMMA period
        lips [default=5, min=2, max=20]: Lips SMMA period
        jaw_offset [default=8, min=0, max=20]: Jaw forward shift
        teeth_offset [default=5, min=0, max=15]: Teeth forward shift
        lips_offset [default=3, min=0, max=10]: Lips forward shift

    Outputs:
        fired [boolean, 0..1]:
            True if lips < teeth < jaw on the current bar

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        jaw (int): Jaw SMMA period. Range: 5-50. Default: 13.
        teeth (int): Teeth SMMA period. Range: 3-30. Default: 8.
        lips (int): Lips SMMA period. Range: 2-20. Default: 5.
        jaw_offset (int): Jaw forward shift. Range: 0-20. Default: 8.
        teeth_offset (int): Teeth forward shift. Range: 0-15. Default: 5.
        lips_offset (int): Lips forward shift. Range: 0-10. Default: 3.

    Returns:
        bool: True if lips < teeth < jaw on the current bar.
    """
    lines = _alligator_lines(df, jaw, teeth, lips, jaw_offset, teeth_offset, lips_offset)
    if lines is None:
        return False
    jaw_s, teeth_s, lips_s = lines
    if pd.isna(jaw_s.iloc[-1]) or pd.isna(teeth_s.iloc[-1]) or pd.isna(lips_s.iloc[-1]):
        return False
    return bool(lips_s.iloc[-1] < teeth_s.iloc[-1] < jaw_s.iloc[-1])

@RuleRegistry.register("alligator_bullish")
def alligator_bullish(
    df: pd.DataFrame,
    jaw: int = 13, teeth: int = 8, lips: int = 5,
    jaw_offset: int = 8, teeth_offset: int = 5, lips_offset: int = 3,
) -> bool:
    """Signal: alligator_bullish

    Check if Williams Alligator lines are in bullish alignment (lips > teeth > jaw). Bill Williams's
    "hungry alligator" state: strong uptrend, all lines spreading upward.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/alligator
    Warmup: jaw + jaw_offset

    Formula:
        lips[t] > teeth[t] > jaw[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        jaw [default=13, min=5, max=50]: Jaw SMMA period
        teeth [default=8, min=3, max=30]: Teeth SMMA period
        lips [default=5, min=2, max=20]: Lips SMMA period
        jaw_offset [default=8, min=0, max=20]: Jaw forward shift
        teeth_offset [default=5, min=0, max=15]: Teeth forward shift
        lips_offset [default=3, min=0, max=10]: Lips forward shift

    Outputs:
        fired [boolean, 0..1]:
            True if lips > teeth > jaw on the current bar

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        jaw (int): Jaw SMMA period. Range: 5-50. Default: 13.
        teeth (int): Teeth SMMA period. Range: 3-30. Default: 8.
        lips (int): Lips SMMA period. Range: 2-20. Default: 5.
        jaw_offset (int): Jaw forward shift. Range: 0-20. Default: 8.
        teeth_offset (int): Teeth forward shift. Range: 0-15. Default: 5.
        lips_offset (int): Lips forward shift. Range: 0-10. Default: 3.

    Returns:
        bool: True if lips > teeth > jaw on the current bar.
    """
    lines = _alligator_lines(df, jaw, teeth, lips, jaw_offset, teeth_offset, lips_offset)
    if lines is None:
        return False
    jaw_s, teeth_s, lips_s = lines
    if pd.isna(jaw_s.iloc[-1]) or pd.isna(teeth_s.iloc[-1]) or pd.isna(lips_s.iloc[-1]):
        return False
    return bool(lips_s.iloc[-1] > teeth_s.iloc[-1] > jaw_s.iloc[-1])

@RuleRegistry.register("alligator_sleeping")
def alligator_sleeping(
    df: pd.DataFrame,
    jaw: int = 13, teeth: int = 8, lips: int = 5,
    jaw_offset: int = 8, teeth_offset: int = 5, lips_offset: int = 3,
) -> bool:
    """Signal: alligator_sleeping

    Check if the Williams Alligator is sleeping (lines tangled, no trend). True when lines are
    neither strictly bullish-aligned nor bearish-aligned. Used as a no-trade filter during
    consolidation.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/alligator
    Warmup: jaw + jaw_offset

    Formula:
        not (lips[t] > teeth[t] > jaw[t]) and not (lips[t] < teeth[t] < jaw[t]) -- neither alignment holds; the lines are tangled

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        jaw [default=13, min=5, max=50]: Jaw SMMA period
        teeth [default=8, min=3, max=30]: Teeth SMMA period
        lips [default=5, min=2, max=20]: Lips SMMA period
        jaw_offset [default=8, min=0, max=20]: Jaw forward shift
        teeth_offset [default=5, min=0, max=15]: Teeth forward shift
        lips_offset [default=3, min=0, max=10]: Lips forward shift

    Outputs:
        fired [boolean, 0..1]:
            True if lines are tangled (no strict bullish or bearish alignment)

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        jaw (int): Jaw SMMA period. Range: 5-50. Default: 13.
        teeth (int): Teeth SMMA period. Range: 3-30. Default: 8.
        lips (int): Lips SMMA period. Range: 2-20. Default: 5.
        jaw_offset (int): Jaw forward shift. Range: 0-20. Default: 8.
        teeth_offset (int): Teeth forward shift. Range: 0-15. Default: 5.
        lips_offset (int): Lips forward shift. Range: 0-10. Default: 3.

    Returns:
        bool: True if lines are tangled (no strict bullish or bearish alignment).
    """
    lines = _alligator_lines(df, jaw, teeth, lips, jaw_offset, teeth_offset, lips_offset)
    if lines is None:
        return False
    jaw_s, teeth_s, lips_s = lines
    if pd.isna(jaw_s.iloc[-1]) or pd.isna(teeth_s.iloc[-1]) or pd.isna(lips_s.iloc[-1]):
        return False
    j, t, l = jaw_s.iloc[-1], teeth_s.iloc[-1], lips_s.iloc[-1]
    bullish = l > t > j
    bearish = l < t < j
    return not (bullish or bearish)

@RuleRegistry.register("alma_cross_down")
def alma_cross_down(
    df: pd.DataFrame,
    window_fast: int = 9,
    window_slow: int = 21,
    offset: float = 0.85,
    sigma: float = 6.0,
) -> bool:
    """Signal: alma_cross_down

    Detect a bearish ALMA crossover (fast ALMA crosses below slow ALMA).

    Warmup: window_slow

    Formula:
        alma(window_fast)[t-1] >= alma(window_slow)[t-1] and alma(window_fast)[t] < alma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast ALMA window
        window_slow [default=21, min=2, max=200]: Slow ALMA window
        offset [default=0.85, min=0.0]: Weight center, 0=oldest, 1=newest
        sigma [default=6.0, min=0.1]: Gaussian spread. Higher = smoother

    Outputs:
        fired [boolean, 0..1]:
            True if bearish ALMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast ALMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow ALMA window. Range: 2-200. Default: 21.
        offset (float): Weight center, 0=oldest, 1=newest. Range: 0.0-1.0. Default: 0.85.
        sigma (float): Gaussian spread. Higher = smoother. Range: 0.1-20.0. Default: 6.0.

    Returns:
        bool: True if bearish ALMA crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    common = {'offset': offset, 'sigma': sigma}
    fast = ALMA.compute(data={'close': closes}, params={'window': window_fast, **common})['alma']
    slow = ALMA.compute(data={'close': closes}, params={'window': window_slow, **common})['alma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)

@RuleRegistry.register("alma_cross_up")
def alma_cross_up(
    df: pd.DataFrame,
    window_fast: int = 9,
    window_slow: int = 21,
    offset: float = 0.85,
    sigma: float = 6.0,
) -> bool:
    """Signal: alma_cross_up

    Detect a bullish ALMA crossover (fast ALMA crosses above slow ALMA). Both ALMAs use the same
    offset and sigma; only the window differs.

    Warmup: window_slow

    Formula:
        alma(window_fast)[t-1] <= alma(window_slow)[t-1] and alma(window_fast)[t] > alma(window_slow)[t] -- both ALMAs share offset and sigma; only the window differs

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast ALMA window
        window_slow [default=21, min=2, max=200]: Slow ALMA window
        offset [default=0.85, min=0.0]: Weight center, 0=oldest, 1=newest
        sigma [default=6.0, min=0.1]: Gaussian spread. Higher = smoother

    Outputs:
        fired [boolean, 0..1]:
            True if bullish ALMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast ALMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow ALMA window. Range: 2-200. Default: 21.
        offset (float): Weight center, 0=oldest, 1=newest. Range: 0.0-1.0. Default: 0.85.
        sigma (float): Gaussian spread. Higher = smoother. Range: 0.1-20.0. Default: 6.0.

    Returns:
        bool: True if bullish ALMA crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False
    common = {'offset': offset, 'sigma': sigma}
    fast = ALMA.compute(data={'close': closes}, params={'window': window_fast, **common})['alma']
    slow = ALMA.compute(data={'close': closes}, params={'window': window_slow, **common})['alma']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)

@RuleRegistry.register("dema_cross_down")
def dema_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: dema_cross_down

    Detect a bearish DEMA crossover (fast DEMA crosses below slow DEMA). Lower-lag equivalent of an
    SMA/EMA death cross.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/double-exponential-moving-average-dema
    Warmup: window_slow

    Formula:
        dema(window_fast)[t-1] >= dema(window_slow)[t-1] and dema(window_fast)[t] < dema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast DEMA window
        window_slow [default=21, min=2, max=200]: Slow DEMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish DEMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast DEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow DEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bearish DEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, DEMA, 'dema', window_fast, window_slow, "bearish")

@RuleRegistry.register("dema_cross_up")
def dema_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: dema_cross_up

    Detect a bullish DEMA crossover (fast DEMA crosses above slow DEMA). Lower-lag equivalent of an
    SMA/EMA golden cross.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/double-exponential-moving-average-dema
    Warmup: window_slow

    Formula:
        dema(window_fast)[t-1] <= dema(window_slow)[t-1] and dema(window_fast)[t] > dema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast DEMA window
        window_slow [default=21, min=2, max=200]: Slow DEMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish DEMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast DEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow DEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bullish DEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, DEMA, 'dema', window_fast, window_slow, "bullish")

@RuleRegistry.register("ema_cross_down")
def ema_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: ema_cross_down

    Detect bearish EMA crossover (fast EMA crosses below slow EMA). Common periods: 9/21
    (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        ema(window_fast)[t-1] >= ema(window_slow)[t-1] and ema(window_fast)[t] < ema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast EMA window
        window_slow [default=21, min=5, max=200]: Slow EMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish crossover detected, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow EMA window. Range: 5-200. Default: 21.

    Returns:
        bool: True if bearish crossover detected, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False

    fast_result = EMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_ema = fast_result['ema']
    slow_result = EMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_ema = slow_result['ema']

    if len(fast_ema) < 2:
        return False

    prev_fast = fast_ema.iloc[-2]
    prev_slow = slow_ema.iloc[-2]
    curr_fast = fast_ema.iloc[-1]
    curr_slow = slow_ema.iloc[-1]

    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False

    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)

@RuleRegistry.register("ema_cross_up")
def ema_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: ema_cross_up

    Detect bullish EMA crossover (fast EMA crosses above slow EMA). Common periods: 9/21
    (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        ema(window_fast)[t-1] <= ema(window_slow)[t-1] and ema(window_fast)[t] > ema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast EMA window
        window_slow [default=21, min=5, max=200]: Slow EMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish crossover detected, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow EMA window. Range: 5-200. Default: 21.

    Returns:
        bool: True if bullish crossover detected, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False

    fast_result = EMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_ema = fast_result['ema']
    slow_result = EMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_ema = slow_result['ema']

    if len(fast_ema) < 2:
        return False

    prev_fast = fast_ema.iloc[-2]
    prev_slow = slow_ema.iloc[-2]
    curr_fast = fast_ema.iloc[-1]
    curr_slow = slow_ema.iloc[-1]

    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False

    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)

@RuleRegistry.register("ema_crossover")
def ema_crossover(df: pd.DataFrame, window_fast: int, window_slow: int, direction: str = "bullish") -> bool:
    """Signal: ema_crossover

    Detect an EMA crossover signal with configurable direction (bullish or bearish). Uses EMA
    indicator to calculate window_fast and window_slow EMAs. Returns True when a crossover is
    detected in the specified direction. Bullish crossover: window_fast EMA crosses above
    window_slow EMA Bearish crossover: window_fast EMA crosses below window_slow EMA The crossover
    detection compares the previous and current bars: - Bullish: prev window_fast <= prev
    window_slow AND current window_fast > current window_slow - Bearish: prev window_fast >= prev
    window_slow AND current window_fast < current window_slow Common periods: 9/21 (short-term),
    50/200 (long-term). Adjust for crypto's 24/7 markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        direction == 'bullish': ema(window_fast)[t-1] <= ema(window_slow)[t-1] and ema(window_fast)[t] > ema(window_slow)[t]; direction == 'bearish': ema(window_fast)[t-1] >= ema(window_slow)[t-1] and ema(window_fast)[t] < ema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [min=1, max=200]: Fast EMA window in bars
        window_slow [min=1, max=200]: Slow EMA window in bars
        direction: Crossover direction, 'bullish' or 'bearish'

    Outputs:
        fired [boolean, 0..1]:
            True if crossover detected in the specified direction, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EMA window in bars. Range: 1-200.
        window_slow (int): Slow EMA window in bars. Range: 1-200.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if crossover detected in the specified direction, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window_slow + 1:
        return False

    fast_result = EMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_ema = fast_result['ema']
    slow_result = EMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_ema = slow_result['ema']

    if len(fast_ema) < 2:
        return False

    prev_fast = fast_ema.iloc[-2]
    prev_slow = slow_ema.iloc[-2]
    curr_fast = fast_ema.iloc[-1]
    curr_slow = slow_ema.iloc[-1]

    # Check for NaN values
    if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow):
        return False

    if direction.lower() == "bullish":
        # Bullish crossover: window_fast was below or equal to window_slow, now window_fast is above window_slow
        return prev_fast <= prev_slow and curr_fast > curr_slow
    elif direction.lower() == "bearish":
        # Bearish crossover: window_fast was above or equal to window_slow, now window_fast is below window_slow
        return prev_fast >= prev_slow and curr_fast < curr_slow
    else:
        logger.warning(f"Unknown direction '{direction}', expected 'bullish' or 'bearish'")
        return False

@RuleRegistry.register("hma_cross_down")
def hma_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 25) -> bool:
    """Signal: hma_cross_down

    Detect a bearish HMA crossover (fast HMA crosses below slow HMA). Low-lag crossover; fires
    earlier than SMA/EMA equivalents.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/hull-moving-average-hma
    Warmup: window_slow

    Formula:
        hma(window_fast)[t-1] >= hma(window_slow)[t-1] and hma(window_fast)[t] < hma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=4, max=100]: Fast HMA window
        window_slow [default=25, min=4, max=200]: Slow HMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish HMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast HMA window. Range: 4-100. Default: 9.
        window_slow (int): Slow HMA window. Range: 4-200. Default: 25.

    Returns:
        bool: True if bearish HMA crossover detected on the current bar.
    """
    return _ma_crossover(df, HMA, 'hma', window_fast, window_slow, "bearish")

@RuleRegistry.register("hma_cross_up")
def hma_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 25) -> bool:
    """Signal: hma_cross_up

    Detect a bullish HMA crossover (fast HMA crosses above slow HMA). Low-lag crossover; fires
    earlier than SMA/EMA equivalents.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/hull-moving-average-hma
    Warmup: window_slow

    Formula:
        hma(window_fast)[t-1] <= hma(window_slow)[t-1] and hma(window_fast)[t] > hma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=4, max=100]: Fast HMA window
        window_slow [default=25, min=4, max=200]: Slow HMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish HMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast HMA window. Range: 4-100. Default: 9.
        window_slow (int): Slow HMA window. Range: 4-200. Default: 25.

    Returns:
        bool: True if bullish HMA crossover detected on the current bar.
    """
    return _ma_crossover(df, HMA, 'hma', window_fast, window_slow, "bullish")

@RuleRegistry.register("is_above_alma")
def is_above_alma(df: pd.DataFrame, window: int = 21, offset: float = 0.85, sigma: float = 6.0) -> bool:
    """Signal: is_above_alma

    Check if the current price is above the Arnaud Legoux Moving Average (ALMA). ALMA is a
    Gaussian-weighted MA that can be tuned to react faster (offset near 1, lower sigma) or smoother
    (offset near 0, higher sigma).

    Warmup: window - 1

    Formula:
        close[t] > alma[t]

    Inputs:
        close: closing price

    Params:
        window [default=21, min=2, max=200]: ALMA window in bars
        offset [default=0.85, min=0.0]: Weight center, 0=oldest, 1=newest
        sigma [default=6.0, min=0.1]: Gaussian spread. Higher = smoother

    Outputs:
        fired [boolean, 0..1]:
            True if close > ALMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): ALMA window in bars. Range: 2-200. Default: 21.
        offset (float): Weight center, 0=oldest, 1=newest. Range: 0.0-1.0. Default: 0.85.
        sigma (float): Gaussian spread. Higher = smoother. Range: 0.1-20.0. Default: 6.0.

    Returns:
        bool: True if close > ALMA, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window:
        return False
    result = ALMA.compute(data={'close': closes}, params={'window': window, 'offset': offset, 'sigma': sigma})
    alma = result['alma']
    if alma.empty or pd.isna(alma.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > alma.iloc[-1])

@RuleRegistry.register("is_above_dema")
def is_above_dema(df: pd.DataFrame, window: int = 21) -> bool:
    """Signal: is_above_dema

    Check if the current price is above the Double Exponential Moving Average (DEMA). DEMA reduces
    lag compared to a standard EMA by combining two EMA passes. Useful for trend-following filters
    where responsiveness matters.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/double-exponential-moving-average-dema
    Warmup: window - 1

    Formula:
        close[t] > dema[t]

    Inputs:
        close: closing price

    Params:
        window [default=21, min=2, max=200]: DEMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > DEMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): DEMA window in bars. Range: 2-200. Default: 21.

    Returns:
        bool: True if close > DEMA, False otherwise.
    """
    return _ma_is_above(df, DEMA, 'dema', window)

@RuleRegistry.register("is_above_hma")
def is_above_hma(df: pd.DataFrame, window: int = 16) -> bool:
    """Signal: is_above_hma

    Check if the current price is above the Hull Moving Average (HMA). HMA tracks price with very
    low lag while remaining smoother than WMA. A common crypto trend filter.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/hull-moving-average-hma
    Warmup: window - 1

    Formula:
        close[t] > hma[t]

    Inputs:
        close: closing price

    Params:
        window [default=16, min=4, max=200]: HMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > HMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): HMA window in bars. Range: 4-200. Default: 16.

    Returns:
        bool: True if close > HMA, False otherwise.
    """
    return _ma_is_above(df, HMA, 'hma', window)

@RuleRegistry.register("is_above_mama")
def is_above_mama(df: pd.DataFrame, fast_limit: float = 0.5, slow_limit: float = 0.05, warmup_bars: int = 64) -> bool:
    """Signal: is_above_mama

    Check if the current price is above the MESA Adaptive Moving Average (MAMA). MAMA adapts its
    smoothing to volatility via a Hilbert transform.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: warmup_bars

    Formula:
        close[t] > mama[t]

    Inputs:
        close: closing price

    Params:
        fast_limit [default=0.5, min=0.1]: Upper alpha bound (fast response)
        slow_limit [default=0.05, min=0.01]: Lower alpha bound (slow response)
        warmup_bars [default=64, min=6, max=200]: Leading bars discarded as contaminated by the zero
        seed

    Outputs:
        fired [boolean, 0..1]:
            True if close > MAMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast_limit (float): Upper alpha bound (fast response). Range: 0.1-1.0. Default: 0.5.
        slow_limit (float): Lower alpha bound (slow response). Range: 0.01-0.5. Default: 0.05.
        warmup_bars (int): Leading bars discarded as contaminated by the zero seed. Range: 6-200. Default: 64.

    Returns:
        bool: True if close > MAMA, False otherwise.
    """
    out = _mama_compute(df, fast_limit, slow_limit, warmup_bars)
    if out is None:
        return False
    mama, _ = out
    return bool(df["Close"].iloc[-1] > mama.iloc[-1])

@RuleRegistry.register("is_above_sma")
def is_above_sma(df: pd.DataFrame, window: int) -> bool:
    """Signal: is_above_sma

    Check if the current price is above the Simple Moving Average. Uses SMA indicator to calculate
    the SMA for the given window and returns True if the most recent close price is strictly greater
    than the SMA value. Returns False if insufficient data is available. Common periods: 9/21
    (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window - 1

    Formula:
        close[t] > sma[t]

    Inputs:
        close: closing price

    Params:
        window [min=1, max=200]: SMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > SMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): SMA window in bars. Range: 1-200.

    Returns:
        bool: True if close > SMA, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window:
        return False

    result = SMA.compute(data={'close': closes}, params={'window': window})
    sma = result['sma']

    if sma.empty or pd.isna(sma.iloc[-1]):
        return False

    return closes.iloc[-1] > sma.iloc[-1]

@RuleRegistry.register("is_above_smma")
def is_above_smma(df: pd.DataFrame, window: int = 14) -> bool:
    """Signal: is_above_smma

    Check if the current price is above the Smoothed Moving Average (SMMA / Wilder's). SMMA uses
    Wilder's smoothing (alpha=1/n) rather than EMA's 2/(n+1), producing a slower, more stable trend
    line. Same family used inside RSI and ATR.

    Warmup: window - 1

    Formula:
        close[t] > smma[t]

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=200]: SMMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > SMMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): SMMA window in bars. Range: 2-200. Default: 14.

    Returns:
        bool: True if close > SMMA, False otherwise.
    """
    return _ma_is_above(df, SMMA, 'smma', window)

@RuleRegistry.register("is_above_t3")
def is_above_t3(df: pd.DataFrame, window: int = 10, volume_factor: float = 0.7) -> bool:
    """Signal: is_above_t3

    Check if the current price is above the Tillson T3 moving average. T3 is a smooth low-lag MA
    that combines 6 EMAs via the volume factor.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window * 6 - 1

    Formula:
        close[t] > t3[t]

    Inputs:
        close: closing price

    Params:
        window [default=10, min=2, max=200]: T3 window in bars
        volume_factor [default=0.7, min=0.0]: Tillson volume factor, controls smoothness

    Outputs:
        fired [boolean, 0..1]:
            True if close > T3, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): T3 window in bars. Range: 2-200. Default: 10.
        volume_factor (float): Tillson volume factor, controls smoothness. Range: 0.0-1.0. Default: 0.7.

    Returns:
        bool: True if close > T3, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window * 6:
        return False
    result = T3.compute(data={'close': closes}, params={'window': window, 'volume_factor': volume_factor})
    t3 = result['t3']
    if t3.empty or pd.isna(t3.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > t3.iloc[-1])

@RuleRegistry.register("is_above_tema")
def is_above_tema(df: pd.DataFrame, window: int = 21) -> bool:
    """Signal: is_above_tema

    Check if the current price is above the Triple Exponential Moving Average (TEMA). TEMA has even
    less lag than DEMA by combining three EMA passes.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/triple-exponential-moving-average-tema
    Warmup: window - 1

    Formula:
        close[t] > tema[t]

    Inputs:
        close: closing price

    Params:
        window [default=21, min=2, max=200]: TEMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > TEMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TEMA window in bars. Range: 2-200. Default: 21.

    Returns:
        bool: True if close > TEMA, False otherwise.
    """
    return _ma_is_above(df, TEMA, 'tema', window)

@RuleRegistry.register("is_above_trima")
def is_above_trima(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: is_above_trima

    Check if the current price is above the Triangular Moving Average (TRIMA). TRIMA is a
    double-smoothed SMA that weights the middle of the window more heavily, producing a smoother
    trend line than SMA.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window - 1

    Formula:
        close[t] > trima[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=2, max=200]: TRIMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > TRIMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): TRIMA window in bars. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > TRIMA, False otherwise.
    """
    return _ma_is_above(df, TRIMA, 'trima', window)

@RuleRegistry.register("ma_ribbon_bearish")
def ma_ribbon_bearish(df: pd.DataFrame, windows: tuple = _DEFAULT_RIBBON_WINDOWS) -> bool:
    """Signal: ma_ribbon_bearish

    Check if all MAs in the ribbon are in strict bearish alignment (faster below slower).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-average-ribbon
    Warmup: max(windows_list) - 1

    Formula:
        sma(windows[0])[t] < sma(windows[1])[t] < ... < sma(windows[-1])[t]

    Inputs:
        close: closing price

    Params:
        windows [min=2, max=1000]: Strictly increasing tuple of SMA periods

    Outputs:
        fired [boolean, 0..1]:
            True if ribbon is bearish-aligned on the current bar

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        windows (tuple): Strictly increasing tuple of SMA periods. Range: 2-1000 per element. Default: (5, 8, 13, 21, 34, 55, 89, 144).

    Returns:
        bool: True if ribbon is bearish-aligned on the current bar.
    """
    closes = df["Close"]
    windows_list = list(windows)
    if len(closes) < max(windows_list):
        return False
    return _ribbon_alignment(closes, windows_list) == "bearish"

@RuleRegistry.register("ma_ribbon_bullish")
def ma_ribbon_bullish(df: pd.DataFrame, windows: tuple = _DEFAULT_RIBBON_WINDOWS) -> bool:
    """Signal: ma_ribbon_bullish

    Check if all MAs in the ribbon are in strict bullish alignment (faster above slower). Uses 8
    Fibonacci-spaced SMAs by default. Strict alignment means SMA(5) > SMA(8) > SMA(13) > ... >
    SMA(144). This is a strong trend filter -- when true, the market is in a clear uptrend across
    all horizons.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-average-ribbon
    Warmup: max(windows_list) - 1

    Formula:
        sma(windows[0])[t] > sma(windows[1])[t] > ... > sma(windows[-1])[t] -- shortest window on top, every gap the same sign

    Inputs:
        close: closing price

    Params:
        windows [min=2, max=1000]: Strictly increasing tuple of SMA periods

    Outputs:
        fired [boolean, 0..1]:
            True if ribbon is bullish-aligned on the current bar

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        windows (tuple): Strictly increasing tuple of SMA periods. Range: 2-1000 per element. Default: (5, 8, 13, 21, 34, 55, 89, 144).

    Returns:
        bool: True if ribbon is bullish-aligned on the current bar.
    """
    closes = df["Close"]
    windows_list = list(windows)
    if len(closes) < max(windows_list):
        return False
    return _ribbon_alignment(closes, windows_list) == "bullish"

@RuleRegistry.register("ma_ribbon_tangled")
def ma_ribbon_tangled(df: pd.DataFrame, windows: tuple = _DEFAULT_RIBBON_WINDOWS) -> bool:
    """Signal: ma_ribbon_tangled

    Check if MAs in the ribbon are tangled (no strict alignment -- consolidation filter). Useful as
    a no-trade filter during choppy markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-average-ribbon
    Warmup: max(windows_list) - 1

    Formula:
        neither the bullish nor the bearish ordering holds across all of windows

    Inputs:
        close: closing price

    Params:
        windows [min=2, max=1000]: Strictly increasing tuple of SMA periods

    Outputs:
        fired [boolean, 0..1]:
            True if ribbon is neither bullish nor bearish aligned

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        windows (tuple): Strictly increasing tuple of SMA periods. Range: 2-1000 per element. Default: (5, 8, 13, 21, 34, 55, 89, 144).

    Returns:
        bool: True if ribbon is neither bullish nor bearish aligned.
    """
    closes = df["Close"]
    windows_list = list(windows)
    if len(closes) < max(windows_list):
        return False
    return _ribbon_alignment(closes, windows_list) == "tangled"

@RuleRegistry.register("mama_cross_down")
def mama_cross_down(df: pd.DataFrame, fast_limit: float = 0.5, slow_limit: float = 0.05, warmup_bars: int = 64) -> bool:
    """Signal: mama_cross_down

    Detect a bearish MAMA/FAMA crossover (MAMA crosses below FAMA). Classic Ehlers exit signal: MAMA
    falling below FAMA signals a downtrend.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: warmup_bars

    Formula:
        mama[t-1] >= fama[t-1] and mama[t] < fama[t]

    Inputs:
        close: closing price

    Params:
        fast_limit [default=0.5, min=0.1]: Upper alpha bound
        slow_limit [default=0.05, min=0.01]: Lower alpha bound

    Outputs:
        fired [boolean, 0..1]:
            True if bearish MAMA/FAMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast_limit (float): Upper alpha bound. Range: 0.1-1.0. Default: 0.5.
        slow_limit (float): Lower alpha bound. Range: 0.01-0.5. Default: 0.05.

    Returns:
        bool: True if bearish MAMA/FAMA crossover detected on the current bar.
    """
    out = _mama_compute(df, fast_limit, slow_limit, warmup_bars)
    if out is None:
        return False
    mama, fama = out
    if pd.isna(mama.iloc[-2]) or pd.isna(fama.iloc[-2]):
        return False
    return bool(mama.iloc[-2] >= fama.iloc[-2] and mama.iloc[-1] < fama.iloc[-1])

@RuleRegistry.register("mama_cross_up")
def mama_cross_up(df: pd.DataFrame, fast_limit: float = 0.5, slow_limit: float = 0.05, warmup_bars: int = 64) -> bool:
    """Signal: mama_cross_up

    Detect a bullish MAMA/FAMA crossover (MAMA crosses above FAMA). Classic Ehlers entry signal:
    MAMA rising above FAMA signals an uptrend.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: warmup_bars

    Formula:
        mama[t-1] <= fama[t-1] and mama[t] > fama[t] -- MAMA against its own following adaptive line FAMA, not a second window

    Inputs:
        close: closing price

    Params:
        fast_limit [default=0.5, min=0.1]: Upper alpha bound
        slow_limit [default=0.05, min=0.01]: Lower alpha bound

    Outputs:
        fired [boolean, 0..1]:
            True if bullish MAMA/FAMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        fast_limit (float): Upper alpha bound. Range: 0.1-1.0. Default: 0.5.
        slow_limit (float): Lower alpha bound. Range: 0.01-0.5. Default: 0.05.

    Returns:
        bool: True if bullish MAMA/FAMA crossover detected on the current bar.
    """
    out = _mama_compute(df, fast_limit, slow_limit, warmup_bars)
    if out is None:
        return False
    mama, fama = out
    if pd.isna(mama.iloc[-2]) or pd.isna(fama.iloc[-2]):
        return False
    return bool(mama.iloc[-2] <= fama.iloc[-2] and mama.iloc[-1] > fama.iloc[-1])

@RuleRegistry.register("price_above_ema")
def price_above_ema(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: price_above_ema

    Check if price is above the EMA. Common periods: 9/21 (short-term), 50/200 (long-term). Adjust
    for crypto's 24/7 markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window - 1

    Formula:
        close[t] > ema[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=2, max=200]: EMA window

    Outputs:
        fired [boolean, 0..1]:
            True if close > EMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EMA window. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > EMA, False otherwise.
    """
    closes = df["Close"]
    if len(closes) < window:
        return False

    result = EMA.compute(data={'close': closes}, params={'window': window})
    ema = result['ema']

    if pd.isna(ema.iloc[-1]):
        return False

    return float(closes.iloc[-1]) > float(ema.iloc[-1])

@RuleRegistry.register("sma_cross_down")
def sma_cross_down(df: pd.DataFrame, window_fast: int, window_slow: int) -> bool:
    """Signal: sma_cross_down

    Detect a bearish SMA crossover as an exit signal. Returns True when the window_fast SMA crosses
    below the window_slow SMA (death cross). This is a momentum-driven exit signal, indicating a
    transition from bullish to bearish momentum. Common periods: 9/21 (short-term), 50/200
    (long-term). Adjust for crypto's 24/7 markets. Note: This is a backwards-compatible wrapper
    around sma_crossover.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        sma(window_fast)[t-1] >= sma(window_slow)[t-1] and sma(window_fast)[t] < sma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [min=1, max=200]: Fast SMA window in bars
        window_slow [min=1, max=200]: Slow SMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if bearish crossover detected in the current bar, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window in bars. Range: 1-200.
        window_slow (int): Slow SMA window in bars. Range: 1-200.

    Returns:
        bool: True if bearish crossover detected in the current bar, False otherwise.
    """
    return sma_crossover(df, window_fast=window_fast, window_slow=window_slow, direction="bearish")

@RuleRegistry.register("sma_cross_up")
def sma_cross_up(df: pd.DataFrame, window_fast: int, window_slow: int) -> bool:
    """Signal: sma_cross_up

    Detect a bullish SMA crossover as an entry signal. Returns True when the window_fast SMA crosses
    above the window_slow SMA (golden cross). This is a momentum-driven entry signal, indicating a
    transition from bearish to bullish momentum. Common periods: 9/21 (short-term), 50/200
    (long-term). Adjust for crypto's 24/7 markets. Note: This is a backwards-compatible wrapper
    around sma_crossover.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        sma(window_fast)[t-1] <= sma(window_slow)[t-1] and sma(window_fast)[t] > sma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [min=1, max=200]: Fast SMA window in bars
        window_slow [min=1, max=200]: Slow SMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if bullish crossover detected in the current bar, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window in bars. Range: 1-200.
        window_slow (int): Slow SMA window in bars. Range: 1-200.

    Returns:
        bool: True if bullish crossover detected in the current bar, False otherwise.
    """
    return sma_crossover(df, window_fast=window_fast, window_slow=window_slow, direction="bullish")

@RuleRegistry.register("sma_crossover")
def sma_crossover(df: pd.DataFrame, window_fast: int, window_slow: int, direction: str = "bullish") -> bool:
    """Signal: sma_crossover

    Detect an SMA crossover signal with configurable direction (bullish or bearish). Uses SMA
    indicator to calculate window_fast and window_slow SMAs. Returns True when a crossover is
    detected in the specified direction. Bullish crossover (golden cross): window_fast SMA crosses
    above window_slow SMA Bearish crossover (death cross): window_fast SMA crosses below window_slow
    SMA The crossover detection compares the previous and current bars: - Bullish: prev window_fast
    <= prev window_slow AND current window_fast > current window_slow - Bearish: prev window_fast >=
    prev window_slow AND current window_fast < current window_slow Common periods: 9/21
    (short-term), 50/200 (long-term). Adjust for crypto's 24/7 markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
    Warmup: window_slow

    Formula:
        direction == 'bullish': sma(window_fast)[t-1] <= sma(window_slow)[t-1] and sma(window_fast)[t] > sma(window_slow)[t]; direction == 'bearish': sma(window_fast)[t-1] >= sma(window_slow)[t-1] and sma(window_fast)[t] < sma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [min=1, max=200]: Fast SMA window in bars
        window_slow [min=1, max=200]: Slow SMA window in bars
        direction: Crossover direction, 'bullish' or 'bearish'

    Outputs:
        fired [boolean, 0..1]:
            True if crossover detected in the specified direction, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMA window in bars. Range: 1-200.
        window_slow (int): Slow SMA window in bars. Range: 1-200.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if crossover detected in the specified direction, False otherwise.
    """
    closes = df["Close"]
    # window_slow + 1, not window_slow: a crossing compares two bars, and with exactly window_slow
    # bars the slow SMA has a single value, so there is no previous bar to compare against. The
    # NaN check below already returned False there, so this changes no result -- it makes the bound
    # state what the signal actually needs, which is what the ontology lifts as warmup_bars. Every
    # other two-average crossing in this file already guards on `window_slow + 1`.
    if len(closes) < window_slow + 1:
        return False

    # Calculate SMAs
    fast_result = SMA.compute(data={'close': closes}, params={'window': window_fast})
    fast_sma = fast_result['sma']
    slow_result = SMA.compute(data={'close': closes}, params={'window': window_slow})
    slow_sma = slow_result['sma']

    # Check if we have enough data for the crossover (need 2 bars to detect crossing)
    if len(fast_sma) < 2 or len(slow_sma) < 2:
        return False

    # Get current and previous values
    current_fast = fast_sma.iloc[-1]
    current_slow = slow_sma.iloc[-1]
    prev_fast = fast_sma.iloc[-2]
    prev_slow = slow_sma.iloc[-2]

    # Check for NaN values
    if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
        return False

    if direction.lower() == "bullish":
        return prev_fast <= prev_slow and current_fast > current_slow
    elif direction.lower() == "bearish":
        # Bearish crossover: window_fast was above or equal to window_slow, now window_fast is below window_slow
        return prev_fast >= prev_slow and current_fast < current_slow
    else:
        logger.warning(f"Unknown direction '{direction}', expected 'bullish' or 'bearish'")
        return False

@RuleRegistry.register("smma_cross_down")
def smma_cross_down(df: pd.DataFrame, window_fast: int = 14, window_slow: int = 50) -> bool:
    """Signal: smma_cross_down

    Detect a bearish SMMA crossover (fast SMMA crosses below slow SMMA). Slower, more stable
    crossover than EMA cross; fewer false triggers.

    Warmup: window_slow

    Formula:
        smma(window_fast)[t-1] >= smma(window_slow)[t-1] and smma(window_fast)[t] < smma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=14, min=2, max=100]: Fast SMMA window
        window_slow [default=50, min=2, max=200]: Slow SMMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish SMMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMMA window. Range: 2-100. Default: 14.
        window_slow (int): Slow SMMA window. Range: 2-200. Default: 50.

    Returns:
        bool: True if bearish SMMA crossover detected on the current bar.
    """
    return _ma_crossover(df, SMMA, 'smma', window_fast, window_slow, "bearish")

@RuleRegistry.register("smma_cross_up")
def smma_cross_up(df: pd.DataFrame, window_fast: int = 14, window_slow: int = 50) -> bool:
    """Signal: smma_cross_up

    Detect a bullish SMMA crossover (fast SMMA crosses above slow SMMA). Slower, more stable
    crossover than EMA cross; fewer false triggers.

    Warmup: window_slow

    Formula:
        smma(window_fast)[t-1] <= smma(window_slow)[t-1] and smma(window_fast)[t] > smma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=14, min=2, max=100]: Fast SMMA window
        window_slow [default=50, min=2, max=200]: Slow SMMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish SMMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast SMMA window. Range: 2-100. Default: 14.
        window_slow (int): Slow SMMA window. Range: 2-200. Default: 50.

    Returns:
        bool: True if bullish SMMA crossover detected on the current bar.
    """
    return _ma_crossover(df, SMMA, 'smma', window_fast, window_slow, "bullish")

@RuleRegistry.register("t3_cross_down")
def t3_cross_down(
    df: pd.DataFrame,
    window_fast: int = 5,
    window_slow: int = 10,
    volume_factor: float = 0.7,
) -> bool:
    """Signal: t3_cross_down

    Detect a bearish T3 crossover (fast T3 crosses below slow T3).

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window_slow * 6

    Formula:
        t3(window_fast)[t-1] >= t3(window_slow)[t-1] and t3(window_fast)[t] < t3(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=5, min=2, max=100]: Fast T3 window
        window_slow [default=10, min=2, max=200]: Slow T3 window
        volume_factor [default=0.7, min=0.0]: Tillson volume factor

    Outputs:
        fired [boolean, 0..1]:
            True if bearish T3 crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast T3 window. Range: 2-100. Default: 5.
        window_slow (int): Slow T3 window. Range: 2-200. Default: 10.
        volume_factor (float): Tillson volume factor. Range: 0.0-1.0. Default: 0.7.

    Returns:
        bool: True if bearish T3 crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow * 6 + 1:
        return False
    common = {'volume_factor': volume_factor}
    fast = T3.compute(data={'close': closes}, params={'window': window_fast, **common})['t3']
    slow = T3.compute(data={'close': closes}, params={'window': window_slow, **common})['t3']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)

@RuleRegistry.register("t3_cross_up")
def t3_cross_up(
    df: pd.DataFrame,
    window_fast: int = 5,
    window_slow: int = 10,
    volume_factor: float = 0.7,
) -> bool:
    """Signal: t3_cross_up

    Detect a bullish T3 crossover (fast T3 crosses above slow T3). Very smooth, low-lag crossover.
    Both T3s share the same volume_factor.

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window_slow * 6

    Formula:
        t3(window_fast)[t-1] <= t3(window_slow)[t-1] and t3(window_fast)[t] > t3(window_slow)[t] -- both T3s share volume_factor

    Inputs:
        close: closing price

    Params:
        window_fast [default=5, min=2, max=100]: Fast T3 window
        window_slow [default=10, min=2, max=200]: Slow T3 window
        volume_factor [default=0.7, min=0.0]: Tillson volume factor

    Outputs:
        fired [boolean, 0..1]:
            True if bullish T3 crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast T3 window. Range: 2-100. Default: 5.
        window_slow (int): Slow T3 window. Range: 2-200. Default: 10.
        volume_factor (float): Tillson volume factor. Range: 0.0-1.0. Default: 0.7.

    Returns:
        bool: True if bullish T3 crossover detected on the current bar.
    """
    closes = df["Close"]
    if len(closes) < window_slow * 6 + 1:
        return False
    common = {'volume_factor': volume_factor}
    fast = T3.compute(data={'close': closes}, params={'window': window_fast, **common})['t3']
    slow = T3.compute(data={'close': closes}, params={'window': window_slow, **common})['t3']
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)

@RuleRegistry.register("tema_cross_down")
def tema_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: tema_cross_down

    Detect a bearish TEMA crossover (fast TEMA crosses below slow TEMA). Very low-lag cross signal;
    expect more whipsaw in noisy markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/triple-exponential-moving-average-tema
    Warmup: window_slow

    Formula:
        tema(window_fast)[t-1] >= tema(window_slow)[t-1] and tema(window_fast)[t] < tema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast TEMA window
        window_slow [default=21, min=2, max=200]: Slow TEMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish TEMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow TEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bearish TEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TEMA, 'tema', window_fast, window_slow, "bearish")

@RuleRegistry.register("tema_cross_up")
def tema_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: tema_cross_up

    Detect a bullish TEMA crossover (fast TEMA crosses above slow TEMA). Very low-lag cross signal;
    expect more whipsaw in noisy markets.

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/triple-exponential-moving-average-tema
    Warmup: window_slow

    Formula:
        tema(window_fast)[t-1] <= tema(window_slow)[t-1] and tema(window_fast)[t] > tema(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=100]: Fast TEMA window
        window_slow [default=21, min=2, max=200]: Slow TEMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish TEMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TEMA window. Range: 2-100. Default: 9.
        window_slow (int): Slow TEMA window. Range: 2-200. Default: 21.

    Returns:
        bool: True if bullish TEMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TEMA, 'tema', window_fast, window_slow, "bullish")

@RuleRegistry.register("trima_cross_down")
def trima_cross_down(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """Signal: trima_cross_down

    Detect a bearish TRIMA crossover (fast TRIMA crosses below slow TRIMA).

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window_slow

    Formula:
        trima(window_fast)[t-1] >= trima(window_slow)[t-1] and trima(window_fast)[t] < trima(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=10, min=2, max=100]: Fast TRIMA window
        window_slow [default=30, min=2, max=200]: Slow TRIMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish TRIMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TRIMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow TRIMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bearish TRIMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TRIMA, 'trima', window_fast, window_slow, "bearish")

@RuleRegistry.register("trima_cross_up")
def trima_cross_up(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """Signal: trima_cross_up

    Detect a bullish TRIMA crossover (fast TRIMA crosses above slow TRIMA).

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window_slow

    Formula:
        trima(window_fast)[t-1] <= trima(window_slow)[t-1] and trima(window_fast)[t] > trima(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=10, min=2, max=100]: Fast TRIMA window
        window_slow [default=30, min=2, max=200]: Slow TRIMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish TRIMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast TRIMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow TRIMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bullish TRIMA crossover detected on the current bar.
    """
    return _ma_crossover(df, TRIMA, 'trima', window_fast, window_slow, "bullish")

@RuleRegistry.register("wma_cross_down")
def wma_cross_down(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: wma_cross_down

    Check if fast WMA crosses below slow WMA (bearish).

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window_slow

    Formula:
        wma(window_fast)[t-1] >= wma(window_slow)[t-1] and wma(window_fast)[t] < wma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=50]: Fast WMA window
        window_slow [default=21, min=10, max=100]: Slow WMA window

    Outputs:
        fired [boolean, 0..1]:
            True if fast WMA crosses below slow WMA, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast WMA window. Range: 2-50. Default: 9.
        window_slow (int): Slow WMA window. Range: 10-100. Default: 21.

    Returns:
        bool: True if fast WMA crosses below slow WMA, False otherwise.
    """
    if len(df) < window_slow + 1:
        return False

    fast_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_fast})
    fast_wma = fast_result['wma']
    slow_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_slow})
    slow_wma = slow_result['wma']

    if len(fast_wma) < 2 or pd.isna(fast_wma.iloc[-1]) or pd.isna(slow_wma.iloc[-1]):
        return False

    prev_above = float(fast_wma.iloc[-2]) >= float(slow_wma.iloc[-2])
    curr_below = float(fast_wma.iloc[-1]) < float(slow_wma.iloc[-1])

    return prev_above and curr_below

@RuleRegistry.register("wma_cross_up")
def wma_cross_up(df: pd.DataFrame, window_fast: int = 9, window_slow: int = 21) -> bool:
    """Signal: wma_cross_up

    Check if fast WMA crosses above slow WMA (bullish).

    Reference: https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html
    Warmup: window_slow

    Formula:
        wma(window_fast)[t-1] <= wma(window_slow)[t-1] and wma(window_fast)[t] > wma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=9, min=2, max=50]: Fast WMA window
        window_slow [default=21, min=10, max=100]: Slow WMA window

    Outputs:
        fired [boolean, 0..1]:
            True if fast WMA crosses above slow WMA, False otherwise

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast WMA window. Range: 2-50. Default: 9.
        window_slow (int): Slow WMA window. Range: 10-100. Default: 21.

    Returns:
        bool: True if fast WMA crosses above slow WMA, False otherwise.
    """
    if len(df) < window_slow + 1:
        return False

    fast_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_fast})
    fast_wma = fast_result['wma']
    slow_result = WMA.compute(data={'close': df["Close"]}, params={'window': window_slow})
    slow_wma = slow_result['wma']

    if len(fast_wma) < 2 or pd.isna(fast_wma.iloc[-1]) or pd.isna(slow_wma.iloc[-1]):
        return False

    prev_below = float(fast_wma.iloc[-2]) <= float(slow_wma.iloc[-2])
    curr_above = float(fast_wma.iloc[-1]) > float(slow_wma.iloc[-1])

    return prev_below and curr_above

# ---------------------------------------------------------------------------
# Moved from trend.py once EPMA, Ichimoku and HeikinAshi were classed `averaging`.
# All three emit reference levels in price units; the class asks what the output IS.
# ---------------------------------------------------------------------------

@RuleRegistry.register("ichimoku_bullish")
def ichimoku_bullish(df: pd.DataFrame, window_tenkan: int = 9, window_kijun: int = 26, window_senkou: int = 52) -> bool:
    """Signal: ichimoku_bullish

    Check if Ichimoku indicates bullish signal (price above cloud).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/ichimoku-cloud
    Warmup: window_senkou - 1

    Formula:
        close[t] > max(span_a[t], span_b[t]) -- above the cloud, whichever span is on top

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_tenkan [default=9, min=5, max=20]: Tenkan-sen (conversion line) window
        window_kijun [default=26, min=15, max=40]: Kijun-sen (base line) window
        window_senkou [default=52, min=30, max=70]: Senkou Span B (leading span B) window

    Outputs:
        fired [boolean, 0..1]:
            True if price above cloud, False otherwise

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_tenkan (int): Tenkan-sen (conversion line) window. Range: 5-20. Default: 9.
        window_kijun (int): Kijun-sen (base line) window. Range: 15-40. Default: 26.
        window_senkou (int): Senkou Span B (leading span B) window. Range: 30-70. Default: 52.

    Returns:
        bool: True if price above cloud, False otherwise.
    """
    if len(df) < window_senkou:
        return False

    result = Ichimoku.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_tenkan, 'window2': window_kijun, 'window3': window_senkou, 'visual': False}
    )
    span_a = result['span_a']
    span_b = result['span_b']

    if pd.isna(span_a.iloc[-1]) or pd.isna(span_b.iloc[-1]):
        return False

    cloud_top = max(float(span_a.iloc[-1]), float(span_b.iloc[-1]))
    close = float(df["Close"].iloc[-1])

    return close > cloud_top

@RuleRegistry.register("ichimoku_bearish")
def ichimoku_bearish(df: pd.DataFrame, window_tenkan: int = 9, window_kijun: int = 26, window_senkou: int = 52) -> bool:
    """Signal: ichimoku_bearish

    Check if Ichimoku indicates bearish signal (price below cloud).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/ichimoku-cloud
    Warmup: window_senkou - 1

    Formula:
        close[t] < min(span_a[t], span_b[t])

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_tenkan [default=9, min=5, max=20]: Tenkan-sen (conversion line) window
        window_kijun [default=26, min=15, max=40]: Kijun-sen (base line) window
        window_senkou [default=52, min=30, max=70]: Senkou Span B (leading span B) window

    Outputs:
        fired [boolean, 0..1]:
            True if price below cloud, False otherwise

    Type: FILTER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_tenkan (int): Tenkan-sen (conversion line) window. Range: 5-20. Default: 9.
        window_kijun (int): Kijun-sen (base line) window. Range: 15-40. Default: 26.
        window_senkou (int): Senkou Span B (leading span B) window. Range: 30-70. Default: 52.

    Returns:
        bool: True if price below cloud, False otherwise.
    """
    if len(df) < window_senkou:
        return False

    result = Ichimoku.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_tenkan, 'window2': window_kijun, 'window3': window_senkou, 'visual': False}
    )
    span_a = result['span_a']
    span_b = result['span_b']

    if pd.isna(span_a.iloc[-1]) or pd.isna(span_b.iloc[-1]):
        return False

    cloud_bottom = min(float(span_a.iloc[-1]), float(span_b.iloc[-1]))
    close = float(df["Close"].iloc[-1])

    return close < cloud_bottom

@RuleRegistry.register("ichimoku_tk_cross")
def ichimoku_tk_cross(df: pd.DataFrame, window_tenkan: int = 9, window_kijun: int = 26, window_senkou: int = 52, direction: str = "bullish") -> bool:
    """Signal: ichimoku_tk_cross

    Check if Tenkan-sen crosses Kijun-sen (TK cross).

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/ichimoku-cloud
    Warmup: window_senkou

    Formula:
        direction == 'bullish': conversion_line[t-1] <= base_line[t-1] and conversion_line[t] > base_line[t]; direction == 'bearish': conversion_line[t-1] >= base_line[t-1] and conversion_line[t] < base_line[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_tenkan [default=9, min=5, max=20]: Tenkan-sen (conversion line) window
        window_kijun [default=26, min=15, max=40]: Kijun-sen (base line) window
        window_senkou [default=52, min=30, max=70]: Senkou Span B (leading span B) window
        direction: Crossover direction, 'bullish' or 'bearish'

    Outputs:
        fired [boolean, 0..1]:
            True if TK cross detected, False otherwise

    Type: TRIGGER
    Requires: High, Low

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_tenkan (int): Tenkan-sen (conversion line) window. Range: 5-20. Default: 9.
        window_kijun (int): Kijun-sen (base line) window. Range: 15-40. Default: 26.
        window_senkou (int): Senkou Span B (leading span B) window. Range: 30-70. Default: 52.
        direction (str): Crossover direction, 'bullish' or 'bearish'. Default: bullish.

    Returns:
        bool: True if TK cross detected, False otherwise.
    """
    if len(df) < window_senkou + 1:
        return False

    result = Ichimoku.compute(
        data={'high': df["High"], 'low': df["Low"]},
        params={'window1': window_tenkan, 'window2': window_kijun, 'window3': window_senkou, 'visual': False}
    )
    tenkan = result['conversion_line']
    kijun = result['base_line']

    if len(tenkan) < 2 or pd.isna(tenkan.iloc[-1]) or pd.isna(kijun.iloc[-1]):
        return False

    if direction.lower() == "bullish":
        prev_below = float(tenkan.iloc[-2]) <= float(kijun.iloc[-2])
        curr_above = float(tenkan.iloc[-1]) > float(kijun.iloc[-1])
        return prev_below and curr_above
    elif direction.lower() == "bearish":
        prev_above = float(tenkan.iloc[-2]) >= float(kijun.iloc[-2])
        curr_below = float(tenkan.iloc[-1]) < float(kijun.iloc[-1])
        return prev_above and curr_below

    return False

@RuleRegistry.register("is_above_epma")
def is_above_epma(df: pd.DataFrame, window: int = 20) -> bool:
    """Signal: is_above_epma

    Check if the current price is above the End Point Moving Average (EPMA / LSMA). EPMA is the
    endpoint of a linear regression over the window, projecting the trend to "now" rather than
    averaging past values.

    Warmup: window - 1

    Formula:
        close[t] > epma[t]

    Inputs:
        close: closing price

    Params:
        window [default=20, min=2, max=200]: EPMA window in bars

    Outputs:
        fired [boolean, 0..1]:
            True if close > EPMA, False otherwise

    Type: FILTER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): EPMA window in bars. Range: 2-200. Default: 20.

    Returns:
        bool: True if close > EPMA, False otherwise.
    """
    return _ma_is_above(df, EPMA, 'epma', window)

@RuleRegistry.register("epma_cross_up")
def epma_cross_up(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """Signal: epma_cross_up

    Detect a bullish EPMA crossover (fast EPMA crosses above slow EPMA).

    Warmup: window_slow

    Formula:
        epma(window_fast)[t-1] <= epma(window_slow)[t-1] and epma(window_fast)[t] > epma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=10, min=2, max=100]: Fast EPMA window
        window_slow [default=30, min=2, max=200]: Slow EPMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bullish EPMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EPMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow EPMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bullish EPMA crossover detected on the current bar.
    """
    return _ma_crossover(df, EPMA, 'epma', window_fast, window_slow, "bullish")

@RuleRegistry.register("epma_cross_down")
def epma_cross_down(df: pd.DataFrame, window_fast: int = 10, window_slow: int = 30) -> bool:
    """Signal: epma_cross_down

    Detect a bearish EPMA crossover (fast EPMA crosses below slow EPMA).

    Warmup: window_slow

    Formula:
        epma(window_fast)[t-1] >= epma(window_slow)[t-1] and epma(window_fast)[t] < epma(window_slow)[t]

    Inputs:
        close: closing price

    Params:
        window_fast [default=10, min=2, max=100]: Fast EPMA window
        window_slow [default=30, min=2, max=200]: Slow EPMA window

    Outputs:
        fired [boolean, 0..1]:
            True if bearish EPMA crossover detected on the current bar

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window_fast (int): Fast EPMA window. Range: 2-100. Default: 10.
        window_slow (int): Slow EPMA window. Range: 2-200. Default: 30.

    Returns:
        bool: True if bearish EPMA crossover detected on the current bar.
    """
    return _ma_crossover(df, EPMA, 'epma', window_fast, window_slow, "bearish")

@RuleRegistry.register("heikin_ashi_bullish")
def heikin_ashi_bullish(df: pd.DataFrame) -> bool:
    """Signal: heikin_ashi_bullish

    Check if the current Heikin-Ashi candle is bullish (HA_close > HA_open). A bullish HA candle
    indicates buying pressure on the smoothed bar. Strings of bullish HA candles indicate a
    sustained uptrend.

    Warmup: 0

    Formula:
        ha_close[t] > ha_open[t] -- the Heikin-Ashi candle closes up, which is not the same as close[t] > open[t]

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if HA_close > HA_open on the current bar

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if HA_close > HA_open on the current bar.
    """
    if len(df) < 1:
        return False
    out = HeikinAshi.compute(
        data={'open': df["Open"], 'high': df["High"], 'low': df["Low"], 'close': df["Close"]}, params={}
    )
    if pd.isna(out['ha_close'].iloc[-1]) or pd.isna(out['ha_open'].iloc[-1]):
        return False
    return bool(out['ha_close'].iloc[-1] > out['ha_open'].iloc[-1])

@RuleRegistry.register("heikin_ashi_bearish")
def heikin_ashi_bearish(df: pd.DataFrame) -> bool:
    """Signal: heikin_ashi_bearish

    Check if the current Heikin-Ashi candle is bearish (HA_close < HA_open).

    Warmup: 0

    Formula:
        ha_close[t] < ha_open[t]

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        fired [boolean, 0..1]:
            True if HA_close < HA_open on the current bar

    Type: FILTER
    Requires: Open, High, Low, Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.

    Returns:
        bool: True if HA_close < HA_open on the current bar.
    """
    if len(df) < 1:
        return False
    out = HeikinAshi.compute(
        data={'open': df["Open"], 'high': df["High"], 'low': df["Low"], 'close': df["Close"]}, params={}
    )
    if pd.isna(out['ha_close'].iloc[-1]) or pd.isna(out['ha_open'].iloc[-1]):
        return False
    return bool(out['ha_close'].iloc[-1] < out['ha_open'].iloc[-1])
