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

The five live X rules below preserve their existing parameter and score contracts.
They read the provider configured by the consuming application at evaluation time,
not a historical bar. They are active live signals; historical callers must use
``RuleRegistry.validate_evaluation_mode(rule, "historical")`` before a replay.

OHLCV columns arrive lowercase (the registry canonicalizes them).
"""

import logging

import numpy as np
import pandas as pd

from mangrove_kb.indicators import ROC, SocialBaselineShift, SocialZScore
from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import deprecated_signal


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
@deprecated_signal(
    "it lost money against a price-filtered reference in strategy backtests, so it is disabled for "
    "new strategies and not in the ontology graph; stored strategies that name it keep evaluating"
)
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
    Disabled: True
    Disabled-Reason: In Oracle engine strategy backtests on BTC, ETH, SOL, XRP, DOGE, BNB and LINK (daily bars, platform default execution config, every strategy one entry trigger plus a price filter, settings chosen on 2025-04-01 to 2026-01-31 and reported untouched on 2026-02-01 to 2026-11-01), no surge variant beat rsi_cross_up with is_above_sma (5.12% selection, 3.25% holdout); 0 of 30 qualified as entry, exit or filter. As an entry with is_above_sma it made 1.52% and 0.52%. It buys after the run-up: entries followed a median +6.2% week and 55% hit the stop. As an exit it closed uptrend trades early: 11 of the 17 it closed would have reached the 2R target. Stored strategies that name this signal keep evaluating.

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
@deprecated_signal(
    "it lost money against a price-filtered reference in strategy backtests, so it is disabled for "
    "new strategies and not in the ontology graph; stored strategies that name it keep evaluating"
)
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
    Disabled: True
    Disabled-Reason: In Oracle engine strategy backtests on BTC, ETH, SOL, XRP, DOGE, BNB and LINK (daily bars, platform default execution config, every strategy one entry trigger plus a price filter, settings chosen on 2025-04-01 to 2026-01-31 and reported untouched on 2026-02-01 to 2026-11-01), no capitulation variant beat rsi_cross_up with is_above_sma (5.12% selection, 3.25% holdout); 0 of 29 qualified as entry, exit or no-entry filter. As an entry it buys falling knives: 76 of 101 unfiltered entries were below the 20-day SMA after a median -5.3% week (-7.6 USDT per trade, 63% stopped out), and with is_above_sma the best version made 0.48% on the selection window. As an exit it sold dips that recovered: 10 of the 12 trades it closed would have reached the target. Stored strategies that name this signal keep evaluating.

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
@deprecated_signal(
    "it lost money against a price-filtered reference in strategy backtests, so it is disabled for "
    "new strategies and not in the ontology graph; stored strategies that name it keep evaluating"
)
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
    Disabled: True
    Disabled-Reason: In Oracle engine strategy backtests on BTC, ETH, SOL, XRP, DOGE, BNB and LINK (daily bars, platform default execution config, every strategy one entry trigger plus a price filter, settings chosen on 2025-04-01 to 2026-01-31 and reported untouched on 2026-02-01 to 2026-11-01), no crowd_bullish variant beat rsi_cross_up with is_above_sma (5.12% selection, 3.25% holdout); 0 of 8 qualified. As a filter at the default 7/60 it made -0.01% and 1.30%. A crowd already more bullish than its norm marks a late, crowded entry: the trades it kept on the selection window lost 7.2 USDT per trade with a 33% win rate, and on the holdout the split vanished. Stored strategies that name this signal keep evaluating.

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


@RuleRegistry.register("social_crowd_cooling")
@deprecated_signal(
    "it trailed a price-filtered reference in strategy backtests, so it is disabled for new "
    "strategies and not in the ontology graph; stored strategies that name it keep evaluating"
)
def social_crowd_cooling(df: pd.DataFrame, window: int = 7, window_baseline: int = 60, margin: float = 0.0) -> bool:
    """Signal: social_crowd_cooling

    Check whether the crowd is no more bullish than usual: the complement of social_crowd_bullish
    at the same windows and margin 0 (contrarian regime filter).

    Friendly-Name: Crowd Not Running Hot
    Display-Name: Social Crowd Cooling
    Short-Description: Recent posts lean no more bullish than this asset's norm.

    Warmup: window + window_baseline - 1

    Formula:
        shift(SocialNetBullShare, window, window_baseline)[t] <= -margin

    Inputs:
        SocialNetBullShare: bullish minus bearish share of posts per bar, -1 to 1

    Params:
        window [default=7, min=1, max=60]: recent readings averaged
        window_baseline [default=60, min=14, max=365]: readings before the recent window forming the norm
        margin [default=0.0, min=0.0, max=0.5]: amount the recent average must sit at or below the norm by

    Outputs:
        fired [boolean, 0..1]:
            True if the mean net bullish share over the last window readings is at or below the mean
            of the preceding window_baseline readings minus margin

    Type: FILTER
    Requires: SocialNetBullShare
    Disabled: True
    Disabled-Reason: In Oracle engine strategy backtests on BTC, ETH, SOL, XRP, DOGE, BNB and LINK (daily bars, platform default execution config, every strategy one entry trigger plus a price filter, settings chosen on 2025-04-01 to 2026-01-31 and reported untouched on 2026-02-01 to 2026-11-01), no crowd_cooling variant beat rsi_cross_up with is_above_sma (5.12% selection, 3.25% holdout); 0 of 16 qualified. It halves the trades and raises P&L per trade, but total return trails: the best version (7/30) made 4.56% and 2.93% and beat the reference on 2 of 7 coins on the holdout, and on macd_bullish_cross with is_above_sma the default 7/60 cut holdout return from 1.04% to -0.06%. Stored strategies that name this signal keep evaluating.

    Args:
        df (pd.DataFrame): DataFrame with a SocialNetBullShare column.
        window (int): Recent readings averaged. Range: 1-60. Default: 7.
        window_baseline (int): Readings before the recent window forming the norm. Range: 14-365. Default: 60.
        margin (float): Amount the recent average must sit at or below the norm by. Range: 0.0-0.5. Default: 0.0.

    Returns:
        bool: True if the mean net bullish share over the last window readings is at or
            below the mean of the preceding window_baseline readings minus margin.
    """
    if len(df) < window + window_baseline:
        return False
    s = _series(df, "SocialNetBullShare")
    if s is None:
        return False
    shift = _last(SocialBaselineShift.compute(
        data={'value': s}, params={'window': window, 'window_baseline': window_baseline})['shift'])
    return shift is not None and shift <= -margin


# social_price_divergence is an EXIT for long positions, not an entry. Oracle engine strategy
# backtests on BTC, ETH, SOL, XRP, DOGE, BNB and LINK (daily bars, platform default execution config;
# settings chosen on 2025-04-01..2026-01-31, then reported untouched on 2026-02-01..2026-11-01):
# as the exit of rsi_cross_up + is_above_sma at window=7, min_drop_pct=3.0, window_baseline=60 the
# holdout return was 4.00% vs 3.25% without it, Sharpe 1.12 vs 0.61, better on 6 of 7 coins. On three
# filtered strategies (that one, ema_cross_up + is_above_sma, macd_bullish_cross + is_above_sma) it
# was never below the strategy without it in either window, over 31 signal exits; the effect is
# small. As a long entry it lost money in every form tested (old defaults 7/5.0/30 + is_above_sma:
# -1.98% and -0.44% vs 5.12% and 3.25%): the crowd usually turns bearish on a drop, so a drop it has
# not reacted to yet tends to begin a longer decline.
@RuleRegistry.register("social_price_divergence")
def social_price_divergence(df: pd.DataFrame, window: int = 7, min_drop_pct: float = 3.0, window_baseline: int = 60) -> bool:
    """Signal: social_price_divergence

    Exit signal for long positions: detect a price drop that the crowd is not following. Use it
    only in the exit rules of a strategy that already has its own entry trigger and a price filter.
    Do not use it as an entry: it lost money as a long entry in every form tested. It is typed
    TRIGGER because the knowledge base has no exit-only type.

    Friendly-Name: Crowd Ignores Drop Exit
    Display-Name: Social Price Divergence
    Short-Description: Exit a long when price falls while the crowd stays bullish.

    Warmup: window + window_baseline - 1

    Formula:
        roc(close, window)[t] <= -min_drop_pct
        AND shift(SocialNetBullShare, window, window_baseline)[t] >= 0

    Inputs:
        close: closing price
        SocialNetBullShare: bullish minus bearish share of posts per bar, -1 to 1

    Params:
        window [default=7, min=2, max=60]: bars over which the price drop and the recent social mean are measured
        min_drop_pct [default=3.0, min=1.0, max=50.0]: minimum percentage fall in close over window
        window_baseline [default=60, min=7, max=180]: social readings before the recent window forming the norm

    Outputs:
        fired [boolean, 0..1]:
            True if close fell at least min_drop_pct over window bars while the mean net bullish
            share over the same bars stayed at or above its baseline mean; True means exit the long

    Type: TRIGGER
    Requires: close, SocialNetBullShare

    Args:
        df (pd.DataFrame): DataFrame with close and SocialNetBullShare columns.
        window (int): Bars over which the price drop and the recent social mean are measured. Range: 2-60. Default: 7.
        min_drop_pct (float): Minimum percentage fall in close over window. Range: 1.0-50.0. Default: 3.0.
        window_baseline (int): Social readings before the recent window forming the norm. Range: 7-180. Default: 60.

    Returns:
        bool: True if close fell at least min_drop_pct over window bars while
            the mean net bullish share over the same bars stayed at or above
            its baseline mean. True means exit the long position.
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


