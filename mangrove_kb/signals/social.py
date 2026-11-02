"""Social trading signals.

Signals over per-bar social readings, built on the social indicators
(`mangrove_kb.indicators.social_indicators`) and, for price legs, `ROC`. Like the
on-chain signals they consume alternative-data columns alongside OHLCV: the CALLER
populates them on the DataFrame, aligned to the bars without lookahead (a bucket's
value is attached only once the bucket has closed). When a required column is absent
or too short every signal fails closed (returns False).

Columns (sourced today from Cambrian Deep42 per-token buckets through MangroveRoots;
in MangroveAI the eval-time fetcher populates them):

    SocialSentiment     average post sentiment, 0-10 (5 = neutral)
    SocialBullShare     share of posts scored bullish or very bullish, 0-1
    SocialBearShare     share of posts scored bearish, 0-1
    SocialNetBullShare  SocialBullShare - SocialBearShare, -1 to 1
    SocialTweets        posts in the bucket (collection volume changed in early 2026,
                        so signals use z-scores and shares rather than raw counts)
    SocialAuthors       unique authors in the bucket
    XPostCount          X posts matching the asset's cashtag query in the bar
                        (``$SYM -is:retweet -is:nullcast`` by default), from X's
                        counts endpoints. MangroveAI fills it on demand from its
                        cache; the bar decided at t sees only buckets that ended
                        (plus an ingest lag) by t, so on 1h bars it is the previous
                        hour. The ``x_query`` param names the query variant the
                        data layer counts; the signals themselves do not read it.

OHLCV columns arrive lowercase (the registry canonicalizes them).
"""

import numpy as np
import pandas as pd

from mangrove_kb.indicators import ROC, SocialBaselineShift, SocialZScore
from mangrove_kb.registry import RuleRegistry


def _series(df: pd.DataFrame, column: str) -> "pd.Series | None":
    """Column as float with NaNs dropped, or None when absent or empty."""
    if column not in df.columns:
        return None
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    return None if s.empty else s


def _last(s: pd.Series) -> "float | None":
    v = s.iloc[-1]
    return None if pd.isna(v) else float(v)


# =============================================================================
# Sentiment surge and capitulation (SocialZScore)
# =============================================================================

@RuleRegistry.register("social_sentiment_surge")
def social_sentiment_surge(df: pd.DataFrame, window: int = 30, z_threshold: float = 2.0, min_authors: int = 20) -> bool:
    """Signal: social_sentiment_surge

    Detect an unusually bullish social-sentiment reading on the latest bar.

    Friendly-Name: Sentiment Surge
    Display-Name: Social Sentiment Surge
    Short-Description: The crowd is far more bullish than usual today.

    Warmup: window

    Formula:
        zscore(SocialSentiment, window)[t] >= z_threshold AND SocialAuthors[t] >= min_authors

    Inputs:
        SocialSentiment: average post sentiment per bar, 0-10
        SocialAuthors: unique authors behind each bar's reading

    Params:
        window [default=30, min=7, max=180]: prior readings forming the baseline (latest excluded)
        z_threshold [default=2.0, min=0.5, max=5.0]: standard deviations above the baseline mean required
        min_authors [default=20, min=1, max=1000]: minimum unique authors behind the latest reading

    Outputs:
        fired [boolean, 0..1]:
            True if the latest sentiment is at least z_threshold standard deviations above the prior
            window and enough authors contributed

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
    if len(df) < window + 1:
        return False
    sent = _series(df, "SocialSentiment")
    authors = _series(df, "SocialAuthors")
    if sent is None or authors is None:
        return False
    z = _last(SocialZScore.compute(data={'value': sent}, params={'window': window})['zscore'])
    return z is not None and z >= z_threshold and float(authors.iloc[-1]) >= min_authors


@RuleRegistry.register("social_sentiment_capitulation")
def social_sentiment_capitulation(df: pd.DataFrame, window: int = 30, z_threshold: float = 2.0, min_authors: int = 20) -> bool:
    """Signal: social_sentiment_capitulation

    Detect an unusually bearish social-sentiment reading on the latest bar (contrarian).

    Friendly-Name: Sentiment Capitulation
    Display-Name: Social Sentiment Capitulation
    Short-Description: The crowd is far more bearish than usual today.

    Warmup: window

    Formula:
        zscore(SocialSentiment, window)[t] <= -z_threshold AND SocialAuthors[t] >= min_authors

    Inputs:
        SocialSentiment: average post sentiment per bar, 0-10
        SocialAuthors: unique authors behind each bar's reading

    Params:
        window [default=30, min=7, max=180]: prior readings forming the baseline (latest excluded)
        z_threshold [default=2.0, min=0.5, max=5.0]: standard deviations below the baseline mean required
        min_authors [default=20, min=1, max=1000]: minimum unique authors behind the latest reading

    Outputs:
        fired [boolean, 0..1]:
            True if the latest sentiment is at least z_threshold standard deviations below the prior
            window and enough authors contributed

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
    if len(df) < window + 1:
        return False
    sent = _series(df, "SocialSentiment")
    authors = _series(df, "SocialAuthors")
    if sent is None or authors is None:
        return False
    z = _last(SocialZScore.compute(data={'value': sent}, params={'window': window})['zscore'])
    return z is not None and z <= -z_threshold and float(authors.iloc[-1]) >= min_authors


