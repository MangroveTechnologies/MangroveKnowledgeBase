"""Live X predicates belong to the KB, with no consumer-package dependency."""
import inspect
import json
from pathlib import Path

import pandas as pd
import pytest

from mangrove_kb import sample_ohlcv
from mangrove_kb.registry import LiveSignalNotAllowed, RuleRegistry
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
    previous_warned = set(social._unconfigured_warned)
    social.configure_x_provider(None)
    social._unconfigured_warned.clear()
    yield
    social.configure_x_provider(previous)
    social._unconfigured_warned.clear()
    social._unconfigured_warned.update(previous_warned)


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
def test_missing_factory_returns_false_and_warns_once_per_rule(name, params, caplog):
    rule = {"name": name, "params": params}
    with caplog.at_level("WARNING", logger=social.logger.name):
        assert RuleRegistry.evaluate(rule, pd.DataFrame(), mode="live") is False
        assert [r.levelname for r in caplog.records] == ["WARNING"]
        assert name in caplog.records[0].getMessage()
        assert "configure_x_provider" in caplog.records[0].getMessage()
        assert RuleRegistry.evaluate(rule, pd.DataFrame(), mode="live") is False
    assert len(caplog.records) == 1


@pytest.mark.parametrize("name,params", CASES.items())
def test_provider_outage_does_not_fire(name, params):
    provider = Provider(failure=RuntimeError("provider unavailable"))
    social.configure_x_provider(lambda: provider)
    assert RuleRegistry.evaluate({"name": name, "params": params}, pd.DataFrame(), mode="live") is False


@pytest.mark.parametrize("name,params", CASES.items())
def test_factory_failure_is_logged_as_error_and_does_not_fire(name, params, caplog):
    def broken():
        raise ConnectionError("factory down")
    social.configure_x_provider(broken)
    with caplog.at_level("ERROR", logger=social.logger.name):
        assert RuleRegistry.evaluate({"name": name, "params": params}, pd.DataFrame(), mode="live") is False
    assert any(r.levelname == "ERROR" for r in caplog.records)


@pytest.mark.parametrize("name,params", CASES.items())
def test_default_mode_rejects_live_rules_before_provider_access(name, params):
    def unexpected():
        pytest.fail("default evaluation resolved an X provider")
    social.configure_x_provider(unexpected)
    with pytest.raises(LiveSignalNotAllowed) as info:
        RuleRegistry.evaluate({"name": name, "params": params}, pd.DataFrame())
    message = str(info.value)
    assert name in message and "'x'" in message and 'mode="live"' in message
    assert isinstance(info.value, ValueError)


def test_default_mode_still_evaluates_frame_signals():
    assert RuleRegistry.evaluate({"name": "rsi_oversold"}, sample_ohlcv()) in (True, False)
    assert RuleRegistry.evaluate({"name": "rsi_oversold"}, sample_ohlcv(), mode="live") in (True, False)
    assert RuleRegistry.evaluate({"name": "rsi_oversold"}, sample_ohlcv(), mode="historical") in (True, False)


def test_unknown_mode_and_unknown_rule_stay_value_errors():
    with pytest.raises(ValueError, match="Unknown evaluation mode") as info:
        RuleRegistry.validate_evaluation_mode("rsi_oversold", "paper")
    assert not isinstance(info.value, LiveSignalNotAllowed)
    with pytest.raises(ValueError, match="Unknown rule name") as info:
        RuleRegistry.validate_evaluation_mode("missing_signal", "live")
    assert not isinstance(info.value, LiveSignalNotAllowed)


@pytest.fixture
def scratch_registry(monkeypatch):
    monkeypatch.setattr(RuleRegistry, "_registry", dict(RuleRegistry._registry))


def test_registration_cannot_downgrade_a_live_rule(scratch_registry):
    original = RuleRegistry._registry["x_user_post_trigger"]
    with pytest.raises(ValueError, match="x_user_post_trigger.*live.*frame"):
        RuleRegistry.register("x_user_post_trigger")(lambda df: True)
    assert RuleRegistry._registry["x_user_post_trigger"] is original