# =============================================================================
# Live X signals. Provider ownership stays with the consuming application.
# =============================================================================

logger = logging.getLogger(__name__)
_x_provider_factory = None


def configure_x_provider(factory):
    """Configure a lazy X provider factory, or pass None to remove it.

    No client is constructed and no network request is made during import or
    configuration. The provider implements ``check_user_post_signal``,
    ``check_topic_mention_signal``, ``get_user_influence_score`` and
    ``detect_social_sentiment``. MangroveRoots' XProvider implements this contract;
    the KB has no dependency on MangroveRoots, credentials or MangroveAI.
    """
    if factory is not None and not callable(factory):
        raise TypeError("X provider factory must be callable or None")
    global _x_provider_factory
    _x_provider_factory = factory


def _get_x_provider():
    factory = _x_provider_factory
    if factory is None:
        raise RuntimeError("Live X signals require social.configure_x_provider(factory)")
    return factory()


def _mention_volume_score(symbol: str, time_window_hours: int, *, provider=None) -> float:
    """Ten points per recent cashtag post, capped at 100; not keyword polarity.

    An unavailable or malformed reading raises, so even a zero threshold cannot
    turn a failed request into a signal. This keeps the five existing score
    contracts independent of the provider's keyword-polarity score.
    """
    if provider is None:
        provider = _get_x_provider()
    reading = provider.detect_social_sentiment(symbol=symbol, time_window_hours=time_window_hours)
    if not isinstance(reading, dict) or reading.get("success") is False or reading.get("error"):
        raise ValueError("X mention-volume reading is unavailable")
    volume = reading.get("mention_volume", reading.get("total_mentions"))
    if volume is None or not np.isfinite(float(volume)) or float(volume) < 0:
        raise ValueError("X mention-volume reading has no valid post count")
    return float(min(int(volume) * 10, 100))


