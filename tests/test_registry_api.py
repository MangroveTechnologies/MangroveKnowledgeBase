"""Public enumeration API on RuleRegistry.

MangroveTechnologies/MangroveKnowledgeBase#102. Consumers need to answer "is this a real signal?"
without evaluating it -- evaluating requires a DataFrame -- and were reading the private `_registry`
to do it.

Usage:
    pytest tests/test_registry_api.py -v
"""

import pandas as pd
import pytest

import mangrove_kb.signals  # noqa: F401  -- registers the signals
from mangrove_kb.registry import RuleRegistry


def test_names_returns_every_registered_signal():
    names = RuleRegistry.names()
    assert isinstance(names, frozenset)
    assert len(names) == 249
    # Spot-check across modules rather than trusting the count alone.
    for expected in ("rsi_oversold", "bb_above_upper", "ma_ribbon_bullish",
                     "macd_line_positive", "funding_flip_positive"):
        assert expected in names, expected


def test_names_is_immutable_from_the_caller():
    """A frozenset, so a consumer cannot corrupt the registry's view by mutating what it got."""
    names = RuleRegistry.names()
    with pytest.raises(AttributeError):
        names.add("not_a_signal")
    assert "not_a_signal" not in RuleRegistry.names()


def test_has_matches_names_without_evaluating():
    assert RuleRegistry.has("rsi_oversold")
    assert not RuleRegistry.has("rsi_oversold_typo")
    assert not RuleRegistry.has("")
    # `has` and `names` must not drift apart.
    assert all(RuleRegistry.has(n) for n in RuleRegistry.names())


def test_names_reflects_registrations_made_after_import():
    """Not an import-time snapshot. A consumer that registers its own signals -- MangroveAI does --
    must see them, because it has to validate against the registry it evaluates with."""
    assert not RuleRegistry.has("_probe_signal_for_test")

    @RuleRegistry.register("_probe_signal_for_test")
    def _probe(df: pd.DataFrame) -> bool:
        return True

    try:
        assert RuleRegistry.has("_probe_signal_for_test")
        assert "_probe_signal_for_test" in RuleRegistry.names()
    finally:
        RuleRegistry._registry.pop("_probe_signal_for_test", None)

    assert not RuleRegistry.has("_probe_signal_for_test")


def test_unknown_name_is_distinguishable_from_a_signal_that_did_not_fire():
    """The defect that motivated the issue: both looked like "False" to the caller. `has` separates
    them before evaluation, and `evaluate` still raises for anyone who skips the check."""
    df = pd.DataFrame({"Open": [1.0] * 60, "High": [1.0] * 60, "Low": [1.0] * 60,
                       "Close": [1.0] * 60, "Volume": [1.0] * 60})

    assert RuleRegistry.has("rsi_oversold")
    did_not_fire = RuleRegistry.evaluate({"name": "rsi_oversold", "params": {}}, df)
    assert did_not_fire is False

    assert not RuleRegistry.has("rsi_oversold_typo")
    with pytest.raises(ValueError, match="Unknown rule name"):
        RuleRegistry.evaluate({"name": "rsi_oversold_typo", "params": {}}, df)
