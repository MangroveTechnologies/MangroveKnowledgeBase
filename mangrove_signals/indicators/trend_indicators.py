"""
Trend Indicators.

Provides trend-based technical analysis indicators including MACD, EMA, SMA,
ADX, Aroon, Ichimoku, PSAR, and more.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import numpy as np
import pandas as pd

from mangrove_signals.indicators.indicator_interface import IndicatorInterface
from mangrove_signals.indicators.utils import get_min_max, true_range


class SMA(IndicatorInterface):
    """Simple Moving Average

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'sma': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["sma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        sma_values = close.rolling(window=window, min_periods=window).mean()
        return {'sma': pd.Series(sma_values, name=f'sma_{window}')}


class EMA(IndicatorInterface):
    """Exponential Moving Average

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'ema': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["ema"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        ema_values = close.ewm(span=window, min_periods=window, adjust=False).mean()
        return {'ema': pd.Series(ema_values, name=f'ema_{window}')}


class WMA(IndicatorInterface):
    """Weighted Moving Average

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'wma': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["wma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        weight = pd.Series(
            [i * 2 / (window * (window + 1)) for i in range(1, window + 1)]
        )

        def weighted_average(x):
            return (weight * x).sum()

        wma_values = close.rolling(window).apply(weighted_average, raw=True)
        return {'wma': pd.Series(wma_values, name=f'wma_{window}')}


class MACD(IndicatorInterface):
    """Moving Average Convergence Divergence (MACD)

    Is a trend-following momentum indicator that shows the relationship between
    two moving averages of prices.

    https://school.stockcharts.com/doku.php?id=technical_indicators:moving_average_convergence_divergence_macd

    Args:
        data: {'close': pd.Series}
        params: {'window_slow': int, 'window_fast': int, 'window_sign': int}

    Returns:
        {'macd': pd.Series, 'signal': pd.Series, 'histogram': pd.Series}
    """
    _data = ["close"]
    _params = ["window_slow", "window_fast", "window_sign"]
    _outputs = ["macd", "signal", "histogram"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']

        # Call EMA indicator
        ema_fast = EMA.compute({'close': close}, {'window': params['window_fast']})['ema']
        ema_slow = EMA.compute({'close': close}, {'window': params['window_slow']})['ema']

        macd_line = ema_fast - ema_slow
        signal_line = EMA.compute({'close': macd_line}, {'window': params['window_sign']})['ema']
        histogram = macd_line - signal_line

        return {
            'macd': pd.Series(macd_line, name=f"MACD_{params['window_fast']}_{params['window_slow']}"),
            'signal': pd.Series(signal_line, name=f"MACD_sign_{params['window_fast']}_{params['window_slow']}"),
            'histogram': pd.Series(histogram, name=f"MACD_diff_{params['window_fast']}_{params['window_slow']}")
        }


class Aroon(IndicatorInterface):
    """Aroon Indicator

    Identify when trends are likely to change direction.

    Aroon Up = ((N - Days Since N-day High) / N) x 100
    Aroon Down = ((N - Days Since N-day Low) / N) x 100
    Aroon Indicator = Aroon Up - Aroon Down

    https://www.investopedia.com/terms/a/aroon.asp

    Args:
        data: {'high': pd.Series, 'low': pd.Series}
        params: {'window': int}

    Returns:
        {'aroon_up': pd.Series, 'aroon_down': pd.Series, 'aroon_indicator': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["window"]
    _outputs = ["aroon_up", "aroon_down", "aroon_indicator"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        window = params['window']

        rolling_high = high.rolling(window + 1, min_periods=window + 1)
        aroon_up = rolling_high.apply(
            lambda x: float(np.argmax(x)) / window * 100, raw=True
        )

        rolling_low = low.rolling(window + 1, min_periods=window + 1)
        aroon_down = rolling_low.apply(
            lambda x: float(np.argmin(x)) / window * 100, raw=True
        )

        aroon_diff = aroon_up - aroon_down

        return {
            'aroon_up': pd.Series(aroon_up, name=f"aroon_up_{window}"),
            'aroon_down': pd.Series(aroon_down, name=f"aroon_down_{window}"),
            'aroon_indicator': pd.Series(aroon_diff, name=f"aroon_ind_{window}")
        }


class TRIX(IndicatorInterface):
    """Trix (TRIX)

    Shows the percent rate of change of a triple exponentially smoothed moving
    average.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:trix

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'trix': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["trix"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        ema1 = EMA.compute({'close': close}, {'window': window})['ema']
        ema2 = EMA.compute({'close': ema1}, {'window': window})['ema']
        ema3 = EMA.compute({'close': ema2}, {'window': window})['ema']

        trix = (ema3 - ema3.shift(1, fill_value=ema3.mean())) / ema3.shift(1, fill_value=ema3.mean())
        trix *= 100

        return {'trix': pd.Series(trix, name=f'trix_{window}')}


class MassIndex(IndicatorInterface):
    """Mass Index (MI)

    It uses the high-low range to identify trend reversals based on range
    expansions. It identifies range bulges that can foreshadow a reversal of
    the current trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:mass_index

    Args:
        data: {'high': pd.Series, 'low': pd.Series}
        params: {'window_fast': int, 'window_slow': int}

    Returns:
        {'mass_index': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["window_fast", "window_slow"]
    _outputs = ["mass_index"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        window_fast = params['window_fast']
        window_slow = params['window_slow']

        amplitude = high - low
        ema1 = EMA.compute({'close': amplitude}, {'window': window_fast})['ema']
        ema2 = EMA.compute({'close': ema1}, {'window': window_fast})['ema']
        mass = ema1 / ema2
        mass_index = mass.rolling(window_slow, min_periods=window_slow).sum()

        return {'mass_index': pd.Series(mass_index, name=f"mass_index_{window_fast}_{window_slow}")}


class Ichimoku(IndicatorInterface):
    """Ichimoku Kinko Hyo (Ichimoku)

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ichimoku_cloud

    Args:
        data: {'high': pd.Series, 'low': pd.Series}
        params: {'window1': int, 'window2': int, 'window3': int, 'visual': bool}

    Returns:
        {'conversion_line': pd.Series, 'base_line': pd.Series, 'span_a': pd.Series, 'span_b': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["window1", "window2", "window3", "visual"]
    _outputs = ["conversion_line", "base_line", "span_a", "span_b"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        window1 = params['window1']
        window2 = params['window2']
        window3 = params['window3']
        visual = params['visual']

        conv = 0.5 * (
            high.rolling(window1, min_periods=window1).max()
            + low.rolling(window1, min_periods=window1).min()
        )
        base = 0.5 * (
            high.rolling(window2, min_periods=window2).max()
            + low.rolling(window2, min_periods=window2).min()
        )

        spana = 0.5 * (conv + base)
        spana = spana.shift(window2, fill_value=spana.mean()) if visual else spana

        spanb = 0.5 * (
            high.rolling(window3, min_periods=window3).max()
            + low.rolling(window3, min_periods=window3).min()
        )
        spanb = spanb.shift(window2, fill_value=spanb.mean()) if visual else spanb

        return {
            'conversion_line': pd.Series(conv, name=f"ichimoku_conv_{window1}_{window2}"),
            'base_line': pd.Series(base, name=f"ichimoku_base_{window1}_{window2}"),
            'span_a': pd.Series(spana, name=f"ichimoku_a_{window1}_{window2}"),
            'span_b': pd.Series(spanb, name=f"ichimoku_b_{window1}_{window2}")
        }


class KST(IndicatorInterface):
    """KST Oscillator (KST Signal)

    It is useful to identify major stock market cycle junctures because its
    formula is weighed to be more greatly influenced by the longer and more
    dominant time spans, in order to better reflect the primary swings of stock
    market cycle.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:know_sure_thing_kst

    Args:
        data: {'close': pd.Series}
        params: {'roc1': int, 'roc2': int, 'roc3': int, 'roc4': int,
                 'window1': int, 'window2': int, 'window3': int, 'window4': int, 'nsig': int}

    Returns:
        {'kst': pd.Series, 'kst_signal': pd.Series, 'kst_diff': pd.Series}
    """
    _data = ["close"]
    _params = ["roc1", "roc2", "roc3", "roc4", "window1", "window2", "window3", "window4", "nsig"]
    _outputs = ["kst", "kst_signal", "kst_diff"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        r1, r2, r3, r4 = params['roc1'], params['roc2'], params['roc3'], params['roc4']
        w1, w2, w3, w4 = params['window1'], params['window2'], params['window3'], params['window4']
        nsig = params['nsig']

        rocma1 = (
            ((close - close.shift(r1, fill_value=close.mean())) / close.shift(r1, fill_value=close.mean()))
            .rolling(w1, min_periods=w1).mean()
        )
        rocma2 = (
            ((close - close.shift(r2, fill_value=close.mean())) / close.shift(r2, fill_value=close.mean()))
            .rolling(w2, min_periods=w2).mean()
        )
        rocma3 = (
            ((close - close.shift(r3, fill_value=close.mean())) / close.shift(r3, fill_value=close.mean()))
            .rolling(w3, min_periods=w3).mean()
        )
        rocma4 = (
            ((close - close.shift(r4, fill_value=close.mean())) / close.shift(r4, fill_value=close.mean()))
            .rolling(w4, min_periods=w4).mean()
        )

        kst = 100 * (rocma1 + 2 * rocma2 + 3 * rocma3 + 4 * rocma4)
        kst_sig = kst.rolling(nsig, min_periods=nsig).mean()
        kst_diff = kst - kst_sig

        return {
            'kst': pd.Series(kst, name="kst"),
            'kst_signal': pd.Series(kst_sig, name="kst_sig"),
            'kst_diff': pd.Series(kst_diff, name="kst_diff")
        }


class DPO(IndicatorInterface):
    """Detrended Price Oscillator (DPO)

    Is an indicator designed to remove trend from price and make it easier to
    identify cycles.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:detrended_price_osci

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'dpo': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["dpo"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        dpo = (
            close.shift(int((0.5 * window) + 1), fill_value=close.mean())
            - close.rolling(window, min_periods=window).mean()
        )

        return {'dpo': pd.Series(dpo, name=f"dpo_{window}")}


class CCI(IndicatorInterface):
    """Commodity Channel Index (CCI)

    CCI measures the difference between a security's price change and its
    average price change. High positive readings indicate that prices are well
    above their average, which is a show of strength. Low negative readings
    indicate that prices are well below their average, which is a show of
    weakness.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:commodity_channel_index_cci

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'constant': float}

    Returns:
        {'cci': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "constant"]
    _outputs = ["cci"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        constant = params['constant']

        def _mad(x):
            return np.mean(np.abs(x - np.mean(x)))

        typical_price = (high + low + close) / 3.0
        cci = (
            typical_price - typical_price.rolling(window, min_periods=window).mean()
        ) / (constant * typical_price.rolling(window, min_periods=window).apply(_mad, True))

        return {'cci': pd.Series(cci, name="cci")}


class ADX(IndicatorInterface):
    """Average Directional Movement Index (ADX)

    The Plus Directional Indicator (+DI) and Minus Directional Indicator (-DI)
    are derived from smoothed averages of these differences, and measure trend
    direction over time. These two indicators are often referred to
    collectively as the Directional Movement Indicator (DMI).

    The Average Directional Index (ADX) is in turn derived from the smoothed
    averages of the difference between +DI and -DI, and measures the strength
    of the trend (regardless of direction) over time.

    Using these three indicators together, chartists can determine both the
    direction and strength of the trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_directional_index_adx

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'adx': pd.Series, 'adx_pos': pd.Series, 'adx_neg': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["adx", "adx_pos", "adx_neg"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        if window == 0:
            raise ValueError("window may not be 0")

        close_shift = close.shift(1)

        pdm = get_min_max(high, close_shift, "max")
        pdn = get_min_max(low, close_shift, "min")

        diff_directional_movement = pdm - pdn

        trs_initial = np.zeros(window - 1)
        trs = np.zeros(len(close) - (window - 1))
        trs[0] = diff_directional_movement.dropna().iloc[0:window].sum()
        diff_directional_movement = diff_directional_movement.reset_index(drop=True)

        for i in range(1, len(trs) - 1):
            trs[i] = (
                trs[i - 1] - (trs[i - 1] / float(window))
                + diff_directional_movement[window + i]
            )

        diff_up = high - high.shift(1)
        diff_down = low.shift(1) - low

        pos = abs(((diff_up > diff_down) & (diff_up > 0)) * diff_up)
        neg = abs(((diff_down > diff_up) & (diff_down > 0)) * diff_down)

        dip = np.zeros(len(close) - (window - 1))
        dip[0] = pos.dropna().iloc[0:window].sum()
        pos = pos.reset_index(drop=True)

        for i in range(1, len(dip) - 1):
            dip[i] = dip[i - 1] - (dip[i - 1] / float(window)) + pos[window + i]

        din = np.zeros(len(close) - (window - 1))
        din[0] = neg.dropna().iloc[0:window].sum()
        neg = neg.reset_index(drop=True)

        for i in range(1, len(din) - 1):
            din[i] = din[i - 1] - (din[i - 1] / float(window)) + neg[window + i]

        # Calculate ADX
        dip_percent = np.zeros(len(trs))
        for idx, value in enumerate(trs):
            if value != 0:
                dip_percent[idx] = 100 * (dip[idx] / value)
            else:
                dip_percent[idx] = 0

        din_percent = np.zeros(len(trs))
        for idx, value in enumerate(trs):
            if value != 0:
                din_percent[idx] = 100 * (din[idx] / value)
            else:
                din_percent[idx] = 0

        directional_index = np.zeros(len(trs))
        for idx in range(len(trs)):
            if dip_percent[idx] + din_percent[idx] != 0:
                directional_index[idx] = 100 * np.abs(
                    (dip_percent[idx] - din_percent[idx]) / (dip_percent[idx] + din_percent[idx])
                )
            else:
                directional_index[idx] = 0

        adx_series = np.zeros(len(trs))
        adx_series[window] = directional_index[0:window].mean()

        for i in range(window + 1, len(adx_series)):
            adx_series[i] = (
                (adx_series[i - 1] * (window - 1)) + directional_index[i - 1]
            ) / float(window)

        adx_series = np.concatenate((trs_initial, adx_series), axis=0)
        adx_series = pd.Series(data=adx_series, index=close.index)

        # Calculate ADX pos
        dip_output = np.zeros(len(close))
        for i in range(1, len(trs) - 1):
            if trs[i] != 0:
                dip_output[i + window] = 100 * (dip[i] / trs[i])
            else:
                dip_output[i + window] = 0
        adx_pos_series = pd.Series(dip_output, index=close.index)

        # Calculate ADX neg
        din_output = np.zeros(len(close))
        for i in range(1, len(trs) - 1):
            if trs[i] != 0:
                din_output[i + window] = 100 * (din[i] / trs[i])
            else:
                din_output[i + window] = 0
        adx_neg_series = pd.Series(din_output, index=close.index)

        return {
            'adx': pd.Series(adx_series, name="adx"),
            'adx_pos': pd.Series(adx_pos_series, name="adx_pos"),
            'adx_neg': pd.Series(adx_neg_series, name="adx_neg")
        }


class Vortex(IndicatorInterface):
    """Vortex Indicator (VI)

    It consists of two oscillators that capture positive and negative trend
    movement. A bullish signal triggers when the positive trend indicator
    crosses above the negative trend indicator or a key level.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:vortex_indicator

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'vortex_pos': pd.Series, 'vortex_neg': pd.Series, 'vortex_diff': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["vortex_pos", "vortex_neg", "vortex_diff"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        close_shift = close.shift(1, fill_value=close.mean())
        tr = true_range(high, low, close)
        trn = tr.rolling(window, min_periods=window).sum()
        vmp = np.abs(high - low.shift(1))
        vmm = np.abs(low - high.shift(1))
        vip = vmp.rolling(window, min_periods=window).sum() / trn
        vin = vmm.rolling(window, min_periods=window).sum() / trn
        vid = vip - vin

        return {
            'vortex_pos': pd.Series(vip, name="vip"),
            'vortex_neg': pd.Series(vin, name="vin"),
            'vortex_diff': pd.Series(vid, name="vid")
        }


class PSAR(IndicatorInterface):
    """Parabolic Stop and Reverse (Parabolic SAR)

    The Parabolic Stop and Reverse, more commonly known as the
    Parabolic SAR,is a trend-following indicator developed by
    J. Welles Wilder. The Parabolic SAR is displayed as a single
    parabolic line (or dots) underneath the price bars in an uptrend,
    and above the price bars in a downtrend.

    https://school.stockcharts.com/doku.php?id=technical_indicators:parabolic_sar

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'step': float, 'max_step': float}

    Returns:
        {'psar': pd.Series, 'psar_up': pd.Series, 'psar_down': pd.Series,
         'psar_up_indicator': pd.Series, 'psar_down_indicator': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["step", "max_step"]
    _outputs = ["psar", "psar_up", "psar_down", "psar_up_indicator", "psar_down_indicator"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        step = params['step']
        max_step = params['max_step']

        up_trend = True
        acceleration_factor = step
        up_trend_high = high.iloc[0]
        down_trend_low = low.iloc[0]

        psar = close.copy()
        psar_up = pd.Series(index=psar.index, dtype="float64")
        psar_down = pd.Series(index=psar.index, dtype="float64")

        for i in range(2, len(close)):
            reversal = False

            max_high = high.iloc[i]
            min_low = low.iloc[i]

            if up_trend:
                psar.iloc[i] = psar.iloc[i - 1] + (
                    acceleration_factor * (up_trend_high - psar.iloc[i - 1])
                )

                if min_low < psar.iloc[i]:
                    reversal = True
                    psar.iloc[i] = up_trend_high
                    down_trend_low = min_low
                    acceleration_factor = step
                else:
                    if max_high > up_trend_high:
                        up_trend_high = max_high
                        acceleration_factor = min(acceleration_factor + step, max_step)

                    low1 = low.iloc[i - 1]
                    low2 = low.iloc[i - 2]
                    if low2 < psar.iloc[i]:
                        psar.iloc[i] = low2
                    elif low1 < psar.iloc[i]:
                        psar.iloc[i] = low1
            else:
                psar.iloc[i] = psar.iloc[i - 1] - (
                    acceleration_factor * (psar.iloc[i - 1] - down_trend_low)
                )

                if max_high > psar.iloc[i]:
                    reversal = True
                    psar.iloc[i] = down_trend_low
                    up_trend_high = max_high
                    acceleration_factor = step
                else:
                    if min_low < down_trend_low:
                        down_trend_low = min_low
                        acceleration_factor = min(acceleration_factor + step, max_step)

                    high1 = high.iloc[i - 1]
                    high2 = high.iloc[i - 2]
                    if high2 > psar.iloc[i]:
                        psar[i] = high2
                    elif high1 > psar.iloc[i]:
                        psar.iloc[i] = high1

            up_trend = up_trend != reversal

            if up_trend:
                psar_up.iloc[i] = psar.iloc[i]
            else:
                psar_down.iloc[i] = psar.iloc[i]

        psar_up_indicator = psar_up.where(
            psar_up.notnull() & psar_up.shift(1).isnull(), 0
        )
        psar_up_indicator = psar_up_indicator.where(psar_up_indicator == 0, 1)

        psar_down_indicator = psar_up.where(
            psar_down.notnull() & psar_down.shift(1).isnull(), 0
        )
        psar_down_indicator = psar_down_indicator.where(psar_down_indicator == 0, 1)

        return {
            'psar': pd.Series(psar, name="psar"),
            'psar_up': pd.Series(psar_up, name="psarup"),
            'psar_down': pd.Series(psar_down, name="psardown"),
            'psar_up_indicator': pd.Series(psar_up_indicator, name="psariup"),
            'psar_down_indicator': pd.Series(psar_down_indicator, name="psaridown")
        }


class STC(IndicatorInterface):
    """Schaff Trend Cycle (STC)

    The Schaff Trend Cycle (STC) is a charting indicator that
    is commonly used to identify market trends and provide buy
    and sell signals to traders. Developed in 1999 by noted currency
    trader Doug Schaff, STC is a type of oscillator and is based on
    the assumption that, regardless of time frame, currency trends
    accelerate and decelerate in cyclical patterns.

    https://www.investopedia.com/articles/forex/10/schaff-trend-cycle-indicator.asp

    Args:
        data: {'close': pd.Series}
        params: {'window_slow': int, 'window_fast': int, 'cycle': int, 'smooth1': int, 'smooth2': int}

    Returns:
        {'stc': pd.Series}
    """
    _data = ["close"]
    _params = ["window_slow", "window_fast", "cycle", "smooth1", "smooth2"]
    _outputs = ["stc"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window_slow = params['window_slow']
        window_fast = params['window_fast']
        cycle = params['cycle']
        smooth1 = params['smooth1']
        smooth2 = params['smooth2']

        emafast = EMA.compute({'close': close}, {'window': window_fast})['ema']
        emaslow = EMA.compute({'close': close}, {'window': window_slow})['ema']
        macd = emafast - emaslow

        macdmin = macd.rolling(window=cycle).min()
        macdmax = macd.rolling(window=cycle).max()
        stoch_k = 100 * (macd - macdmin) / (macdmax - macdmin)
        stoch_d = EMA.compute({'close': stoch_k}, {'window': smooth1})['ema']

        stoch_d_min = stoch_d.rolling(window=cycle).min()
        stoch_d_max = stoch_d.rolling(window=cycle).max()
        stoch_kd = 100 * (stoch_d - stoch_d_min) / (stoch_d_max - stoch_d_min)
        stc = EMA.compute({'close': stoch_kd}, {'window': smooth2})['ema']

        return {'stc': pd.Series(stc, name="stc")}
