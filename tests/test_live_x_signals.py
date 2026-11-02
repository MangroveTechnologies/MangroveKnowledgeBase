"""Live X predicates belong to the KB, with no consumer-package dependency."""
import inspect
import json
from pathlib import Path

import pandas as pd
import pytest

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import social

CASES = {
    "x_user_post_trigger": {"username": "alice"},
    "x_topic_mention_trigger": {"topic": "ETH"},
    "x_social_sentiment_trigger": {"symbol": "ETH"},
    "x_user_influence_filter": {"username": "alice"},
    "x_topic_sentiment_filter": {"topic": "ETH"},
}


class Provider:
    def __init__(self, *, posts=8, influence=75.0, triggered=True, failure=None, reading=None):
        self.posts, self.influence, self.triggered = posts, influence, triggered
        self.failure, self.reading, self.calls = failure, reading, []

    def _record(self, method, kwargs):
        self.calls.append((method, kwargs))
        if self.failure:
            raise self.failure

    def check_user_post_signal(self, **kwargs):
        self._record("user", kwargs)
        return self.triggered

    def check_topic_mention_signal(self, **kwargs):
        self._record("topic", kwargs)
        return self.triggered

    def get_user_influence_score(self, username):
        self._record("influence", {"username": username})
        return self.influence

    def detect_social_sentiment(self, **kwargs):
        self._record("sentiment", kwargs)
        return self.reading if self.reading is not None else {
            "mention_volume": self.posts, "sentiment_score": 0.0,
        }


@pytest.fixture(autouse=True)
def provider_reset():
    previous = social._x_provider_factory
    social.configure_x_provider(None)
    yield
    social.configure_x_provider(previous)


@pytest.mark.parametrize("name,params", CASES.items())
@pytest.mark.parametrize("fires", [False, True])
def test_direct_and_registry_execute_live_signals(name, params, fires):
    provider = Provider(posts=8 if fires else 0, influence=75 if fires else 0, triggered=fires)
    social.configure_x_provider(lambda: provider)
    assert getattr(social, name)(pd.DataFrame(), **params) is fires
    assert RuleRegistry.evaluate({"name": name, "params": params}, pd.DataFrame(), mode="live") is fires
    assert len(provider.calls) == 2
    d = RuleRegistry.describe(name)
    assert (d["status"], d["composable"], d["executable"]) == ("active", True, True)
    assert (d["evaluation_mode"], d["data_provider"], d["requires"]) == ("live", "x", [])
    assert RuleRegistry._registry[name].__module__ == "mangrove_kb.signals.social"


@pytest.mark.parametrize("name,params", CASES.items())
def test_missing_factory_is_a_configuration_error(name, params):
    with pytest.raises(RuntimeError, match="configure_x_provider"):
        RuleRegistry.evaluate({"name": name, "params": params}, pd.DataFrame())


@pytest.mark.parametrize("name,params", CASES.items())
def test_provider_outage_does_not_fire(name, params):
    provider = Provider(failure=RuntimeError("provider unavailable"))
    social.configure_x_provider(lambda: provider)
    assert RuleRegistry.evaluate({"name": name, "params": params}, pd.DataFrame()) is False


@pytest.mark.parametrize("name", CASES)
def test_historical_validation_never_resolves_provider(name):
    def unexpected():
        pytest.fail("historical evaluation resolved an X provider")
    social.configure_x_provider(unexpected)
    with pytest.raises(ValueError, match="cannot be evaluated historically"):
        RuleRegistry.evaluate({"name": name, "params": CASES[name]}, pd.DataFrame(), mode="historical")
    with pytest.raises(ValueError, match="cannot be evaluated historically"):
        RuleRegistry.validate_evaluation_mode(name, "historical")


@pytest.mark.parametrize("reading", [
    {"success": False, "mention_volume": 100}, {"error": "outage", "mention_volume": 100},
    {}, {"mention_volume": None}, {"mention_volume": -1}, {"mention_volume": float("nan")},
])
def test_failed_reading_never_fires_even_at_zero_threshold(reading):
    social.configure_x_provider(lambda: Provider(reading=reading))
    assert social.x_social_sentiment_trigger(pd.DataFrame(), "ETH", threshold=0) is False
    assert social.x_topic_sentiment_filter(pd.DataFrame(), "ETH", min_sentiment=0) is False


