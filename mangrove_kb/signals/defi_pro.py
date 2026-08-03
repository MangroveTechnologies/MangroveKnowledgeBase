"""DeFiLlama Pro signal families.

These signals consume DeFiLlama Pro alternative-data columns (sourced via the
paid DeFiLlama API tier and surfaced through MangroveAI's /defi/* Pro routes)
alongside OHLCV. As with the on-chain signals, the CALLER is responsible for
populating the named column on the DataFrame (in MangroveAI this is done by the
eval-time fetcher); when a required column is absent or empty every signal
fails closed (returns False), exactly like the OHLCV signals.

Five families, each keyed to one Pro column:
    - token-unlock pressure   -> TokenUnlockPressure  (upcoming unlock supply as
                                 a fraction of circulating supply; higher = more
                                 dilution / sell-pressure ahead)
    - funding-rate regime     -> PerpFundingRate       (aggregated perp funding;
                                 positive = longs pay shorts)
    - ETF-flow momentum       -> EtfNetFlow            (net ETF flow, USD;
                                 positive = inflow)
    - treasury accumulation   -> TreasuryUsd           (protocol treasury value, USD)
    - lending-rate spread     -> LendingRateSpread      (borrow minus supply rate;
                                 widening = rising leverage demand)
"""
import logging

import pandas as pd

from mangrove_kb.registry import RuleRegistry

logger = logging.getLogger(__name__)


def _clean_series(df: pd.DataFrame, column: str) -> "pd.Series | None":
    """Return the named column as a float Series with NaNs dropped, or None.

    Mirrors signals/onchain.py so callers fail closed (return False) when the
    Pro column was not populated.
    """
    if column not in df.columns:
        return None
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return None
    return series


# =============================================================================
# Token-unlock pressure (DeFiLlama emissions/unlocks)
# =============================================================================

@RuleRegistry.register("token_unlock_pressure_low")
def token_unlock_pressure_low(df: pd.DataFrame, threshold: float = 0.02) -> bool:
    """
    Confirm there is little near-term unlock dilution ahead.

    Type: FILTER
    Family: none   # TODO(review)
    Requires: TokenUnlockPressure

    Args:
        df (pd.DataFrame): DataFrame with a TokenUnlockPressure column (upcoming
            unlock supply as a fraction of circulating supply, e.g. 0.05 = 5%).
        threshold (float): Maximum acceptable unlock pressure (a value of 0.02
            means 2% of circulating supply). Range: 0.005-0.25. Default: 0.02.

    Returns:
        bool: True if the latest unlock pressure is at or below ``threshold``
            (i.e. safe from a large imminent supply unlock).
    """
    series = _clean_series(df, "TokenUnlockPressure")
    if series is None:
        return False
    return float(series.iloc[-1]) <= threshold


@RuleRegistry.register("token_unlock_cliff_ahead")
def token_unlock_cliff_ahead(
    df: pd.DataFrame, window: int = 30, z_threshold: float = 2.0, min_pressure: float = 0.03
) -> bool:
    """
    Detect a large upcoming unlock cliff (supply-shock warning).

    Type: TRIGGER
    Family: none   # TODO(review)
    Requires: TokenUnlockPressure

    Args:
        df (pd.DataFrame): DataFrame with a TokenUnlockPressure column.
        window (int): Prior bars forming the rolling baseline (latest excluded).
            Range: 5-200. Default: 30.
        z_threshold (float): Std-devs above the baseline mean the latest pressure
            must reach to fire. Range: 0.5-5.0. Default: 2.0.
        min_pressure (float): Floor the latest pressure must also clear, so noise
            around a tiny baseline does not fire. Range: 0.005-0.5. Default: 0.03.

    Returns:
        bool: True if the latest unlock pressure both exceeds ``min_pressure``
            and is at least ``z_threshold`` std-devs above the prior window.
    """
    series = _clean_series(df, "TokenUnlockPressure")
    if series is None or len(series) < window + 1:
        return False

    baseline = series.iloc[-(window + 1):-1]
    last = float(series.iloc[-1])
    std = float(baseline.std())
    if std == 0 or pd.isna(std):
        return last >= min_pressure
    z = (last - float(baseline.mean())) / std
    return last >= min_pressure and z >= z_threshold


# =============================================================================
# Perp funding-rate regime (DeFiLlama perps)
# =============================================================================

