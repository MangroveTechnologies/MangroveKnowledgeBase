"""
Others Indicators.

Daily Return, Daily Log Return, and Cumulative Return indicators.
Adapted from ta-master library.
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface


class DailyReturn(IndicatorInterface):
    """Indicator: DailyReturn

    Indicator `DailyReturn` -- no description in source.

    Abbreviation: none
    Warmup: 1

    Formula:
        R = (close / prior close - 1) * 100

        Elementary finance quantity, not a named technical indicator. Identical to a
        1-period Rate of Change.

    Inputs:
        close: closing price

    Outputs:
        daily_return [percent, -100..inf] "simple return":
            one-bar percent change, (close / prior close - 1) * 100. HARD floor at -100 because
            prices cannot go below zero; no ceiling. Aggregates MULTIPLICATIVELY -- daily simple
            returns cannot be summed -- and is asymmetric, since a -50% move needs +100% to recover.
            It is the correct quantity for aggregating across assets at a point in time. Not a named
            technical indicator; it is the elementary finance quantity, identical to a 1-period Rate
            of Change

    Interpretation:
        - Fractional one-bar price change, scale-free and comparable across instruments
        - Sign is the bar's direction; magnitude is the move relative to the prior close
        - Aggregates MULTIPLICATIVELY across time -- daily simple returns cannot be summed
        - Asymmetric: a -50% move requires +100% to recover
        - The correct quantity for aggregating across assets at a point in time

    Applications:
        - Input to volatility, Sharpe, drawdown and other performance statistics
        - Feature and target construction for forecasting and backtesting
        - Portfolio profit-and-loss accounting and weighted aggregation across holdings
        - Bar-by-bar momentum readout

    Args:
        data: {'close': pd.Series}
        params: {}

    Returns:
        {'daily_return': pd.Series}
    """
    _data = ["close"]
    _params = []
    _outputs = ["daily_return"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']

        dr = (close / close.shift(1)) - 1
        dr *= 100

        return {'daily_return': pd.Series(dr, name="d_ret")}


class DailyLogReturn(IndicatorInterface):
    """Indicator: DailyLogReturn

    Indicator `DailyLogReturn` -- no description in source.

    Abbreviation: none
    Reference: https://stackoverflow.com/questions/31287552/logarithmic-returns-in-pandas-dataframe
    Warmup: 1

    Formula:
        r = ln(close / prior close) * 100
          = (ln(close) - ln(prior close)) * 100

        Relation to the simple return: r = ln(1 + R).
        Elementary finance quantity, not a named technical indicator.

    Inputs:
        close: closing price

    Outputs:
        daily_log_return [percent, -inf..inf] "log return":
            one-bar continuously compounded return, ln(close / prior close) * 100. UNBOUNDED IN BOTH
            DIRECTIONS -- ln maps (0, inf) onto the whole real line, which removes the -100 floor
            the simple return has. That is precisely why it is preferred for modelling: it is
            time-additive, so multi-period returns are plain sums, and symmetric, so equal up and
            down moves cancel. Undefined at a zero or negative price. Not additive across assets,
            unlike the simple return. Not a named technical indicator

    Interpretation:
        - The continuously compounded one-bar growth rate
        - TIME-ADDITIVE: a multi-period log return is the plain sum of its parts
        - SYMMETRIC: equal-magnitude up and down moves cancel exactly
        - Unbounded on the real line, which makes it compatible with Gaussian modelling assumptions
        the simple return cannot satisfy
        - Close to the simple return for small moves, diverging as the move grows
        - NOT additive across assets -- portfolio aggregation needs simple returns

    Applications:
        - Default return series for time-series and volatility modelling
        - Cumulative performance by summation, and clean horizon scaling
        - Machine-learning features and targets needing a stationary, roughly symmetric series
        - Comparing performance across horizons without compounding artefacts

    Args:
        data: {'close': pd.Series}
        params: {}

    Returns:
        {'daily_log_return': pd.Series}
    """
    _data = ["close"]
    _params = []
    _outputs = ["daily_log_return"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']

        dr = pd.Series(np.log(close)).diff()
        dr *= 100

        return {'daily_log_return': pd.Series(dr, name="d_logret")}


class CumulativeReturn(IndicatorInterface):
    """Indicator: CumulativeReturn

    Indicator `CumulativeReturn` -- no description in source.

    Abbreviation: none
    Warmup: 0

    Formula:
        CumulativeReturn[t] = (close[t] / close[0] - 1) * 100

        Equivalently, from periodic simple returns:  (PROD (1 + r_i)) - 1
        Or from log returns:                        exp(SUM z_i) - 1

        Not annualised. Contrast CAGR = (1 + CumulativeReturn)^(1/years) - 1.
        Elementary finance quantity, not a named technical indicator.

    Inputs:
        close: closing price

    Outputs:
        cumulative_return [percent, -100..inf] "Cumulative Return":
            total percent change from the FIRST BAR OF THE SUPPLIED SERIES to each bar: (close /
            close[0] - 1) * 100. Its value therefore depends entirely on where the caller's data
            slice begins -- reslicing the input rebases the whole series. HARD floor at -100 because
            prices cannot go below zero and, once a factor reaches zero, the product is absorbed
            there permanently; no ceiling. Not annualised, so two windows of different length are
            not comparable. Path-independent given the endpoints, so it says nothing about drawdown
            along the way. Not a named technical indicator -- it is the elementary finance quantity,
            also called total return, holding-period return or compounded return

    Interpretation:
        - Aggregate gain or loss since the start of the series, with compounding, independent of how
        long that took
        - Zero is breakeven; the growth-of-one-unit curve is simply 1 + this value
        - NOT time-normalised, so two windows of different length are not comparable
        - Path-independent given the endpoints -- it reveals nothing about drawdown or volatility
        along the way
        - Rebased by the caller's data slice: change where the series starts and every value changes

    Applications:
        - Headline performance figure for a backtest or portfolio over a fixed window
        - Input to annualised metrics such as CAGR
        - Equity-curve construction
        - Benchmark-relative comparison over an identical window

    Args:
        data: {'close': pd.Series}
        params: {}

    Returns:
        {'cumulative_return': pd.Series}
    """
    _data = ["close"]
    _params = []
    _outputs = ["cumulative_return"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']

        cr = (close / close.iloc[0]) - 1
        cr *= 100

        return {'cumulative_return': pd.Series(cr, name="cum_ret")}