@pytest.mark.parametrize("posts,score", [(0, 0), (1, 10), (6, 60), (7, 70), (10, 100), (40, 100)])
def test_volume_formula_and_inclusive_thresholds(posts, score):
    social.configure_x_provider(lambda: Provider(posts=posts))
    assert social._mention_volume_score("ETH", 24) == score
    assert social.x_social_sentiment_trigger(pd.DataFrame(), "ETH") is (score >= 70)
    assert social.x_topic_sentiment_filter(pd.DataFrame(), "ETH") is (score >= 60)


def test_parameter_names_defaults_and_provider_forwarding_are_preserved():
    expected = {
        "x_user_post_trigger": [("df", inspect.Parameter.empty), ("username", inspect.Parameter.empty), ("topic", None), ("max_age_hours", 1)],
        "x_topic_mention_trigger": [("df", inspect.Parameter.empty), ("topic", inspect.Parameter.empty), ("min_mentions", 3), ("min_followers", 10000), ("time_window_hours", 1)],
        "x_social_sentiment_trigger": [("df", inspect.Parameter.empty), ("symbol", inspect.Parameter.empty), ("threshold", 70.0), ("time_window_hours", 24)],
        "x_user_influence_filter": [("df", inspect.Parameter.empty), ("username", inspect.Parameter.empty), ("min_influence_score", 50.0)],
        "x_topic_sentiment_filter": [("df", inspect.Parameter.empty), ("topic", inspect.Parameter.empty), ("min_sentiment", 60.0)],
    }
    for name, signature in expected.items():
        assert [(p.name, p.default) for p in inspect.signature(getattr(social, name)).parameters.values()] == signature
    provider = Provider()
    social.configure_x_provider(lambda: provider)
    social.x_user_post_trigger(pd.DataFrame(), "alice", "ETH", 6)
    social.x_topic_mention_trigger(pd.DataFrame(), "ETH", 5, 20000, 4)
    assert provider.calls == [
        ("user", {"username": "alice", "topic": "ETH", "max_posts_age_hours": 6}),
        ("topic", {"topic": "ETH", "min_mentions": 5, "min_followers": 20000, "time_window_hours": 4}),
    ]


def test_factory_is_lazy_and_frame_signals_remain_historical():
    social.configure_x_provider(lambda: pytest.fail("configuration made an X request"))
    RuleRegistry.validate_evaluation_mode("rsi_oversold", "historical")
    assert RuleRegistry.describe("rsi_oversold")["evaluation_mode"] == "frame"
    with pytest.raises(TypeError, match="callable"):
        social.configure_x_provider(object())
    with pytest.raises(ValueError, match="Unknown rule name"):
        RuleRegistry.validate_evaluation_mode("missing_signal", "historical")


def test_graph_models_live_provider_contract_without_invented_indicators():
    record = json.loads((Path(__file__).parents[1] / "ontology/signal-indicator-ontology.json").read_text())
    nodes = {a["id"]: a for a in record["atoms"]}
    for name in CASES:
        nid = "procedure:signal-" + name.replace("_", "-")
        node = nodes[nid]
        assert node["props"]["evaluation_mode"] == "live"
        assert node["props"]["data_provider"] == "x"
        assert node["props"]["inputs"] == {}
        edges = [e for e in record["relations"] if e["from_id"] == nid]
        assert any(e["rel"] == "about" and e["to_id"] == "concept:social" for e in edges)
        assert not any(e["rel"] == "uses" for e in edges)
    assert record["meta"]["live_provider_signals"] == sorted(CASES)
    for nid, node in nodes.items():
        if nid.startswith("procedure:signal-") and node["props"].get("evaluation_mode") != "live":
            assert any(e["from_id"] == nid and e["rel"] == "uses" for e in record["relations"]), nid


@pytest.mark.parametrize("kwargs", [
    {"evaluation_mode": "unknown"}, {"evaluation_mode": "live"},
    {"data_provider": "x"},
])
def test_invalid_execution_contract_is_rejected_at_registration(kwargs):
    with pytest.raises(ValueError):
        RuleRegistry.register("_invalid_live_contract", **kwargs)
    assert not RuleRegistry.has("_invalid_live_contract")
