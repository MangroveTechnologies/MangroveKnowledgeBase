"""
Momentum Indicators.

Provides momentum-based technical analysis indicators including RSI, Stochastic,
Williams %R, KAMA, ROC, and more.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.trend_indicators import EMA, SMA
from mangrove_kb.indicators.utils import true_range


class RSI(IndicatorInterface):
    """Relative Strength Index (RSI)

    Compares the magnitude of recent gains and losses over a specified time
    period to measure speed and change of price movements of a security. It is
    primarily used to attempt to identify overbought or oversold conditions in
    the trading of an asset.

    https://www.investopedia.com/terms/r/rsi.asp

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'rsi': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["rsi"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        diff = close.diff(1)
        up_direction = diff.where(diff > 0, 0.0)
        down_direction = -diff.where(diff < 0, 0.0)

        emaup = up_direction.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        emadn = down_direction.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

        relative_strength = emaup / emadn
        rsi = pd.Series(
            np.where(emadn == 0, 100, 100 - (100 / (1 + relative_strength))),
            index=close.index,
        )

        return {'rsi': pd.Series(rsi, name="rsi")}


class TSI(IndicatorInterface):
    """True strength index (TSI)

    Shows both trend direction and overbought/oversold conditions.

    https://school.stockcharts.com/doku.php?id=technical_indicators:true_strength_index

    Args:
        data: {'close': pd.Series}
        params: {'window_slow': int, 'window_fast': int}

    Returns:
        {'tsi': pd.Series}
    """
    _data = ["close"]
    _params = ["window_slow", "window_fast"]
    _outputs = ["tsi"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window_slow = params['window_slow']
        window_fast = params['window_fast']

        diff_close = close - close.shift(1)

        smoothed = (
            diff_close.ewm(span=window_slow, min_periods=window_slow, adjust=False)
            .mean()
            .ewm(span=window_fast, min_periods=window_fast, adjust=False)
            .mean()
        )
        smoothed_abs = (
            abs(diff_close)
            .ewm(span=window_slow, min_periods=window_slow, adjust=False)
            .mean()
            .ewm(span=window_fast, min_periods=window_fast, adjust=False)
            .mean()
        )
        tsi = smoothed / smoothed_abs
        tsi *= 100

        return {'tsi': pd.Series(tsi, name="tsi")}


class UltimateOscillator(IndicatorInterface):
    """Ultimate Oscillator

    Larry Williams' (1976) signal, a momentum oscillator designed to capture
    momentum across three different timeframes.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ultimate_oscillator

    BP = Close - Minimum(Low or Prior Close).
    TR = Maximum(High or Prior Close)  -  Minimum(Low or Prior Close)
    Average7 = (7-period BP Sum) / (7-period TR Sum)
    Average14 = (14-period BP Sum) / (14-period TR Sum)
    Average28 = (28-period BP Sum) / (28-period TR Sum)

    UO = 100 x [(4 x Average7)+(2 x Average14)+Average28]/(4+2+1)

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window1': int, 'window2': int, 'window3': int,
                 'weight1': float, 'weight2': float, 'weight3': float}

    Returns:
        {'ultimate_oscillator': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window1", "window2", "window3", "weight1", "weight2", "weight3"]
    _outputs = ["ultimate_oscillator"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window1 = params['window1']
        window2 = params['window2']
        window3 = params['window3']
        weight1 = params['weight1']
        weight2 = params['weight2']
        weight3 = params['weight3']

        close_shift = close.shift(1)
        tr = true_range(high, low, close)
        buying_pressure = close - pd.DataFrame(
            {"low": low, "close": close_shift}
        ).min(axis=1, skipna=False)

        avg_s = (
            buying_pressure.rolling(window1, min_periods=window1).sum()
            / tr.rolling(window1, min_periods=window1).sum()
        )
        avg_m = (
            buying_pressure.rolling(window2, min_periods=window2).sum()
            / tr.rolling(window2, min_periods=window2).sum()
        )
        avg_l = (
            buying_pressure.rolling(window3, min_periods=window3).sum()
            / tr.rolling(window3, min_periods=window3).sum()
        )
        uo = (
            100.0
            * ((weight1 * avg_s) + (weight2 * avg_m) + (weight3 * avg_l))
            / (weight1 + weight2 + weight3)
        )

        return {'ultimate_oscillator': pd.Series(uo, name="uo")}


class StochasticOscillator(IndicatorInterface):
    """Stochastic Oscillator

    Developed in the late 1950s by George Lane. The stochastic
    oscillator presents the location of the closing price of a
    stock in relation to the high and low range of the price
    of a stock over a period of time, typically a 14-day period.

    VARIANT: this is the **Fast** stochastic. `stoch_k` is the raw %K and `stoch_d` is an SMA of
    it. The literature distinguishes Fast, Slow (%K itself smoothed, %D an SMA of that) and Full
    (user-specified smoothing on both); they produce materially different series, and neither the
    class name nor the parameters say which one this is.

    https://school.stockcharts.com/doku.php?id=technical_indicators:stochastic_oscillator_fast_slow_and_full

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'smooth_window': int}

    Returns:
        {'stoch_k': pd.Series, 'stoch_d': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "smooth_window"]
    _outputs = ["stoch_k", "stoch_d"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        smooth_window = params['smooth_window']

        smin = low.rolling(window, min_periods=window).min()
        smax = high.rolling(window, min_periods=window).max()
        stoch_k = 100 * (close - smin) / (smax - smin)
        stoch_d = stoch_k.rolling(smooth_window, min_periods=smooth_window).mean()

        return {
            'stoch_k': pd.Series(stoch_k, name="stoch_k"),
            'stoch_d': pd.Series(stoch_d, name="stoch_d")
        }


class KAMA(IndicatorInterface):
    """Kaufman's Adaptive Moving Average (KAMA)

    Moving average designed to account for market noise or volatility. KAMA
    will closely follow prices when the price swings are relatively small and
    the noise is low. KAMA will adjust when the price swings widen and follow
    prices from a greater distance. This trend-following indicator can be
    used to identify the overall trend, time turning points and filter price
    movements.

    https://www.tradingview.com/ideas/kama/

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'pow1': int, 'pow2': int}

    Returns:
        {'kama': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "pow1", "pow2"]
    _outputs = ["kama"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        pow1 = params['pow1']
        pow2 = params['pow2']

        close_values = close.values
        vol = pd.Series(abs(close - np.roll(close, 1)))

        er_num = abs(close_values - np.roll(close_values, window))
        er_den = vol.rolling(window, min_periods=window).sum()
        efficiency_ratio = np.divide(
            er_num, er_den, out=np.zeros_like(er_num), where=er_den != 0
        )

        smoothing_constant = (
            (
                efficiency_ratio * (2.0 / (pow1 + 1) - 2.0 / (pow2 + 1.0))
                + 2 / (pow2 + 1.0)
            )
            ** 2.0
        ).values

        kama_values = np.zeros(smoothing_constant.size)
        len_kama = len(kama_values)
        first_value = True

        for i in range(len_kama):
            if np.isnan(smoothing_constant[i]):
                kama_values[i] = np.nan
            elif first_value:
                # Seed with the SMA of the trailing `window` closes, per the documented
                # construction (StockCharts step 3). This used to seed with the bar's own close --
                # a warmup-only divergence that decays, but the seed bar is exactly where it is
                # largest, and it is a divergence from the reference.
                kama_values[i] = np.mean(close_values[max(0, i - window + 1): i + 1])
                first_value = False
            else:
                kama_values[i] = kama_values[i - 1] + smoothing_constant[i] * (
                    close_values[i] - kama_values[i - 1]
                )

        kama_series = pd.Series(kama_values, index=close.index)
        return {'kama': pd.Series(kama_series, name="kama")}


class ROC(IndicatorInterface):
    """Rate of Change (ROC)

    The Rate-of-Change (ROC) indicator, which is also referred to as simply
    Momentum, is a pure momentum oscillator that measures the percent change in
    price from one period to the next. The ROC calculation compares the current
    price with the price "n" periods ago. The plot forms an oscillator that
    fluctuates above and below the zero line as the Rate-of-Change moves from
    positive to negative. As a momentum oscillator, ROC signals include
    centerline crossovers, divergences and overbought-oversold readings.

    https://school.stockcharts.com/doku.php?id=technical_indicators:rate_of_change_roc_and_momentum

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'roc': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["roc"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        roc = ((close - close.shift(window)) / close.shift(window)) * 100
        return {'roc': pd.Series(roc, name="roc")}


class AwesomeOscillator(IndicatorInterface):
    """Awesome Oscillator

    The Awesome Oscillator is an indicator used to measure market momentum. AO
    calculates the difference of a 34 Period and 5 Period Simple Moving
    Averages. The Simple Moving Averages that are used are not calculated
    using closing price but rather each bar's midpoints. AO is generally used
    to affirm trends or to anticipate possible reversals.

    MEDIAN PRICE = (HIGH+LOW)/2
    AO = SMA(MEDIAN PRICE, 5)-SMA(MEDIAN PRICE, 34)

    Args:
        data: {'high': pd.Series, 'low': pd.Series}
        params: {'window1': int, 'window2': int}

    Returns:
        {'ao': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["window1", "window2"]
    _outputs = ["ao"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        window1 = params['window1']
        window2 = params['window2']

        median_price = 0.5 * (high + low)

        sma_short = SMA.compute({'close': median_price}, {'window': window1})['sma']
        sma_long = SMA.compute({'close': median_price}, {'window': window2})['sma']
        ao = sma_short - sma_long

        return {'ao': pd.Series(ao, name="ao")}


class WilliamsR(IndicatorInterface):
    """Williams %R

    Developed by Larry Williams, Williams %R is a momentum indicator that is
    the inverse of the Fast Stochastic Oscillator. Also referred to as %R,
    Williams %R reflects the level of the close relative to the highest high
    for the look-back period. In contrast, the Stochastic Oscillator reflects
    the level of the close relative to the lowest low. %R corrects for the
    inversion by multiplying the raw value by -100. As a result, the Fast
    Stochastic Oscillator and Williams %R produce the exact same lines, only
    the scaling is different. Williams %R oscillates from 0 to -100.

    Readings from 0 to -20 are considered overbought. Readings from -80 to -100
    are considered oversold.

    %R = (Highest High - Close)/(Highest High - Lowest Low) * -100

    https://school.stockcharts.com/doku.php?id=technical_indicators:williams_r

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'wr': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["wr"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        highest_high = high.rolling(window, min_periods=window).max()
        lowest_low = low.rolling(window, min_periods=window).min()
        wr = -100 * (highest_high - close) / (highest_high - lowest_low)

        return {'wr': pd.Series(wr, name="wr")}


class StochRSI(IndicatorInterface):
    """Stochastic RSI

    The StochRSI oscillator was developed to take advantage of both momentum
    indicators in order to create a more sensitive indicator that is attuned to
    a specific security's historical performance rather than a generalized analysis
    of price change.

    SCALE: this emits 0..1, the canonical Chande-Kroll / StockCharts form. The literature is
    genuinely split -- Fidelity and many platforms render the same quantity x100, and TradingView
    is internally inconsistent (its docs say 0-1, its plotted indicator renders 0-100). The
    conventional 20/80 overbought/oversold levels are therefore **0.20 / 0.80** here. Applying 20
    and 80 directly to this series can never produce a signal.

    https://school.stockcharts.com/doku.php?id=technical_indicators:stochrsi
    https://www.investopedia.com/terms/s/stochrsi.asp

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'smooth1': int, 'smooth2': int}

    Returns:
        {'stochrsi': pd.Series, 'stochrsi_k': pd.Series, 'stochrsi_d': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "smooth1", "smooth2"]
    _outputs = ["stochrsi", "stochrsi_k", "stochrsi_d"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        smooth1 = params['smooth1']
        smooth2 = params['smooth2']

        rsi_result = RSI.compute({'close': close}, {'window': window})['rsi']
        lowest_low_rsi = rsi_result.rolling(window).min()
        stochrsi = (rsi_result - lowest_low_rsi) / (
            rsi_result.rolling(window).max() - lowest_low_rsi
        )
        stochrsi_k = stochrsi.rolling(smooth1).mean()
        stochrsi_d = stochrsi_k.rolling(smooth2).mean()

        return {
            'stochrsi': pd.Series(stochrsi, name="stochrsi"),
            'stochrsi_k': pd.Series(stochrsi_k, name="stochrsi_k"),
            'stochrsi_d': pd.Series(stochrsi_d, name="stochrsi_d")
        }


class PPO(IndicatorInterface):
    """
    The Percentage Price Oscillator (PPO) is a momentum oscillator that measures
    the difference between two moving averages as a percentage of the larger moving average.

    https://school.stockcharts.com/doku.php?id=technical_indicators:price_oscillators_ppo

    Args:
        data: {'close': pd.Series}
        params: {'window_slow': int, 'window_fast': int, 'window_sign': int}

    Returns:
        {'ppo': pd.Series, 'ppo_signal': pd.Series, 'ppo_hist': pd.Series}
    """
    _data = ["close"]
    _params = ["window_slow", "window_fast", "window_sign"]
    _outputs = ["ppo", "ppo_signal", "ppo_hist"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window_slow = params['window_slow']
        window_fast = params['window_fast']
        window_sign = params['window_sign']

        emafast = EMA.compute({'close': close}, {'window': window_fast})['ema']
        emaslow = EMA.compute({'close': close}, {'window': window_slow})['ema']
        ppo = ((emafast - emaslow) / emaslow) * 100
        ppo_signal = EMA.compute({'close': ppo}, {'window': window_sign})['ema']
        ppo_hist = ppo - ppo_signal

        return {
            'ppo': pd.Series(ppo, name=f"PPO_{window_fast}_{window_slow}"),
            'ppo_signal': pd.Series(ppo_signal, name=f"PPO_sign_{window_fast}_{window_slow}"),
            'ppo_hist': pd.Series(ppo_hist, name=f"PPO_hist_{window_fast}_{window_slow}")
        }


class PVO(IndicatorInterface):
    """
    The Percentage Volume Oscillator (PVO) is a momentum oscillator for volume.
    The PVO measures the difference between two volume-based moving averages as a
    percentage of the larger moving average.

    https://school.stockcharts.com/doku.php?id=technical_indicators:percentage_volume_oscillator_pvo

    Args:
        data: {'volume': pd.Series}
        params: {'window_slow': int, 'window_fast': int, 'window_sign': int}

    Returns:
        {'pvo': pd.Series, 'pvo_signal': pd.Series, 'pvo_hist': pd.Series}
    """
    _data = ["volume"]
    _params = ["window_slow", "window_fast", "window_sign"]
    _outputs = ["pvo", "pvo_signal", "pvo_hist"]

    @classmethod
    def _compute(cls, data, params):
        volume = data['volume']
        window_slow = params['window_slow']
        window_fast = params['window_fast']
        window_sign = params['window_sign']

        emafast = EMA.compute({'close': volume}, {'window': window_fast})['ema']
        emaslow = EMA.compute({'close': volume}, {'window': window_slow})['ema']
        pvo = ((emafast - emaslow) / emaslow) * 100
        pvo_signal = EMA.compute({'close': pvo}, {'window': window_sign})['ema']
        pvo_hist = pvo - pvo_signal

        return {
            'pvo': pd.Series(pvo, name=f"PVO_{window_fast}_{window_slow}"),
            'pvo_signal': pd.Series(pvo_signal, name=f"PVO_sign_{window_fast}_{window_slow}"),
            'pvo_hist': pd.Series(pvo_hist, name=f"PVO_hist_{window_fast}_{window_slow}")
        }


class MOM(IndicatorInterface):
    """Momentum (MOM)

    Absolute price change over a lookback window: MOM = close - close[-n].
    Distinct from ROC which expresses the same change as a percentage.

    Reference: Standard TA-Lib definition.

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'mom': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["mom"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        mom = close - close.shift(window)
        return {'mom': pd.Series(mom.values, index=close.index, name=f'mom_{window}')}


class BOP(IndicatorInterface):
    """Balance of Power (BOP)

    Measures buying vs. selling pressure within a single bar:
        BOP = (close - open) / (high - low)
    Returns a value in [-1, 1] where positive = buyers in control, negative =
    sellers. NaN where high == low (no intrabar range).

    SMOOTHING: this is the RAW single-bar series, which the literature does not use directly.
    Livshin writes "I typically plot a 14-day moving average of the balance of power indicator",
    and TradingView notes the raw series is "quite choppy". Every source plots a 14-period moving
    average of it. A consumer wanting the indicator as published must smooth this themselves.

    Reference: Igor Livshin. TA-Lib canonical definition.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {}

    Returns:
        {'bop': pd.Series}
    """
    _data = ["open", "high", "low", "close"]
    _params = []
    _outputs = ["bop"]

    @classmethod
    def _compute(cls, data, params):
        open_ = data['open']
        high = data['high']
        low = data['low']
        close = data['close']

        # Element-wise, fully vectorized. Divide-by-zero yields NaN (correct).
        numerator = (close - open_).to_numpy(dtype=np.float64, copy=False)
        denom = (high - low).to_numpy(dtype=np.float64, copy=False)
        with np.errstate(divide='ignore', invalid='ignore'):
            bop = np.where(denom != 0, numerator / denom, np.nan)
        return {'bop': pd.Series(bop, index=close.index, name='bop')}


class APO(IndicatorInterface):
    """Absolute Price Oscillator (APO)

    Difference between a fast and slow EMA of close:
        APO = EMA(close, window_fast) - EMA(close, window_slow)
    Same quantity as the MACD line (MACD without its signal line).

    Reference: TA-Lib canonical definition.

    Args:
        data: {'close': pd.Series}
        params: {'window_fast': int, 'window_slow': int}

    Returns:
        {'apo': pd.Series}
    """
    _data = ["close"]
    _params = ["window_fast", "window_slow"]
    _outputs = ["apo"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window_fast = params['window_fast']
        window_slow = params['window_slow']

        ema_fast = EMA.compute({'close': close}, {'window': window_fast})['ema']
        ema_slow = EMA.compute({'close': close}, {'window': window_slow})['ema']
        apo = ema_fast - ema_slow
        return {'apo': pd.Series(apo.values, index=close.index, name=f'apo_{window_fast}_{window_slow}')}


class CMO(IndicatorInterface):
    """Chande Momentum Oscillator (CMO)

    Similar in spirit to RSI but uses the raw sum of gains and losses rather
    than smoothed averages. Ranges from -100 (strongest down) to +100
    (strongest up), with 0 as neutral.

    Formula:
        diff = close.diff(1)
        pos_sum = sum(diff where diff > 0, over window)
        neg_sum = sum(|diff| where diff < 0, over window)
        CMO = 100 * (pos_sum - neg_sum) / (pos_sum + neg_sum)

    Reference: Tushar S. Chande, "The New Technical Trader" (1994).

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'cmo': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["cmo"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        diff = close.diff(1)
        # np.where mask, then vanilla rolling().sum() -- avoids the rolling.apply anti-pattern.
        diff_arr = diff.to_numpy(dtype=np.float64, copy=False)
        positive = pd.Series(np.where(diff_arr > 0, diff_arr, 0.0), index=close.index)
        negative = pd.Series(np.where(diff_arr < 0, -diff_arr, 0.0), index=close.index)

        pos_sum = positive.rolling(window, min_periods=window).sum()
        neg_sum = negative.rolling(window, min_periods=window).sum()

        with np.errstate(divide='ignore', invalid='ignore'):
            cmo = 100.0 * (pos_sum - neg_sum) / (pos_sum + neg_sum)
        return {'cmo': pd.Series(cmo.values, index=close.index, name=f'cmo_{window}')}