def test_registration_cannot_upgrade_a_frame_rule_or_change_provider(scratch_registry):
    with pytest.raises(ValueError, match="rsi_oversold.*frame.*live"):
        RuleRegistry.register("rsi_oversold", evaluation_mode="live", data_provider="x")(lambda df: True)
    with pytest.raises(ValueError, match="x_user_post_trigger.*'x'.*'other'"):
        RuleRegistry.register("x_user_post_trigger", evaluation_mode="live", data_provider="other")(lambda df: True)


def test_identical_reregistration_is_allowed(scratch_registry):
    RuleRegistry.register("x_user_post_trigger", evaluation_mode="live", data_provider="x")(lambda df: True)
    assert RuleRegistry._registry["x_user_post_trigger"].evaluation_mode == "live"
    RuleRegistry.register("rsi_oversold")(lambda df: True)
    assert RuleRegistry._registry["rsi_oversold"].evaluation_mode == "frame"


def test_provider_protocol_declares_the_four_methods_the_rules_call():
    methods = {
        "check_user_post_signal": ["username", "topic", "max_posts_age_hours"],
        "check_topic_mention_signal": ["topic", "min_mentions", "min_followers", "time_window_hours"],
        "get_user_influence_score": ["username"],
        "detect_social_sentiment": ["symbol", "time_window_hours"],
    }
    for method, names in methods.items():
        declared = list(inspect.signature(getattr(social.XSignalProvider, method)).parameters)
        assert declared == ["self", *names], method
    keyword_only = {
        n for n, p in inspect.signature(social.XSignalProvider.check_user_post_signal).parameters.items()
        if p.kind is inspect.Parameter.KEYWORD_ONLY
    }
    assert keyword_only == {"username", "topic", "max_posts_age_hours"}


@pytest.mark.parametrize("name", CASES)
def test_historical_validation_never_resolves_provider(name):
    def unexpected():
        pytest.fail("historical evaluation resolved an X provider")
    social.configure_x_provider(unexpected)
    with pytest.raises(LiveSignalNotAllowed, match="cannot be evaluated historically"):
        RuleRegistry.evaluate({"name": name, "params": CASES[name]}, pd.DataFrame(), mode="historical")
    with pytest.raises(LiveSignalNotAllowed, match="cannot be evaluated historically"):
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


def test_optional_topic_none_is_not_advertised_as_a_literal_keyword():
    record = json.loads((Path(__file__).parents[1] / "ontology/signal-indicator-ontology.json").read_text())
    node = next(a for a in record["atoms"] if a["id"] == "procedure:signal-x-user-post-trigger")
    assert node["props"]["params"]["topic"]["default"] is None
    runtime = RuleRegistry.describe("x_user_post_trigger")["params"]["topic"]
    assert runtime["optional"] is True
    assert "default" not in runtime


def test_graph_literal_parser_distinguishes_none_from_a_quoted_word():
    import ast

    source = (Path(__file__).parents[1] / "ontology/build_signal_indicator_ontology.py").read_text()
    parser = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "_authored_literal")
    namespace = {}
    exec(compile(ast.Module(body=[parser], type_ignores=[]), "ontology_literals", "exec"), namespace)
    lift = namespace["_authored_literal"]
    assert lift("str", "None") is None
    assert lift("str", "'None'") == "None"
    assert lift("str", '"None"') == "None"
    assert lift("str", "bullish") == "bullish"


@pytest.mark.parametrize("kwargs", [
    {"evaluation_mode": "unknown"}, {"evaluation_mode": "live"},
    {"data_provider": "x"},
])
def test_invalid_execution_contract_is_rejected_at_registration(kwargs):
    with pytest.raises(ValueError):
        RuleRegistry.register("_invalid_live_contract", **kwargs)
    assert not RuleRegistry.has("_invalid_live_contract")


