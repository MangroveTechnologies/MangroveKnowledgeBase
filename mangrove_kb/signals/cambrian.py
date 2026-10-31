"""Cambrian signal families: Deep42 social sentiment and Solana holder distribution.

These signals consume alternative-data columns sourced from the Cambrian API
(through MangroveRoots' Cambrian provider) alongside OHLCV. As with the on-chain
and DeFi Pro signals, the CALLER populates the named columns on the DataFrame,
time-aligned to the bars without lookahead (in MangroveAI this is the eval-time
fetcher); when a required column is absent or too short every signal fails
closed (returns False).

Social columns (Deep42 per-token buckets, attached when each bucket closes):
    SocialSentiment     average post sentiment, 0-10 (5 = neutral)
    SocialBullShare     share of posts scored bullish or very bullish, 0-1
    SocialBearShare     share of posts scored bearish, 0-1
    SocialNetBullShare  SocialBullShare - SocialBearShare, -1 to 1
    SocialTweets        posts in the bucket (collection volume changed in early
                        2026, so signals use z-scores and shares, not raw counts)
    SocialAuthors       unique authors in the bucket

Holder columns (Solana holder-distribution snapshots, attached at block time):
    HolderCount         wallets holding the token (all USD bands)
    RetailHolderCount   wallets holding under $1,000
    WhaleHolderCount    wallets holding $100,000 or more
    WhaleHeldShare      share of USD held by $100,000+ wallets, 0-1

USD bands move with price (a falling price pushes wallets into smaller bands), so
the holder signals use counts and a share of USD held, which largely cancel price.
OHLCV columns arrive lowercase (the registry canonicalizes them).
"""

import pandas as pd
from mangrove_kb.registry import RuleRegistry


def _series(df: pd.DataFrame, column: str) -> "pd.Series | None":
    """Column as float with NaNs dropped, or None when absent or empty."""
    if column not in df.columns:
        return None
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    return None if s.empty else s


def _latest_zscore(s: pd.Series, window: int) -> "float | None":
    """z-score of the latest value against the ``window`` values before it."""
    if len(s) < window + 1:
        return None
    base = s.iloc[-(window + 1):-1]
    std = float(base.std())
    if std == 0 or pd.isna(std):
        return None
    return (float(s.iloc[-1]) - float(base.mean())) / std


@RuleRegistry.register("social_sentiment_surge")
def social_sentiment_surge(df: pd.DataFrame, window: int = 30, z_threshold: float = 2.0, min_authors: int = 20) -> bool:
    """
    Detect an unusually bullish social-sentiment reading on the latest bar.

    Type: TRIGGER
    Requires: SocialSentiment, SocialAuthors

    Args:
        df (pd.DataFrame): DataFrame with SocialSentiment and SocialAuthors columns.
        window (int): Prior readings forming the baseline (latest excluded). Range: 7-180. Default: 30.
        z_threshold (float): Standard deviations above the baseline mean required. Range: 0.5-5.0. Default: 2.0.
        min_authors (int): Minimum unique authors behind the latest reading. Range: 1-1000. Default: 20.

    Returns:
        bool: True if the latest sentiment is at least z_threshold standard
            deviations above the prior window and enough authors contributed.
    """
    sent = _series(df, "SocialSentiment")
    authors = _series(df, "SocialAuthors")
    if sent is None or authors is None:
        return False
    z = _latest_zscore(sent, window)
    return z is not None and z >= z_threshold and float(authors.iloc[-1]) >= min_authors


@RuleRegistry.register("social_sentiment_capitulation")
def social_sentiment_capitulation(df: pd.DataFrame, window: int = 30, z_threshold: float = 2.0, min_authors: int = 20) -> bool:
    """
    Detect an unusually bearish social-sentiment reading on the latest bar (contrarian).

    Type: TRIGGER
    Requires: SocialSentiment, SocialAuthors

    Args:
        df (pd.DataFrame): DataFrame with SocialSentiment and SocialAuthors columns.
        window (int): Prior readings forming the baseline (latest excluded). Range: 7-180. Default: 30.
        z_threshold (float): Standard deviations below the baseline mean required. Range: 0.5-5.0. Default: 2.0.
        min_authors (int): Minimum unique authors behind the latest reading. Range: 1-1000. Default: 20.

    Returns:
        bool: True if the latest sentiment is at least z_threshold standard
            deviations below the prior window and enough authors contributed.
    """
    sent = _series(df, "SocialSentiment")
    authors = _series(df, "SocialAuthors")
    if sent is None or authors is None:
        return False
    z = _latest_zscore(sent, window)
    return z is not None and z <= -z_threshold and float(authors.iloc[-1]) >= min_authors


