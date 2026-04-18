"""
Volume Indicators.

Provides volume-based technical analysis indicators including OBV, MFI,
CMF, Force Index, ADI, VWAP, and more.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.trend_indicators import EMA, SMA
from mangrove_kb.indicators.utils import typical_price


class ADI(IndicatorInterface):
    """Accumulation/Distribution Index (ADI)

    Acting as leading indicator of price movements.

    https://school.stockcharts.com/doku.php?id=technical_indicators:accumulation_distribution_line

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {}

    Returns:
        {'adi': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = []
    _outputs = ["adi"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']

        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.fillna(0.0)  # float division by zero
        adi = clv * volume
        adi = adi.cumsum()

        return {'adi': pd.Series(adi, name="adi")}


class OBV(IndicatorInterface):
    """On-balance volume (OBV)

    It relates price and volume in the stock market. OBV is based on a
    cumulative total volume.

    https://en.wikipedia.org/wiki/On-balance_volume

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {}

    Returns:
        {'obv': pd.Series}
    """
    _data = ["close", "volume"]
    _params = []
    _outputs = ["obv"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']

        obv = np.where(close < close.shift(1), -volume, volume)
        obv = pd.Series(obv, index=close.index).cumsum()

        return {'obv': pd.Series(obv, name="obv")}


class CMF(IndicatorInterface):
    """Chaikin Money Flow (CMF)

    It measures the amount of Money Flow Volume over a specific period.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:chaikin_money_flow_cmf

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'cmf': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["window"]
    _outputs = ["cmf"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        window = params['window']

        mfv = ((close - low) - (high - close)) / (high - low)
        mfv = mfv.fillna(0.0)  # float division by zero
        mfv *= volume

        cmf = (
            mfv.rolling(window, min_periods=window).sum()
            / volume.rolling(window, min_periods=window).sum()
        )

        return {'cmf': pd.Series(cmf, name="cmf")}


class ForceIndex(IndicatorInterface):
    """Force Index (FI)

    It illustrates how strong the actual buying or selling pressure is. High
    positive values mean there is a strong rising trend, and low values signify
    a strong downward trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:force_index

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'fi': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["window"]
    _outputs = ["fi"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        window = params['window']

        fi_series = (close - close.shift(1)) * volume
        fi = EMA.compute({'close': fi_series}, {'window': window})['ema']

        return {'fi': pd.Series(fi, name=f"fi_{window}")}


class EaseOfMovement(IndicatorInterface):
    """Ease of movement (EoM, EMV)

    It relate an asset's price change to its volume and is particularly useful
    for assessing the strength of a trend.

    https://en.wikipedia.org/wiki/Ease_of_movement

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'eom': pd.Series, 'sma_eom': pd.Series}
    """
    _data = ["high", "low", "volume"]
    _params = ["window"]
    _outputs = ["eom", "sma_eom"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        volume = data['volume']
        window = params['window']

        emv = (
            (high.diff(1) + low.diff(1))
            * (high - low)
            / (2 * volume)
        )
        emv *= 100000000

        sma_emv = emv.rolling(window, min_periods=window).mean()

        return {
            'eom': pd.Series(emv, name=f"eom_{window}"),
            'sma_eom': pd.Series(sma_emv, name=f"sma_eom_{window}")
        }


class VPT(IndicatorInterface):
    """Volume-price trend (VPT)

    Is based on a running cumulative volume that adds or substracts a multiple
    of the percentage change in share price trend and current volume, depending
    upon the investment's upward or downward movements.

    https://en.wikipedia.org/wiki/Volume-price_trend

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'smoothing_factor': Optional[int], 'dropnans': bool}

    Returns:
        {'vpt': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["smoothing_factor", "dropnans"]
    _outputs = ["vpt"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        smoothing_factor = params['smoothing_factor']
        dropnans = params['dropnans']

        vpt = (close.pct_change() * volume).cumsum()
        if smoothing_factor:
            vpt = vpt.rolling(smoothing_factor, min_periods=smoothing_factor).mean()
        if dropnans:
            vpt = vpt.dropna()

        return {'vpt': pd.Series(vpt, name="vpt")}


class NVI(IndicatorInterface):
    """Negative Volume Index (NVI)

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:negative_volume_inde

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'nvi': pd.Series, 'nvi_ema': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["window"]
    _outputs = ["nvi", "nvi_ema"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        window = params['window']

        price_change = close.pct_change()
        vol_decrease = volume.shift(1) > volume

        # NVI is a compounding index: on volume-decrease bars, scale by
        # (1 + pct_change); otherwise carry forward. Express as a cumulative
        # product of per-bar factors. pct_change[0] is NaN by definition;
        # vol_decrease[0] is False (prev_volume is NaN); so factor[0] is 1
        # and nvi[0] = 1000 * 1 = 1000, matching the original's hand-seed.
        pct_arr = price_change.to_numpy(dtype=np.float64)
        dec_arr = vol_decrease.to_numpy(dtype=bool)
        pct_clean = np.where(np.isnan(pct_arr), 0.0, pct_arr)
        factor = np.where(dec_arr, 1.0 + pct_clean, 1.0)
        nvi_arr = 1000.0 * np.cumprod(factor)
        nvi = pd.Series(nvi_arr, index=close.index, name="nvi")

        nvi_ema = nvi.ewm(span=window, adjust=False).mean()

        return {'nvi': pd.Series(nvi, name="nvi"), 'nvi_ema': pd.Series(nvi_ema, name="nvi_ema")}


class MFI(IndicatorInterface):
    """Money Flow Index (MFI)

    Uses both price and volume to measure buying and selling pressure. It is
    positive when the typical price rises (buying pressure) and negative when
    the typical price declines (selling pressure). A ratio of positive and
    negative money flow is then plugged into an RSI formula to create an
    oscillator that moves between zero and one hundred.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:money_flow_index_mfi

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'mfi': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["window"]
    _outputs = ["mfi"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        window = params['window']

        tp = typical_price(high, low, close)
        up_down = np.where(
            tp > tp.shift(1),
            1,
            np.where(tp < tp.shift(1), -1, 0),
        )
        mfr = tp * volume * up_down

        # Positive and negative money flow with n periods.
        # Mask outside the roll so the window op is a plain vectorized sum.
        mfr_arr = np.asarray(mfr, dtype=np.float64)
        pos_mfr = pd.Series(np.where(mfr_arr >= 0.0, mfr_arr, 0.0), index=tp.index)
        neg_mfr = pd.Series(np.where(mfr_arr < 0.0, mfr_arr, 0.0), index=tp.index)
        n_positive_mf = pos_mfr.rolling(window, min_periods=window).sum()
        n_negative_mf = neg_mfr.rolling(window, min_periods=window).sum().abs()

        # Money flow index
        mfi_ratio = n_positive_mf / n_negative_mf
        mfi = 100 - (100 / (1 + mfi_ratio))

        return {'mfi': pd.Series(mfi, name=f"mfi_{window}")}


class VWAP(IndicatorInterface):
    """Volume Weighted Average Price (VWAP)

    VWAP equals the dollar value of all trading periods divided
    by the total trading volume for the current day.
    The calculation starts when trading opens and ends when it closes.
    Because it is good for the current trading day only,
    intraday periods and data are used in the calculation.

    https://school.stockcharts.com/doku.php?id=technical_indicators:vwap_intraday

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'vwap': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["window"]
    _outputs = ["vwap"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        window = params['window']

        # 1 typical price
        tp = typical_price(high, low, close)

        # 2 typical price * volume
        tp_volume = tp * volume

        # 3 total price * volume
        total_pv = tp_volume.rolling(window, min_periods=window).sum()

        # 4 total volume
        total_volume = volume.rolling(window, min_periods=window).sum()

        vwap = total_pv / total_volume

        return {'vwap': pd.Series(vwap, name=f"vwap_{window}")}

class VWMA(IndicatorInterface):
    """Volume-Weighted Moving Average (VWMA)

    Weights each price by its bar's volume, emphasizing bars with heavy
    participation. Unlike VWAP (which resets daily/session), VWMA is a true
    rolling moving average over the last N bars.

    Formula: VWMA(n) = sum(close * volume over n) / sum(volume over n)

    Reference: Standard volume-weighted moving average.

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'vwma': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["window"]
    _outputs = ["vwma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        window = params['window']

        pv_sum = (close * volume).rolling(window, min_periods=window).sum()
        vol_sum = volume.rolling(window, min_periods=window).sum()
        vwma = pv_sum / vol_sum
        return {'vwma': pd.Series(vwma.values, index=close.index, name=f'vwma_{window}')}

