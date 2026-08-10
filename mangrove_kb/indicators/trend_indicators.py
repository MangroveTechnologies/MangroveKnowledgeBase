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
    """Indicator: SMA

    The arithmetic mean of price over a specified number of periods.

    Abbreviation: SMA
    Warmup: window - 1

    Formula:
        SMA(n) = (P_1 + P_2 + ... + P_n) / n

    Inputs:
        close: closing price

    Params:
        window [min=1, max=200]: SMA window in bars

    Outputs:
        sma [price, 0..inf] "Simple Moving Average":
            unweighted arithmetic mean of close over window -- every bar in the window carries equal
            weight. A finite-window (FIR) average: a value leaving the window changes the line even
            with no new price action. Lags by construction, and the longer the window the greater
            the lag

    Interpretation:
        - Price above SMA = Bullish bias
        - Price below SMA = Bearish bias
        - Slope indicates trend strength
        - Common periods: 20 (short-term), 50 (medium), 200 (long-term)

    Applications:
        - 200 SMA as major trend filter
        - Price crossing SMA as trend change signal
        - Multiple SMA crossovers (Golden Cross: 50 crosses above 200; Death Cross: 50 crosses below
        200)

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
    """Indicator: EMA

    A weighted moving average that gives more weight to recent prices, making it more responsive to
    new information.

    Abbreviation: EMA
    Warmup: window - 1

    Formula:
        EMA_t = (Price_t * k) + (EMA_(t-1) * (1-k))
        Where k = 2 / (n + 1)

    Inputs:
        close: closing price

    Params:
        window [default=20, min=2, max=200]: EMA window

    Outputs:
        ema [price, 0..inf] "Exponential Moving Average":
            recursive average with alpha = 2/(window+1), weighting recent bars more heavily.
            Infinite memory (IIR): old data never fully leaves, so the whole history is embedded and
            the weighting halves each time the window doubles. Turns before an SMA of the same
            length. SEEDING CAVEAT: seeded from the FIRST observation (the statistics convention),
            not from an SMA of the first `window` bars as StockCharts, TradingView and Fidelity
            specify -- a warmup-only difference that decays to zero within roughly 100 bars

    Interpretation:
        - More responsive than SMA to recent price changes
        - Less lag but more sensitive to noise
        - Popular periods: 8, 12, 21, 50, 200

    Applications:
        - Faster trend identification than SMA
        - Short-term EMAs (8, 12, 21) for momentum
        - EMA ribbons (multiple EMAs) for trend strength visualization

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
    """Indicator: WMA

    A moving average that assigns more weight to recent prices using a linear weighting scheme.

    Abbreviation: WMA
    Warmup: window - 1

    Formula:
        WMA = (P_n * n + P_(n-1) * (n-1) + ... + P_1 * 1) / (n + (n-1) + ... + 1)
        Where weights decrease linearly from most recent to oldest

    Inputs:
        close: closing price

    Params:
        window: period over which the linear weights are laid

    Outputs:
        wma [price, 0..inf] "Weighted Moving Average":
            linearly weighted average -- the newest bar carries weight `window`, the next
            `window-1`, down to 1, normalised by the triangle number window*(window+1)/2. Finite
            window, so weights reach exactly zero at the edge, unlike the EMA's exponential tail.
            Not to be confused with VWMA, which weights by volume rather than recency

    Interpretation:
        - More responsive than SMA but smoother than EMA
        - Price above WMA suggests bullish bias
        - Crossovers between fast and slow WMA signal trend changes

    Applications:
        - Trend identification and confirmation
        - Dynamic support in uptrends and resistance in downtrends
        - Crossover signals against price or another moving average
        - Building block inside other indicators -- the Hull Moving Average is built from WMAs

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
    """Indicator: DEMA

    Reduces lag of a traditional EMA by applying EMA twice and combining.

    Abbreviation: DEMA
    Warmup: 2 * (window - 1)

    Formula:
        DEMA = 2 * EMA(n) - EMA(EMA(n))

    Inputs:
        close: closing price

    Params:
        window: EMA period; the double smoothing uses it twice

    Outputs:
        dema [price, 0..inf] "Double Exponential Moving Average":
            2*EMA - EMA(EMA), both passes at the same window. Mulloy's construction subtracts the
            double-smoothed lag from the single-smoothed line, so it tracks closer to price and
            crosses earlier than an EMA. OVERSHOOT: the negative -EMA(EMA) term means this is NOT a
            convex combination of the window's prices and can print outside that window's high-low
            range -- measured on a step change, 53 of 181 bars printed outside, up to 3.46 price
            units beyond

    Interpretation:
        - Less lag than standard EMA
        - More responsive to price changes
        - Smoother than single EMA

    Applications:
        - Trend confirmation and spotting trend changes
        - DEMA crossovers -- against price, or a shorter DEMA against a longer one
        - Drop-in replacement for the EMA inside other indicators such as MACD or TRIX
        - Short-term, responsive trend following

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
    """Indicator: TEMA

    Further reduces lag over DEMA by combining three EMA passes.

    Abbreviation: TEMA
    Warmup: 3 * (window - 1)

    Formula:
        TEMA = 3 * EMA - 3 * EMA(EMA) + EMA(EMA(EMA))

    Inputs:
        close: closing price

    Params:
        window: EMA period; the triple smoothing uses it three times

    Outputs:
        tema [price, 0..inf] "Triple Exponential Moving Average":
            3*EMA - 3*EMA(EMA) + EMA(EMA(EMA)), all passes at the same window. The name is a
            misnomer -- it is not a thrice-smoothed EMA but a composite of single, double and triple
            EMAs. Least lag of the EMA family and the earliest crossovers, at the cost of more
            whipsaw in sideways markets. OVERSHOOT: more pronounced than DEMA -- 57 of 181 bars
            outside the window's range, up to 5.05 price units, from the negative -3*EMA(EMA) term

    Interpretation:
        - Minimal lag among moving average variants
        - Highly responsive but may generate more false signals
        - Best for shorter-term trend identification

    Applications:
        - Short-term trading and fast trend following
        - TEMA crossovers against price or against a longer-period TEMA
        - Early trend-change detection where EMA lag is unacceptable
        - Low-lag smoothing substrate inside composite indicators

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
    """Indicator: TRIMA

    Double-smoothed SMA. More weight is placed on the middle of the window than on the edges, reducing noise at both ends. Formula (TA-Lib convention): - if window is odd:  inner = SMA(window), outer = SMA((window+1)//2, inner) - if window is even: inner = SMA(window//2), outer = SMA(window//2 + 1, inner)

    Abbreviation: TRIMA
    Warmup: window - 1

    Formula:
        odd  n:  TRIMA = SMA( SMA(price, (n+1)/2), (n+1)/2 )
        even n:  TRIMA = SMA( SMA(price, n/2),     n/2 + 1 )

        Equivalent to symmetric triangular weights, e.g.
          n=7 -> 1,2,3,4,3,2,1     n=4 -> 1,2,2,1

    Inputs:
        close: closing price

    Params:
        window: period of both passes of the double SMA

    Outputs:
        trima [price, 0..inf] "Triangular Moving Average":
            an SMA of an SMA, producing symmetric triangular weights that emphasise the MIDDLE of
            the window and de-emphasise both ends. Odd windows use (window+1)/2 twice; even windows
            use window/2 then window/2+1, giving a flat-topped kernel -- verified to produce the
            canonical weights (n=7 -> 1,2,3,4,3,2,1; n=4 -> 1,2,2,1). The laggiest average here, the
            opposite bargain from DEMA/TEMA/HMA, bought for far stronger noise rejection. All
            weights positive, so unlike them it CANNOT overshoot the window's price range --
            measured 0 excursions

    Interpretation:
        - Center-weighted: the middle of the window carries most weight, both ends least
        - The laggiest of these averages -- it trades timeliness for smoothness
        - Far stronger noise rejection than a plain SMA
        - Symmetric weights mean turns are reported late but with little whipsaw
        - All weights positive, so unlike DEMA/TEMA/HMA it cannot overshoot

    Applications:
        - Smooth trend identification where noise suppression matters more than timeliness
        - Pre-smoothing an input series before feeding another indicator
        - Longer-horizon trend direction, accepting the extra lag
        - Baseline for comparison against lag-reduced averages

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
    """Indicator: SMMA

    Exponential smoothing with alpha = 1/window (vs EMA's 2/(window+1)), giving slower, more stable
    smoothing. Same family as used inside RSI and ATR.

    Abbreviation: SMMA
    Warmup: window - 1

    Formula:
        alpha = 1 / n
        SMMA_t = alpha * P_t + (1 - alpha) * SMMA_{t-1}
               = (SMMA_{t-1} * (n-1) + P_t) / n

        Equivalently an EMA at alpha = 1/n, i.e. EMA(2n-1).
        Also published as RMA (Running), MMA (Modified), and Wilder's Smoothing.

    Inputs:
        close: closing price

    Params:
        window: period, applied as Wilder's alpha = 1/window

    Outputs:
        smma [price, 0..inf] "Smoothed Moving Average":
            recursive average with alpha = 1/window -- Wilder's smoothing, the engine inside RSI and
            ATR. Also published as RMA (Running), MMA (Modified) and Wilder's Moving Average; all
            four names denote this series. Because 2/(N+1) = 1/n at N = 2n-1, SMMA(n) is EXACTLY our
            EMA(2n-1) -- verified to zero difference; the literature hedges to 'approximately' only
            because implementations seed differently. Roughly half the responsiveness of an EMA of
            the same nominal length

    Interpretation:
        - Wilder's smoothing -- the averaging engine inside RSI and ATR
        - Roughly half the responsiveness of an EMA of the same nominal length, so smoother and
        slower
        - Infinite memory: the oldest data never leaves the calculation, it only fades
        - Effective period is longer than the nominal one, so it is usually paired with longer
        settings
        - Slope and price-cross readings are the generic moving-average readings

    Applications:
        - Trend smoothing over longer horizons
        - The smoothing engine inside Wilder's indicators (RSI average gain/loss, ATR)
        - Smoothing non-price series such as gains, losses or true range
        - Bill Williams' Alligator Balance Lines are SMMAs of median price

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
    """Indicator: EPMA

    For each bar, fits a linear regression over the last `window` closes and returns the regression
    value at the endpoint (most recent bar). Projects the trend to "now" rather than averaging past
    values.

    Abbreviation: EPMA
    Warmup: window - 1

    Formula:
        epma[t] = sum(w_i * close[t-window+1+i]) for i in 0..window-1, w_i = (6i + 4 - 2*window) / (window*(window+1))

    Inputs:
        close: closing price

    Params:
        window: period of the linear regression fitted each bar

    Outputs:
        epma [price, 0..inf] "epma":
            The value at the endpoint of a linear regression fitted over the window -- the trend
            projected to now, rather than an average of the past.

    Interpretation:
        Where the window's linear trend says price IS now, rather than where it has been on average.
        The FIR weights are the closed form of a least-squares fit evaluated at its endpoint, so it
        turns faster than an SMA of the same length and overshoots more.

    Applications:
        Used like any other moving average -- price against the line, or two windows crossing -- but
        it leads them, which is the point and also the cost.

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
    """Indicator: HMA

    Low-lag moving average designed to track price without sacrificing smoothness. Reduces lag
    compared to EMA/SMA while remaining smoother than WMA.

    Abbreviation: HMA
    Reference: https://alanhull.com/hull-moving-average
    Warmup: window + floor(sqrt(window)) - 2

    Formula:
        WMA1 = WMA(price, n/2)
        WMA2 = WMA(price, n)
        raw  = 2*WMA1 - WMA2
        HMA  = WMA(raw, sqrt(n))

        Rounding of n/2 and sqrt(n) is unsettled: floor (Tulip, Chart manual) vs
        round-to-nearest (StockCharts). Hull's own listing defers to the platform.

    Inputs:
        close: closing price

    Params:
        window: period; the construction also uses window/2 and sqrt(window)

    Outputs:
        hma [price, 0..inf] "Hull Moving Average":
            WMA(2*WMA(window/2) - WMA(window), sqrt(window)) -- Alan Hull's construction, near-zero
            lag while staying smooth. Both window/2 and sqrt(window) are FLOORED here, matching
            Tulip and the Chart manual; StockCharts rounds window/2 up instead, so odd windows
            differ between implementations and Hull's own listing settles neither. OVERSHOOT:
            weights go negative beyond about window/2 bars back, so it can print outside the
            window's range -- 14 of 181 bars measured, the largest excursion of the family at 7.64
            price units. Hull explicitly advises AGAINST crossover signals, since those rely on the
            lag he removed; read the turning points instead

    Interpretation:
        - Very fast yet smooth -- Hull's aim was responsiveness without sacrificing smoothness
        - Far less lag than an SMA or EMA of the same length
        - Weights go negative beyond about n/2 bars back, which is what permits overshoot
        - Hull explicitly advises AGAINST crossover signals, because those rely on the lag he
        removed
        - Read the turning points instead: a turn up is the long cue, a turn down the short cue

    Applications:
        - Trend direction from a longer-period HMA
        - Entry and exit timing from turning points of a shorter-period HMA
        - Two-timeframe use -- long HMA for regime, short HMA for timing
        - Explicitly not recommended for crossover systems

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
    """Indicator: ALMA

    Gaussian-weighted moving average where `offset` controls which part of the window carries most
    weight and `sigma` controls spread. Offset near 1 reacts faster to recent bars; offset near 0
    resembles an SMA.

    Abbreviation: ALMA
    Warmup: window - 1

    Formula:
        m = offset * (n - 1)
        s = n / sigma
        w(k) = exp( -((k - m)^2) / (2 * s^2) )

        ALMA = sum( w(k) * price(k) ) / sum( w(k) )

        Defaults: window 9, offset 0.85, sigma 6.

    Inputs:
        close: closing price

    Params:
        window [default=21, min=2, max=200]: ALMA window in bars
        offset [default=0.85, min=0]: Weight center, 0=oldest, 1=newest
        sigma [default=6, min=0.1]: Gaussian spread. Higher = smoother

    Outputs:
        alma [price, 0..inf] "Arnaud Legoux Moving Average":
            Gaussian-weighted average: weight exp(-0.5*((sigma/window)*(i-k))^2) with the peak at k
            = floor(offset*(window-1)), normalised to sum to 1. `offset` slides the peak toward the
            newest bars (higher = more responsive); `sigma` sets the bell's width (higher =
            smoother). NOT adaptive in the data-driven sense -- the weights are fixed at
            configuration time and never respond to market state, unlike KAMA or MAMA. All weights
            positive and normalised, so it CANNOT overshoot the window's price range -- measured 0
            excursions

    Interpretation:
        - Gaussian-weighted average whose peak position and width are both user-set
        - offset slides the peak toward the newest bars -- higher means more responsive
        - sigma sets the width of the bell -- higher means smoother
        - NOT adaptive in the data-driven sense: the weights never respond to market state
        - All weights positive and normalised, so it cannot overshoot the window's range

    Applications:
        - Trend direction and filtering from price-versus-line position
        - Price/ALMA crossovers as entries and exits, with fewer whipsaws
        - Dynamic support in uptrends and resistance in downtrends
        - Window tuned to horizon -- shorter for intraday, longer for swing

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
    """Indicator: T3

    Six chained EMAs combined via Tillson's volume-factor formula. Produces a smooth, low-lag trend
    line. The `volume_factor` (a) controls smoothness: a=0 collapses to a triple EMA; a=1 is the
    most responsive.

    Abbreviation: T3
    Warmup: 6 * (window - 1)

    Formula:
        GD(n,v) = EMA(n)*(1+v) - EMA(EMA(n))*v      # generalised DEMA
        T3(n)   = GD(GD(GD(n)))

        Expanded over six chained EMAs, with a = volume factor:
          c1 = -a^3
          c2 =  3a^2 + 3a^3
          c3 = -6a^2 - 3a - 3a^3
          c4 =  1 + 3a + 3a^2 + a^3
          T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3

        Tillson's default volume factor: 0.7.

    Inputs:
        close: closing price

    Params:
        window [default=10, min=2, max=200]: T3 window in bars
        volume_factor [default=0.7, min=0]: Tillson volume factor, controls smoothness

    Outputs:
        t3 [price, 0..inf] "T3":
            Tillson's generalised DEMA run through itself three times, expanded as c1*e6 + c2*e5 +
            c3*e4 + c4*e3 over six chained EMAs, with the coefficients functions of the volume
            factor alone. The volume factor dials how much lag-reduction is applied: 0 gives a plain
            EMA, 1 gives DEMA, and Tillson chose 0.7. Adaptive only in his filter-theory sense --
            the coefficients are constant and measure nothing about the market. OVERSHOOT: c1 and c3
            are negative, so this is not a convex combination and can print outside the price range.
            Tillson's claim that T3 'does not overshoot the data' holds only comparatively: on a
            clean step, DEMA-cubed (the construction he set out to cure) rings 10.82 past the new
            level while T3 at his default 0.7 rings 4.28 -- a 60% reduction, but not elimination,
            and marginally worse than a plain DEMA's 3.67

    Interpretation:
        - Sits between an EMA and a DEMA of the same length in responsiveness
        - The volume factor is a responsiveness dial: 0 gives an EMA, 1 gives DEMA
        - Adaptive only in Tillson's filter-theory sense -- the coefficients are constant
        - Tillson's stated achievement was curing DEMA-cubed's overshoot while keeping smoothness
        - Two of the four coefficients are negative, so it is not confined to the price range

    Applications:
        - General-purpose replacement for SMA/EMA/DEMA as a trend line
        - Signal generation from the derivative of the line rather than crossovers
        - Smoothing building block inside other indicators and systems
        - Noise reduction where a longer conventional average's lag is unacceptable

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
    """Indicator: MAMA

    Adaptive moving average that speeds up in trending markets and slows down in consolidations,
    using a Hilbert Transform Discriminator to estimate the dominant cycle period and adjust alpha
    dynamically. Also emits FAMA (Following Adaptive MA), half-alpha of MAMA -- MAMA/FAMA crossovers
    are used as trend signals.

    Abbreviation: MAMA
    Reference: http://traders.com/documentation/feedbk_docs/2014/01/traderstips.html
    Warmup: warmup_bars

    Formula:
        Hilbert-transform discriminator measures the dominant cycle period and phase.

          DeltaPhase = Phase[1] - Phase        (floored at 1)
          alpha      = FastLimit / DeltaPhase  (clamped to [SlowLimit, FastLimit])

          MAMA = alpha*Price + (1 - alpha)*MAMA[1]
          FAMA = 0.5*alpha*MAMA + (1 - 0.5*alpha)*FAMA[1]

        Defaults: FastLimit 0.5, SlowLimit 0.05. Canonical input: median price (H+L)/2.
        Internal period clamped to [6, 50] bars, rate-limited to [0.67x, 1.5x].

    Inputs:
        high: bar high, half of the median price Ehlers specifies as the input
        low: bar low, half of the median price Ehlers specifies as the input

    Params:
        fast_limit [default=0.5, min=0.1]: Upper alpha bound (fast response)
        slow_limit [default=0.05, min=0.01]: Lower alpha bound (slow response)
        warmup_bars [default=64, min=6, max=200]: Leading bars discarded as contaminated by the zero
        seed

    Outputs:
        mama [price, 0..inf] "MAMA":
            Ehlers' MESA Adaptive Moving Average. Adapts to the CYCLE PHASE RATE OF CHANGE measured
            by a Hilbert-transform discriminator -- explicitly not to volatility, which is what
            distinguishes it from KAMA and VIDYA. Phase snaps back every half cycle, forcing alpha
            to its fast limit so the line rapidly approaches price, then decays slowly and holds:
            Ehlers' 'fast attack, slow decay' ratcheting. Alpha is clamped between the slow and fast
            limits, so it cannot overshoot. INPUT CAVEAT: Ehlers specifies median price
            (high+low)/2; this implementation consumes close. WARMUP CAVEAT: the recursion starts
            from zero and only the first 6 bars are masked, so roughly ten further bars are
            published while still converging -- at bar 6 the value sat 50% below price in testing
        fama [price, 0..inf] "FAMA":
            Following Adaptive Moving Average -- the same recursion driven at half MAMA's alpha, so
            it steps in time with MAMA but moves less dramatically. The pair is the point: MAMA and
            FAMA do not cross unless market direction has genuinely changed, which is what makes the
            crossover system resistant to whipsaw. Same input and warmup caveats as MAMA

    Interpretation:
        - Adapts to the cycle PHASE RATE OF CHANGE, not volatility -- the difference from KAMA and
        VIDYA
        - Phase snaps back every half cycle, forcing alpha to its fast limit so the line rushes to
        price
        - Then alpha falls and the line holds: Ehlers' 'fast attack, slow decay' ratcheting
        - Ratcheting happens less often in trend mode, where the dominant cycle is longer
        - MAMA and FAMA do not cross unless market direction has genuinely changed

    Applications:
        - The MAMA/FAMA crossover system, designed to be nearly free of whipsaw trades
        - Trend following where holding through noise matters
        - Regime reading -- trend mode versus cycle mode, from how often the line ratchets
        - Dominant-cycle measurement as a by-product of the discriminator

    Args:
        data: {'high': pd.Series, 'low': pd.Series}
        params: {'fast_limit': float, 'slow_limit': float, 'warmup_bars': int}

    Returns:
        {'mama': pd.Series, 'fama': pd.Series}
    """
    _data = ["high", "low"]
    _params = ["fast_limit", "slow_limit", "warmup_bars"]
    _outputs = ["mama", "fama"]

    @classmethod
    def _compute(cls, data, params):
        # Ehlers specifies the input explicitly: "Inputs: Price = (H+L)/2". This consumed `close`,
        # which changes every downstream value -- the Hilbert coefficients, the [6, 50] period
        # clamp, the rate limit and the alpha limits all already match the paper, so the input was
        # the single divergence from it.
        price = (data['high'] + data['low']) / 2.0
        fast_limit = float(params['fast_limit'])
        slow_limit = float(params['slow_limit'])
        warmup_bars = int(params['warmup_bars'])

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
        #
        # Measured by comparing a cold start against a warm start (800 bars prepended), across
        # seven regimes -- random walk, trending, mean-reverting, low and high volatility, gappy,
        # and cyclical -- at three price levels and three seeds each. Seed dependence clears 1% by
        # bar 19 but does not clear 0.1% until bar 57, with the trending regime worst. 64 is that
        # bound with margin.
        #
        # An earlier revision used 40, derived from random walks alone; that sample understated the
        # tail by more than 20 bars, which is why the regimes above are enumerated rather than
        # summarised.
        mama_out = mama.copy()
        fama_out = fama.copy()
        mama_out[:warmup_bars] = np.nan
        fama_out[:warmup_bars] = np.nan

        return {
            'mama': pd.Series(mama_out, index=price.index, name='mama'),
            'fama': pd.Series(fama_out, index=price.index, name='fama'),
        }


class MACD(IndicatorInterface):
    """Indicator: MACD

    Is a trend-following momentum indicator that shows the relationship between two moving averages
    of prices.

    Abbreviation: MACD
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator
    Warmup: window_slow + window_sign - 2

    Formula:
        MACD Line = EMA(12) - EMA(26)
        Signal Line = EMA(9) of MACD Line
        Histogram = MACD Line - Signal Line

    Inputs:
        close: closing price

    Params:
        window_slow [default=26, min=5, max=200]: Slow EMA period
        window_fast [default=12, min=2, max=100]: Fast EMA period
        window_sign [default=9, min=2, max=50]: Signal line EMA window

    Outputs:
        macd [price, -inf..inf] "MACD Line":
            fast EMA minus slow EMA of close. Positive means the fast EMA sits above the slow one,
            i.e. rising momentum; the zero line is where they cross. UNBOUNDED and in the
            instrument's own PRICE UNITS, so its magnitude scales with the price level and readings
            are NOT comparable across instruments -- use PPO for that. Explicitly not an
            overbought/oversold tool: it can over-extend past its own historical extremes
        signal [price, -inf..inf] "Signal Line":
            EMA of the MACD line over window_sign. Crossings of macd against this line are the most
            commonly used MACD signal
        histogram [price, -inf..inf] "MACD Histogram":
            macd minus signal. Crosses zero exactly when macd crosses its signal line, and expands
            as the two diverge -- Aspray added it to anticipate those crossovers

    Interpretation:
        - MACD above zero: Bullish momentum
        - MACD below zero: Bearish momentum
        - MACD crossing Signal Line up: Buy signal
        - MACD crossing Signal Line down: Sell signal
        - Histogram shows momentum strength and direction

    Applications:
        - Signal line crossovers for entries
        - Zero line crossovers for trend confirmation
        - Histogram divergences for reversal warnings
        - MACD in conjunction with price patterns

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
    """Indicator: Aroon

    Identify when trends are likely to change direction. Aroon Up = ((N - Days Since N-day High) /
    N) x 100 Aroon Down = ((N - Days Since N-day Low) / N) x 100 Aroon Indicator = Aroon Up - Aroon
    Down

    Abbreviation: Aroon
    Reference: https://www.investopedia.com/terms/a/aroon.asp
    Warmup: window

    Formula:
        Aroon Up = ((Period - Days Since Highest High) / Period) * 100
        Aroon Down = ((Period - Days Since Lowest Low) / Period) * 100
        Standard period: 25

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window [default=25, min=10, max=50]: Lookback period

    Outputs:
        aroon_up [dimensionless, 0..100] "Aroon-Up":
            how recently the window's HIGH occurred, as a percentage: ((window - bars since the
            high) / window) * 100. Measures elapsed TIME since the extreme, not price magnitude --
            100 means the current bar set the high. Hard-bounded 0..100 as a rescaling of a counter
            confined to [0, window]. This implementation looks back over window+1 bars (current plus
            window prior), which makes 0 genuinely attainable -- the literature leaves that indexing
            ambiguous. 50/70/30 are conventional levels
        aroon_down [dimensionless, 0..100] "Aroon-Down":
            the mirror of aroon_up for the window's LOW. Both lines low at once indicates
            consolidation rather than trend
        aroon_indicator [dimensionless, -100..100] "Aroon Oscillator":
            aroon_up minus aroon_down, hard-bounded -100..100 as a difference of two [0,100] series.
            Positive favours an uptrend; +/-50 and +/-90 are conventional strength levels, not
            bounds

    Interpretation:
        - Aroon Up > 70 and Aroon Down < 30: Strong uptrend
        - Aroon Down > 70 and Aroon Up < 30: Strong downtrend
        - Both below 50: Consolidation/no clear trend
        - Crossovers signal potential trend changes

    Applications:
        - Trend identification and confirmation
        - Timing entries on trend strength readings
        - Detecting consolidation periods

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
    """Indicator: TRIX

    Shows the percent rate of change of a triple exponentially smoothed moving average.

    Abbreviation: TRIX
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/trix
    Warmup: 3 * (window - 1) + 1

    Formula:
        EMA1 = EMA(Close, period)
        EMA2 = EMA(EMA1, period)
        EMA3 = EMA(EMA2, period)
        TRIX = (EMA3 - Previous EMA3) / Previous EMA3 * 100

    Inputs:
        close: closing price

    Params:
        window [default=15, min=5, max=30]: TRIX period
        window_sign [default=9, min=2, max=50]: Period of the EMA applied to TRIX to form the signal
        line. 9 is canonical

    Outputs:
        trix [percent, -inf..inf] "TRIX":
            1-period percent change OF a triple-smoothed EMA -- the three EMAs are applied in
            sequence first, and the rate of change is taken last, on the final series only. Triple
            smoothing is a noise filter: it takes more than a one-day move to turn it.
            Percent-normalised, so unlike MACD its magnitude does not scale with price level, but it
            is unbounded above. NOTE the canonical TRIX also carries a signal line (a 9-period EMA
            of this series), and signal-line crossovers are its primary documented use -- that
            second series is NOT emitted here
        trix_signal [percent, -inf..inf] "signal line":
            9-period EMA of TRIX. Signal-line crossovers are the primary documented TRIX signal:
            TRIX crossing above it is bullish, below it bearish. Same units and unbounded domain as
            TRIX itself, since it is a moving average of that series

    Interpretation:
        - Positive TRIX: Bullish momentum
        - Negative TRIX: Bearish momentum
        - Zero line crossovers signal trend changes
        - Very smooth—filters out most noise

    Applications:
        - Trend-following momentum with heavy noise suppression, for instruments where MACD whipsaws
        - Signal-line crossover entries and exits -- the most common use, though this implementation
        does not emit the signal line
        - Divergence detection for reversal warning
        - Trend-direction filter via the zero line, accepting the lag

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
    """Indicator: MassIndex

    It uses the high-low range to identify trend reversals based on range expansions. It identifies
    range bulges that can foreshadow a reversal of the current trend.

    Abbreviation: MI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/mass-index
    Warmup: window_slow - 1

    Formula:
        Single EMA = EMA(High - Low, 9)
        Double EMA = EMA(Single EMA, 9)
        Mass Index = Sum(Single EMA / Double EMA, 25)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window_fast [default=9, min=5, max=15]: Fast EMA period
        window_slow [default=25, min=15, max=40]: Sum period

    Outputs:
        mass_index [dimensionless, 0..inf] "Mass Index":
            sum over window_slow of the ratio of a single- to a double-smoothed EMA of the high-low
            range. A pure RANGE-EXPANSION measure with no directional content -- a bulge signals
            that a reversal is near without saying which way, so it must be paired with a
            directional indicator. Strictly positive, with no ceiling; it rests near 25 because each
            of the 25 ratios sits near 1, but readings below 25 are entirely normal when volatility
            contracts. The reversal bulge at 27 with confirmation back below 26.5 is a conventional
            signal level, not a bound

    Interpretation:
        - Mass Index > 27 then < 26.5: "Reversal bulge" pattern
        - Signals that current trend may be exhausted
        - Best combined with trend indicators for direction
        - Identifies volatility cycle changes

    Applications:
        - Anticipating trend reversals ahead of price confirmation
        - Reversal-bulge screening: above 27, then back below 26.5
        - Pairing with a directional indicator to assign a side to the signal
        - Monitoring volatility regime against the instrument's own historical range

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
    """Indicator: Ichimoku

    A comprehensive indicator system providing support/resistance, trend direction, and momentum
    through five components. **Components:** ``` Tenkan-sen (Conversion Line) = (Highest High +
    Lowest Low) / 2 over 9 periods Kijun-sen (Base Line) = (Highest High + Lowest Low) / 2 over 26
    periods Senkou Span A (Leading Span A) = (Tenkan + Kijun) / 2, plotted 26 periods ahead Senkou
    Span B (Leading Span B) = (Highest High + Lowest Low) / 2 over 52 periods, plotted 26 periods
    ahead Chikou Span (Lagging Span) = Current close, plotted 26 periods back ```

    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/ichimoku-cloud
    Warmup: max(window1, window2, window3) - 1

    Formula:
        conversion_line[t] = (max(high[t-w1+1..t]) + min(low[t-w1+1..t]))/2; base_line[t] the same over w2; span_a[t] = (conversion_line[t] + base_line[t])/2; span_b[t] = (max(high[t-w3+1..t]) + min(low[t-w3+1..t]))/2

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window1: Tenkan-sen period
        window2: Kijun-sen period
        window3: Senkou Span B period
        visual: shift the spans forward for plotting; False keeps them lookahead-free

    Outputs:
        conversion_line [price, 0..inf] "conversion_line":
            Tenkan-sen: midpoint of the high/low range over window1.
        base_line [price, 0..inf] "base_line":
            Kijun-sen: the same midpoint over the longer window2.
        span_a [price, 0..inf] "span_a":
            Senkou Span A: midpoint of the conversion and base lines. With span_b it bounds the
            cloud.
        span_b [price, 0..inf] "span_b":
            Senkou Span B: midpoint of the high/low range over window3. Which span is on top is what
            makes the cloud bullish or bearish.

    Interpretation:
        - Price above cloud: Bullish
        - Price below cloud: Bearish
        - Price in cloud: Consolidation
        - Cloud color change: Trend shift
        - Thick cloud: Strong support/resistance
        - Thin cloud: Weak support/resistance

    Applications:
        - Cloud as dynamic support/resistance
        - Tenkan/Kijun cross as entry signal
        - Chikou Span for momentum confirmation
        - All-time-frame analysis system

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
    """Indicator: KST

    It is useful to identify major stock market cycle junctures because its formula is weighed to be
    more greatly influenced by the longer and more dominant time spans, in order to better reflect
    the primary swings of stock market cycle.

    Abbreviation: KST
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-know-sure-thing-kst
    Warmup: max(roc1 + window1, roc2 + window2, roc3 + window3, roc4 + window4) + nsig - 2

    Formula:
        ROC1 = SMA(ROC(10), 10)
        ROC2 = SMA(ROC(15), 10)
        ROC3 = SMA(ROC(20), 10)
        ROC4 = SMA(ROC(30), 15)
        KST = (ROC1 * 1) + (ROC2 * 2) + (ROC3 * 3) + (ROC4 * 4)
        Signal = SMA(KST, 9)

    Inputs:
        close: closing price

    Params:
        roc1 [default=10, min=1, max=200]: ROC1 period
        roc2 [default=15, min=1, max=200]: ROC2 period
        roc3 [default=20, min=1, max=200]: ROC3 period
        roc4 [default=30, min=1, max=200]: ROC4 period
        window1: SMA period smoothing the first ROC
        window2: SMA period for the second ROC
        window3: SMA period for the third ROC
        window4: SMA period for the fourth ROC
        nsig [default=9, min=1, max=200]: Signal line period

    Outputs:
        kst [percent, -inf..inf] "KST":
            Pring's summed rate of change: four smoothed ROCs over increasing lookbacks, weighted
            1/2/3/4 so the longest cycle dominates. Unbounded in both directions and explicitly
            ill-suited to overbought/oversold work -- Pring's own preference is signal-line
            crossovers and trend-line breaks. A -1000 floor follows arithmetically from the four ROC
            floors but is not a literature claim and is unreachable
        kst_signal [percent, -inf..inf] "Signal Line":
            SMA (not EMA) of kst over nsig. Pring favours crossings of kst against this line as the
            primary signal
        kst_diff [percent, -inf..inf]:
            kst minus kst_signal. Convenience histogram; the literature defines only the KST line
            and its signal, and names no third series

    Interpretation:
        - KST above Signal: Bullish momentum
        - KST below Signal: Bearish momentum
        - Crossovers generate trading signals
        - Smoothed version reduces whipsaws

    Applications:
        - Signal-line crossovers -- Pring's own stated preference
        - Centreline (zero) crossovers for trend bias
        - Trend lines drawn on the KST series itself, which Pring used to reinforce crossovers
        - Adapting to timeframe by swapping period presets rather than changing chart period
        - Large, blatant divergences, confirmed by a subsequent signal-line crossover

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
    """Indicator: DPO

    Is an indicator designed to remove trend from price and make it easier to identify cycles.

    Abbreviation: DPO
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/detrended-price-oscillator-dpo
    Warmup: window - 1

    Formula:
        DPO = Close - SMA(Close, period) shifted back (period/2 + 1) days

    Inputs:
        close: closing price

    Params:
        window [default=20, min=10, max=50]: DPO period

    Outputs:
        dpo [price, -inf..inf] "Detrended Price Oscillator":
            close from (window/2 + 1) bars ago minus the current window-period SMA. This is the
            CAUSAL alignment -- it uses only past data and is lookahead-free, unlike the centred
            alignment that charting platforms plot, which reaches (window/2 + 1) bars into the
            future and therefore cannot produce a value on the most recent bar. The trade-off is
            that this series describes a state (window/2 + 1) bars STALE. Every primary source rules
            DPO out for momentum signals, overbought/oversold levels and scans -- it exists to
            identify cycle length by counting bars between its peaks and troughs. Unbounded, in
            price units, so not comparable across instruments

    Interpretation:
        - Positive DPO: Price above detrended average
        - Negative DPO: Price below detrended average
        - Helps identify cycle highs and lows
        - Not affected by long-term trends

    Applications:
        - Estimating cycle length by counting bars between peaks or troughs
        - Detrending -- removing the longer trend to expose short-cycle structure
        - Searching for the dominant cycle by varying the window
        - EXPLICITLY NOT for momentum signals, overbought/oversold levels, or scans -- all three are
        ruled out by the primary sources

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
    """Indicator: CCI

    CCI measures the difference between a security's price change and its average price change. High
    positive readings indicate that prices are well above their average, which is a show of
    strength. Low negative readings indicate that prices are well below their average, which is a
    show of weakness.

    Abbreviation: CCI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/commodity-channel-index-cci
    Warmup: window - 1

    Formula:
        Typical Price (TP) = (High + Low + Close) / 3
        CCI = (TP - SMA(TP, n)) / (0.015 * Mean Deviation)
        Mean Deviation = Average of |TP - SMA(TP)|

        Typical period: 20

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: CCI period
        constant [default=0.015, min=0.001]: CCI constant

    Outputs:
        cci [dimensionless, -inf..inf] "CCI":
            (typical price - its moving average) / (constant * mean absolute deviation) over window.
            NOT BOUNDED -- the familiar +/-100 band is a distributional convention created by
            Lambert's 0.015 constant, which he chose so that roughly 70-80% of readings fall inside
            it; the remainder lie outside BY DESIGN. Observed here from -320 to +327. This
            implementation computes the TRUE mean absolute deviation, measuring each window's
            deviations against that window's own mean, which matches the published formula; the
            common library shortcut of rolling-averaging |tp - rolling_mean| is a different quantity
            and diverges from this by over 150 CCI points on the same data

    Interpretation:
        - CCI > +100: Strong uptrend / overbought
        - CCI < -100: Strong downtrend / oversold
        - Zero line crossovers: Trend changes
        - Divergences: Potential reversals

    Applications:
        - Trend identification and strength
        - Overbought/oversold signals
        - Breakout confirmation
        - Divergence trading

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
    """Indicator: ADX

    The Plus Directional Indicator (+DI) and Minus Directional Indicator (-DI) are derived from
    smoothed averages of these differences, and measure trend direction over time. These two
    indicators are often referred to collectively as the Directional Movement Indicator (DMI). The
    Average Directional Index (ADX) is in turn derived from the smoothed averages of the difference
    between +DI and -DI, and measures the strength of the trend (regardless of direction) over time.
    Using these three indicators together, chartists can determine both the direction and strength
    of the trend.

    Abbreviation: ADX
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx
    Warmup: 2 * window - 1

    Formula:
        +DI = 100 * EMA(+DM) / ATR
        -DI = 100 * EMA(-DM) / ATR
        DX = 100 * |+DI - -DI| / (+DI + -DI)
        ADX = EMA(DX, n periods, typically 14)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: ADX period

    Outputs:
        adx [dimensionless, 0..100] "ADX":
            Wilder's trend-STRENGTH index -- non-directional by design, it says how strongly price
            is trending without saying which way. Hard-bounded 0..100 because it averages DX, itself
            100*|+DI - -DI|/(+DI + -DI) over non-negative inputs. Conventional strength levels vary
            by source (25 strong / 20 absent per Wilder and StockCharts; 20/40/50 per others) and
            are NOT bounds. WARMUP CAVEAT: the first 27 bars are filled with literal 0.0 rather than
            NaN, and since 0 is itself a meaningful reading (no directional strength) warmup is
            indistinguishable from a genuinely flat market -- mask them before use
        adx_pos [dimensionless, 0..100] "+DI":
            Plus Directional Indicator: smoothed upward directional movement as a percentage of
            smoothed true range. Hard-bounded 0..100 because +DM can never exceed TR on a bar. Above
            -DI indicates upward direction; ADX supplies the strength. First 15 bars are zero-filled
            rather than NaN
        adx_neg [dimensionless, 0..100] "-DI":
            Minus Directional Indicator: the mirror of +DI for downward movement, with the same hard
            0..100 bound and the same 15-bar zero-filled warmup. Crossings of +DI and -DI are the
            directional signal of Wilder's system

    Interpretation:
        - ADX > 25: Strong trend
        - ADX < 20: Weak trend / ranging
        - ADX rising: Trend strengthening
        - ADX falling: Trend weakening
        - +DI > -DI: Uptrend; -DI > +DI: Downtrend

    Applications:
        - Filter trades based on trend strength (only trade when ADX > 25)
        - Avoid trend strategies when ADX < 20
        - Use DI crossovers for directional signals

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
    """Indicator: Vortex

    It consists of two oscillators that capture positive and negative trend movement. A bullish
    signal triggers when the positive trend indicator crosses above the negative trend indicator or
    a key level.

    Abbreviation: VI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/vortex-indicator
    Warmup: window - 1

    Formula:
        +VM = |High - Previous Low|
        -VM = |Low - Previous High|
        TR = True Range
        +VI = Sum(+VM, n) / Sum(TR, n)
        -VI = Sum(-VM, n) / Sum(TR, n)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=30]: Vortex period

    Outputs:
        vortex_pos [ratio, 0..inf] "+VI":
            upward vortex movement, sum|high - prior low|, divided by the summed true range. Bounded
            below at 0 by the absolute value, but UNBOUNDED ABOVE -- the numerator spans across bars
            while true range is a within-bar measure, so a gap drives the ratio past 1 without
            limit. The familiar 'oscillates around 1' and the 0.90/1.10 signal levels are
            behavioural conventions, not bounds
        vortex_neg [ratio, 0..inf] "-VI":
            downward vortex movement, sum|low - prior high|, over the same summed true range. Same 0
            floor and same absence of a ceiling. Crossings against +VI are the primary signal
        vortex_diff [ratio, -inf..inf]:
            vortex_pos minus vortex_neg -- greater separation means a stronger trend. The literature
            names no third Vortex series; five sources were checked

    Interpretation:
        - +VI > -VI: Bullish trend
        - -VI > +VI: Bearish trend
        - Crossovers signal trend reversals
        - Wider spread = stronger trend

    Applications:
        - Identifying the start of a new trend or the continuation of an existing one
        - Crossover-based directional entry and exit signals
        - Reducing whipsaws by setting signal thresholds just above and below 1
        - Gauging trend strength from the separation between the two lines
        - Confirmation alongside other analysis -- the authors state it is not designed to stand
        alone

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
    """DEPRECATED for the ontology: its level is downstream of a verdict.

    `psar[i]` cannot be computed without the indicator having decided which regime it is in --
    the anchor, the acceleration factor and the update rule all switch on `up_trend` -- and
    `psar_up_indicator` / `psar_down_indicator` expose that decision as 0/1 flags. So unlike
    ChandelierLevels, which is a pure function of its window, there is no regime-free
    measurement to recover. Kept working and unchanged.
