"""
Others Indicators.

Daily Return, Daily Log Return, and Cumulative Return indicators.
Adapted from ta-master library.
"""
import numpy as np
import pandas as pd

from mangrove_knowledge_base.indicators.indicator_interface import IndicatorInterface


class DailyReturn(IndicatorInterface):
    """Daily Return (DR)

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
    """Daily Log Return (DLR)

    https://stackoverflow.com/questions/31287552/logarithmic-returns-in-pandas-dataframe

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
    """Cumulative Return (CR)

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