@RuleRegistry.register("x_user_post_trigger", evaluation_mode="live", data_provider="x")
def x_user_post_trigger(
    df: pd.DataFrame,
    username: str,
    topic: str = None,
    max_age_hours: int = 1
) -> bool:
    """Signal: x_user_post_trigger

    Fires when a specific X user posts about a topic.

    Reads live X data at evaluation time. The DataFrame is accepted for the
    registry contract but is not a historical data source for this rule.

    Friendly-Name: User Posts About Topic
    Display-Name: X User Post Trigger
    Short-Description: A monitored X user has posted about the requested topic.
    Warmup: 0

    Formula:
        recent_posts(username, topic, max_age_hours) > 0

    Outputs:
        fired [boolean, 0..1]:
            True when the requested live X condition is met; False on provider read failure

    Type: TRIGGER
    Requires: None

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        username (str): X username to monitor (without @).
        topic (str): Topic keyword to filter posts. Default: None.
        max_age_hours (int): How recent the post must be (hours). Range: 1-168. Default: 1.

    Returns:
        bool: True if user posted about topic within time window.
    """
    provider = _get_x_provider()
    try:
        logger.info(f"TRIGGER: Checking if @{username} posted about '{topic}' in last {max_age_hours}h")

        triggered = provider.check_user_post_signal(
            username=username,
            topic=topic,
            max_posts_age_hours=max_age_hours
        )

        return triggered
    except Exception as e:
        logger.error(f"Error checking user post trigger for @{username}: {e}")
        return False