Parabolic Stop and Reverse (Parabolic SAR)

    The Parabolic Stop and Reverse, more commonly known as the
    Parabolic SAR,is a trend-following indicator developed by
    J. Welles Wilder. The Parabolic SAR is displayed as a single
    parabolic line (or dots) underneath the price bars in an uptrend,
    and above the price bars in a downtrend.

    https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/parabolic-sar

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
    """Indicator: STC

    The Schaff Trend Cycle (STC) is a charting indicator that is commonly used to identify market
    trends and provide buy and sell signals to traders. Developed in 1999 by noted currency trader
    Doug Schaff, STC is a type of oscillator and is based on the assumption that, regardless of time
    frame, currency trends accelerate and decelerate in cyclical patterns.

    Abbreviation: STC
    Reference: https://www.investopedia.com/articles/forex/10/schaff-trend-cycle-indicator.asp
    Warmup: window_slow + 2 * cycle + smooth1 + smooth2 - 5

    Formula:
        MACD Line = EMA(23) - EMA(50)
        %K of MACD = Stochastic of MACD Line
        STC = Double smoothed %K

    Inputs:
        close: closing price

    Params:
        window_slow [default=50, min=2, max=200]: Slow EMA period
        window_fast [default=23, min=2, max=200]: Fast EMA period
        cycle [default=10, min=1, max=200]: Cycle period
        smooth1 [default=3, min=1, max=200]: First smoothing period
        smooth2 [default=3, min=1, max=200]: Second smoothing period

    Outputs:
        stc [dimensionless, 0..100] "STC":
            MACD line put through two successive rounds of stochastic normalisation, each followed
            by an EMA smoothing. Hard-bounded 0..100: each normalisation confines its output to that
            range and each smoothing is a convex combination of values already inside it, so unlike
            the MACD it is built from, this cannot leave the range. Verified to touch both 0 and 100
            exactly. Pins at the extremes for extended stretches, so the turn rather than the level
            is the signal. 25/75 are the conventional thresholds

    Interpretation:
        - STC > 75: Overbought
        - STC < 25: Oversold
        - Faster signals than traditional MACD
        - Good for identifying trend changes early

    Applications:
        - Early trend-direction identification and turning points
        - Overbought/oversold entries and exits at 25 and 75
        - Cycle top and bottom detection
        - Lower-lag substitute for MACD
        - Divergence against price

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


class SwingDelta(IndicatorInterface):
    """Indicator: SwingDelta

    Divergence analysis compares two changes: what price did between its last two swing extremes, and what an indicator did between the two extremes that pair with them. This emits those changes. Whether opposite signs mean "regular bullish divergence" or anything else is a reading of the measurement, and belongs to the signal that makes it. low_price_delta[t]       price[pi2] - price[pi1]        between the last two swing LOWS low_indicator_delta[t]   indicator[ii2] - indicator[ii1]  between the paired indicator lows high_price_delta[t]      price[pi2] - price[pi1]        between the last two swing HIGHS high_indicator_delta[t]  indicator[ii2] - indicator[ii1]  between the paired indicator highs All four are NaN except on a confirmation bar. Swings are found with `argrelextrema` at `swing_window`, consecutive price extremes closer together than `min_swing_distance` are skipped, and each pair is matched to the indicator extremes nearest in time. A pair is reported at `max(price_idx, indicator_idx) + swing_window`, the bar on which both extremes are confirmed -- so sliding-window evaluation sees the same pairing as a full-series pass and nothing leaks backwards. Replaces `Divergence`, which emitted four booleans and so stated a conclusion rather than a measurement. That class still exists and still works; it is deprecated. NaN, not zero, when scipy is unavailable: a delta that could not be computed is unknown, which is not the same claim as a delta of zero. `Divergence` returned all-False there, asserting "no divergence" when nothing had been examined.

    Warmup: swing_window

    Formula:
        low_price_delta[t] = price[pi2] - price[pi1] and low_indicator_delta[t] = indicator[ii2] - indicator[ii1] at t = max(pi2, ii2) + swing_window, where pi1, pi2 are the last two swing lows at least min_swing_distance apart and ii1, ii2 the indicator lows nearest them; the high_* pair is the same over swing highs

    Inputs:
        price: the price series swings are found in, normally close
        indicator: any series to compare against price -- RSI, MACD, OBV; its swings are paired with
        price's

    Params:
        swing_window [default=5, min=2, max=20]: Bars on each side to confirm swing extremum
        min_swing_distance [default=10, min=3, max=50]: Min bars between the two swing points
        compared

    Outputs:
        low_price_delta [price, -inf..inf] "low_price_delta":
            Change in price between its last two confirmed swing LOWS. NaN except on a confirmation
            bar.
        low_indicator_delta [indicator units, -inf..inf] "low_indicator_delta":
            Change in the companion indicator between the two lows paired with those price lows.
        high_price_delta [price, -inf..inf] "high_price_delta":
            The same across swing HIGHS.
        high_indicator_delta [indicator units, -inf..inf] "high_indicator_delta":
            The companion indicator's change across the paired highs. Opposite signs between a price
            delta and its indicator delta are what divergence analysis reads as a divergence.

    Interpretation:
        How much price moved between two confirmed swings, and how much a companion indicator moved
        between the two that pair with them. Opposite signs are what divergence analysis calls a
        divergence -- but the sign comparison is the reading, and it belongs to the signal.

    Applications:
        Divergence detection of every classic kind. Which kind is a question about the two signs and
        which swing side they came from, so the four cases are four signals rather than four outputs
        here.

    Args:
        data: {'price': pd.Series, 'indicator': pd.Series}
        params: {'swing_window': int, 'min_swing_distance': int}

    Returns:
        {'low_price_delta': pd.Series, 'low_indicator_delta': pd.Series,
         'high_price_delta': pd.Series, 'high_indicator_delta': pd.Series}
    """
    _data = ["price", "indicator"]
    _params = ["swing_window", "min_swing_distance"]
    _outputs = ["low_price_delta", "low_indicator_delta",
                "high_price_delta", "high_indicator_delta"]

    @classmethod
    def _compute(cls, data, params):
        price = data['price']
        indicator = data['indicator']
        n = len(price)
        blank = {k: pd.Series(np.full(n, np.nan), index=price.index, name=k) for k in cls._outputs}
        try:
            from scipy.signal import argrelextrema
        except ImportError:
            return blank

        sw = int(params['swing_window'])
        min_dist = int(params['min_swing_distance'])
        p_arr = price.to_numpy(dtype=np.float64, copy=False)
        i_arr = indicator.to_numpy(dtype=np.float64, copy=False)

        out = {k: np.full(n, np.nan) for k in cls._outputs}

        def pairs(price_idx, ind_idx):
            if len(price_idx) < 2 or len(ind_idx) < 2:
                return
            for pos in range(1, len(price_idx)):
                pi2, pi1 = price_idx[pos], price_idx[pos - 1]
                if pi2 - pi1 < min_dist:
                    continue
                ind1 = ind_idx[np.argmin(np.abs(ind_idx - pi1))]
                ind2 = ind_idx[np.argmin(np.abs(ind_idx - pi2))]
                if ind1 == ind2:
                    continue
                fire = int(max(pi2, ind2)) + sw
                if fire >= n:
                    continue
                yield pi1, pi2, ind1, ind2, fire

        for side, p_idx, i_idx in (
            ("low", argrelextrema(p_arr, np.less, order=sw)[0], argrelextrema(i_arr, np.less, order=sw)[0]),
            ("high", argrelextrema(p_arr, np.greater, order=sw)[0], argrelextrema(i_arr, np.greater, order=sw)[0]),
        ):
            for pi1, pi2, ii1, ii2, fire in pairs(p_idx, i_idx):
                out[f"{side}_price_delta"][fire] = p_arr[pi2] - p_arr[pi1]
                out[f"{side}_indicator_delta"][fire] = i_arr[ii2] - i_arr[ii1]

        return {k: pd.Series(v, index=price.index, name=k) for k, v in out.items()}


class HeikinAshi(IndicatorInterface):
    """Indicator: HeikinAshi

    Smoothed candlestick representation that averages across multiple bars, making trends visually
    easier to identify. Japanese for "average bar".

    Abbreviation: HA
    Warmup: 0

    Formula:
        ha_close[t] = (open[t]+high[t]+low[t]+close[t])/4; ha_open[t] = (ha_open[t-1]+ha_close[t-1])/2; ha_high[t] = max(high[t], ha_open[t], ha_close[t]); ha_low[t] = min(low[t], ha_open[t], ha_close[t])

    Inputs:
        open: opening price
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        ha_open [price, 0..inf] "ha_open":
            Mean of the PREVIOUS ha_open and ha_close, so it is recursive and each candle inherits
            the last.
        ha_high [price, 0..inf] "ha_high":
            The highest of the bar's high, ha_open and ha_close.
        ha_low [price, 0..inf] "ha_low":
            The lowest of the bar's low, ha_open and ha_close.
        ha_close [price, 0..inf] "ha_close":
            Mean of the bar's own open, high, low and close.

    Interpretation:
        A smoothed re-drawing of the bars themselves rather than a line laid over them. ha_open is
        recursive, so each candle carries the previous one, which is what suppresses the single-bar
        noise and also what makes a run of same-colour candles persist longer than the raw bars
        would.

    Applications:
        Trend legibility: consecutive same-colour candles read as a continuing move. Because ha_open
        depends on its own history, these are NOT the bars the market traded and should not be used
        for fills.

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