# =============================================================================
# Crowd regime and divergence (SocialBaselineShift, ROC)
# =============================================================================

@RuleRegistry.register("social_crowd_bullish")
def social_crowd_bullish(df: pd.DataFrame, window: int = 7, window_baseline: int = 60, margin: float = 0.0) -> bool:
    """Signal: social_crowd_bullish

    Check whether the crowd is more bullish than usual (regime filter).

    Friendly-Name: Crowd Running Bullish
    Display-Name: Social Crowd Bullish
    Short-Description: Recent posts lean more bullish than this asset's norm.

    Warmup: window + window_baseline - 1

    Formula:
        shift(SocialNetBullShare, window, window_baseline)[t] > margin

    Inputs:
        SocialNetBullShare: bullish minus bearish share of posts per bar, -1 to 1

    Params:
        window [default=7, min=1, max=60]: recent readings averaged
        window_baseline [default=60, min=14, max=365]: readings before the recent window forming the norm
        margin [default=0.0, min=0.0, max=0.5]: amount the recent average must exceed the norm by

    Outputs:
        fired [boolean, 0..1]:
            True if the mean net bullish share over the last window readings exceeds the mean of the
            preceding window_baseline readings by more than margin

    Type: FILTER
    Requires: SocialNetBullShare

    Args:
        df (pd.DataFrame): DataFrame with a SocialNetBullShare column.
        window (int): Recent readings averaged. Range: 1-60. Default: 7.
        window_baseline (int): Readings before the recent window forming the norm. Range: 14-365. Default: 60.
        margin (float): Amount the recent average must exceed the norm by. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if the mean net bullish share over the last window readings
            exceeds the mean of the preceding window_baseline readings by more than margin.
    """
    if len(df) < window + window_baseline:
        return False
    s = _series(df, "SocialNetBullShare")
    if s is None:
        return False
    shift = _last(SocialBaselineShift.compute(
        data={'value': s}, params={'window': window, 'window_baseline': window_baseline})['shift'])
    return shift is not None and shift > margin


@RuleRegistry.register("social_price_divergence")
def social_price_divergence(df: pd.DataFrame, window: int = 7, min_drop_pct: float = 5.0, window_baseline: int = 30) -> bool:
    """Signal: social_price_divergence

    Detect a price drop that the crowd is not following (bullish divergence).

    Friendly-Name: Crowd Holds Through Drop
    Display-Name: Social Price Divergence
    Short-Description: Price fell but the crowd stayed as bullish as usual.

    Warmup: window + window_baseline - 1

    Formula:
        roc(close, window)[t] <= -min_drop_pct
        AND shift(SocialNetBullShare, window, window_baseline)[t] >= 0

    Inputs:
        close: closing price
        SocialNetBullShare: bullish minus bearish share of posts per bar, -1 to 1

    Params:
        window [default=7, min=2, max=60]: bars over which the price drop and the recent social mean are measured
        min_drop_pct [default=5.0, min=1.0, max=50.0]: minimum percentage fall in close over window
        window_baseline [default=30, min=7, max=180]: social readings before the recent window forming the norm

    Outputs:
        fired [boolean, 0..1]:
            True if close fell at least min_drop_pct over window bars while the mean net bullish
            share over the same bars stayed at or above its baseline mean

    Type: TRIGGER
    Requires: close, SocialNetBullShare

    Args:
        df (pd.DataFrame): DataFrame with close and SocialNetBullShare columns.
        window (int): Bars over which the price drop and the recent social mean are measured. Range: 2-60. Default: 7.
        min_drop_pct (float): Minimum percentage fall in close over window. Range: 1.0-50.0. Default: 5.0.
        window_baseline (int): Social readings before the recent window forming the norm. Range: 7-180. Default: 30.

    Returns:
        bool: True if close fell at least min_drop_pct over window bars while
            the mean net bullish share over the same bars stayed at or above
            its baseline mean.
    """
    if len(df) < window + window_baseline:
        return False
    close = _series(df, "close")
    s = _series(df, "SocialNetBullShare")
    if close is None or s is None:
        return False
    drop = _last(ROC.compute(data={'close': close}, params={'window': window})['roc'])
    shift = _last(SocialBaselineShift.compute(
        data={'value': s}, params={'window': window, 'window_baseline': window_baseline})['shift'])
    # tolerance: equal means can differ in the last float bit
    return drop is not None and shift is not None and drop <= -min_drop_pct and shift >= -1e-9


