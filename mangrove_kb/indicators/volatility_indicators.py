"""
Volatility Indicators.

Provides volatility-based technical analysis indicators including ATR,
Bollinger Bands, Keltner Channel, Donchian Channel, and Ulcer Index.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.utils import true_range, typical_price


class ATR(IndicatorInterface):
    """Average True Range (ATR)

    The indicator provide an indication of the degree of price volatility.
    Strong moves, in either direction, are often accompanied by large ranges,
    or large True Ranges.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_true_range_atr

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'atr': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["atr"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        tr = true_range(high, low, close)
        tr_arr = tr.to_numpy(dtype=np.float64)
        n = len(tr_arr)

        # Original convention: atr[0..window-2] = 0 (from np.zeros warm-up),
        # atr[window-1] = mean of the first `window` tr values (skipna; tr[0]
        # is NaN so it's really mean of window-1 valid values), then Wilder
        # smooth forward. Wilder's recurrence is identical to
        # ewm(alpha=1/window, adjust=False) applied to
        # [seed, tr[window], tr[window+1], ...].
        atr_arr = np.zeros(n)
        if n >= window:
            seed = np.nanmean(tr_arr[:window])
            tail = np.concatenate(([seed], tr_arr[window:]))
            smoothed = pd.Series(tail).ewm(alpha=1.0 / window, adjust=False).mean().to_numpy()
            atr_arr[window - 1 :] = smoothed

        return {'atr': pd.Series(atr_arr, index=close.index, name='atr')}


class BollingerBands(IndicatorInterface):
    """Bollinger Bands

    https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'window_dev': int}

    Returns:
        {'mavg': pd.Series, 'hband': pd.Series, 'lband': pd.Series,
         'wband': pd.Series, 'pband': pd.Series,
         'hband_indicator': pd.Series, 'lband_indicator': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "window_dev"]
    _outputs = ["mavg", "hband", "lband", "wband", "pband", "hband_indicator", "lband_indicator"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        window_dev = params['window_dev']

        mavg = close.rolling(window, min_periods=window).mean()
        mstd = close.rolling(window, min_periods=window).std(ddof=0)
        hband = mavg + window_dev * mstd
        lband = mavg - window_dev * mstd

        wband = ((hband - lband) / mavg) * 100
        pband = (close - lband) / (hband - lband).where(hband != lband, np.nan)

        hband_indicator = pd.Series(
            np.where(close > hband, 1.0, 0.0), index=close.index
        )
        lband_indicator = pd.Series(
            np.where(close < lband, 1.0, 0.0), index=close.index
        )

        return {
            'mavg': pd.Series(mavg, name="mavg"),
            'hband': pd.Series(hband, name="hband"),
            'lband': pd.Series(lband, name="lband"),
            'wband': pd.Series(wband, name="bbiwband"),
            'pband': pd.Series(pband, name="bbipband"),
            'hband_indicator': pd.Series(hband_indicator, name="bbihband"),
            'lband_indicator': pd.Series(lband_indicator, name="bbilband")
        }


class KeltnerChannel(IndicatorInterface):
    """KeltnerChannel

    Keltner Channels are a trend following indicator used to identify reversals with channel breakouts and
    channel direction. Channels can also be used to identify overbought and oversold levels when the trend
    is flat.

    https://school.stockcharts.com/doku.php?id=technical_indicators:keltner_channels

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'window_atr': int, 'original_version': bool, 'multiplier': int}

    Returns:
        {'mband': pd.Series, 'hband': pd.Series, 'lband': pd.Series,
         'wband': pd.Series, 'pband': pd.Series,
         'hband_indicator': pd.Series, 'lband_indicator': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "window_atr", "original_version", "multiplier"]
    _outputs = ["mband", "hband", "lband", "wband", "pband", "hband_indicator", "lband_indicator"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        window_atr = params['window_atr']
        original_version = params['original_version']
        multiplier = params['multiplier']

        if original_version:
            tp = typical_price(high, low, close).rolling(window, min_periods=window).mean()
            tp_high = (((4 * high) - (2 * low) + close) / 3.0).rolling(window, min_periods=window).mean()
            tp_low = (((-2 * high) + (4 * low) + close) / 3.0).rolling(window, min_periods=window).mean()
        else:
            tp = close.ewm(span=window, min_periods=window, adjust=False).mean()
            atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window_atr})['atr']
            tp_high = tp + (multiplier * atr)
            tp_low = tp - (multiplier * atr)

        wband = ((tp_high - tp_low) / tp) * 100
        pband = (close - tp_low) / (tp_high - tp_low)

        hband_indicator = pd.Series(
            np.where(close > tp_high, 1.0, 0.0), index=close.index
        )
        lband_indicator = pd.Series(
            np.where(close < tp_low, 1.0, 0.0), index=close.index
        )

        return {
            'mband': pd.Series(tp, name="mavg"),
            'hband': pd.Series(tp_high, name="kc_hband"),
            'lband': pd.Series(tp_low, name="kc_lband"),
            'wband': pd.Series(wband, name="bbiwband"),
            'pband': pd.Series(pband, name="bbipband"),
            'hband_indicator': pd.Series(hband_indicator, name="dcihband"),
            'lband_indicator': pd.Series(lband_indicator, name="dcilband")
        }


