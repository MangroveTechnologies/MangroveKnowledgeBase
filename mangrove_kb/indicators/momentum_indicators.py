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
    """Indicator: RSI

    Compares the magnitude of recent gains and losses over a specified time period to measure speed
    and change of price movements of a security. It is primarily used to attempt to identify
    overbought or oversold conditions in the trading of an asset.

    Abbreviation: RSI
    Reference: https://www.investopedia.com/terms/r/rsi.asp
    Warmup: window - 1

    Formula:
        RS = Average Gain over n periods / Average Loss over n periods
        RSI = 100 - (100 / (1 + RS))

        Standard period: 14

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: RSI calculation window

    Outputs:
        rsi [dimensionless, 0..100] "Relative Strength Index":
            Wilder's momentum index, 100 - 100/(1 + avg_gain/avg_loss), with both averages
            Wilder-smoothed at alpha=1/window. Hard-bounded 0..100 by construction, not by
            convention: the ratio is non-negative so the expression cannot leave the range. Returns
            100 where average loss is zero AND there are gains -- a genuine limit, since the ratio
            diverges. Returns NaN where there are neither gains nor losses (a perfectly flat
            window), which is 0/0 with no limit to take; an earlier guard tested only the
            denominator and returned 100 there, the all-gains answer for a market with no gains.
            That NaN convention matches StochasticOscillator, WilliamsR and StochRSI. 70/30 and
            80/20 are conventional thresholds, NOT bounds; the traversed range shifts with regime
            (roughly 40-90 in bull markets, 10-60 in bear)

    Interpretation:
        - RSI > 70: Overbought (potential pullback)
        - RSI < 30: Oversold (potential bounce)
        - RSI 40-60: Neutral zone
        - Bullish divergence: Price makes lower low, RSI makes higher low
        - Bearish divergence: Price makes higher high, RSI makes lower high

    Applications:
        - Overbought/oversold signals in ranging markets
        - Divergence signals for reversal warnings
        - RSI trend lines and pattern analysis
        - Failure swings as reversal confirmation
        - Centerline (50) crossovers as trend signals

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

        # ZERO-RANGE CONVENTION. Two different degenerate cases hide behind `emadn == 0`, and they
        # do not have the same answer:
        #
        #   gains, no losses -> 100. A real limit: RS -> infinity, so RSI -> 100. This is the
        #                       documented behaviour and it is correct.
        #   no gains, no losses (a perfectly flat series) -> undefined. RS is 0/0. The previous
        #                       guard tested only the denominator, so it returned 100 -- the
        #                       all-gains answer for a market with no gains.
        #
        # NaN for the flat case lines RSI up with StochasticOscillator, WilliamsR and StochRSI,
        # which are all per-bar bounded readings where a NaN is contained to the bar it describes.
        # (Contrast ADI and CMF, which are running sums: there a NaN would poison every later bar,
        # so they substitute 0.)
        with np.errstate(divide='ignore', invalid='ignore'):
            rsi = np.where(
                (emadn == 0) & (emaup > 0),
                100.0,
                np.where(
                    (emadn == 0) & (emaup == 0),
                    np.nan,
                    100 - (100 / (1 + relative_strength)),
                ),
            )

        return {'rsi': pd.Series(rsi, index=close.index, name="rsi")}


class TSI(IndicatorInterface):
    """Indicator: TSI

    Shows both trend direction and overbought/oversold conditions.

    Abbreviation: TSI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/true-strength-index
    Warmup: window_slow + window_fast - 1

    Formula:
        PC = Close - Previous Close
        Double Smoothed PC = EMA(EMA(PC, 25), 13)
        Double Smoothed Absolute PC = EMA(EMA(|PC|, 25), 13)
        TSI = (Double Smoothed PC / Double Smoothed Absolute PC) * 100

    Inputs:
        close: closing price

    Params:
        window_slow [default=25, min=10, max=50]: Slow EMA period
        window_fast [default=13, min=5, max=25]: Fast EMA period

    Outputs:
        tsi [dimensionless, -100..100] "TSI":
            100 * double-smoothed momentum / double-smoothed absolute momentum, each an EMA over
            window_slow then an EMA over window_fast of close-to-close change. Hard-bounded
            -100..100: an EMA is a weighted average with non-negative weights, so the smoothed
            signed series can never exceed the smoothed absolute series in magnitude at either
            stage. In practice values cluster far inside, typically within +/-25, and the literature
            sets no fixed overbought level -- the zero-line crossover is the primary reading

    Interpretation:
        - TSI > 0: Bullish momentum
        - TSI < 0: Bearish momentum
        - Extreme readings suggest overbought/oversold
        - Less noise than RSI due to double smoothing

    Applications:
        - Trend and bias determination via the zero-line crossover, the purest signal
        - Entry and exit timing via signal-line crossovers
        - Bullish and bearish divergence to anticipate reversals
        - Support, resistance and trendline analysis drawn on the oscillator itself

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
    """Indicator: UltimateOscillator

    Larry Williams' (1976) signal, a momentum oscillator designed to capture momentum across three different timeframes. BP = Close - Minimum(Low or Prior Close). TR = Maximum(High or Prior Close)  -  Minimum(Low or Prior Close) Average7 = (7-period BP Sum) / (7-period TR Sum) Average14 = (14-period BP Sum) / (14-period TR Sum) Average28 = (28-period BP Sum) / (28-period TR Sum) UO = 100 x [(4 x Average7)+(2 x Average14)+Average28]/(4+2+1)

    Abbreviation: UO
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ultimate-oscillator
    Warmup: window3

    Formula:
        BP = Close - Min(Low, Previous Close)
        TR = Max(High, Previous Close) - Min(Low, Previous Close)
        Average7 = Sum(BP, 7) / Sum(TR, 7)
        Average14 = Sum(BP, 14) / Sum(TR, 14)
        Average28 = Sum(BP, 28) / Sum(TR, 28)
        UO = 100 * ((4 * Average7) + (2 * Average14) + Average28) / 7

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window1: shortest lookback
        window2: middle lookback
        window3: longest lookback
        weight1: weight on the shortest average
        weight2: weight on the middle average
        weight3: weight on the longest average

    Outputs:
        ultimate_oscillator [dimensionless, 0..100] "Ultimate Oscillator":
            weighted blend of buying pressure over true range across three windows, 100 * (w1*avg1 +
            w2*avg2 + w3*avg3) / (w1+w2+w3). Each average is a SUM of buying pressure over a SUM of
            true range, not a mean of per-bar ratios. Hard-bounded 0..100 because buying pressure is
            non-negative and never exceeds true range on a bar. Blending three horizons is what
            damps the false divergences a single-period oscillator produces. 30/50/70 are
            conventional levels

    Interpretation:
        - UO > 70: Overbought
        - UO < 30: Oversold
        - Multi-timeframe reduces whipsaws
        - Divergences with price signal reversals

    Applications:
        - Three-part divergence trade signals -- the canonical Williams use
        - Overbought/oversold extremity screening at 70 and 30
        - Trend bias via position relative to the 50 centreline
        - Multi-timeframe momentum confirmation blended into one series

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
    """Indicator: StochasticOscillator

    Developed in the late 1950s by George Lane. The stochastic oscillator presents the location of
    the closing price of a stock in relation to the high and low range of the price of a stock over
    a period of time, typically a 14-day period. VARIANT: this is the **Fast** stochastic. `stoch_k`
    is the raw %K and `stoch_d` is an SMA of it. The literature distinguishes Fast, Slow (%K itself
    smoothed, %D an SMA of that) and Full (user-specified smoothing on both); they produce
    materially different series, and neither the class name nor the parameters say which one this
    is.

    Abbreviation: Stoch
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochastic-oscillator-fast-slow-and-full
    Warmup: window + smooth_window - 2

    Formula:
        %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low)
        %D = SMA(%K, 3)

        Typical period: 14 for %K
        Fast Stochastic: Raw %K and %D
        Slow Stochastic: %K smoothed, %D of smoothed %K

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: %K period
        smooth_window [default=3, min=1, max=10]: %K smoothing period

    Outputs:
        stoch_k [dimensionless, 0..100] "%K":
            100 * (close - lowest low) / (highest high - lowest low) over window. Hard-bounded
            0..100 because the current bar is inside the lookback, so close necessarily lies within
            the window's range. This is the FAST %K -- unsmoothed -- so the pair emitted here is
            Fast Stochastic, not the Slow or Full variant. NaN when the window's high equals its
            low; the literature states no convention for that case
        stoch_d [dimensionless, 0..100] "%D":
            signal line: simple moving average of stoch_k over smooth_window. Bounded 0..100 as an
            average of values already in that range. With the fast %K above, this is Fast %D

    Interpretation:
        - Above 80: Overbought
        - Below 20: Oversold
        - %K crossing above %D: Buy signal
        - %K crossing below %D: Sell signal
        - Divergences with price signal potential reversals

    Applications:
        - Overbought/oversold signals
        - Crossover signals in trend direction
        - Divergence analysis
        - Slow stochastic for smoother signals

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

        # ZERO-RANGE CONVENTION: NaN, deliberately. Where the window's high equals its low, %K is
        # 0/0 -- close sits simultaneously at the top and the bottom of the range, and there is no
        # limit to take. No source states a convention for this case. The result was already NaN,
        # but by falling through pandas' division rather than by decision; the explicit guard also
        # covers the malformed-data case where close lies outside [low, high], which would otherwise
        # divide a non-zero numerator by zero and yield +/-inf.
        #
        # NaN is the right answer here because %K is a per-bar bounded reading: the NaN is contained
        # to the bar it describes. ADI and CMF face the same 0/0 and answer 0 instead, because they
        # are running sums where a NaN propagates forever.
        span = smax - smin
        stoch_k = (100 * (close - smin) / span).where(span != 0, np.nan)
        stoch_d = stoch_k.rolling(smooth_window, min_periods=smooth_window).mean()

        return {
            'stoch_k': pd.Series(stoch_k, name="stoch_k"),
            'stoch_d': pd.Series(stoch_d, name="stoch_d")
        }