# =============================================================================
# X attention (XPostCount): post volume, not sentiment
# =============================================================================

def _x_counts(df: pd.DataFrame, need: int) -> "pd.Series | None":
    """XPostCount as floats over the last ``need`` bars, or None.

    Gaps are kept, not dropped: dropping one would let a "prior N bars" baseline reach
    further back than N bars. Any gap in the bars read fails closed.
    """
    if "XPostCount" not in df.columns or len(df) < need:
        return None
    s = pd.to_numeric(df["XPostCount"], errors="coerce").iloc[-need:]
    return None if s.isna().any() else s


@RuleRegistry.register("x_post_count_spike")
def x_post_count_spike(df: pd.DataFrame, window: int = 48, z_threshold: float = 3.0, min_count: int = 20,
                       x_query: str = "all") -> bool:
    """Signal: x_post_count_spike

    Detect an unusual burst of X posts about the asset on the latest bar.

    Friendly-Name: X Post Spike
    Display-Name: X Post Count Spike
    Short-Description: Far more people are posting about this asset on X than usual.

    Warmup: window

    Formula:
        zscore(log1p(XPostCount), window)[t] >= z_threshold AND XPostCount[t] >= min_count

    Inputs:
        XPostCount: X posts matching the asset's cashtag query per bar

    Params:
        window [default=48, min=6, max=365]: prior bars forming the baseline (latest excluded)
        z_threshold [default=3.0, min=1.0, max=10.0]: standard deviations of log1p(count) above the baseline mean required
        min_count [default=20, min=0, max=100000]: minimum posts on the latest bar, guarding thin assets
        x_query: X query variant the data layer counts, 'all' or 'en_original'

    Outputs:
        fired [boolean, 0..1]:
            True if the latest post count is at least min_count and its log1p is z_threshold
            standard deviations above the prior window

    Type: TRIGGER
    Requires: XPostCount

    Args:
        df (pd.DataFrame): DataFrame with an XPostCount column.
        window (int): Prior bars forming the baseline (latest excluded). Range: 6-365. Default: 48.
        z_threshold (float): Standard deviations of log1p(count) above the baseline mean required. Range: 1.0-10.0. Default: 3.0.
        min_count (int): Minimum posts on the latest bar, guarding thin assets. Range: 0-100000. Default: 20.
        x_query (str): X query variant the data layer counts. Options: all, en_original. Default: all.

    Returns:
        bool: True if the latest post count is at least min_count and its
            log1p is z_threshold standard deviations above the prior window.
    """
    s = _x_counts(df, window + 1)
    if s is None:
        return False
    z = _last(SocialZScore.compute(data={'value': np.log1p(s.clip(lower=0))}, params={'window': window})['zscore'])
    return z is not None and z >= z_threshold and float(s.iloc[-1]) >= min_count


