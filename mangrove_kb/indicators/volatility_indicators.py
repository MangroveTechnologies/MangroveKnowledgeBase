"""
Volatility Indicators.

Provides volatility-based technical analysis indicators including ATR,
Bollinger Bands, Keltner Channel, Donchian Channel, and Ulcer Index.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.utils import true_range


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
            tp = ((high + low + close) / 3.0).rolling(window, min_periods=window).mean()
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