class KAMA(IndicatorInterface):
    """Indicator: KAMA

    Moving average designed to account for market noise or volatility. KAMA will closely follow
    prices when the price swings are relatively small and the noise is low. KAMA will adjust when
    the price swings widen and follow prices from a greater distance. This trend-following indicator
    can be used to identify the overall trend, time turning points and filter price movements.

    Abbreviation: KAMA
    Reference: https://www.tradingview.com/ideas/kama/
    Warmup: window - 1

    Formula:
        ER = Change / Volatility (Efficiency Ratio)
        SC = (ER * (Fast - Slow) + Slow)^2 (Smoothing Constant)
        KAMA = Previous KAMA + SC * (Price - Previous KAMA)

    Inputs:
        close: closing price

    Params:
        window [default=10, min=5, max=30]: Efficiency ratio period
        pow1 [default=2, min=1, max=10]: Fast smoothing constant
        pow2 [default=30, min=10, max=50]: Slow smoothing constant

    Outputs:
        kama [price, 0..inf] "Kaufman's Adaptive Moving Average":
            genuinely data-driven adaptive average: the smoothing constant is recomputed each bar
            from the efficiency ratio, net directional movement divided by total path length.
            Efficient trends drive the constant toward the fast bound so the line hugs price; choppy
            action drives it toward the slow bound so the line nearly stops. A FLAT KAMA is itself
            information -- it means inefficient, ranging price, not merely unchanged price. The
            constant is squared, capping effective smoothing near 0.44 rather than 0.67, and stays
            within (0,1) so the line cannot overshoot. SEEDING CAVEAT: seeded with the price at the
            first valid bar; StockCharts specifies an initial SMA

    Interpretation:
        - Adapts to market conditions automatically
        - Less whipsaw than traditional MAs in ranging markets
        - More responsive during trending periods

    Applications:
        - Trend following and identifying directional changes
        - Whipsaw filtering via price and time filters around the line
        - Defining overall trend by combining multiple parameter sets
        - Crossovers against price or another moving average
        - Distinguishing trending from choppy regimes

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
    """Indicator: ROC

    The Rate-of-Change (ROC) indicator, which is also referred to as simply Momentum, is a pure
    momentum oscillator that measures the percent change in price from one period to the next. The
    ROC calculation compares the current price with the price "n" periods ago. The plot forms an
    oscillator that fluctuates above and below the zero line as the Rate-of-Change moves from
    positive to negative. As a momentum oscillator, ROC signals include centerline crossovers,
    divergences and overbought-oversold readings.

    Abbreviation: ROC
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc
    Warmup: window

    Formula:
        ROC(n) = ((Close - Close[n]) / Close[n]) * 100

    Inputs:
        close: closing price

    Params:
        window [default=12, min=1, max=50]: ROC period

    Outputs:
        roc [percent, -100..inf] "Rate of Change":
            percent change of close over window: (close - close_n) / close_n * 100. HARD floor at
            -100 because a security can only fall to zero; no ceiling at all. The conventional +/-10
            overbought/oversold band is volatility-dependent (+/-5 for quiet names, +/-15 for
            volatile ones) and is NOT a bound. The literature warns that ROC divergences fail more
            often than they work

    Interpretation:
        - **Positive ROC**: Price is rising over the period (bullish momentum)
        - **Negative ROC**: Price is falling over the period (bearish momentum)
        - **Zero line cross**: Momentum shift from positive to negative or vice versa
        - **Extreme values**: Can indicate overbought (high positive) or oversold (high negative)
        conditions

    Applications:
        - **Momentum confirmation**: Positive ROC confirms uptrend, negative ROC confirms downtrend
        - **Divergence detection**: ROC making lower highs while price makes higher highs (bearish
        divergence)
        - **Threshold signals**: ROC crossing above/below specific levels (e.g., +10%/-10%)
        - **Zero line crosses**: ROC crossing zero indicates momentum direction change

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
    """Indicator: AwesomeOscillator

    The Awesome Oscillator is an indicator used to measure market momentum. AO calculates the
    difference of a 34 Period and 5 Period Simple Moving Averages. The Simple Moving Averages that
    are used are not calculated using closing price but rather each bar's midpoints. AO is generally
    used to affirm trends or to anticipate possible reversals. MEDIAN PRICE = (HIGH+LOW)/2 AO =
    SMA(MEDIAN PRICE, 5)-SMA(MEDIAN PRICE, 34)

    Abbreviation: AO
    Warmup: window2 - 1

    Formula:
        Midpoint = (High + Low) / 2
        AO = SMA(Midpoint, 5) - SMA(Midpoint, 34)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar

    Params:
        window1: fast SMA period on median price
        window2: slow SMA period on median price

    Outputs:
        ao [price, -inf..inf] "Awesome Oscillator":
            5-period SMA minus 34-period SMA of MEDIAN price (high+low)/2, not close. Unbounded and
            in price units, so not comparable across instruments; zero is a structural level (the
            two SMAs are equal), not a bound. Plotted as a histogram whose bar colour encodes the
            change from the prior bar, not the sign -- the saucer and twin-peaks patterns are read
            from that

    Interpretation:
        - AO > 0: Bullish momentum
        - AO < 0: Bearish momentum
        - Zero line crossovers signal momentum shifts
        - Twin peaks pattern for divergence analysis

    Applications:
        - Confirming that momentum agrees with price direction
        - Anticipating reversals via the saucer and twin-peaks patterns
        - Zero-line crossover timing
        - Component of Williams' wider Chaos toolkit alongside fractals and the Alligator

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
    """Indicator: WilliamsR

    Developed by Larry Williams, Williams %R is a momentum indicator that is the inverse of the Fast
    Stochastic Oscillator. Also referred to as %R, Williams %R reflects the level of the close
    relative to the highest high for the look-back period. In contrast, the Stochastic Oscillator
    reflects the level of the close relative to the lowest low. %R corrects for the inversion by
    multiplying the raw value by -100. As a result, the Fast Stochastic Oscillator and Williams %R
    produce the exact same lines, only the scaling is different. Williams %R oscillates from 0 to
    -100. Readings from 0 to -20 are considered overbought. Readings from -80 to -100 are considered
    oversold. %R = (Highest High - Close)/(Highest High - Lowest Low) * -100

    Abbreviation: %R
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r
    Warmup: window - 1

    Formula:
        %R = (Highest High - Close) / (Highest High - Lowest Low) * -100

        Typical period: 14

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: Lookback window

    Outputs:
        wr [dimensionless, -100..0] "%R":
            -100 * (highest high - close) / (highest high - lowest low) over window. NEGATIVE by
            construction: hard-bounded -100..0, where 0 means close sat at the window's high and
            -100 at its low. The minus sign is part of the canonical formula, not a display choice
            -- a 0..+100 implementation is computing Stochastic %K, not %R. Verified here to equal
            stoch_k - 100 exactly. -20/-80 are conventional thresholds. NaN when the window's high
            equals its low

    Interpretation:
        - -20 to 0: Overbought
        - -80 to -100: Oversold
        - Note: Scale is inverted (0 at top, -100 at bottom)

    Applications:
        - Overbought/oversold identification at -20 and -80
        - Trend-bias reading via -50 centreline crossings (upper vs lower half of the range)
        - Momentum-failure detection when %R can no longer reach a prior extreme
        - Longer-lookback big-picture trend reading (e.g. a 125-day %R for a six-month view)
        - Confirmation alongside volume, chart patterns and breakouts

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

        # ZERO-RANGE CONVENTION: NaN, deliberately -- see StochasticOscillator, of which this is the
        # inverse. A window whose high equals its low makes this 0/0 with no limit to take.
        span = highest_high - lowest_low
        wr = (-100 * (highest_high - close) / span).where(span != 0, np.nan)

        return {'wr': pd.Series(wr, name="wr")}