@RuleRegistry.register("x_topic_mention_trigger", evaluation_mode="live", data_provider="x")
def x_topic_mention_trigger(
    df: pd.DataFrame,
    topic: str,
    min_mentions: int = 3,
    min_followers: int = 10000,
    time_window_hours: int = 1
) -> bool:
    """Signal: x_topic_mention_trigger

    Compares the provider's reported topic-mention count with the requested threshold.

    The follower and time-window parameters are forwarded unchanged. Filtering
    depends on the provider: MangroveRoots 0.21 reports follower_filter_applied=False
    and counts all returned posts on its basic X path, so this does not establish
    that the observed authors meet min_followers.

    Reads live X data at evaluation time. The DataFrame is accepted for the
    registry contract but is not a historical data source for this rule.

    Friendly-Name: Topic Draws Attention
    Display-Name: X Influential Topic Mentions
    Short-Description: The provider-reported topic mention count reaches the requested threshold.
    Warmup: 0

    Formula:
        influential_mentions(topic, min_followers, time_window_hours) >= min_mentions

    Outputs:
        fired [boolean, 0..1]:
            True when the requested live X condition is met; False on provider read failure

    Type: TRIGGER
    Requires: None

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        topic (str): Topic/keyword to monitor.
        min_mentions (int): Minimum influential mentions. Range: 1-100. Default: 3.
        min_followers (int): Minimum followers for influential users. Range: 100-10000000. Default: 10000.
        time_window_hours (int): Analysis time window (hours). Range: 1-168. Default: 1.

    Returns:
        bool: True if the provider reports that the topic mention threshold is met.
    """
    provider = _get_x_provider()
    try:
        logger.info(f"TRIGGER: Checking if '{topic}' mentioned {min_mentions}+ times by users >{min_followers} followers in {time_window_hours}h")

        triggered = provider.check_topic_mention_signal(
            topic=topic,
            min_mentions=min_mentions,
            min_followers=min_followers,
            time_window_hours=time_window_hours
        )

        return triggered
    except Exception as e:
        logger.error(f"Error checking topic mention trigger for '{topic}': {e}")
        return False


