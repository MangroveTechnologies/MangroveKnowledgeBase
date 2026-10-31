"""Cambrian signal families: fire on the intended pattern, fail closed otherwise."""

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.docstring_parser import parse_signal_policy
from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import cambrian as cs

TRIGGERS = ["social_sentiment_surge", "social_sentiment_capitulation", "social_price_divergence", "whale_share_divergence"]
FILTERS = ["social_crowd_bullish", "holder_growth_trend"]
NAMES = TRIGGERS + FILTERS


def _frame(sentiment, net_bull=None, close=None, authors=50, holders=None, whale_share=None):
    n = len(sentiment)
    idx = pd.date_range("2026-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({
        "close": close if close is not None else np.linspace(100, 110, n),
        "SocialSentiment": sentiment,
        "SocialAuthors": [authors] * n,
        "SocialNetBullShare": net_bull if net_bull is not None else [0.4] * n,
        "HolderCount": holders if holders is not None else [1000.0] * n,
        "WhaleHeldShare": whale_share if whale_share is not None else [0.3] * n,
    }, index=idx)


def _noisy(n, mean, seed=0):
    return list(mean + np.random.default_rng(seed).normal(0, 0.1, n))


def test_registered_with_types():
    assert set(NAMES) <= RuleRegistry.names()
    for name in NAMES:
        doc = cs.__dict__[name].__doc__
        assert ("Type: TRIGGER" in doc) == (name in TRIGGERS)
        assert not parse_signal_policy(cs.__dict__[name])["disabled"]


@pytest.mark.parametrize("name", NAMES)
def test_missing_columns_fail_closed(name):
    assert getattr(cs, name)(pd.DataFrame({"close": np.linspace(1, 2, 120)})) is False


@pytest.mark.parametrize("name", NAMES)
def test_short_history_fails_closed(name):
    assert getattr(cs, name)(_frame(_noisy(5, 5.5))) is False


def test_surge_and_capitulation():
    base = _noisy(40, 5.5)
    assert cs.social_sentiment_surge(_frame(base + [7.0])) is True
    assert cs.social_sentiment_surge(_frame(base + [5.5])) is False
    assert cs.social_sentiment_surge(_frame(base + [7.0], authors=3)) is False
    assert cs.social_sentiment_capitulation(_frame(base + [4.0])) is True
    assert cs.social_sentiment_capitulation(_frame(base + [7.0])) is False
    assert cs.social_sentiment_surge(_frame([5.5] * 40 + [9.0])) is False  # flat baseline, no divide by zero


def test_crowd_bullish():
    n = 80
    assert cs.social_crowd_bullish(_frame(_noisy(n, 5.5), net_bull=[0.3] * (n - 7) + [0.5] * 7)) is True
    assert cs.social_crowd_bullish(_frame(_noisy(n, 5.5), net_bull=[0.5] * (n - 7) + [0.3] * 7)) is False


def test_price_divergence_accepts_either_close_case():
    n = 50
    drop = [100.0] * (n - 7) + list(np.linspace(100, 90, 7))
    df = _frame(_noisy(n, 5.5), close=drop)
    assert cs.social_price_divergence(df) is True
    assert cs.social_price_divergence(df.rename(columns={"close": "Close"})) is True
    souring = [0.4] * (n - 7) + [0.2] * 7
    assert cs.social_price_divergence(_frame(_noisy(n, 5.5), net_bull=souring, close=drop)) is False


def test_holder_signals():
    n = 30
    assert cs.holder_growth_trend(_frame(_noisy(n, 5.5), holders=list(np.linspace(1000, 1050, n)))) is True
    assert cs.holder_growth_trend(_frame(_noisy(n, 5.5))) is False
    drop = [100.0] * (n - 7) + list(np.linspace(100, 90, 7))
    rising = [0.30] * (n - 7) + list(np.linspace(0.30, 0.33, 7))
    falling = [0.30] * (n - 7) + list(np.linspace(0.30, 0.28, 7))
    assert cs.whale_share_divergence(_frame(_noisy(n, 5.5), close=drop, whale_share=rising)) is True
    assert cs.whale_share_divergence(_frame(_noisy(n, 5.5), close=drop, whale_share=falling)) is False


def test_nan_buckets_are_skipped():
    assert cs.social_sentiment_surge(_frame(_noisy(40, 5.5) + [np.nan, 7.0])) is True