def test_historical_audit_reports_live_rules_as_skipped_without_provider_io(monkeypatch, tmp_path):
    from scripts.audit.audit_signals import (
        classify_signals, generate_signal_report, review_filter_signals, smoke_test_all,
    )

    social.configure_x_provider(lambda: pytest.fail("historical audit resolved an X provider"))
    monkeypatch.setattr(RuleRegistry, "_registry", {name: RuleRegistry._registry[name] for name in CASES})
    smoke = smoke_test_all(pd.DataFrame())
    reviews = review_filter_signals()
    assert len(smoke) == 5 and len(reviews) == 2
    assert all(r.get("skipped") and r["error"] is None for r in smoke)
    assert all(r.get("skipped") and r["pass"] is None for r in reviews)
    report = generate_signal_report(smoke, [], reviews, classify_signals(), tmp_path / "report.md")
    assert "| Total signals tested | 0 |" in report
    assert "| Skipped (live provider; not historical) | 5 |" in report
    assert "| Bad return type (not bool) | 0 |" in report
    for name in CASES:
        assert f"SKIP `{name}`" in report


@pytest.mark.parametrize("name,params", CASES.items())
def test_historical_comparison_rejects_live_rules_before_replay(name, params):
    import numpy as np
    from scripts.audit.compare import verify_signal

    social.configure_x_provider(lambda: pytest.fail("historical comparison resolved an X provider"))
    with pytest.raises(ValueError, match="cannot be evaluated historically"):
        verify_signal(name, params, pd.DataFrame(index=range(3)), np.zeros(3), start_bar=0)


def test_validation_notebook_rejects_live_rules_before_swallowing_errors(tmp_path):
    import ast
    import runpy

    root = Path(__file__).parents[1]
    notebook = json.loads((root / "notebooks/signal_validation.ipynb").read_text())
    generator = runpy.run_path(str(root / "scripts/generate-validation-notebook.py"))
    generator["build_notebook"].__globals__["OUTPUT_PATH"] = str(tmp_path / "generated.ipynb")
    generator["build_notebook"]()
    generated = json.loads((tmp_path / "generated.ipynb").read_text())
    helpers = []
    for artifact in (notebook, generated):
        source = next("".join(c["source"]) for c in artifact["cells"]
                      if "def evaluate_signal_rolling" in "".join(c["source"]))
        node = ast.parse(source).body[0]
        helpers.append(ast.dump(node))
        namespace = {"RuleRegistry": RuleRegistry}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "validation_notebook", "exec"), namespace)
        social.configure_x_provider(lambda: pytest.fail("historical notebook resolved an X provider"))
        for name, params in CASES.items():
            with pytest.raises(ValueError, match="cannot be evaluated historically"):
                namespace["evaluate_signal_rolling"](name, pd.DataFrame(index=range(3)), warmup=0, params=params)
    assert helpers[0] == helpers[1]


def test_a_failing_provider_logs_error_once_then_debug(caplog, monkeypatch):
    import logging
    from mangrove_kb.signals import social

    class Boom:
        def check_user_post_signal(self, **kwargs):
            raise RuntimeError("held back")

    social._provider_failed_logged.clear()
    social.configure_x_provider(lambda: Boom())
    try:
        rule = {"name": "x_user_post_trigger", "parameters": {"username": "u"}}
        with caplog.at_level(logging.DEBUG, logger="mangrove_kb.signals.social"):
            assert RuleRegistry.evaluate(rule, pd.DataFrame({"close": [1.0]}), mode="live") is False
            assert RuleRegistry.evaluate(rule, pd.DataFrame({"close": [1.0]}), mode="live") is False
        errors = [r for r in caplog.records if r.levelno == logging.ERROR and "did not fire" in r.getMessage()]
        debugs = [r for r in caplog.records if r.levelno == logging.DEBUG and "did not fire" in r.getMessage()]
        assert len(errors) == 1 and len(debugs) == 1
        monkeypatch.setattr(social.time, "monotonic", lambda: social._provider_failed_logged[("x_user_post_trigger", "RuntimeError")] + 901)
        with caplog.at_level(logging.DEBUG, logger="mangrove_kb.signals.social"):
            assert RuleRegistry.evaluate(rule, pd.DataFrame({"close": [1.0]}), mode="live") is False
        errors = [r for r in caplog.records if r.levelno == logging.ERROR and "did not fire" in r.getMessage()]
        assert len(errors) == 2
    finally:
        social.configure_x_provider(None)
        social._provider_failed_logged.clear()