@RuleRegistry.register("funding_negative_regime")
def funding_negative_regime(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check for a persistently negative funding regime (shorts pay longs).

    Type: FILTER
    Family: none   # TODO(review)
    Requires: PerpFundingRate

    Args:
        df (pd.DataFrame): DataFrame with a PerpFundingRate column.
        window (int): Number of recent bars to average. Range: 3-200. Default: 14.

    Returns:
        bool: True if the mean funding rate over the last ``window`` bars is
            negative (a contrarian-bullish crowd-positioning condition).
    """
    series = _clean_series(df, "PerpFundingRate")
    if series is None or len(series) < window:
        return False
    return float(series.iloc[-window:].mean()) < 0


@RuleRegistry.register("funding_flip_positive")
def funding_flip_positive(df: pd.DataFrame) -> bool:
    """
    Detect funding crossing from non-positive to positive on the latest bar.

    Type: TRIGGER
    Family: none   # TODO(review)
    Requires: PerpFundingRate

    Args:
        df (pd.DataFrame): DataFrame with a PerpFundingRate column.

    Returns:
        bool: True if funding was <= 0 on the prior bar and > 0 on the latest
            (leverage demand flipping long).
    """
    series = _clean_series(df, "PerpFundingRate")
    if series is None or len(series) < 2:
        return False
    return float(series.iloc[-2]) <= 0 < float(series.iloc[-1])


# =============================================================================
# ETF-flow momentum (DeFiLlama ETF flows)
# =============================================================================

@RuleRegistry.register("etf_inflow_streak")
def etf_inflow_streak(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Confirm sustained net ETF inflows.

    Type: FILTER
    Family: none   # TODO(review)
    Requires: EtfNetFlow

    Args:
        df (pd.DataFrame): DataFrame with an EtfNetFlow column (net flow, USD).
        window (int): Number of consecutive latest bars that must be positive.
            Range: 2-60. Default: 5.

    Returns:
        bool: True if net ETF flow is strictly positive on each of the last
            ``window`` bars.
    """
    series = _clean_series(df, "EtfNetFlow")
    if series is None or len(series) < window:
        return False
    return bool((series.iloc[-window:] > 0).all())


@RuleRegistry.register("etf_inflow_spike")
def etf_inflow_spike(df: pd.DataFrame, window: int = 20, z_threshold: float = 2.0) -> bool:
    """
    Detect an unusually large net ETF inflow on the latest bar.

    Type: TRIGGER
    Family: none   # TODO(review)
    Requires: EtfNetFlow

    Args:
        df (pd.DataFrame): DataFrame with an EtfNetFlow column.
        window (int): Prior bars forming the rolling baseline (latest excluded).
            Range: 5-200. Default: 20.
        z_threshold (float): Std-devs above the baseline mean to fire.
            Range: 0.5-5.0. Default: 2.0.

    Returns:
        bool: True if the latest net flow is positive and at least
            ``z_threshold`` std-devs above the preceding window.
    """
    series = _clean_series(df, "EtfNetFlow")
    if series is None or len(series) < window + 1:
        return False
    baseline = series.iloc[-(window + 1):-1]
    last = float(series.iloc[-1])
    std = float(baseline.std())
    if std == 0 or pd.isna(std):
        return False
    z = (last - float(baseline.mean())) / std
    return last > 0 and z >= z_threshold


# =============================================================================
# Treasury accumulation (DeFiLlama treasuries)
# =============================================================================

@RuleRegistry.register("treasury_growing")
def treasury_growing(df: pd.DataFrame, window: int = 14) -> bool:
    """
    Check whether the protocol treasury is growing over the window.

    Type: FILTER
    Family: none   # TODO(review)
    Requires: TreasuryUsd

    Args:
        df (pd.DataFrame): DataFrame with a TreasuryUsd column (treasury value, USD).
        window (int): Lookback for the comparison. Range: 3-200. Default: 14.

    Returns:
        bool: True if the latest treasury value is greater than it was
            ``window`` bars ago (sustainable runway / revenue retention).
    """
    series = _clean_series(df, "TreasuryUsd")
    if series is None or len(series) < window + 1:
        return False
    return float(series.iloc[-1]) > float(series.iloc[-(window + 1)])


@RuleRegistry.register("treasury_accumulation_trigger")
def treasury_accumulation_trigger(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Detect treasury value crossing above its moving average.

    Type: TRIGGER
    Family: none   # TODO(review)
    Requires: TreasuryUsd

    Args:
        df (pd.DataFrame): DataFrame with a TreasuryUsd column.
        window (int): Moving-average window. Range: 3-200. Default: 20.

    Returns:
        bool: True if treasury was at/below its MA on the prior bar and above it
            on the latest bar.
    """
    series = _clean_series(df, "TreasuryUsd")
    if series is None or len(series) < window + 1:
        return False
    ma = series.rolling(window=window).mean()
    prev, last = series.iloc[-2], series.iloc[-1]
    prev_ma, last_ma = ma.iloc[-2], ma.iloc[-1]
    if pd.isna(prev_ma) or pd.isna(last_ma):
        return False
    return prev <= prev_ma and last > last_ma


# =============================================================================
# Lending-rate spread (DeFiLlama lending/borrow rates)
# =============================================================================

@RuleRegistry.register("lending_spread_low")
def lending_spread_low(df: pd.DataFrame, threshold: float = 0.02) -> bool:
    """
    Confirm a calm lending market (narrow borrow-supply spread).

    Type: FILTER
    Family: none   # TODO(review)
    Requires: LendingRateSpread

    Args:
        df (pd.DataFrame): DataFrame with a LendingRateSpread column (borrow rate
            minus supply rate, as a decimal, e.g. 0.03 = 3%).
        threshold (float): Maximum spread to consider calm. Range: 0.001-0.5.
            Default: 0.02.

    Returns:
        bool: True if the latest spread is at or below ``threshold`` (low
            leverage demand / no funding stress).
    """
    series = _clean_series(df, "LendingRateSpread")
    if series is None:
        return False
    return float(series.iloc[-1]) <= threshold


@RuleRegistry.register("lending_spread_widening")
def lending_spread_widening(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Detect the borrow-supply spread crossing above its moving average.

    Type: TRIGGER
    Family: none   # TODO(review)
    Requires: LendingRateSpread

    Args:
        df (pd.DataFrame): DataFrame with a LendingRateSpread column.
        window (int): Moving-average window. Range: 3-200. Default: 20.

    Returns:
        bool: True if the spread was at/below its MA on the prior bar and above
            it on the latest bar (rising leverage demand).
    """
    series = _clean_series(df, "LendingRateSpread")
    if series is None or len(series) < window + 1:
        return False
    ma = series.rolling(window=window).mean()
    prev, last = series.iloc[-2], series.iloc[-1]
    prev_ma, last_ma = ma.iloc[-2], ma.iloc[-1]
    if pd.isna(prev_ma) or pd.isna(last_ma):
        return False
    return prev <= prev_ma and last > last_ma