@RuleRegistry.register("x_social_sentiment_trigger", evaluation_mode="live", data_provider="x")
def x_social_sentiment_trigger(
    df: pd.DataFrame,
    symbol: str,
    threshold: float = 70.0,
    time_window_hours: int = 24
) -> bool:
    """Signal: x_social_sentiment_trigger

    Fires when the mention-volume score reaches its threshold.

    The requested time window is forwarded; the current basic X provider reads
    recent search (roughly seven days) rather than enforcing that window.

    Reads live X data at evaluation time. The DataFrame is accepted for the
    registry contract but is not a historical data source for this rule.

    Friendly-Name: Social Interest Reaches Threshold
    Display-Name: X Mention Volume Trigger
    Short-Description: Recent cashtag post volume reaches the requested score threshold.
    Warmup: 0

    Formula:
        min(mention_volume(symbol, time_window_hours) * 10, 100) >= threshold

    Outputs:
        fired [boolean, 0..1]:
            True when the requested live X condition is met; False on provider read failure

    Type: TRIGGER
    Requires: None

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        symbol (str): Crypto symbol (e.g., 'BTC', 'ETH').
        threshold (float): Mention-volume score threshold (0-100). Range: 0-100. Default: 70.0.
        time_window_hours (int): Analysis time window (hours). Range: 1-168. Default: 24.

    Returns:
        bool: True if the mention-volume score reaches the threshold.
    """
    provider = _get_x_provider()
    try:
        logger.info(f"TRIGGER: Checking if ${symbol} social sentiment > {threshold} in {time_window_hours}h")
        # Mention-volume score; a failed X search raises and the signal does not fire.
        score = _mention_volume_score(symbol, time_window_hours, provider=provider)
        triggered = score >= threshold
        if triggered:
            logger.info(f"SOCIAL_SENTIMENT_SIGNAL: ${symbol} sentiment {score:.1f} >= {threshold}")
        return triggered
    except Exception as e:
        logger.error(f"Error checking social sentiment trigger for ${symbol}: {e}")
        return False


@RuleRegistry.register("x_user_influence_filter", evaluation_mode="live", data_provider="x")
def x_user_influence_filter(
    df: pd.DataFrame,
    username: str,
    min_influence_score: float = 50.0
) -> bool:
    """Signal: x_user_influence_filter

    Checks if X user has sufficient influence.

    Reads live X data at evaluation time. The DataFrame is accepted for the
    registry contract but is not a historical data source for this rule.

    Friendly-Name: User Has Influence
    Display-Name: X User Influence Filter
    Short-Description: The X account meets the requested influence score.
    Warmup: 0

    Formula:
        influence_score(username) >= min_influence_score

    Outputs:
        fired [boolean, 0..1]:
            True when the requested live X condition is met; False on provider read failure

    Type: FILTER
    Requires: None

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        username (str): X username to check.
        min_influence_score (float): Minimum influence score (0-100). Range: 0-100. Default: 50.0.

    Returns:
        bool: True if user influence meets threshold.
    """
    provider = _get_x_provider()
    try:
        influence_score = provider.get_user_influence_score(username)
        meets_threshold = influence_score >= min_influence_score
        logger.debug(f"FILTER: @{username} influence {influence_score:.1f} >= {min_influence_score}: {meets_threshold}")
        return meets_threshold
    except Exception as e:
        logger.error(f"Error checking user influence filter for @{username}: {e}")
        return False


@RuleRegistry.register("x_topic_sentiment_filter", evaluation_mode="live", data_provider="x")
def x_topic_sentiment_filter(
    df: pd.DataFrame,
    topic: str,
    min_sentiment: float = 60.0
) -> bool:
    """Signal: x_topic_sentiment_filter

    Checks if topic has sufficient social interest.

    Reads live X data at evaluation time. The DataFrame is accepted for the
    registry contract but is not a historical data source for this rule.

    Friendly-Name: Topic Has Social Interest
    Display-Name: X Topic Mention Volume Filter
    Short-Description: Recent cashtag post volume meets the requested social interest score.
    Warmup: 0

    Formula:
        min(mention_volume(topic, 24) * 10, 100) >= min_sentiment

    Outputs:
        fired [boolean, 0..1]:
            True when the requested live X condition is met; False on provider read failure

    Type: FILTER
    Requires: None

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        topic (str): Topic to analyze.
        min_sentiment (float): Minimum sentiment score (0-100). Range: 0-100. Default: 60.0.

    Returns:
        bool: True if topic sentiment meets threshold.
    """
    provider = _get_x_provider()
    try:
        # Mention-volume score; a failed X search raises and the filter is not met.
        sentiment_score = _mention_volume_score(topic, 24, provider=provider)
        meets_threshold = sentiment_score >= min_sentiment
        logger.debug(f"FILTER: '{topic}' sentiment {sentiment_score:.1f} >= {min_sentiment}: {meets_threshold}")
        return meets_threshold
    except Exception as e:
        logger.error(f"Error checking topic sentiment filter for '{topic}': {e}")
        return False
