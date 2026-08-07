"""
Trend Indicators.

Provides trend-based technical analysis indicators including MACD, EMA, SMA,
ADX, Aroon, Ichimoku, PSAR, and more.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
from functools import lru_cache

import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.utils import get_min_max, true_range, typical_price


@lru_cache(maxsize=64)
def _wma_weights(window: int) -> np.ndarray:
    """Weighted-moving-average weights. Read-only; safe to reuse across calls."""
    w = np.arange(1, window + 1, dtype=np.float64) * (2.0 / (window * (window + 1)))
    w.flags.writeable = False
    return w


@lru_cache(maxsize=64)
def _epma_weights(window: int) -> np.ndarray:
    """Cached weight vector for End Point Moving Average (linear regression endpoint).

    For a window of size n, the linear regression fitted to y values at x = [0..n-1]
    projected to x = n-1 can be expressed as a weighted sum: EPMA = sum(w_i * y_i).

    Derivation: with mean_x = (n-1)/2 and S_xx = n*(n^2-1)/12,
        slope = sum((x_i - mean_x) * y_i) / S_xx
        EPMA  = mean_y + slope * (n-1)/2
              = sum( y_i * (1/n + (6*i + 4 - 2*n) / (n*(n+1))) )
    which simplifies to: w_i = (6*i + 4 - 2*n) / (n*(n+1))
    """
    i = np.arange(window, dtype=np.float64)
    w = (6.0 * i + 4.0 - 2.0 * window) / (window * (window + 1))
    w.flags.writeable = False
    return w


@lru_cache(maxsize=256)
def _alma_weights(window: int, offset: float, sigma: float) -> np.ndarray:
    """Cached Gaussian weights for Arnaud Legoux Moving Average.

    For a window of size n, offset in [0, 1], and sigma > 0:
        k = floor(offset * (n - 1))
        w_i = exp(-0.5 * ((sigma / n) * (i - k))^2) / Z
    where Z normalizes weights to sum to 1. Higher offset (closer to 1)
    weights more recent bars; higher sigma widens the Gaussian.
    """
    x = np.arange(window, dtype=np.float64)
    k = np.floor(offset * (window - 1))
    raw = np.exp(-0.5 * ((sigma / window) * (x - k)) ** 2)
    w = raw / raw.sum()
    w.flags.writeable = False
    return w


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

        weights = _wma_weights(window)
        close_values = close.to_numpy(dtype=np.float64, copy=False)

        wma_values = np.empty(len(close_values), dtype=np.float64)
        if len(close_values) < window:
            wma_values[:] = np.nan
        else:
            # output[j] = sum(close[j:j+window] * weights); pad warmup with NaN
            wma_values[: window - 1] = np.nan
            wma_values[window - 1 :] = np.convolve(close_values, weights[::-1], mode='valid')

        return {'wma': pd.Series(wma_values, index=close.index, name=f'wma_{window}')}


class DEMA(IndicatorInterface):
    """Double Exponential Moving Average (DEMA)

    Reduces lag of a traditional EMA by applying EMA twice and combining.

    Formula: DEMA = 2 * EMA(n) - EMA(EMA(n))

    Reference: Patrick Mulloy, "Smoothing Data with Less Lag",
    Technical Analysis of Stocks & Commodities, Jan 1994.

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'dema': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["dema"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        ema1 = EMA.compute({'close': close}, {'window': window})['ema']
        ema2 = EMA.compute({'close': ema1}, {'window': window})['ema']
        dema = 2.0 * ema1 - ema2
        return {'dema': pd.Series(dema.values, index=close.index, name=f'dema_{window}')}


class TEMA(IndicatorInterface):
    """Triple Exponential Moving Average (TEMA)

    Further reduces lag over DEMA by combining three EMA passes.

    Formula: TEMA = 3 * EMA - 3 * EMA(EMA) + EMA(EMA(EMA))

    Reference: Patrick Mulloy, "Smoothing Data with Less Lag",
    Technical Analysis of Stocks & Commodities, Jan 1994.

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'tema': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["tema"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        ema1 = EMA.compute({'close': close}, {'window': window})['ema']
        ema2 = EMA.compute({'close': ema1}, {'window': window})['ema']
        ema3 = EMA.compute({'close': ema2}, {'window': window})['ema']
        tema = 3.0 * ema1 - 3.0 * ema2 + ema3
        return {'tema': pd.Series(tema.values, index=close.index, name=f'tema_{window}')}


class TRIMA(IndicatorInterface):
    """Triangular Moving Average (TRIMA)

    Double-smoothed SMA. More weight is placed on the middle of the window than
    on the edges, reducing noise at both ends.

    Formula (TA-Lib convention):
      - if window is odd:  inner = SMA(window), outer = SMA((window+1)//2, inner)
      - if window is even: inner = SMA(window//2), outer = SMA(window//2 + 1, inner)

    Equivalently: TRIMA = SMA(SMA(close, n1), n2) where n1 + n2 - 1 = window.

    Reference: TA-Lib canonical implementation.

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'trima': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["trima"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        if window % 2 == 1:
            n1 = (window + 1) // 2
            n2 = n1
        else:
            n1 = window // 2
            n2 = n1 + 1
        inner = close.rolling(window=n1, min_periods=n1).mean()
        trima = inner.rolling(window=n2, min_periods=n2).mean()
        return {'trima': pd.Series(trima.values, index=close.index, name=f'trima_{window}')}


class SMMA(IndicatorInterface):
    """Smoothed Moving Average (SMMA), a.k.a. Wilder's Smoothing or RMA.

    Exponential smoothing with alpha = 1/window (vs EMA's 2/(window+1)), giving
    slower, more stable smoothing. Same family as used inside RSI and ATR.

    Formula: SMMA[i] = (SMMA[i-1] * (n-1) + close[i]) / n
             equivalent to ewm(alpha=1/n, adjust=False)

    Reference: J. Welles Wilder Jr., "New Concepts in Technical Trading Systems" (1978).

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'smma': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["smma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        smma = close.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
        return {'smma': pd.Series(smma.values, index=close.index, name=f'smma_{window}')}


class EPMA(IndicatorInterface):
    """End Point Moving Average (EPMA), a.k.a. Linear Regression Moving Average (LSMA).

    For each bar, fits a linear regression over the last `window` closes and returns
    the regression value at the endpoint (most recent bar). Projects the trend
    to "now" rather than averaging past values.

    Implementation: Expressed as a FIR filter with precomputed weights
      w_i = (6*i + 4 - 2*n) / (n*(n+1))
    for i = 0..n-1, so that EPMA = sum(w_i * close_i) over each window.

    Reference: Standard linear-regression-at-endpoint formulation.

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'epma': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["epma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        weights = _epma_weights(window)
        close_values = close.to_numpy(dtype=np.float64, copy=False)
        n = len(close_values)
        epma_values = np.full(n, np.nan)
        if n >= window:
            # np.convolve with reversed weights gives a rolling weighted sum.
            epma_values[window - 1:] = np.convolve(close_values, weights[::-1], mode='valid')
        return {'epma': pd.Series(epma_values, index=close.index, name=f'epma_{window}')}


class HMA(IndicatorInterface):
    """Hull Moving Average (HMA)

    Low-lag moving average designed to track price without sacrificing smoothness.
    Reduces lag compared to EMA/SMA while remaining smoother than WMA.

    Formula: HMA(n) = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))

    Reference: Alan Hull, "How to reduce lag in a moving average" (2005).
    https://alanhull.com/hull-moving-average

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'hma': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["hma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        half = max(1, int(window / 2))
        sqrt_n = max(1, int(np.sqrt(window)))

        wma_fast = WMA.compute({'close': close}, {'window': half})['wma']
        wma_slow = WMA.compute({'close': close}, {'window': window})['wma']
        raw = 2.0 * wma_fast - wma_slow
        hma = WMA.compute({'close': raw}, {'window': sqrt_n})['wma']
        return {'hma': pd.Series(hma.values, index=close.index, name=f'hma_{window}')}


class ALMA(IndicatorInterface):
    """Arnaud Legoux Moving Average (ALMA)

    Gaussian-weighted moving average where `offset` controls which part of the
    window carries most weight and `sigma` controls spread. Offset near 1 reacts
    faster to recent bars; offset near 0 resembles an SMA.

    Weights: w_i = exp(-0.5 * ((sigma / n) * (i - floor(offset*(n-1))))^2), normalized.
    Applied via np.convolve against cached weight vector.

    Reference: Arnaud Legoux & Dimitrios Kouzis-Loukas, "ALMA" (2009).

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'offset': float, 'sigma': float}

    Returns:
        {'alma': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "offset", "sigma"]
    _outputs = ["alma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        offset = float(params['offset'])
        sigma = float(params['sigma'])

        weights = _alma_weights(window, offset, sigma)
        close_values = close.to_numpy(dtype=np.float64, copy=False)
        n = len(close_values)
        alma_values = np.full(n, np.nan)
        if n >= window:
            # ALMA uses "forward" weight orientation (weights[0] applies to oldest
            # bar in each window), so reverse before convolve.
            alma_values[window - 1:] = np.convolve(close_values, weights[::-1], mode='valid')
        return {'alma': pd.Series(alma_values, index=close.index, name=f'alma_{window}')}


class T3(IndicatorInterface):
    """Tillson T3 Moving Average

    Six chained EMAs combined via Tillson's volume-factor formula. Produces a
    smooth, low-lag trend line. The `volume_factor` (a) controls smoothness:
    a=0 collapses to a triple EMA; a=1 is the most responsive.

    Formula:
        T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3
        where e1..e6 are EMAs chained and c1-c4 are Tillson's coefficients:
            c1 = -a^3
            c2 = 3*a^2 + 3*a^3
            c3 = -6*a^2 - 3*a - 3*a^3
            c4 = 1 + 3*a + 3*a^2 + a^3

    Reference: Tim Tillson, "Better Moving Averages",
    Technical Analysis of Stocks & Commodities, Jan 1998.

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'volume_factor': float}

    Returns:
        {'t3': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "volume_factor"]
    _outputs = ["t3"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        a = float(params['volume_factor'])

        # Tillson coefficients (derived from a)
        c1 = -a ** 3
        c2 = 3.0 * a ** 2 + 3.0 * a ** 3
        c3 = -6.0 * a ** 2 - 3.0 * a - 3.0 * a ** 3
        c4 = 1.0 + 3.0 * a + 3.0 * a ** 2 + a ** 3

        # Six chained EMAs via ewm (adjust=False, matches our EMA convention)
        e1 = EMA.compute({'close': close}, {'window': window})['ema']
        e2 = EMA.compute({'close': e1}, {'window': window})['ema']
        e3 = EMA.compute({'close': e2}, {'window': window})['ema']
        e4 = EMA.compute({'close': e3}, {'window': window})['ema']
        e5 = EMA.compute({'close': e4}, {'window': window})['ema']
        e6 = EMA.compute({'close': e5}, {'window': window})['ema']

        t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
        return {'t3': pd.Series(t3.values, index=close.index, name=f't3_{window}')}


class MAMA(IndicatorInterface):
    """MESA Adaptive Moving Average (MAMA) -- Ehlers.

    Adaptive moving average that speeds up in trending markets and slows down
    in consolidations, using a Hilbert Transform Discriminator to estimate the
    dominant cycle period and adjust alpha dynamically. Also emits FAMA
    (Following Adaptive MA), half-alpha of MAMA -- MAMA/FAMA crossovers are
    used as trend signals.

    Reference: John F. Ehlers, "MESA Adaptive Moving Averages",
    Technical Analysis of Stocks & Commodities, Sept 2001.
    http://traders.com/documentation/feedbk_docs/2014/01/traderstips.html

    Implementation: genuinely sequential (per-bar Hilbert phase/period state).
    Cannot be vectorized; loop is pure Python. Future optimization wave may
    numba-accelerate this if it becomes a hot spot.

    Args:
        data: {'close': pd.Series}
        params: {'fast_limit': float, 'slow_limit': float}

    Returns:
        {'mama': pd.Series, 'fama': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["fast_limit", "slow_limit"]
    _outputs = ["mama", "fama"]

    # See the warmup note in `_compute`: measured seed dependence, not a guess.
    _WARMUP_BARS = 40

    @classmethod
    def _compute(cls, data, params):
        # Ehlers specifies the input explicitly: "Inputs: Price = (H+L)/2". This consumed `close`,
        # which changes every downstream value -- the Hilbert coefficients, the [6, 50] period
        # clamp, the rate limit and the alpha limits all already match the paper, so the input was
        # the single divergence from it.
        price = (data['high'] + data['low']) / 2.0
        fast_limit = float(params['fast_limit'])
        slow_limit = float(params['slow_limit'])

        x = price.to_numpy(dtype=np.float64, copy=False)
        n = len(x)

        # Hilbert transform FIR coefficients (Ehlers)
        a_h, b_h = 0.0962, 0.5769
        # Smoothing weights (Ehlers): 0.2 for phase, 0.33/0.67 for period smoothing
        p_w = 0.2
        smp_w = 0.33
        smp_w_c = 0.67

        wma4 = np.zeros(n)
        dt = np.zeros(n)
        i1 = np.zeros(n)
        i2 = np.zeros(n)
        ji = np.zeros(n)
        jq = np.zeros(n)
        q1 = np.zeros(n)
        q2 = np.zeros(n)
        re = np.zeros(n)
        im = np.zeros(n)
        period = np.zeros(n)
        phase = np.zeros(n)
        mama = np.zeros(n)
        fama = np.zeros(n)
        smp = np.zeros(n)

        # State-dependent loop -- cannot be vectorized; Hilbert discriminator
        # requires per-bar phase/period feedback from previous bars.
        for i in range(6, n):
            adj_prev_period = 0.075 * period[i - 1] + 0.54

            # WMA(x, 4) and detrended WMA(x, 4)
            wma4[i] = 0.4 * x[i] + 0.3 * x[i - 1] + 0.2 * x[i - 2] + 0.1 * x[i - 3]
            dt[i] = adj_prev_period * (a_h * wma4[i] + b_h * wma4[i - 2] - b_h * wma4[i - 4] - a_h * wma4[i - 6])

            # Quadrature (detrender) and In-Phase component
            q1[i] = adj_prev_period * (a_h * dt[i] + b_h * dt[i - 2] - b_h * dt[i - 4] - a_h * dt[i - 6])
            i1[i] = dt[i - 3]

            # Phase Q1 and I1 by 90 degrees
            ji[i] = adj_prev_period * (a_h * i1[i] + b_h * i1[i - 2] - b_h * i1[i - 4] - a_h * i1[i - 6])
            jq[i] = adj_prev_period * (a_h * q1[i] + b_h * q1[i - 2] - b_h * q1[i - 4] - a_h * q1[i - 6])

            # Phasor addition for 3-bar averaging
            i2[i] = i1[i] - jq[i]
            q2[i] = q1[i] + ji[i]

            # Smooth I2 and Q2
            i2[i] = p_w * i2[i] + (1 - p_w) * i2[i - 1]
            q2[i] = p_w * q2[i] + (1 - p_w) * q2[i - 1]

            # Homodyne discriminator
            re[i] = i2[i] * i2[i - 1] + q2[i] * q2[i - 1]
            im[i] = i2[i] * q2[i - 1] - q2[i] * i2[i - 1]

            # Smooth re and im
            re[i] = p_w * re[i] + (1 - p_w) * re[i - 1]
            im[i] = p_w * im[i] + (1 - p_w) * im[i - 1]

            if im[i] != 0.0 and re[i] != 0.0:
                period[i] = 360.0 / np.degrees(np.arctan(im[i] / re[i]))
            else:
                period[i] = 0.0

            # Clamp period: no more than 1.5x previous, no less than 0.67x, bounds [6, 50]
            if period[i] > 1.5 * period[i - 1]:
                period[i] = 1.5 * period[i - 1]
            if period[i] < 0.67 * period[i - 1]:
                period[i] = 0.67 * period[i - 1]
            if period[i] < 6.0:
                period[i] = 6.0
            if period[i] > 50.0:
                period[i] = 50.0

            period[i] = p_w * period[i] + (1 - p_w) * period[i - 1]
            smp[i] = smp_w * period[i] + smp_w_c * smp[i - 1]

            if i1[i] != 0.0:
                phase[i] = np.degrees(np.arctan(q1[i] / i1[i]))

            dphase = phase[i - 1] - phase[i]
            if dphase < 1.0:
                dphase = 1.0

            alpha = fast_limit / dphase
            if alpha > fast_limit:
                alpha = fast_limit
            if alpha < slow_limit:
                alpha = slow_limit

            mama[i] = alpha * x[i] + (1.0 - alpha) * mama[i - 1]
            fama[i] = 0.5 * alpha * mama[i] + (1.0 - 0.5 * alpha) * fama[i - 1]

        # Warmup mask. Six bars covers the Hilbert FIR depth but NOT the recursion, which starts
        # from an uninitialised zero and needs far longer to forget that seed. Bar 6 previously
        # published a value roughly 50% below price as though it were an ordinary reading.
        #
        # The ramp itself is faithful to Ehlers' EasyLanguage, which gates on CurrentBar > 5 and
        # lets the recursion start from zero -- so the fix is to mask longer, not to reseed.
        # Measured by comparing a cold start against a warm start (600 bars prepended) across 15
        # synthetic series at three price levels: seed dependence falls below 1% by bar 19 and
        # below 0.1% by bar 34. 40 is that bound with margin.
        mama_out = mama.copy()
        fama_out = fama.copy()
        mama_out[:cls._WARMUP_BARS] = np.nan
        fama_out[:cls._WARMUP_BARS] = np.nan

        return {
            'mama': pd.Series(mama_out, index=price.index, name='mama'),
            'fama': pd.Series(fama_out, index=price.index, name='fama'),
        }


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

        w = window + 1
        high_arr = high.to_numpy(dtype=np.float64, copy=False)
        low_arr = low.to_numpy(dtype=np.float64, copy=False)
        n = len(high_arr)

        aroon_up_arr = np.full(n, np.nan)
        aroon_down_arr = np.full(n, np.nan)
        if n >= w:
            high_wins = np.lib.stride_tricks.sliding_window_view(high_arr, w)
            low_wins = np.lib.stride_tricks.sliding_window_view(low_arr, w)
            aroon_up_arr[w - 1 :] = high_wins.argmax(axis=-1).astype(np.float64) / window * 100.0
            aroon_down_arr[w - 1 :] = low_wins.argmin(axis=-1).astype(np.float64) / window * 100.0

        aroon_up = pd.Series(aroon_up_arr, index=high.index)
        aroon_down = pd.Series(aroon_down_arr, index=low.index)
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

    Note: Early bars (warmup period) produce NaN rather than approximated values.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:trix

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'window_sign': int}

    Returns:
        {'trix': pd.Series, 'trix_signal': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "window_sign"]
    _outputs = ["trix", "trix_signal"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        window_sign = params['window_sign']

        ema1 = EMA.compute({'close': close}, {'window': window})['ema']
        ema2 = EMA.compute({'close': ema1}, {'window': window})['ema']
        ema3 = EMA.compute({'close': ema2}, {'window': window})['ema']

        trix = (ema3 - ema3.shift(1)) / ema3.shift(1)
        trix *= 100

        # The signal line is TRIX's primary documented signal -- StockCharts calls signal-line
        # crossovers "the most common" TRIX signal -- and it was not emitted at all, so every
        # consumer had to reconstruct it. Canonically a 9-period EMA of TRIX.
        trix_signal = EMA.compute({'close': trix}, {'window': window_sign})['ema']

        return {
            'trix': pd.Series(trix, name=f'trix_{window}'),
            'trix_signal': pd.Series(trix_signal, name=f'trix_signal_{window_sign}'),
        }


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

    Note: Early bars (warmup period) produce NaN rather than approximated values.

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
            ((close - close.shift(r1)) / close.shift(r1))
            .rolling(w1, min_periods=w1).mean()
        )
        rocma2 = (
            ((close - close.shift(r2)) / close.shift(r2))
            .rolling(w2, min_periods=w2).mean()
        )
        rocma3 = (
            ((close - close.shift(r3)) / close.shift(r3))
            .rolling(w3, min_periods=w3).mean()
        )
        rocma4 = (
            ((close - close.shift(r4)) / close.shift(r4))
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

    Note: Early bars (warmup period) produce NaN rather than approximated values.

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
            close.shift(int((0.5 * window) + 1))
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

        tp = typical_price(high, low, close)
        tp_arr = tp.to_numpy(dtype=np.float64, copy=False)
        n = len(tp_arr)

        # True rolling mean absolute deviation: for each window, deviations are
        # measured against the window's OWN mean. Not the same as
        # |tp - rolling_mean|.rolling(w).mean() (which uses each bar's own
        # rolling mean as its reference point).
        mad_arr = np.full(n, np.nan)
        if n >= window:
            tp_wins = np.lib.stride_tricks.sliding_window_view(tp_arr, window)
            win_means = tp_wins.mean(axis=-1, keepdims=True)
            mad_arr[window - 1 :] = np.abs(tp_wins - win_means).mean(axis=-1)
        mad = pd.Series(mad_arr, index=tp.index)

        cci = (
            tp - tp.rolling(window, min_periods=window).mean()
        ) / (constant * mad)

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

        n = len(close)
        close_shift = close.shift(1)

        # True-range equivalent: max(high, prev_close) - min(low, prev_close).
        pdm = get_min_max(high, close_shift, "max")
        pdn = get_min_max(low, close_shift, "min")
        tr_arr = (pdm - pdn).to_numpy(dtype=np.float64)

        # Directional movements. Preserve original NaN-at-index-0 semantics so
        # nansum(...[:window+1]) matches dropna().iloc[0:window].sum().
        diff_up = high - high.shift(1)
        diff_down = low.shift(1) - low
        pos = abs(((diff_up > diff_down) & (diff_up > 0)) * diff_up)
        neg = abs(((diff_down > diff_up) & (diff_down > 0)) * diff_down)
        pos_arr = pos.to_numpy(dtype=np.float64)
        neg_arr = neg.to_numpy(dtype=np.float64)

        trs_len = n - window + 1
        trs = np.zeros(trs_len)
        dip = np.zeros(trs_len)
        din = np.zeros(trs_len)

        if trs_len >= 1:
            trs[0] = np.nansum(tr_arr[: window + 1])
            dip[0] = np.nansum(pos_arr[: window + 1])
            din[0] = np.nansum(neg_arr[: window + 1])

        # Wilder running-sum recurrence:
        #   x[i] = x[i-1] * (1 - 1/w) + raw[w + i]   for i = 1..trs_len-2
        # The original loop stops one short, leaving trs[trs_len-1] at 0.
        # Mean form y = x/w obeys ewm(alpha=1/w, adjust=False); scale back.
        if trs_len >= 3:
            alpha = 1.0 / window
            last_inclusive = trs_len - 2

            def _wilder_sum(seed_sum: float, raw: np.ndarray) -> np.ndarray:
                # Convert the Wilder running-sum recurrence into the ewm mean
                # form: y[i] = x[i]/w obeys ewm(alpha=1/w, adjust=False) when
                # its input is inp[0]=seed_sum/w and inp[k>=1]=raw[w+k]. Then
                # x = y * w. (Do NOT divide the tail by w -- that's the bug.)
                inp = np.empty(last_inclusive + 1)
                inp[0] = seed_sum / window
                inp[1:] = raw[window + 1 : window + last_inclusive + 1]
                y = pd.Series(inp).ewm(alpha=alpha, adjust=False).mean().to_numpy()
                return y * window

            trs[0 : last_inclusive + 1] = _wilder_sum(trs[0], tr_arr)
            dip[0 : last_inclusive + 1] = _wilder_sum(dip[0], pos_arr)
            din[0 : last_inclusive + 1] = _wilder_sum(din[0], neg_arr)

        # Percent directional indices + DX. Undefined cases are NaN, not zero. DX is undefined when
        # +DI + -DI == 0, and 0 is a meaningful DX reading, so substituting it conflates "no
        # directional strength" with "not computable".
        with np.errstate(divide='ignore', invalid='ignore'):
            dip_pct = np.where(trs != 0, 100.0 * dip / trs, np.nan)
            din_pct = np.where(trs != 0, 100.0 * din / trs, np.nan)
            denom = dip_pct + din_pct
            dx = np.where(denom != 0, 100.0 * np.abs(dip_pct - din_pct) / denom, np.nan)

        # ADX: Wilder smoothing of DX with a one-step lag.
        #   adx[w]   = mean(DX[0:w])
        #   adx[i]   = (adx[i-1]*(w-1) + DX[i-1]) / w    for i = w+1..trs_len-1
        # Equivalent to ewm(alpha=1/w, adjust=False) on [seed, DX[w..trs_len-2]].
        # Warmup is NaN, not zero. ADX = 0 means "no directional strength", which is a real market
        # state, so zero-filling 2*window-1 warmup bars left a consumer unable to tell twenty-seven
        # bars of warmup from a genuinely flat market -- and there was no NaN anywhere in the series
        # to mark them.
        adx_local = np.full(trs_len, np.nan)
        if trs_len > window:
            seed = np.nanmean(dx[0:window])
            adx_input = np.concatenate(([seed], dx[window : trs_len - 1]))
            adx_out = pd.Series(adx_input).ewm(alpha=1.0 / window, adjust=False).mean().to_numpy()
            adx_local[window:trs_len] = adx_out

        trs_initial = np.full(window - 1, np.nan)
        adx_series = pd.Series(np.concatenate((trs_initial, adx_local), axis=0), index=close.index)

        # adx_pos / adx_neg: fill positions [window+1 .. n-1] with the
        # percent directional indices for i = 1..trs_len-2 (original loop).
        dip_output = np.full(n, np.nan)
        din_output = np.full(n, np.nan)
        if trs_len >= 3:
            dip_output[window + 1 : n] = dip_pct[1 : trs_len - 1]
            din_output[window + 1 : n] = din_pct[1 : trs_len - 1]
        adx_pos_series = pd.Series(dip_output, index=close.index)
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

    Note: Early bars (warmup period) produce NaN rather than approximated values.

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

        close_shift = close.shift(1)
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
                        psar.iloc[i] = high2
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

        psar_down_indicator = psar_down.where(
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


class HeikinAshi(IndicatorInterface):
    """Heikin-Ashi candles.

    Smoothed candlestick representation that averages across multiple bars,
    making trends visually easier to identify. Japanese for "average bar".

    Formulas:
        HA_close = (open + high + low + close) / 4
        HA_open  = (prev_HA_open + prev_HA_close) / 2   (first: (open + close) / 2)
        HA_high  = max(high, HA_open, HA_close)
        HA_low   = min(low,  HA_open, HA_close)

    Implementation: HA_open requires the previous HA_open, so the open series
    is computed in a sequential loop. HA_high / HA_low / HA_close are fully
    vectorized.

    Reference: Dan Valcu, "Heikin-Ashi: How to Trade Without Candlestick
    Patterns" (2011); widely discussed earlier in the Japanese literature.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {}

    Returns:
        {'ha_open': pd.Series, 'ha_high': pd.Series, 'ha_low': pd.Series, 'ha_close': pd.Series}
    """
    _data = ["open", "high", "low", "close"]
    _params = []
    _outputs = ["ha_open", "ha_high", "ha_low", "ha_close"]

    @classmethod
    def _compute(cls, data, params):
        open_ = data['open']
        high = data['high']
        low = data['low']
        close = data['close']

        n = len(close)
        o_arr = open_.to_numpy(dtype=np.float64, copy=False)
        h_arr = high.to_numpy(dtype=np.float64, copy=False)
        l_arr = low.to_numpy(dtype=np.float64, copy=False)
        c_arr = close.to_numpy(dtype=np.float64, copy=False)

        # HA_close is fully vectorized.
        ha_close_arr = (o_arr + h_arr + l_arr + c_arr) / 4.0

        # HA_open is state-dependent: needs prev HA_open and prev HA_close.
        ha_open_arr = np.empty(n, dtype=np.float64)
        if n > 0:
            ha_open_arr[0] = (o_arr[0] + c_arr[0]) / 2.0
        for i in range(1, n):
            ha_open_arr[i] = (ha_open_arr[i - 1] + ha_close_arr[i - 1]) / 2.0

        # HA_high / HA_low are vectorized: element-wise max/min of three series.
        ha_high_arr = np.fmax(np.fmax(h_arr, ha_open_arr), ha_close_arr)
        ha_low_arr = np.fmin(np.fmin(l_arr, ha_open_arr), ha_close_arr)

        return {
            'ha_open': pd.Series(ha_open_arr, index=close.index, name='ha_open'),
            'ha_high': pd.Series(ha_high_arr, index=close.index, name='ha_high'),
            'ha_low': pd.Series(ha_low_arr, index=close.index, name='ha_low'),
            'ha_close': pd.Series(ha_close_arr, index=close.index, name='ha_close'),
        }


class ChandelierExit(IndicatorInterface):
    """Chandelier Exit (Chuck LeBeau).

    Volatility-scaled trailing stop using rolling extreme and ATR:
        long_stop  = highest_high(window) - multiplier * ATR(window)
        short_stop = lowest_low(window)   + multiplier * ATR(window)

    Unlike ATRTrailingStop this is NOT a state machine -- long and short stops
    are always computed, and the user picks which one applies based on their
    current position. Use `long_stop` as a floor for long positions;
    `short_stop` as a ceiling for shorts.

    Reference: Chuck LeBeau, SmartTrader. Popularized in Chande's "Beyond
    Technical Analysis" (1997).

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'long_stop': pd.Series, 'short_stop': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "multiplier"]
    _outputs = ["long_stop", "short_stop"]

    @classmethod
    def _compute(cls, data, params):
        # Local import -- ATR lives in volatility_indicators; avoids circular import at load time.
        from mangrove_kb.indicators.volatility_indicators import ATR

        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        # Mask warmup to NaN: our ATR fills first window-1 bars with 0.
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False).copy()
        atr_vals[: window - 1] = np.nan
        atr_masked = pd.Series(atr_vals, index=close.index)

        hh = high.rolling(window, min_periods=window).max()
        ll = low.rolling(window, min_periods=window).min()

        long_stop = hh - mult * atr_masked
        short_stop = ll + mult * atr_masked

        return {
            'long_stop': pd.Series(long_stop.values, index=close.index, name='long_stop'),
            'short_stop': pd.Series(short_stop.values, index=close.index, name='short_stop'),
        }


class WilliamsAlligator(IndicatorInterface):
    """Williams Alligator (Bill Williams).

    Three SMMA lines plotted on median price ((high + low) / 2) with forward
    offsets:
        Jaw   = SMMA(13) shifted forward 8 bars (slowest, "sleeping alligator")
        Teeth = SMMA( 8) shifted forward 5 bars
        Lips  = SMMA( 5) shifted forward 3 bars (fastest, "gator's lips")

    The forward shift is applied via pandas .shift(+n), which is
    lookahead-free in backtesting: the value at bar `t` in the output is the
    SMMA computed at bar `t - n`.

    Trend interpretation:
      - Lips > Teeth > Jaw (all spreading upward): alligator is eating,
        strong uptrend.
      - Lips < Teeth < Jaw (all spreading downward): strong downtrend.
      - Tangled (lines crossing/converging): alligator is sleeping, no trend.

    Reference: Bill Williams, "New Trading Dimensions" (1998).

    Args:
        data: {'high': pd.Series, 'low': pd.Series}
        params: {'jaw': int, 'teeth': int, 'lips': int,
                 'jaw_offset': int, 'teeth_offset': int, 'lips_offset': int}

    Returns:
        {'jaw': pd.Series, 'teeth': pd.Series, 'lips': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["jaw", "teeth", "lips", "jaw_offset", "teeth_offset", "lips_offset"]
    _outputs = ["jaw", "teeth", "lips"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        jaw_n = params['jaw']
        teeth_n = params['teeth']
        lips_n = params['lips']
        jaw_off = params['jaw_offset']
        teeth_off = params['teeth_offset']
        lips_off = params['lips_offset']

        median = (high + low) / 2.0
        # Use our SMMA (Wave A) for Wilder smoothing on median price.
        jaw_raw = SMMA.compute({'close': median}, {'window': jaw_n})['smma']
        teeth_raw = SMMA.compute({'close': median}, {'window': teeth_n})['smma']
        lips_raw = SMMA.compute({'close': median}, {'window': lips_n})['smma']

        # Forward shifts -- lookahead-free: value at bar t is SMMA computed at
        # bar t - offset. pandas .shift(+n) moves old values forward in time.
        jaw = jaw_raw.shift(jaw_off)
        teeth = teeth_raw.shift(teeth_off)
        lips = lips_raw.shift(lips_off)

        return {
            'jaw': pd.Series(jaw.values, index=high.index, name='alligator_jaw'),
            'teeth': pd.Series(teeth.values, index=high.index, name='alligator_teeth'),
            'lips': pd.Series(lips.values, index=high.index, name='alligator_lips'),
        }


class SuperTrend(IndicatorInterface):
    """SuperTrend (Olivier Seban).

    ATR-scaled bands around hl2 with a trend-following flip rule. When close
    crosses the opposite band, the trend flips; between flips, the active
    band ratchets to preserve the trailing-stop property.

    Formula:
        hl2       = (high + low) / 2
        basic_ub  = hl2 + multiplier * ATR(window)
        basic_lb  = hl2 - multiplier * ATR(window)
        # Then per-bar:
        if close > prev_upper: dir = +1
        elif close < prev_lower: dir = -1
        else: dir stays; ratchet the active band
        trend = lower if dir == +1 else upper

    Outputs:
      - supertrend: the active trend line (trailing stop level)
      - direction:  +1 long, -1 short
      - long_band:  the lower band (NaN when in short regime)
      - short_band: the upper band (NaN when in long regime)

    Reference: Olivier Seban (popularized via MetaTrader community, 2000s).

    Implementation: state-dependent per-bar loop; same pattern as
    ATRTrailingStop / MAMA / PSAR.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'supertrend': pd.Series, 'direction': pd.Series,
         'long_band': pd.Series, 'short_band': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "multiplier"]
    _outputs = ["supertrend", "direction", "long_band", "short_band"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.volatility_indicators import ATR

        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False)
        h_arr = high.to_numpy(dtype=np.float64, copy=False)
        l_arr = low.to_numpy(dtype=np.float64, copy=False)
        c_arr = close.to_numpy(dtype=np.float64, copy=False)
        hl2 = (h_arr + l_arr) / 2.0

        n = len(close)
        lb = hl2 - mult * atr_vals  # "basic" lower band, mutated by ratchet
        ub = hl2 + mult * atr_vals  # "basic" upper band, mutated by ratchet
        # Work on copies so we don't accidentally mutate inputs.
        lb = lb.copy()
        ub = ub.copy()

        direction = np.full(n, np.nan)
        supertrend = np.full(n, np.nan)
        long_band = np.full(n, np.nan)
        short_band = np.full(n, np.nan)

        if n == 0:
            return {
                'supertrend': pd.Series(supertrend, index=close.index, name='supertrend'),
                'direction': pd.Series(direction, index=close.index, name='direction'),
                'long_band': pd.Series(long_band, index=close.index, name='long_band'),
                'short_band': pd.Series(short_band, index=close.index, name='short_band'),
            }

        # Start in long regime at bar 1 (convention used by pandas-ta; direction
        # is NaN for the first `window` bars via the output mask below).
        dir_curr = 1
        for i in range(1, n):
            if c_arr[i] > ub[i - 1]:
                dir_curr = 1
            elif c_arr[i] < lb[i - 1]:
                dir_curr = -1
            # else: direction unchanged; ratchet the active band toward the trend
            else:
                if dir_curr == 1 and lb[i] < lb[i - 1]:
                    lb[i] = lb[i - 1]
                if dir_curr == -1 and ub[i] > ub[i - 1]:
                    ub[i] = ub[i - 1]

            direction[i] = dir_curr
            if dir_curr == 1:
                supertrend[i] = long_band[i] = lb[i]
            else:
                supertrend[i] = short_band[i] = ub[i]

        # Mask first `window` bars of direction to NaN (ATR warmup).
        direction[:window] = np.nan
        supertrend[:window] = np.nan
        long_band[:window] = np.nan
        short_band[:window] = np.nan

        return {
            'supertrend': pd.Series(supertrend, index=close.index, name='supertrend'),
            'direction': pd.Series(direction, index=close.index, name='direction'),
            'long_band': pd.Series(long_band, index=close.index, name='long_band'),
            'short_band': pd.Series(short_band, index=close.index, name='short_band'),
        }


class MARibbon(IndicatorInterface):
    """Moving Average Ribbon -- multi-MA alignment detector.

    Computes N simple moving averages and flags the bar as in a "bullish
    ribbon" (all MAs stacked in descending-period order, fastest on top),
    "bearish ribbon" (ascending-period order, slowest on top), or "tangled"
    (neither strict alignment).

    A strict bullish ribbon means every pair (MA[i], MA[i+1]) for ascending
    periods satisfies MA[fast] > MA[slow]. This is a strong trend filter.

    Default windows use Fibonacci-spaced periods [5, 8, 13, 21, 34, 55, 89, 144]
    which is a common choice for long-horizon ribbons.

    Reference: TradingView Pine Script community standard.

    Args:
        data: {'close': pd.Series}
        params: {'windows': list[int]} -- MA periods; must be strictly increasing.

    Returns:
        {'ribbon_bullish': pd.Series (bool),
         'ribbon_bearish': pd.Series (bool),
         'ribbon_tangled': pd.Series (bool)}
    """
    _data = ["close"]
    _params = ["windows"]
    _outputs = ["ribbon_bullish", "ribbon_bearish", "ribbon_tangled"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        windows = list(params['windows'])
        if sorted(windows) != windows:
            raise ValueError(f"windows must be strictly increasing; got {windows}")

        # Stack N MAs into a 2D array (rows = bars, cols = windows ascending).
        n = len(close)
        close_vals = close.to_numpy(dtype=np.float64, copy=False)
        mas = np.full((n, len(windows)), np.nan)
        for j, w in enumerate(windows):
            mas[:, j] = SMA.compute({'close': close}, {'window': w})['sma'].to_numpy(dtype=np.float64)

        # Bullish: for every adjacent pair, faster (smaller window) MA > slower (larger window) MA.
        # i.e., row is strictly DECREASING across columns.
        diffs = np.diff(mas, axis=1)  # diffs[i, j] = mas[i, j+1] - mas[i, j]
        bullish = np.all(diffs < 0, axis=1)
        bearish = np.all(diffs > 0, axis=1)

        # Rows with any NaN in diffs are undefined -- mark as not bullish, not bearish.
        any_nan = np.any(np.isnan(diffs), axis=1)
        bullish = bullish & ~any_nan
        bearish = bearish & ~any_nan
        tangled = (~bullish) & (~bearish) & (~any_nan)

        return {
            'ribbon_bullish': pd.Series(bullish, index=close.index, name='ribbon_bullish'),
            'ribbon_bearish': pd.Series(bearish, index=close.index, name='ribbon_bearish'),
            'ribbon_tangled': pd.Series(tangled, index=close.index, name='ribbon_tangled'),
        }


class MultiTFTrend(IndicatorInterface):
    """Multi-Timeframe Trend Confirmation.

    Resamples to a higher timeframe, computes EMA slope on the resampled
    closes, and broadcasts the slope direction back onto the base-timeframe
    index via forward-fill. The resulting `higher_tf_trend` series is +1
    (higher-TF EMA rising), -1 (falling), or 0 (flat / insufficient data).

    Lookahead-free: each base-TF bar at time t sees only the most recently
    CLOSED higher-TF bar as of time t. The resample uses label='right' so
    a higher-TF bar labeled at time t aggregates data up to and including
    time t on the base TF.

    Requires a DatetimeIndex. If the input DataFrame has a non-datetime
    index, returns all NaN.

    Reference: Standard multi-timeframe confluence construction.

    Args:
        data: {'close': pd.Series} -- must have DatetimeIndex
        params: {'higher_tf': str, 'window': int, 'slope_threshold': float}
          higher_tf: pandas offset alias (e.g., '4H', '1D', '1W')
          window: EMA period on the resampled close
          slope_threshold: minimum |slope / mean| to count as non-flat (default 0.0)

    Returns:
        {'higher_tf_trend': pd.Series (values in {-1, 0, +1})}
    """
    _data = ["close"]
    _params = ["higher_tf", "window", "slope_threshold"]
    _outputs = ["higher_tf_trend"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        higher_tf = params['higher_tf']
        window = params['window']
        threshold = float(params.get('slope_threshold', 0.0))

        if not isinstance(close.index, pd.DatetimeIndex):
            return {'higher_tf_trend': pd.Series(np.full(len(close), np.nan), index=close.index, name='higher_tf_trend')}

        # Resample to higher_tf, taking the last close in each bucket (label=right
        # so the bucket label = end-of-period, which is the time at which that
        # higher-TF bar "closes" and becomes available on the base TF).
        higher = close.resample(higher_tf, label='right', closed='right').last().dropna()
        if len(higher) < window + 2:
            return {'higher_tf_trend': pd.Series(np.full(len(close), np.nan), index=close.index, name='higher_tf_trend')}

        # EMA on higher TF
        ema_higher = EMA.compute({'close': higher}, {'window': window})['ema']
        # Slope = first difference of the EMA; scale by its own absolute mean so
        # the threshold is unitless.
        slope = ema_higher.diff()
        denom = ema_higher.abs().rolling(window, min_periods=1).mean().replace(0, np.nan)
        rel_slope = slope / denom

        trend_higher = np.where(rel_slope > threshold, 1, np.where(rel_slope < -threshold, -1, 0)).astype(np.float64)
        trend_higher[np.isnan(rel_slope.to_numpy())] = np.nan
        trend_ser = pd.Series(trend_higher, index=higher.index, name='higher_tf_trend')

        # Broadcast back to base TF via reindex + forward-fill. At each base
        # bar, we use the most recently CLOSED higher-TF bar (asof semantics).
        broadcast = trend_ser.reindex(close.index, method='ffill')
        return {'higher_tf_trend': pd.Series(broadcast.values, index=close.index, name='higher_tf_trend')}


class Divergence(IndicatorInterface):
    """Divergence detection between price and an indicator (RSI/MACD/OBV/...).

    Detects the four classic divergence types via swing-point matching:
      regular_bullish:  price makes lower low, indicator makes higher low (reversal up)
      regular_bearish:  price makes higher high, indicator makes lower high (reversal down)
      hidden_bullish:   price makes higher low,  indicator makes lower low  (continuation up)
      hidden_bearish:   price makes lower high,  indicator makes higher high (continuation down)

    Swing points are detected via scipy.signal.argrelextrema with a
    configurable comparison window. A divergence flag fires on the bar where
    the second swing point is confirmed (i.e., `swing_window` bars AFTER
    the actual extreme -- so it is not lookahead-biased in backtests).

    Reference: Cardwell / Constance Brown, "Technical Analysis for the
    Trading Professional" (2000); Cardwell's classic hidden-divergence work.

    Args:
        data: {'price': pd.Series, 'indicator': pd.Series}
        params: {'swing_window': int, 'min_swing_distance': int}
          swing_window: bars on each side used to confirm an extremum
          min_swing_distance: minimum bars between the two swings being compared

    Returns:
        {'regular_bullish': pd.Series (bool),
         'regular_bearish': pd.Series (bool),
         'hidden_bullish':  pd.Series (bool),
         'hidden_bearish':  pd.Series (bool)}
    """
    _data = ["price", "indicator"]
    _params = ["swing_window", "min_swing_distance"]
    _outputs = ["regular_bullish", "regular_bearish", "hidden_bullish", "hidden_bearish"]

    @classmethod
    def _compute(cls, data, params):
        # Local import keeps scipy optional (degrades gracefully if missing).
        try:
            from scipy.signal import argrelextrema
        except ImportError:
            price = data['price']
            empty = pd.Series(np.zeros(len(price), dtype=bool), index=price.index)
            return {k: empty.copy() for k in cls._outputs}

        price = data['price']
        indicator = data['indicator']
        sw = int(params['swing_window'])
        min_dist = int(params['min_swing_distance'])

        p_arr = price.to_numpy(dtype=np.float64, copy=False)
        i_arr = indicator.to_numpy(dtype=np.float64, copy=False)
        n = len(p_arr)

        # Highs/lows detected via argrelextrema; these are indices where the
        # bar is strictly greater (or less) than `sw` bars on either side.
        price_highs = argrelextrema(p_arr, np.greater, order=sw)[0]
        price_lows = argrelextrema(p_arr, np.less, order=sw)[0]
        ind_highs = argrelextrema(i_arr, np.greater, order=sw)[0]
        ind_lows = argrelextrema(i_arr, np.less, order=sw)[0]

        reg_bull = np.zeros(n, dtype=bool)
        reg_bear = np.zeros(n, dtype=bool)
        hid_bull = np.zeros(n, dtype=bool)
        hid_bear = np.zeros(n, dtype=bool)

        def _last_two_pairs(price_idx, ind_idx):
            """Yield (prev_p, curr_p, prev_i, curr_i) where each quadruple
            pairs the last two confirmed price extremes with the two
            indicator extremes closest in time to them (within min_dist)."""
            if len(price_idx) < 2 or len(ind_idx) < 2:
                return
            for pi2_pos in range(1, len(price_idx)):
                pi2 = price_idx[pi2_pos]
                pi1 = price_idx[pi2_pos - 1]
                if pi2 - pi1 < min_dist:
                    continue
                # Find indicator extremes closest to pi1 and pi2
                ind1 = ind_idx[np.argmin(np.abs(ind_idx - pi1))] if len(ind_idx) else None
                ind2 = ind_idx[np.argmin(np.abs(ind_idx - pi2))] if len(ind_idx) else None
                if ind1 is None or ind2 is None or ind1 == ind2:
                    continue
                # Confirmation bar: both price and indicator extremes must be
                # sw-bars old to be confirmed. Fire at max(pi2, ind2) + sw so
                # sliding-window evaluation sees the same pairing as full-dataset
                # evaluation (otherwise a later ind2 leaks information forward).
                fire_bar = int(max(pi2, ind2)) + sw
                if fire_bar >= n:
                    continue
                yield pi1, pi2, ind1, ind2, fire_bar

        # Bullish divergences use price LOWS
        for pi1, pi2, ii1, ii2, fire in _last_two_pairs(price_lows, ind_lows):
            if p_arr[pi2] < p_arr[pi1] and i_arr[ii2] > i_arr[ii1]:
                reg_bull[fire] = True
            elif p_arr[pi2] > p_arr[pi1] and i_arr[ii2] < i_arr[ii1]:
                hid_bull[fire] = True

        # Bearish divergences use price HIGHS
        for pi1, pi2, ii1, ii2, fire in _last_two_pairs(price_highs, ind_highs):
            if p_arr[pi2] > p_arr[pi1] and i_arr[ii2] < i_arr[ii1]:
                reg_bear[fire] = True
            elif p_arr[pi2] < p_arr[pi1] and i_arr[ii2] > i_arr[ii1]:
                hid_bear[fire] = True

        return {
            'regular_bullish': pd.Series(reg_bull, index=price.index, name='div_regular_bullish'),
            'regular_bearish': pd.Series(reg_bear, index=price.index, name='div_regular_bearish'),
            'hidden_bullish': pd.Series(hid_bull, index=price.index, name='div_hidden_bullish'),
            'hidden_bearish': pd.Series(hid_bear, index=price.index, name='div_hidden_bearish'),
        }