class StochRSI(IndicatorInterface):
    """Indicator: StochRSI

    The StochRSI oscillator was developed to take advantage of both momentum indicators in order to
    create a more sensitive indicator that is attuned to a specific security's historical
    performance rather than a generalized analysis of price change. SCALE: this emits 0..1, the
    canonical Chande-Kroll / StockCharts form. The literature is genuinely split -- Fidelity and
    many platforms render the same quantity x100, and TradingView is internally inconsistent (its
    docs say 0-1, its plotted indicator renders 0-100). The conventional 20/80 overbought/oversold
    levels are therefore **0.20 / 0.80** here. Applying 20 and 80 directly to this series can never
    produce a signal.

    Abbreviation: StochRSI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochrsi
    Warmup: 2 * window + smooth1 + smooth2 - 4

    Formula:
        StochRSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI)

          over the lookback window (default 14, applied to both the RSI and the stochastic range)

        Optional smoothing:
          %K = n-period SMA of StochRSI   (default 3)
          %D = m-period SMA of %K         (default 3)

    Inputs:
        close: closing price

    Params:
        window [default=14, min=5, max=30]: RSI period
        smooth1 [default=3, min=1, max=10]: Stochastic %K smoothing
        smooth2 [default=3, min=1, max=10]: Stochastic %D smoothing

    Outputs:
        stochrsi [ratio, 0..1] "StochRSI":
            position of RSI within its own recent range, (rsi - min rsi) / (max rsi - min rsi) over
            window -- a second derivative of price, measuring where RSI sits rather than where price
            sits. Emitted on the 0..1 SCALE, which is the canonical form from Chande and Kroll and
            from StockCharts; many platforms render the same quantity multiplied by 100. Consumers
            applying 20/80 thresholds to this series will never trigger -- the equivalent levels
            here are 0.20/0.80. NaN when RSI is flat across the window
        stochrsi_k [ratio, 0..1] "%K":
            stochrsi smoothed by a simple moving average over smooth1. The %K/%D naming is a
            platform convention borrowed from the Stochastic Oscillator and is absent from the
            Chande-Kroll original, which names only the raw series
        stochrsi_d [ratio, 0..1] "%D":
            signal line: simple moving average of stochrsi_k over smooth2. Same 0..1 scale caveat as
            the raw series

    Interpretation:
        - Measures where RSI sits within its own recent range -- a second derivative of price, not a
        reading of price
        - On the 0..1 scale, above 0.80 is overbought and below 0.20 oversold (not 70/30)
        - Equals 0 when RSI is at its lowest in the window, 1 when at its highest -- the extremes
        are literal
        - Centreline is 0.50, where RSI sits mid-range
        - Highly volatile: reaches its extremes far more often than RSI does

    Applications:
        - Generating more frequent overbought/oversold signals than raw RSI
        - Short-term trend identification via the 0.50 centreline
        - Short-term entry and exit timing on overbought/oversold crosses
        - Smoothed short-term trend reading when averaged

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

        # ZERO-RANGE CONVENTION: NaN, deliberately -- the same 0/0 as StochasticOscillator, one
        # level up. A window over which RSI never moves gives an identical rolling max and min, so
        # there is no range to locate the current reading within.
        span = rsi_result.rolling(window).max() - lowest_low_rsi
        stochrsi = ((rsi_result - lowest_low_rsi) / span).where(span != 0, np.nan)
        stochrsi_k = stochrsi.rolling(smooth1).mean()
        stochrsi_d = stochrsi_k.rolling(smooth2).mean()

        return {
            'stochrsi': pd.Series(stochrsi, name="stochrsi"),
            'stochrsi_k': pd.Series(stochrsi_k, name="stochrsi_k"),
            'stochrsi_d': pd.Series(stochrsi_d, name="stochrsi_d")
        }


class PPO(IndicatorInterface):
    """Indicator: PPO

    the difference between two moving averages as a percentage of the larger moving average.

    Abbreviation: PPO
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-price-oscillator-ppo
    Warmup: window_slow + window_sign - 2

    Formula:
        PPO = ((EMA(12) - EMA(26)) / EMA(26)) * 100
        Signal Line = EMA(PPO, 9)

    Inputs:
        close: closing price

    Params:
        window_slow [default=26, min=15, max=50]: Slow EMA period
        window_fast [default=12, min=5, max=20]: Fast EMA period
        window_sign [default=9, min=3, max=15]: Signal line period

    Outputs:
        ppo [percent, -inf..inf] "PPO Line":
            MACD expressed as a percentage: (fast EMA - slow EMA) / slow EMA * 100, the denominator
            being the SLOW EMA. Normalising by price level is the whole point -- unlike MACD,
            readings ARE comparable across instruments and across periods where the price level
            changed. Still UNBOUNDED: percentage normalisation removes price-level dependence, not
            magnitude. A theoretical -100 floor follows from positive prices but is not a literature
            claim and is unreachable in practice
        ppo_signal [percent, -inf..inf] "Signal Line":
            EMA of ppo over window_sign, read exactly like the MACD signal line
        ppo_hist [percent, -inf..inf] "PPO Histogram":
            ppo minus ppo_signal; anticipates signal-line crossovers the same way the MACD histogram
            does

    Interpretation:
        - Positive PPO: Short-term momentum above long-term
        - Negative PPO: Short-term momentum below long-term
        - Normalized for comparison across different price levels
        - Signal line crossovers for timing

    Applications:
        - Comparing momentum across securities at very different price levels -- the main reason to
        prefer PPO over MACD
        - Comparing one security's momentum across long periods where its price level changed
        substantially
        - Signal-line crossovers
        - Centreline (zero) crossovers for trend bias
        - Divergence against price

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
    """Indicator: PVO

    The PVO measures the difference between two volume-based moving averages as a percentage of the
    larger moving average.

    Abbreviation: PVO
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-volume-oscillator-pvo
    Warmup: window_slow + window_sign - 2

    Formula:
        PVO = ((EMA(Volume, 12) - EMA(Volume, 26)) / EMA(Volume, 26)) * 100
        Signal Line = EMA(PVO, 9)

    Inputs:
        volume: units traded during the bar

    Params:
        window_slow [default=26, min=15, max=50]: Slow EMA period
        window_fast [default=12, min=5, max=20]: Fast EMA period
        window_sign [default=9, min=3, max=15]: Signal line period

    Outputs:
        pvo [percent, -100..inf] "PVO Line":
            the PPO construction applied to VOLUME: (fast EMA - slow EMA) / slow EMA * 100 of
            volume. Measures volume momentum and carries no directional price information. Positive
            means volume is running above its longer average. Hard floor at -100 since volumes are
            non-negative; no ceiling. The literature warns it is choppy because volume does not
            trend, which makes divergence analysis unreliable here
        pvo_signal [percent, -100..inf] "Signal Line":
            EMA of pvo over window_sign
        pvo_hist [percent, -inf..inf] "PVO Histogram":
            pvo minus pvo_signal. Unbounded either way, being a difference of two bounded-below
            series

    Interpretation:
        - Positive PVO: Short-term volume above average
        - Negative PVO: Short-term volume below average
        - Crossovers indicate volume momentum shifts
        - Confirms price breakouts with volume expansion

    Applications:
        - Validating breakouts and support/resistance breaks on volume participation
        - Confirming price moves rather than generating standalone entries
        - Identifying volume surges and contractions against a moving-average baseline
        - Comparing volume-momentum magnitude across securities, which the percentage form permits

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
    """Indicator: MOM

    Absolute price change over a lookback window: MOM = close - close[-n]. Distinct from ROC which
    expresses the same change as a percentage.

    Abbreviation: MOM
    Warmup: window

    Formula:
        MOM = close - close[n bars ago]

        The absolute-difference form. Note two other quantities also travel under the
        name 'Momentum': the percent form (this corpus's ROC) and a ratio form,
        close/close[n] * 100, which is centred on 100 rather than 0.

    Inputs:
        close: closing price

    Params:
        window [default=10, min=1, max=200]: Lookback period

    Outputs:
        mom [price, -inf..inf] "Momentum":
            absolute price difference over window: close - close_n. Same zero crossings as ROC --
            they differ only in scale, not in signal timing. Unbounded both ways and in PRICE UNITS,
            so no conventional threshold band exists, unlike ROC's. Beware a three-way name
            collision: 'Momentum' also denotes the percent form (this corpus's ROC) and a ratio form
            centred on 100 rather than 0; this is the difference form

    Interpretation:
        - Positive while an uptrend is sustained, negative while a downtrend is
        - Zero crossings are identical to ROC's -- the two differ in scale, not in signal timing
        - Magnitude shows trend strength, but in price units, so it is not comparable across
        instruments
        - Equivalent to the slope of an SMA: MOM/(n+1) is the bar-to-bar change in the SMA
        - Unbounded, which makes overbought/oversold reading impractical unlike RSI or Stochastic

    Applications:
        - Zero-line crossovers as entry and exit triggers
        - Trend-strength gauge from the magnitude
        - Peak and trough reversal signals
        - Reading SMA turning points without plotting the SMA

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
    """Indicator: BOP

    Measures buying vs. selling pressure within a single bar: BOP = (close - open) / (high - low)
    Returns a value in [-1, 1] where positive = buyers in control, negative = sellers. NaN where
    high == low (no intrabar range). SMOOTHING: this is the RAW single-bar series, which the
    literature does not use directly. Livshin writes "I typically plot a 14-day moving average of
    the balance of power indicator", and TradingView notes the raw series is "quite choppy". Every
    source plots a 14-period moving average of it. A consumer wanting the indicator as published
    must smooth this themselves.

    Abbreviation: BOP
    Warmup: 0

    Formula:
        BOP = (Close - Open) / (High - Low)

        Single bar, no lookback. Algebraically identical to Livshin's original
        six-term Balance of Market Power construction. Normally plotted as a
        14-period moving average of this raw value.

    Inputs:
        open: opening price of the bar
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        bop [ratio, -1..1] "Balance of Power":
            (close - open) / (high - low) on a single bar -- no lookback and no parameters.
            Hard-bounded -1..1 because open and close both lie within the bar's range; +1 means the
            bar opened at its low and closed at its high. Emitted RAW here; the literature normally
            plots a 14-period moving average of it, and the raw series is very noisy. NaN on a
            zero-range bar. Algebraically identical to Livshin's original six-term Balance of Market
            Power construction

    Interpretation:
        - Positive: buyers in control (close above open); negative: sellers in control
        - Near zero: balance between buyers and sellers
        - Forms v-shaped tops and bottoms rather than meandering at extremes
        - The level at which its extremes cluster is regime-dependent, so overbought/oversold levels
        are security-specific, not fixed
        - A change in BOP trend is a warning that should be confirmed by a change in price trend
        - The raw single-bar series is very noisy and is normally smoothed

    Applications:
        - Zero-line crossover signals
        - Trend identification via the smoothed line
        - Price/BOP divergence
        - Trendline breaks on the indicator confirmed by a longer-period BOP
        - Security-specific overbought/oversold levels

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


# APO (Absolute Price Oscillator) was removed here. It computed
# `EMA(close, window_fast) - EMA(close, window_slow)`, which is the MACD line: verified
# byte-identical to `MACD.macd`, maximum difference 0.00e+00 across 400 bars -- the same series, not
# an approximation. The literature agrees this is expected rather than a coincidence (LuxAlgo calls
# APO "the MACD line under another name"; Fidelity frames MACD as APO with the periods and average
# type pinned; StockCharts has no APO page at all), and APO is also the one member of the MACD
# family where sources disagree on both the moving-average type and the default periods.
#
# The corpus was presenting one measurement as two independent indicators, which double-counts under
# anything that ranks or selects over indicators. Use `MACD` and read its `macd` output. The four
# `apo_*` signals are now `macd_line_*` in signals/momentum.py, unchanged in behaviour.


class CMO(IndicatorInterface):
    """Indicator: CMO

    Similar in spirit to RSI but uses the raw sum of gains and losses rather than smoothed averages.
    Ranges from -100 (strongest down) to +100 (strongest up), with 0 as neutral.

    Abbreviation: CMO
    Warmup: window - 1

    Formula:
        Su = SUM of up-move magnitudes over n periods
        Sd = SUM of down-move magnitudes over n periods

        CMO = 100 * (Su - Sd) / (Su + Sd)

        Default period contested: 20 (Fidelity, TradingView) or 9 (secondary sources)

    Inputs:
        close: closing price

    Params:
        window [default=14, min=2, max=100]: CMO lookback

    Outputs:
        cmo [dimensionless, -100..100] "CMO":
            100 * (sum of up-moves - sum of down-moves) / (sum of up-moves + sum of down-moves) over
            window, using unsmoothed sums of close-to-close differences. Hard-bounded -100..100
            because both sums are non-negative, so the numerator's magnitude cannot exceed the
            denominator; the endpoints are attained by an all-up or all-down window. Unsmoothed by
            design, so it signals more often than RSI. +/-50 are conventional thresholds. NaN when
            price does not move at all across the window

    Interpretation:
        - Positive: net upward momentum over the window; negative: net downward
        - Above +50 overbought, below -50 oversold (conventional levels)
        - Absolute magnitude measures trend strength -- low absolute values indicate sideways
        trading
        - Unsmoothed by construction, so it signals more frequently than RSI
        - Divergence against price flags possible reversals

    Applications:
        - Overbought/oversold timing at +/-50
        - Trend-strength and choppiness filtering via |CMO|
        - Signal-line crossover entries (9- or 10-period MA of CMO)
        - Divergence-based reversal anticipation
        - Pattern and trendline analysis drawn on the oscillator itself

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