@RuleRegistry.register("x_attention_elevated")
def x_attention_elevated(df: pd.DataFrame, window: int = 6, window_baseline: int = 72, min_ratio: float = 1.5,
                         x_query: str = "all") -> bool:
    """Signal: x_attention_elevated

    Check whether recent X attention runs above its longer baseline (regime filter).

    Friendly-Name: X Attention Elevated
    Display-Name: X Attention Elevated
    Short-Description: People have been posting about this asset on X more than usual lately.

    Warmup: window + window_baseline - 1

    Formula:
        ratio(XPostCount, window, window_baseline)[t] >= min_ratio

    Inputs:
        XPostCount: X posts matching the asset's cashtag query per bar

    Params:
        window [default=6, min=1, max=90]: recent bars averaged
        window_baseline [default=72, min=5, max=365]: bars before the recent window forming the norm
        min_ratio [default=1.5, min=1.0, max=20.0]: required ratio of the recent mean to the baseline mean
        x_query: X query variant the data layer counts, 'all' or 'en_original'

    Outputs:
        fired [boolean, 0..1]:
            True if the mean post count over the last window bars is at least min_ratio times the
            mean of the preceding window_baseline bars

    Type: FILTER
    Requires: XPostCount

    Args:
        df (pd.DataFrame): DataFrame with an XPostCount column.
        window (int): Recent bars averaged. Range: 1-90. Default: 6.
        window_baseline (int): Bars before the recent window forming the norm. Range: 5-365. Default: 72.
        min_ratio (float): Required ratio of the recent mean to the baseline mean. Range: 1.0-20.0. Default: 1.5.
        x_query (str): X query variant the data layer counts. Options: all, en_original. Default: all.

    Returns:
        bool: True if the mean post count over the last window bars is at
            least min_ratio times the mean of the preceding window_baseline bars.
    """
    s = _x_counts(df, window + window_baseline)
    if s is None:
        return False
    ratio = _last(SocialBaselineShift.compute(
        data={'value': s}, params={'window': window, 'window_baseline': window_baseline})['ratio'])
    return ratio is not None and ratio >= min_ratio


@RuleRegistry.register("x_attention_price_divergence")
def x_attention_price_divergence(df: pd.DataFrame, window_price: int = 24, min_drop_pct: float = 5.0,
                                 window: int = 72, z_threshold: float = 2.0, x_query: str = "all") -> bool:
    """Signal: x_attention_price_divergence

    Detect a price drop accompanied by an X attention spike (capitulation chatter, contrarian).

    Friendly-Name: X Capitulation Chatter
    Display-Name: X Attention Price Divergence
    Short-Description: Price fell while posts about this asset on X spiked.

    Warmup: window

    Formula:
        roc(close, window_price)[t] <= -min_drop_pct
        AND zscore(log1p(XPostCount), window)[t] >= z_threshold

    Inputs:
        close: closing price
        XPostCount: X posts matching the asset's cashtag query per bar

    Params:
        window_price [default=24, min=1, max=50]: bars over which the price drop is measured
        min_drop_pct [default=5.0, min=0.5, max=90.0]: minimum percentage fall in close over window_price
        window [default=72, min=6, max=365]: prior bars forming the attention baseline (latest excluded)
        z_threshold [default=2.0, min=0.5, max=10.0]: standard deviations of log1p(count) above the baseline mean required
        x_query: X query variant the data layer counts, 'all' or 'en_original'

    Outputs:
        fired [boolean, 0..1]:
            True if close fell at least min_drop_pct over window_price bars and the latest post
            count's log1p is z_threshold standard deviations above the prior window

    Type: TRIGGER
    Requires: close, XPostCount

    Args:
        df (pd.DataFrame): DataFrame with close and XPostCount columns.
        window_price (int): Bars over which the price drop is measured. Range: 1-50. Default: 24.
        min_drop_pct (float): Minimum percentage fall in close over window_price. Range: 0.5-90.0. Default: 5.0.
        window (int): Prior bars forming the attention baseline (latest excluded). Range: 6-365. Default: 72.
        z_threshold (float): Standard deviations of log1p(count) above the baseline mean required. Range: 0.5-10.0. Default: 2.0.
        x_query (str): X query variant the data layer counts. Options: all, en_original. Default: all.

    Returns:
        bool: True if close fell at least min_drop_pct over window_price bars
            and the latest post count's log1p is z_threshold standard
            deviations above the prior window.
    """
    s = _x_counts(df, window + 1)
    close = _series(df, "close")
    if s is None or close is None or len(close) < window_price + 1:
        return False
    drop = _last(ROC.compute(data={'close': close}, params={'window': window_price})['roc'])
    z = _last(SocialZScore.compute(data={'value': np.log1p(s.clip(lower=0))}, params={'window': window})['zscore'])
    return drop is not None and z is not None and drop <= -min_drop_pct and z >= z_threshold