class DonchianChannel(IndicatorInterface):
    """Donchian Channel

    https://www.investopedia.com/terms/d/donchianchannels.asp

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'offset': int}

    Returns:
        {'hband': pd.Series, 'lband': pd.Series, 'mband': pd.Series,
         'wband': pd.Series, 'pband': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "offset"]
    _outputs = ["hband", "lband", "mband", "wband", "pband"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        offset = params['offset']

        hband = high.rolling(window, min_periods=window).max()
        lband = low.rolling(window, min_periods=window).min()
        mband = ((hband - lband) / 2.0) + lband

        mavg = close.rolling(window, min_periods=window).mean()
        wband = ((hband - lband) / mavg) * 100
        pband = (close - lband) / (hband - lband)

        if offset != 0:
            hband = hband.shift(offset)
            lband = lband.shift(offset)
            mband = mband.shift(offset)
            wband = wband.shift(offset)
            pband = pband.shift(offset)

        return {
            'hband': pd.Series(hband, name="dchband"),
            'lband': pd.Series(lband, name="dclband"),
            'mband': pd.Series(mband, name="dcmband"),
            'wband': pd.Series(wband, name="dcwband"),
            'pband': pd.Series(pband, name="dcpband")
        }


class UlcerIndex(IndicatorInterface):
    """Ulcer Index

    https://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ulcer_index

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'ulcer_index': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["ulcer_index"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        ui_max = close.rolling(window, min_periods=1).max()
        r_i = 100 * (close - ui_max) / ui_max

        # sqrt(sum(r_i^2) / window) over the rolling window == sqrt(mean(r_i^2)).
        ulcer_idx = np.sqrt((r_i ** 2).rolling(window, min_periods=window).mean())

        return {'ulcer_index': pd.Series(ulcer_idx, name="ui")}


class TrueRange(IndicatorInterface):
    """True Range (TR)

    Welles Wilder's True Range: max of
        (high - low), |high - prev_close|, |low - prev_close|
    captures gap volatility that a simple high-low range misses.

    This is the raw building block used inside ATR (and Vortex, UO, etc.).
    Exposed as a standalone indicator for strategies that want the raw per-bar
    range rather than a smoothed average.

    Reference: J. Welles Wilder Jr., "New Concepts in Technical Trading
    Systems" (1978).

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {}

    Returns:
        {'true_range': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = []
    _outputs = ["true_range"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        tr = true_range(high, low, close)
        return {'true_range': pd.Series(tr.values, index=close.index, name='true_range')}


class NATR(IndicatorInterface):
    """Normalized Average True Range (NATR)

    ATR expressed as a percentage of close: NATR = 100 * ATR / close. Useful
    for comparing volatility across assets and timeframes where absolute ATR
    scales with price.

    Reference: TA-Lib canonical definition.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'natr': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["natr"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        # ATR is zero during warmup (first window-1 bars); avoid 0/x artifacts
        # by masking those to NaN.
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False)
        close_vals = close.to_numpy(dtype=np.float64, copy=False)
        natr = np.full_like(atr_vals, np.nan)
        valid = np.arange(len(atr_vals)) >= (window - 1)
        with np.errstate(divide='ignore', invalid='ignore'):
            natr[valid] = 100.0 * atr_vals[valid] / close_vals[valid]
        return {'natr': pd.Series(natr, index=close.index, name=f'natr_{window}')}


class ATRTrailingStop(IndicatorInterface):
    """ATR Trailing Stop (Chuck LeBeau variant).

    Stateful trailing stop that flips between long and short regimes:
      - In long regime: stop = max(previous_stop, close - multiplier*ATR).
        Flip to short when close crosses below the long stop.
      - In short regime: stop = min(previous_stop, close + multiplier*ATR).
        Flip to long when close crosses above the short stop.

    Outputs:
      - trailing_stop: the active stop level on each bar
      - direction: +1 long, -1 short

    Reference: Chuck LeBeau (Smart Trader), popularized in Chande's
    "Beyond Technical Analysis" (1997).

    Implementation: genuinely state-dependent (stop level accumulates forward);
    pure-Python loop, same pattern as SuperTrend and PSAR.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'trailing_stop': pd.Series, 'direction': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "multiplier"]
    _outputs = ["trailing_stop", "direction"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        close_vals = close.to_numpy(dtype=np.float64, copy=False)
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False)
        n = len(close_vals)

        stop = np.full(n, np.nan)
        direction = np.zeros(n, dtype=np.int64)

        # Warmup: need valid ATR before starting. ATR becomes non-zero at
        # index window-1 in our implementation.
        start = window
        if n <= start:
            return {
                'trailing_stop': pd.Series(stop, index=close.index, name='trailing_stop'),
                'direction': pd.Series(direction.astype(np.float64), index=close.index, name='direction'),
            }

        # Initialize direction based on first bar after warmup using simple
        # comparison to the previous close.
        direction[start] = 1 if close_vals[start] >= close_vals[start - 1] else -1
        if direction[start] == 1:
            stop[start] = close_vals[start] - mult * atr_vals[start]
        else:
            stop[start] = close_vals[start] + mult * atr_vals[start]

        # State-dependent loop: trailing stop ratchets in the trend direction
        # and flips on the opposite-side close cross.
        for i in range(start + 1, n):
            prev_stop = stop[i - 1]
            prev_dir = direction[i - 1]
            candidate_long = close_vals[i] - mult * atr_vals[i]
            candidate_short = close_vals[i] + mult * atr_vals[i]

            if prev_dir == 1:
                if close_vals[i] < prev_stop:
                    # Flip to short
                    direction[i] = -1
                    stop[i] = candidate_short
                else:
                    # Ratchet long stop higher (never lower)
                    direction[i] = 1
                    stop[i] = max(prev_stop, candidate_long)
            else:
                if close_vals[i] > prev_stop:
                    # Flip to long
                    direction[i] = 1
                    stop[i] = candidate_long
                else:
                    # Ratchet short stop lower (never higher)
                    direction[i] = -1
                    stop[i] = min(prev_stop, candidate_short)

        return {
            'trailing_stop': pd.Series(stop, index=close.index, name='trailing_stop'),
            'direction': pd.Series(direction.astype(np.float64), index=close.index, name='direction'),
        }


class STARCBands(IndicatorInterface):
    """Stoller Average Range Channels (STARC Bands).

    SMA-centered ATR-scaled envelope:
        upper = SMA(close, window) + multiplier * ATR(window_atr)
        lower = SMA(close, window) - multiplier * ATR(window_atr)

    Similar to Keltner Channel but with an explicitly separate window for the
    SMA and ATR. Useful for breakout strategies.

    Reference: Manning Stoller, popularized in "Beyond Candlesticks" (Steve
    Nison, 1994 era).

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'window_atr': int, 'multiplier': float}

    Returns:
        {'starc_mid': pd.Series, 'starc_hband': pd.Series, 'starc_lband': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "window_atr", "multiplier"]
    _outputs = ["starc_mid", "starc_hband", "starc_lband"]

    @classmethod
    def _compute(cls, data, params):
        # Local import to avoid a circular dependency with trend_indicators.
        from mangrove_kb.indicators.trend_indicators import SMA

        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        window_atr = params['window_atr']
        mult = float(params['multiplier'])

        mid = SMA.compute({'close': close}, {'window': window})['sma']
        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window_atr})['atr']
        # Mask warmup bars of ATR to NaN so bands don't leak zero-ATR values.
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False).copy()
        atr_vals[: window_atr - 1] = np.nan
        atr_masked = pd.Series(atr_vals, index=close.index)

        hband = mid + mult * atr_masked
        lband = mid - mult * atr_masked

        return {
            'starc_mid': pd.Series(mid.values, index=close.index, name='starc_mid'),
            'starc_hband': pd.Series(hband.values, index=close.index, name='starc_hband'),
            'starc_lband': pd.Series(lband.values, index=close.index, name='starc_lband'),
        }


