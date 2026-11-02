"""Social and holder signals (and the indicators they read): fire on the intended pattern, fail closed otherwise."""

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.docstring_parser import parse_signal_policy
from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators import OnchainChange, SocialBaselineShift, SocialZScore
from mangrove_kb.signals import onchain, social

cs = type("Signals", (), {**{k: staticmethod(v) for k, v in vars(onchain).items() if callable(v)},
                            **{k: staticmethod(v) for k, v in vars(social).items() if callable(v)}})

TRIGGERS = ["social_sentiment_surge", "social_sentiment_capitulation", "social_price_divergence", "whale_share_divergence"]
FILTERS = ["social_crowd_bullish", "social_crowd_cooling", "holder_growth_trend"]
NAMES = TRIGGERS + FILTERS
#: Disabled for new strategies (lost to price-filtered references in strategy backtests) but kept
#: executable for stored ones. social_price_divergence is enabled again, as an exit for longs.
DISABLED = {"social_sentiment_surge", "social_sentiment_capitulation", "social_crowd_bullish",
            "social_crowd_cooling", "whale_share_divergence", "holder_growth_trend"}


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
        doc = getattr(cs, name).__doc__
        assert ("Type: TRIGGER" in doc) == (name in TRIGGERS)
        assert parse_signal_policy(getattr(cs, name))["disabled"] is (name in DISABLED)


#: A frame each disabled signal fires on, so the legacy path is shown to still compute.
def _firing_frame(name):
    n = 80
    drop = [100.0] * (n - 7) + list(np.linspace(100, 90, 7))
    return {
        "social_sentiment_surge": lambda: _frame(_noisy(40, 5.5) + [7.0]),
        "social_sentiment_capitulation": lambda: _frame(_noisy(40, 5.5) + [4.0]),
        "social_crowd_bullish": lambda: _frame(_noisy(n, 5.5), net_bull=[0.3] * (n - 7) + [0.5] * 7),
        "social_crowd_cooling": lambda: _frame(_noisy(n, 5.5), net_bull=[0.5] * (n - 7) + [0.3] * 7),
        "holder_growth_trend": lambda: _frame(_noisy(30, 5.5), holders=list(np.linspace(1000, 1050, 30))),
        "whale_share_divergence": lambda: _frame(
            _noisy(n, 5.5), close=drop, whale_share=[0.30] * (n - 7) + list(np.linspace(0.30, 0.33, 7))),
    }[name]()


@pytest.mark.parametrize("name", sorted(DISABLED))
def test_disabled_for_new_strategies_but_still_executes(name):
    """The atr_trailing_stop_* pattern: not composable, not in the graph, stored strategies run."""
    from mangrove_kb.graph import KnowledgeGraph

    d = RuleRegistry.describe(name)
    assert d["status"] == "disabled"
    assert d["composable"] is False
    assert d["executable"] is True and d["legacy_compatible"] is True
    assert "Oracle engine strategy backtests" in d["reason"] and "Stored strategies" in d["reason"]
    assert d["reason"].isascii()
    assert f"procedure:signal-{name.replace('_', '-')}" not in KnowledgeGraph.load().nodes

    with pytest.warns(DeprecationWarning):
        assert RuleRegistry.evaluate({"name": name}, _firing_frame(name)) is True


