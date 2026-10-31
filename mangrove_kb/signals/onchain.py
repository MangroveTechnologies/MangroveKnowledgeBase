"""On-chain trading signals.

Signal functions based on on-chain data feeds that Mangrove exposes through its
API (Nansen smart-money + token analytics and WhaleAlert transaction flows).
Unlike the price/volume signals in the other modules, these consume
alternative-data columns alongside (or instead of) OHLCV.

The caller is responsible for populating these columns on the DataFrame,
time-aligned to the same bars as OHLCV -- exactly the way OHLCV itself is
supplied. The MangroveAI data layer derives them from Nansen's tgm/flows
(hourly per-wallet-category series) and historical-top-holders. Each value is
the metric for that bar:

    SmartMoneyNetflow   Per-bar net USD flow of smart-money wallets into the
                        token (Δ holdings × price). Positive = net accumulation.
                        (Nansen tgm/flows, label=smart_money.)
    SmartMoneyHoldings  Aggregate USD held by smart-money wallets, level per bar.
                        (Nansen tgm/flows, label=smart_money, value_usd.)
    ExchangeNetflow     Per-bar net USD flow INTO exchanges. Positive = inflow
                        (potential sell pressure); negative = outflow (coins
                        leaving exchanges, typically bullish).
                        (Nansen tgm/flows, label=exchange.)
    WhaleNetInflow      Per-bar net whale flow. Positive = whale accumulation.
                        (Nansen tgm/flows, label=whale.)
    HolderConcentration Share of supply held by the top holders, 0.0-1.0.
                        Higher = more concentrated (higher dump risk).
                        (Nansen historical-top-holders, sum of top-N ownership.)

See docs/data-providers.mdx for the upstream provider coverage map and how a
series is fetched and time-aligned to OHLCV bars.

Holder-distribution columns (Cambrian /solana/tokens/holder-distribution-over-time,
through MangroveRoots; Solana tokens only), read through `OnchainChange`:

    HolderCount         wallets holding the token (all USD bands), per snapshot.
    WhaleHeldShare      share of USD held by $100,000+ wallets, 0.0-1.0.

Nansen exposes no clean total-holders series; Cambrian's holder distribution does,
which is what `holder_growth_trend` reads. USD bands move with price (a falling
price pushes wallets into smaller bands), so the holder signals use counts and a
share of USD held, which largely cancel price.
"""

import logging

import pandas as pd

from mangrove_kb.indicators import ROC, OnchainChange
from mangrove_kb.registry import RuleRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================

def _clean_series(df: pd.DataFrame, column: str) -> "pd.Series | None":
    """Return the named column as a float Series with NaNs dropped.

    Returns None if the column is absent or has no usable values, so callers
    can fail closed (return False) the same way the OHLCV signals do.
    """
    if column not in df.columns:
        return None
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return None
    return series


# =============================================================================
# Smart-money signals (Nansen)
# =============================================================================

@RuleRegistry.register("smart_money_inflow_spike")
def smart_money_inflow_spike(df: pd.DataFrame, window: int = 20, z_threshold: float = 2.0) -> bool:
    """
    Detect an unusually large smart-money inflow on the latest bar.

    Type: TRIGGER
    Requires: SmartMoneyNetflow

    Args:
        df (pd.DataFrame): DataFrame with a SmartMoneyNetflow column.
        window (int): Number of prior bars forming the rolling baseline (the
            latest bar is excluded from its own baseline). Range: 5-200. Default: 20.
        z_threshold (float): How many standard deviations above the baseline
            mean the latest inflow must be to fire. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if the latest net inflow is positive and at least
            z_threshold standard deviations above the mean of the preceding
            window bars.
    """
    series = _clean_series(df, "SmartMoneyNetflow")
    if series is None or len(series) < window + 1:
        return False

    baseline = series.iloc[-(window + 1):-1]  # the window bars BEFORE the latest
    last = float(series.iloc[-1])
    std = float(baseline.std())
    if std == 0 or pd.isna(std):
        return False

    z = (last - float(baseline.mean())) / std
    return last > 0 and z >= z_threshold