class WilliamsAlligator(IndicatorInterface):
    """Indicator: WilliamsAlligator

    Three SMMA lines plotted on median price ((high + low) / 2) with forward offsets: Jaw   = SMMA(13) shifted forward 8 bars (slowest, "sleeping alligator") Teeth = SMMA( 8) shifted forward 5 bars Lips  = SMMA( 5) shifted forward 3 bars (fastest, "gator's lips") The forward shift is applied via pandas .shift(+n), which is lookahead-free in backtesting: the value at bar `t` in the output is the SMMA computed at bar `t - n`. Trend interpretation: - Lips > Teeth > Jaw (all spreading upward): alligator is eating, strong uptrend. - Lips < Teeth < Jaw (all spreading downward): strong downtrend. - Tangled (lines crossing/converging): alligator is sleeping, no trend.

    Abbreviation: Alligator
    Warmup: max(jaw + jaw_offset, teeth + teeth_offset, lips + lips_offset) - 1

    Formula:
        Median Price = (High + Low) / 2

          Jaw   (blue)  = SMMA(Median, 13), displaced 8 bars
          Teeth (red)   = SMMA(Median,  8), displaced 5 bars
          Lips  (green) = SMMA(Median,  5), displaced 3 bars

        Periods are Fibonacci numbers. Williams' collective term: Balance Lines.

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
        jaw [price, 0..inf] "Jaw":
            the slowest of Bill Williams' three Balance Lines -- a smoothed moving average of median
            price (high+low)/2 over the jaw window, displaced forward. Conventionally 13-period
            smoothed and shifted 8 bars, plotted blue. Displacement is applied by carrying older
            values forward, which is lookahead-free and preserves the canonical spacing between the
            three lines
        teeth [price, 0..inf] "Teeth":
            the middle Balance Line -- conventionally an 8-period smoothed moving average of median
            price shifted 5 bars, plotted red
        lips [price, 0..inf] "Lips":
            the fastest Balance Line -- conventionally a 5-period smoothed moving average of median
            price shifted 3 bars, plotted green. Lips crossing the other two is the 'awakening' that
            marks a trend emerging from the sleeping, interwoven state

    Interpretation:
        - Sleeping: the lines intertwine -- consolidation, no trend, stand aside
        - Awakening: Lips crosses the other lines, a trend may be emerging
        - Hungry: the lines separate and fan out, confirming strength; convergence signals weakening
        - Ordering gives direction -- Lips above Teeth above Jaw is bullish, inverted is bearish
        - Premise: markets trend only 15-30% of the time, and the indicator exists to skip the rest
        - Known weakness: a high rate of false signals while sleeping

    Applications:
        - Entering during the awakening phase
        - Confirming trend strength during the hungry phase
        - Exiting when the lines converge
        - Range filter -- standing aside while the Alligator sleeps
        - Combined with Williams' Fractals to refine entry and exit timing

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
    """DEPRECATED for the ontology: emits a verdict, not only a measurement.

    `direction` is +1 long / -1 short, and `long_band` / `short_band` are NaN according to it.
    Indicators here state what they measured; deciding what it means is the signal layer's
    job. Unlike TTMSqueeze and MultiTFTrend there is no regime-free core to split out --
    the bands themselves switch on the regime. Kept working and unchanged.
