"""
On-Chain Indicators.

Measurements over a per-bar on-chain reading -- a holder count, a share of supply value held by
large wallets, a smart-money balance -- that the caller has aligned to the bars without lookahead.
The reading is the `value` input; which column feeds it is the signal's choice, named in that
signal's `Requires:`.
"""
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface


class OnchainChange(IndicatorInterface):
    """Indicator: OnchainChange

    How much an on-chain reading has moved over the last `window` bars, both in percent of where it
    started and in its own units. Percent suits counts (holders, transfers); the absolute change
    suits readings that are already shares or ratios (share of supply value held by whales), where a
    percent of a percent is misleading.

    Abbreviation: none
    Warmup: window

    Formula:
        change     = value[t] - value[t-window]
        pct_change = (value[t] / value[t-window] - 1) * 100     (NaN where value[t-window] <= 0)

    Inputs:
        value: per-bar on-chain reading (holder count, whale-held share, smart-money balance, ...)

    Params:
        window [default=14, min=1, max=365]: bars between the two readings compared

    Outputs:
        pct_change [percent, -100..inf] "on-chain percent change":
            percent change of the reading over `window` bars. Floor of -100 for a count that falls to
            zero; no ceiling. NaN where the starting reading is zero or negative, so it is for
            strictly positive readings
        change [input units, -inf..inf] "on-chain change":
            the reading now minus the reading `window` bars ago, in the input's own units. For a 0-1
            share this is a change in share points, the quantity to threshold

    Interpretation:
        - **Positive**: the on-chain quantity grew over the window (more holders, larger whale share)
        - **Negative**: it shrank
        - Wallet-size bands defined in USD move with price, so a falling price alone pushes wallets
          into smaller bands; a count or share that rises against a falling price moved against
          that drift

    Applications:
        - **Adoption filter**: trade only while the holder base is growing
        - **Accumulation divergence**: large holders gaining share while price falls
        - **Supply tracking**: change in mint/burn or smart-money balances over a window

    Args:
        data: {'value': pd.Series}
        params: {'window': int}

    Returns:
        {'pct_change': pd.Series, 'change': pd.Series}
    """
    _data = ["value"]
    _params = ["window"]
    _outputs = ["pct_change", "change"]

    @classmethod
    def _compute(cls, data, params):
        value = pd.to_numeric(data['value'], errors='coerce')
        window = params['window']

        start = value.shift(window)
        pct = (value / start.where(start > 0) - 1) * 100
        return {
            'pct_change': pd.Series(pct, name="onchain_pct_change"),
            'change': pd.Series(value - start, name="onchain_change"),
        }