def test_price_divergence_is_an_exit_composable_and_in_the_graph():
    """Enabled again as an exit for long positions, with the defaults the exit backtests chose."""
    import inspect
    import warnings
    from mangrove_kb.graph import KnowledgeGraph

    d = RuleRegistry.describe("social_price_divergence")
    assert d["status"] == "active" and d["composable"] is True and not d["disabled"]
    assert d["type"] == "TRIGGER"
    defaults = {k: v.default for k, v in inspect.signature(cs.social_price_divergence).parameters.items()
                if k != "df"}
    assert defaults == {"window": 7, "min_drop_pct": 3.0, "window_baseline": 60}
    assert {k: v["default"] for k, v in d["params"].items()} == defaults
    doc = cs.social_price_divergence.__doc__
    assert "Exit signal for long positions" in doc and "Do not use it as an entry" in doc
    assert "Short-Description: Exit a long when price falls while the crowd stays bullish." in doc

    kg = KnowledgeGraph.load()
    node = "procedure:signal-social-price-divergence"
    assert node in kg.nodes
    assert node in {x["id"] for x in kg.find(kind="social", role="trigger", limit=None).items}

    n = 80
    drop = [100.0] * (n - 7) + list(np.linspace(100, 96, 7))  # a 4% fall: fires at 3.0, not at 5.0
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert RuleRegistry.evaluate({"name": "social_price_divergence"}, _frame(_noisy(n, 5.5), close=drop)) is True
    assert cs.social_price_divergence(_frame(_noisy(n, 5.5), close=drop), min_drop_pct=5.0) is False


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


def test_crowd_cooling():
    n = 80
    assert "social_crowd_cooling" in RuleRegistry.names()
    below = [0.5] * (n - 7) + [0.3] * 7
    level = [0.25] * n  # exactly representable, so the shift is exactly 0: at the norm fires
    above = [0.3] * (n - 7) + [0.5] * 7
    assert cs.social_crowd_cooling(_frame(_noisy(n, 5.5), net_bull=below)) is True
    assert cs.social_crowd_cooling(_frame(_noisy(n, 5.5), net_bull=level)) is True
    assert cs.social_crowd_cooling(_frame(_noisy(n, 5.5), net_bull=above)) is False
    assert cs.social_crowd_cooling(_frame(_noisy(n, 5.5), net_bull=below), margin=0.3) is False


@pytest.mark.parametrize("seed", range(25))
def test_crowd_cooling_is_the_complement_of_crowd_bullish_at_margin_zero(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(67, 200))
    window, window_baseline = int(rng.integers(1, 15)), int(rng.integers(14, 60))
    df = _frame(_noisy(n, 5.5, seed), net_bull=list(rng.uniform(-1, 1, n)))
    kw = {"window": window, "window_baseline": window_baseline, "margin": 0.0}
    assert cs.social_crowd_cooling(df, **kw) is (not cs.social_crowd_bullish(df, **kw))


def test_price_divergence_accepts_either_close_case():
    n = 80  # window + window_baseline = 67 bars at the defaults
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


def test_indicators_match_their_formulas():
    v = pd.Series([1.0, 2.0, 3.0, 4.0, 10.0])
    z = SocialZScore.compute(data={"value": v}, params={"window": 4})["zscore"]
    base = v.iloc[:4]
    assert z.iloc[:4].isna().all()
    assert z.iloc[-1] == pytest.approx((10.0 - base.mean()) / base.std())
    assert SocialZScore.compute(data={"value": pd.Series([5.0] * 6)}, params={"window": 4})["zscore"].isna().all()

    shift = SocialBaselineShift.compute(data={"value": pd.Series([1.0, 1.0, 1.0, 3.0, 3.0])},
                                        params={"window": 2, "window_baseline": 3})
    assert shift["recent"].iloc[-1] == 3.0 and shift["baseline"].iloc[-1] == 1.0
    assert shift["shift"].iloc[-1] == 2.0 and shift["ratio"].iloc[-1] == 3.0
    signed = SocialBaselineShift.compute(data={"value": pd.Series([-0.2, -0.2, -0.2, 0.1, 0.1])},
                                         params={"window": 2, "window_baseline": 3})
    assert pd.isna(signed["ratio"].iloc[-1]) and signed["shift"].iloc[-1] == pytest.approx(0.3)

    ch = OnchainChange.compute(data={"value": pd.Series([100.0, 105.0, 110.0])}, params={"window": 2})
    assert ch["pct_change"].iloc[-1] == pytest.approx(10.0) and ch["change"].iloc[-1] == 10.0
    assert pd.isna(OnchainChange.compute(data={"value": pd.Series([0.0, 1.0])}, params={"window": 1})["pct_change"].iloc[-1])