SuperTrend (Olivier Seban).

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


# MARibbon (Moving Average Ribbon) was removed here. It stacked N simple moving averages and asked
# three ordering questions, emitting `ribbon_bullish` / `ribbon_bearish` / `ribbon_tangled` -- all
# three boolean, which was ALL of its outputs. An indicator emits a numeric measurement and a signal
# emits a boolean predicate, so it was not an indicator under our own definition; it was three
# signals wearing an indicator's clothes, and it had no numeric output left once they moved.
#
# The ordering test now lives in `signals/trend.py`, in the `ma_ribbon_bullish` / `ma_ribbon_bearish`
# / `ma_ribbon_tangled` signals that were always its only consumer. Those names are unchanged --
# MangroveOracle's plan_generator references all three. The SMAs come straight from `SMA`.


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


class MultiTFSlope(IndicatorInterface):
    """Indicator: MultiTFSlope

    higher = close resampled to `higher_tf`, last value in each bucket slope  = EMA(higher, window).diff() output = slope / rolling_mean(|EMA(higher, window)|, window) Unitless by construction, so the same number is comparable across assets and price levels. Broadcast back to base bars by forward-fill from the most recently CLOSED higher-timeframe bar, so no base bar sees a period that has not finished. Replaces `MultiTFTrend`, which emitted this slope already thresholded into -1 / 0 / +1. The threshold is the judgement, so it moved to the signals -- and with it `slope_threshold`, which was an indicator parameter describing a decision the indicator should not have been making. That class still exists and still works; it is deprecated.

    Warmup: 1 - 1

    Formula:
        higher_tf_slope[t] = diff(ema(resample(close, higher_tf), window)) / rolling_mean(|ema|, window), forward-filled from the last CLOSED higher-tf bar

    Inputs:
        close: closing price

    Params:
        higher_tf: Pandas offset alias for the higher timeframe
        window [default=10, min=2, max=100]: EMA period on the resampled close

    Outputs:
        higher_tf_slope [unitless, -inf..inf] "higher_tf_slope":
            Slope of a higher-timeframe EMA divided by that EMA's own rolling magnitude, so the
            number is comparable across assets and price levels. Forward-filled from the most
            recently CLOSED higher-timeframe bar.

    Interpretation:
        Direction and steepness of a higher timeframe's trend, normalised by its own magnitude so
        the number is unitless and comparable across assets.

    Applications:
        Higher-timeframe confirmation. Where to put the threshold is the judgement, and it moved to
        the signals with `slope_threshold`.

    Args:
        data: {'close': pd.Series}
        params: {'higher_tf': str, 'window': int}

    Returns:
        {'higher_tf_slope': pd.Series}
    """
    _data = ["close"]
    _params = ["higher_tf", "window"]
    _outputs = ["higher_tf_slope"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        blank = pd.Series(np.full(len(close), np.nan), index=close.index, name='higher_tf_slope')
        if not isinstance(close.index, pd.DatetimeIndex):
            return {'higher_tf_slope': blank}
        window = params['window']
        higher = close.resample(params['higher_tf'], label='right', closed='right').last().dropna()
        if len(higher) < window + 2:
            return {'higher_tf_slope': blank}
        ema_higher = EMA.compute({'close': higher}, {'window': window})['ema']
        denom = ema_higher.abs().rolling(window, min_periods=1).mean().replace(0, np.nan)
        rel = (ema_higher.diff() / denom).reindex(close.index, method='ffill')
        return {'higher_tf_slope': pd.Series(rel.values, index=close.index, name='higher_tf_slope')}



class Divergence(IndicatorInterface):
    """DEPRECATED: use `SwingDelta`, which measures instead of concluding.

    Divergence detection between price and an indicator (RSI/MACD/OBV/...).

    All four outputs are booleans, so this states a conclusion rather than a measurement -- which
    is what disqualified it from the ontology's indicator layer. `SwingDelta` emits the two changes
    the conclusion is drawn from; the four sign comparisons live in the signals that read it. Kept
    working and unchanged for anything that already calls it.

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