@RuleRegistry.register("smart_money_holdings_cross")
def smart_money_holdings_cross(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Detect smart-money holdings crossing above their moving average.

    Type: TRIGGER
    Requires: SmartMoneyHoldings

    Args:
        df (pd.DataFrame): DataFrame with a SmartMoneyHoldings column.
        window (int): Moving-average window for the holdings baseline.
            Range: 3-200. Default: 20.

    Returns:
        bool: True if holdings were at/below their moving average on the prior
            bar and are above it on the latest bar.
    """
    series = _clean_series(df, "SmartMoneyHoldings")
    if series is None or len(series) < window + 1:
        return False

    ma = series.rolling(window=window).mean()
    prev, last = series.iloc[-2], series.iloc[-1]
    prev_ma, last_ma = ma.iloc[-2], ma.iloc[-1]
    if pd.isna(prev_ma) or pd.isna(last_ma):
        return False

    return prev <= prev_ma and last > last_ma


@RuleRegistry.register("smart_money_net_positive")
def smart_money_net_positive(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check whether smart money has been a net buyer over the window.

    Type: FILTER
    Requires: SmartMoneyNetflow

    Args:
        df (pd.DataFrame): DataFrame with a SmartMoneyNetflow column.
        window (int): Number of bars to sum. Range: 2-200. Default: 14.

    Returns:
        bool: True if the summed net inflow over the window is positive.
    """
    series = _clean_series(df, "SmartMoneyNetflow")
    if series is None or len(series) < window:
        return False

    return float(series.iloc[-window:].sum()) > 0


@RuleRegistry.register("smart_money_holdings_rising")
def smart_money_holdings_rising(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check whether smart-money holdings are higher than window bars ago.

    Type: FILTER
    Requires: SmartMoneyHoldings

    Args:
        df (pd.DataFrame): DataFrame with a SmartMoneyHoldings column.
        window (int): Lookback for the comparison. Range: 2-200. Default: 14.

    Returns:
        bool: True if the latest holdings exceed the value window bars ago.
    """
    series = _clean_series(df, "SmartMoneyHoldings")
    if series is None or len(series) < window + 1:
        return False

    return float(series.iloc[-1]) > float(series.iloc[-1 - window])


# =============================================================================
# Exchange-flow signals (Nansen tgm/flows label=exchange; WhaleAlert fallback)
# =============================================================================

@RuleRegistry.register("exchange_outflow_spike")
def exchange_outflow_spike(df: pd.DataFrame, window: int = 20, z_threshold: float = 2.0) -> bool:
    """
    Detect an unusually large net outflow from exchanges on the latest bar.

    Coins leaving exchanges reduce immediately sellable supply and are
    typically read as bullish.

    Type: TRIGGER
    Requires: ExchangeNetflow

    Args:
        df (pd.DataFrame): DataFrame with an ExchangeNetflow column (positive
            = inflow to exchanges, negative = outflow).
        window (int): Number of prior bars forming the rolling baseline (the
            latest bar is excluded from its own baseline). Range: 5-200. Default: 20.
        z_threshold (float): How many standard deviations below the baseline
            mean the latest flow must be to fire. Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if the latest flow is a net outflow (negative) and at least
            z_threshold standard deviations below the mean of the preceding
            window bars.
    """
    series = _clean_series(df, "ExchangeNetflow")
    if series is None or len(series) < window + 1:
        return False

    baseline = series.iloc[-(window + 1):-1]  # the window bars BEFORE the latest
    last = float(series.iloc[-1])
    std = float(baseline.std())
    if std == 0 or pd.isna(std):
        return False

    z = (last - float(baseline.mean())) / std
    return last < 0 and z <= -z_threshold


@RuleRegistry.register("exchange_net_outflow")
def exchange_net_outflow(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check whether exchanges saw net outflows over the window.

    Type: FILTER
    Requires: ExchangeNetflow

    Args:
        df (pd.DataFrame): DataFrame with an ExchangeNetflow column.
        window (int): Number of bars to sum. Range: 2-200. Default: 14.

    Returns:
        bool: True if the summed exchange flow over the window is negative
            (more leaving exchanges than entering).
    """
    series = _clean_series(df, "ExchangeNetflow")
    if series is None or len(series) < window:
        return False

    return float(series.iloc[-window:].sum()) < 0


# =============================================================================
# Whale-flow signals (Nansen tgm/flows label=whale; WhaleAlert fallback)
# =============================================================================

@RuleRegistry.register("whale_accumulation_trigger")
def whale_accumulation_trigger(df: pd.DataFrame, window: int = 7) -> bool:
    """
    Detect whale net flow flipping to accumulation.

    Type: TRIGGER
    Requires: WhaleNetInflow

    Args:
        df (pd.DataFrame): DataFrame with a WhaleNetInflow column.
        window (int): Smoothing window for the net-flow moving average.
            Range: 2-100. Default: 7.

    Returns:
        bool: True if the smoothed whale net inflow was at/below zero on the
            prior bar and is positive on the latest bar.
    """
    series = _clean_series(df, "WhaleNetInflow")
    if series is None or len(series) < window + 1:
        return False

    ma = series.rolling(window=window).mean()
    prev_ma, last_ma = ma.iloc[-2], ma.iloc[-1]
    if pd.isna(prev_ma) or pd.isna(last_ma):
        return False

    return prev_ma <= 0 and last_ma > 0


@RuleRegistry.register("whale_net_accumulation")
def whale_net_accumulation(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check whether whales were net accumulators over the window.

    Type: FILTER
    Requires: WhaleNetInflow

    Args:
        df (pd.DataFrame): DataFrame with a WhaleNetInflow column.
        window (int): Number of bars to sum. Range: 2-200. Default: 14.

    Returns:
        bool: True if the summed whale net inflow over the window is positive.
    """
    series = _clean_series(df, "WhaleNetInflow")
    if series is None or len(series) < window:
        return False

    return float(series.iloc[-window:].sum()) > 0


# =============================================================================
# Holder-distribution signals (Nansen historical-top-holders)
# =============================================================================

@RuleRegistry.register("holder_concentration_low")
def holder_concentration_low(df: pd.DataFrame, threshold: float = 0.5) -> bool:
    """
    Check whether top-holder concentration is below a threshold.

    Lower concentration means supply is more widely distributed and less
    exposed to a single-wallet dump.

    Type: FILTER
    Requires: HolderConcentration

    Args:
        df (pd.DataFrame): DataFrame with a HolderConcentration column (0.0-1.0).
        threshold (float): Maximum acceptable top-holder share. Range: 0.0-1.0.
            Default: 0.5.

    Returns:
        bool: True if the latest concentration is below the threshold.
    """
    series = _clean_series(df, "HolderConcentration")
    if series is None:
        return False

    return float(series.iloc[-1]) < threshold


@RuleRegistry.register("holder_concentration_falling")
def holder_concentration_falling(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check whether top-holder concentration is declining over the window.

    Type: FILTER
    Requires: HolderConcentration

    Args:
        df (pd.DataFrame): DataFrame with a HolderConcentration column (0.0-1.0).
        window (int): Lookback for the comparison. Range: 2-200. Default: 14.

    Returns:
        bool: True if the latest concentration is below the value window bars ago.
    """
    series = _clean_series(df, "HolderConcentration")
    if series is None or len(series) < window + 1:
        return False

    return float(series.iloc[-1]) < float(series.iloc[-1 - window])


# =============================================================================
# Holder distribution (OnchainChange, ROC)
# =============================================================================

@RuleRegistry.register("holder_growth_trend")
def holder_growth_trend(df: pd.DataFrame, window: int = 14, min_growth_pct: float = 1.0) -> bool:
    """Signal: holder_growth_trend

    Check whether the token's holder base is growing (adoption filter).

    Friendly-Name: Holder Base Growing
    Display-Name: Holder Growth Trend
    Short-Description: More wallets hold the token than a few weeks ago.

    Warmup: window

    Formula:
        pct_change(HolderCount, window)[t] >= min_growth_pct

    Inputs:
        HolderCount: wallets holding the token, per bar

    Params:
        window [default=14, min=2, max=180]: readings between the two holder counts compared
        min_growth_pct [default=1.0, min=0.0, max=50.0]: minimum percentage growth in holders over window

    Outputs:
        fired [boolean, 0..1]:
            True if the holder count grew at least min_growth_pct percent over the last window
            readings

    Type: FILTER
    Requires: HolderCount

    Args:
        df (pd.DataFrame): DataFrame with a HolderCount column.
        window (int): Readings between the two holder counts compared. Range: 2-180. Default: 14.
        min_growth_pct (float): Minimum percentage growth in holders over window. Range: 0.0-50.0. Default: 1.0.

    Returns:
        bool: True if the holder count grew at least min_growth_pct percent over the last
            window readings.
    """
    if len(df) < window + 1:
        return False
    series = _clean_series(df, "HolderCount")
    if series is None:
        return False
    growth = OnchainChange.compute(data={'value': series}, params={'window': window})['pct_change'].iloc[-1]
    return not pd.isna(growth) and float(growth) >= min_growth_pct


@RuleRegistry.register("whale_share_divergence")
def whale_share_divergence(df: pd.DataFrame, window: int = 7, min_drop_pct: float = 5.0,
                           min_share_rise: float = 0.0) -> bool:
    """Signal: whale_share_divergence

    Detect large holders gaining share of the supply value while price falls.

    Friendly-Name: Whales Buying the Drop
    Display-Name: Whale Share Divergence
    Short-Description: Price fell while large wallets held a bigger share.

    Warmup: window

    Formula:
        roc(close, window)[t] <= -min_drop_pct AND change(WhaleHeldShare, window)[t] > min_share_rise

    Inputs:
        close: closing price
        WhaleHeldShare: share of USD held by $100,000+ wallets per bar, 0-1

    Params:
        window [default=7, min=2, max=60]: bars over which price and share changes are measured
        min_drop_pct [default=5.0, min=1.0, max=50.0]: minimum percentage fall in close over window
        min_share_rise [default=0.0, min=0.0, max=0.2]: minimum rise in WhaleHeldShare over window, in share points

    Outputs:
        fired [boolean, 0..1]:
            True if close fell at least min_drop_pct over window bars while the share of USD held by
            $100,000+ wallets rose by more than min_share_rise

    Type: TRIGGER
    Requires: close, WhaleHeldShare

    Args:
        df (pd.DataFrame): DataFrame with close and WhaleHeldShare columns.
        window (int): Bars over which price and share changes are measured. Range: 2-60. Default: 7.
        min_drop_pct (float): Minimum percentage fall in close over window. Range: 1.0-50.0. Default: 5.0.
        min_share_rise (float): Minimum rise in WhaleHeldShare over window (absolute, 0-1 scale). Range: 0.0-0.2. Default: 0.0.

    Returns:
        bool: True if close fell at least min_drop_pct over window bars while the share of
            USD held by $100,000+ wallets rose by more than min_share_rise. A falling price
            mechanically pushes whales below the band threshold, so a rising share is against
            that drift.
    """
    if len(df) < window + 1:
        return False
    close = _clean_series(df, "close")
    share = _clean_series(df, "WhaleHeldShare")
    if close is None or share is None:
        return False
    drop = ROC.compute(data={'close': close}, params={'window': window})['roc'].iloc[-1]
    rise = OnchainChange.compute(data={'value': share}, params={'window': window})['change'].iloc[-1]
    if pd.isna(drop) or pd.isna(rise):
        return False
    return float(drop) <= -min_drop_pct and float(rise) > min_share_rise