class VolatilityStop(IndicatorInterface):
    """Standard-deviation-based volatility envelope.

    Uses rolling standard deviation of returns to build an "expected range"
    for the current bar around the previous close:
        upper = prev_close + multiplier * stdev(returns, window) * prev_close
        lower = prev_close - multiplier * stdev(returns, window) * prev_close

    When the current close exceeds the upper band, price has moved more than
    `multiplier` standard deviations up from yesterday -- a potential
    exhaustion or breakout signal. Conversely for the lower band.

    Distinct from ATR Trailing Stop: uses stdev of returns rather than
    smoothed true range, and is not a state machine (no ratcheting).

    Reference: Common stdev-envelope construction; variants appear in
    Bollinger Bands and Cynthia Kase's stop loss methodology.

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'vstop_hband': pd.Series, 'vstop_lband': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "multiplier"]
    _outputs = ["vstop_hband", "vstop_lband"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        # Rolling stdev of returns (not close), for a scale-invariant measure.
        returns = close.pct_change()
        vol = returns.rolling(window, min_periods=window).std()
        # Use PREVIOUS close as the center: today's expected-range envelope
        # given yesterday's close and recent volatility. If we used current
        # close as the center, close would be trivially between the bands
        # and the signals would never fire.
        prev_close = close.shift(1)
        offset = prev_close * vol * mult

        hband = prev_close + offset
        lband = prev_close - offset
        return {
            'vstop_hband': pd.Series(hband.values, index=close.index, name='vstop_hband'),
            'vstop_lband': pd.Series(lband.values, index=close.index, name='vstop_lband'),
        }
