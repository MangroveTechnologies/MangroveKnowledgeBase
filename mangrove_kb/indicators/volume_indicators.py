"""
Volume Indicators.

Provides volume-based technical analysis indicators including OBV, MFI,
CMF, Force Index, ADI, VWAP, and more.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import warnings

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

        # Granville's rule has THREE branches, and the third one matters: an unchanged close
        # contributes nothing. A two-way test folds flat bars into the up-branch, so every flat
        # close adds volume that should have been ignored and the line drifts upward independently
        # of price -- worst on illiquid instruments, coarse tick sizes, and resampled series where
        # flat closes are common. OBV is read by its direction, so a spurious drift is precisely
        # the failure mode that matters.
        direction = np.sign(close.diff())
        # Bar 0 has no prior close, so its direction is undefined and it contributes nothing --
        # the same reasoning as the flat-close branch. Seeding it with +volume (as an earlier
        # revision did) offsets the whole series by one bar's volume. That offset is harmless for
        # reading OBV, whose level is an artefact of where the data begins, but it is an invented
        # value rather than a measured one.
        direction = direction.fillna(0.0)

        obv = (direction * volume).cumsum()

        return {'obv': pd.Series(obv, index=close.index, name="obv")}


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
        params: {'smoothing_factor': Optional[int]}

    Returns:
        {'vpt': pd.Series}
    """
    _data = ["close", "volume"]
    # `dropnans` is REMOVED, not repaired. It returned a shorter series starting at a later index,
    # silently breaking the aligned-index guarantee `compute_frame` documents. Filling the warmup
    # instead would have been worse: VPT is a running cumulative total, so 0 is a real reading, and
    # substituting it makes warmup indistinguishable from a genuinely flat stretch -- the same
    # defect corrected in ATR and ADX. Warmup is NaN here, as it is everywhere else, and no
    # indicator in this package carries an escape hatch from that.
    _params = ["smoothing_factor"]
    _outputs = ["vpt"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        smoothing_factor = params['smoothing_factor']

        # `_validate` only checks for MISSING params, so dropping `dropnans` from `_params` would
        # let an old caller keep passing it and silently get different behaviour -- NaN-padded
        # warmup where they previously got dropped rows. Tell them instead of failing quietly.
        if params.get('dropnans') is not None:
            warnings.warn(
                "VPT's 'dropnans' parameter is removed and has no effect. It returned a shorter "
                "series starting at a later index, breaking the aligned-index guarantee that lets "
                "compute_frame outer-join indicators into a feature matrix. Warmup is now NaN, as "
                "it is for every other indicator.",
                DeprecationWarning,
                stacklevel=3,
            )

        vpt = (close.pct_change() * volume).cumsum()
        if smoothing_factor:
            vpt = vpt.rolling(smoothing_factor, min_periods=smoothing_factor).mean()
        return {'vpt': pd.Series(vpt, index=close.index, name="vpt")}


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

    Rolling volume-weighted average of typical price: traded value over the window divided
    by volume over the window. Each bar is weighted by how much actually traded, so heavy
    bars pull the level toward them and quiet bars barely move it.

    Uses a rolling `window` rather than a session anchor. The textbook definition resets at
    each session open, but anchoring presupposes a session boundary, and a continuously
    traded 24/7 market does not have one -- there is no open to accumulate from and no close
    to reset at. The rolling form is therefore the coherent definition here, not an
    approximation of the anchored one.

    Consequence worth knowing: on a session-traded instrument such as an equity, this is not
    the institutional execution benchmark, because that benchmark is defined by the session
    it anchors to. This series is exactly VWMA computed on typical price.

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



class ADOSC(IndicatorInterface):
    """Chaikin Accumulation/Distribution Oscillator (ADOSC).

    Momentum of the Accumulation/Distribution Line: difference of two EMAs
    of the AD line. Positive values indicate accumulation; negative indicate
    distribution. A classic Chaikin confirmation indicator.

    Formula: ADOSC = EMA(AD, fast) - EMA(AD, slow)

    Reference: Marc Chaikin. TA-Lib canonical. Reuses our ADI indicator for
    the AD line and our EMA for smoothing.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'fast': int, 'slow': int}

    Returns:
        {'adosc': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["fast", "slow"]
    _outputs = ["adosc"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.trend_indicators import EMA

        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        fast = params['fast']
        slow = params['slow']

        ad = ADI.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, {})['adi']
        ema_fast = EMA.compute({'close': ad}, {'window': fast})['ema']
        ema_slow = EMA.compute({'close': ad}, {'window': slow})['ema']
        adosc = ema_fast - ema_slow
        return {'adosc': pd.Series(adosc.values, index=close.index, name=f'adosc_{fast}_{slow}')}


class KVO(IndicatorInterface):
    """Klinger Volume Oscillator (KVO).

    Volume-weighted momentum oscillator. pandas-ta / modern simplified form:
    sign the volume by the direction of the typical price change, then take
    the difference of a fast and slow EMA.

        trend = sign(typical_price - prev_typical_price)
        signed_volume = volume * trend
        KVO = EMA(signed_volume, fast) - EMA(signed_volume, slow)
        KVO_signal = EMA(KVO, signal_window)

    Positive KVO with rising signal = bullish volume pressure; negative with
    falling signal = bearish. Divergences from price are the classic
    Klinger entry cue.

    Reference: Stephen J. Klinger (simplified modern form as implemented in
    pandas-ta / TradingView; Klinger's original 1997 formulation uses a
    more elaborate cumulative-measurement reset that this does not
    replicate).

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'fast': int, 'slow': int, 'signal_window': int}

    Returns:
        {'kvo': pd.Series, 'kvo_signal': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["fast", "slow", "signal_window"]
    _outputs = ["kvo", "kvo_signal"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.trend_indicators import EMA
        from mangrove_kb.indicators.utils import typical_price

        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        fast = params['fast']
        slow = params['slow']
        signal_window = params['signal_window']

        tp = typical_price(high, low, close)
        diff = tp.diff(1)
        # Sign of the typical-price change: +1 / -1 / 0 (no change).
        # np.sign gives 0.0 for no-change; we leave that as 0 to match
        # pandas-ta behavior on flat bars.
        trend = np.sign(diff.to_numpy(dtype=np.float64, copy=False))
        # NaN-safe: diff[0] is NaN so sign[0] is NaN -- replace with 0
        # (no prior bar, no trend direction).
        trend = np.nan_to_num(trend, nan=0.0)

        vol_arr = volume.to_numpy(dtype=np.float64, copy=False)
        signed_volume = pd.Series(vol_arr * trend, index=close.index)

        ema_fast = EMA.compute({'close': signed_volume}, {'window': fast})['ema']
        ema_slow = EMA.compute({'close': signed_volume}, {'window': slow})['ema']
        kvo = ema_fast - ema_slow
        kvo_signal = EMA.compute({'close': kvo}, {'window': signal_window})['ema']

        return {
            'kvo': pd.Series(kvo.values, index=close.index, name=f'kvo_{fast}_{slow}'),
            'kvo_signal': pd.Series(kvo_signal.values, index=close.index, name=f'kvo_signal_{signal_window}'),
        }