@RuleRegistry.register("social_crowd_bullish")
def social_crowd_bullish(df: pd.DataFrame, window: int = 7, baseline: int = 60, margin: float = 0.0) -> bool:
    """
    Check whether the crowd is more bullish than usual (regime filter).

    Type: FILTER
    Requires: SocialNetBullShare

    Args:
        df (pd.DataFrame): DataFrame with a SocialNetBullShare column.
        window (int): Recent readings averaged. Range: 1-60. Default: 7.
        baseline (int): Readings before the recent window forming the norm. Range: 14-365. Default: 60.
        margin (float): Amount the recent average must exceed the norm by. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if the mean net bullish share over the last window readings
            exceeds the mean of the preceding baseline readings by more than margin.
    """
    s = _series(df, "SocialNetBullShare")
    if s is None or len(s) < window + baseline:
        return False
    recent = float(s.iloc[-window:].mean())
    norm = float(s.iloc[-(window + baseline):-window].mean())
    return recent > norm + margin


@RuleRegistry.register("social_price_divergence")
def social_price_divergence(df: pd.DataFrame, lookback: int = 7, min_drop_pct: float = 5.0, baseline: int = 30) -> bool:
    """
    Detect a price drop that the crowd is not following (bullish divergence).

    Type: TRIGGER
    Requires: close, SocialNetBullShare

    Args:
        df (pd.DataFrame): DataFrame with close and SocialNetBullShare columns.
        lookback (int): Bars over which the price drop is measured. Range: 2-60. Default: 7.
        min_drop_pct (float): Minimum percentage fall in close over lookback. Range: 1.0-50.0. Default: 5.0.
        baseline (int): Social readings before the lookback forming the norm. Range: 7-180. Default: 30.

    Returns:
        bool: True if close fell at least min_drop_pct over lookback bars while
            the mean net bullish share over the same bars stayed at or above
            its baseline mean.
    """
    close = _series(df, "close")
    s = _series(df, "SocialNetBullShare")
    if close is None or s is None or len(close) < lookback + 1 or len(s) < lookback + baseline:
        return False
    drop_pct = (float(close.iloc[-1]) / float(close.iloc[-(lookback + 1)]) - 1) * 100
    recent = float(s.iloc[-lookback:].mean())
    norm = float(s.iloc[-(lookback + baseline):-lookback].mean())
    return drop_pct <= -min_drop_pct and recent >= norm - 1e-9  # tolerance: equal means differ in float


# =============================================================================
# On-chain holder signals (Cambrian /solana/tokens/holder-distribution-over-time)
#
# Columns from MangroveAI.domains.signal_builder.series.holder_cohorts:
#   HolderCount     wallets holding the token (all USD bands)
#   WhaleHeldShare  share of USD held by $100,000+ wallets, 0-1
# USD bands move with price (a falling price pushes wallets into smaller bands),
# so these signals use counts and a share of USD held, which largely cancel price.
# =============================================================================

@RuleRegistry.register("holder_growth_trend")
def holder_growth_trend(df: pd.DataFrame, window: int = 14, min_growth_pct: float = 1.0) -> bool:
    """
    Check whether the token's holder base is growing (adoption filter).

    Type: FILTER
    Requires: HolderCount

    Args:
        df (pd.DataFrame): DataFrame with a HolderCount column.
        window (int): Readings over which growth is measured. Range: 3-90. Default: 14.
        min_growth_pct (float): Minimum percentage growth in holders over the window. Range: 0.0-50.0. Default: 1.0.

    Returns:
        bool: True if HolderCount grew by at least min_growth_pct over the last
            window readings.
    """
    s = _series(df, "HolderCount")
    if s is None or len(s) < window + 1 or float(s.iloc[-(window + 1)]) <= 0:
        return False
    growth_pct = (float(s.iloc[-1]) / float(s.iloc[-(window + 1)]) - 1) * 100
    return growth_pct >= min_growth_pct


@RuleRegistry.register("whale_share_divergence")
def whale_share_divergence(df: pd.DataFrame, lookback: int = 7, min_drop_pct: float = 5.0,
                           min_share_rise: float = 0.0) -> bool:
    """
    Detect large holders gaining share of the supply value while price falls.

    Type: TRIGGER
    Requires: close, WhaleHeldShare

    Args:
        df (pd.DataFrame): DataFrame with close and WhaleHeldShare columns.
        lookback (int): Bars over which price and share changes are measured. Range: 2-60. Default: 7.
        min_drop_pct (float): Minimum percentage fall in close over lookback. Range: 1.0-50.0. Default: 5.0.
        min_share_rise (float): Minimum rise in WhaleHeldShare over lookback (absolute, 0-1 scale). Range: 0.0-0.2. Default: 0.0.

    Returns:
        bool: True if close fell at least min_drop_pct over lookback bars while
            the share of USD held by $100,000+ wallets rose by more than
            min_share_rise. A falling price mechanically pushes whales below the
            band threshold, so a rising share is against that drift.
    """
    close = _series(df, "close")
    share = _series(df, "WhaleHeldShare")
    if close is None or share is None or len(close) < lookback + 1 or len(share) < lookback + 1:
        return False
    drop_pct = (float(close.iloc[-1]) / float(close.iloc[-(lookback + 1)]) - 1) * 100
    share_rise = float(share.iloc[-1]) - float(share.iloc[-(lookback + 1)])
    return drop_pct <= -min_drop_pct and share_rise > min_share_rise
