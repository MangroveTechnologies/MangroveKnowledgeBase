"""Runtime existence, composition and stored execution are separate contracts."""

from typing import ClassVar

import pandas as pd
import pytest

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals._common import deprecated_signal


@pytest.fixture
def isolated_registry():
    class Registry(RuleRegistry):
        _registry: ClassVar[dict] = {}
        _aliases: ClassVar[dict] = {}

    return Registry


def test_disabled_legacy_signal_is_known_but_not_composable(isolated_registry):
    registry = isolated_registry

    @registry.register("legacy")
    @deprecated_signal("Stored strategies keep evaluating")
    def legacy(df):
        """Legacy policy.

        Type: FILTER
        Requires: close
        Disabled: True
        Disabled-Reason: Policy is excluded from new signal pools; stored strategies keep evaluating.
        """
        return True

    descriptor = registry.describe("legacy")
    assert descriptor["status"] == "disabled"
    assert descriptor["composable"] is False
    assert descriptor["executable"] is True
    assert descriptor["legacy_compatible"] is True
    with pytest.warns(DeprecationWarning):
        assert registry.evaluate({"name": "legacy"}, pd.DataFrame()) is True


def test_explicit_runtime_disable_blocks_every_execution_path(isolated_registry):
    registry = isolated_registry
    calls = []

    @registry.register("blocked", executable=False)
    @deprecated_signal("Old strategies used this")
    def blocked(df):
        calls.append(df)
        return True

    registry.alias("old_blocked", "blocked")
    for name in ("blocked", "old_blocked"):
        descriptor = registry.describe(name)
        assert descriptor["status"] == "disabled"
        assert not descriptor["composable"]
        assert not descriptor["executable"]
        assert not descriptor["legacy_compatible"]
        with pytest.raises(ValueError, match="disabled for execution"):
            registry.evaluate({"name": name}, pd.DataFrame())
    with pytest.raises(ValueError, match="disabled for execution"):
        blocked(pd.DataFrame())
    assert calls == []


def test_alias_identity_does_not_inflate_catalog(isolated_registry):
    registry = isolated_registry

    @registry.register("current")
    def current(df):
        return True

    registry.alias("retired", "current")
    descriptor = registry.describe("retired")
    assert descriptor["rule_name"] == "retired"
    assert descriptor["canonical_name"] == "current"
    assert descriptor["status"] == "deprecated"
    assert descriptor["executable"]
    assert descriptor["composable"]
    assert set(registry.catalog()) == registry.names() == {"current"}
    assert registry.describe("missing") == {}


def test_existing_atr_policy_stored_compatibility_is_preserved():
    import mangrove_kb.signals  # noqa: F401

    descriptor = RuleRegistry.describe("atr_trailing_stop_long")
    assert descriptor["status"] == "disabled"
    assert not descriptor["composable"]
    assert descriptor["executable"] and descriptor["legacy_compatible"]
    assert "Stored strategies" in descriptor["reason"]
    frame = pd.DataFrame({"high": [10.0] * 50, "low": [9.0] * 50, "close": [9.5] * 50})
    with pytest.warns(DeprecationWarning):
        assert isinstance(
            RuleRegistry.evaluate({"name": "atr_trailing_stop_long"}, frame), bool
        )


def test_malformed_descriptive_metadata_cannot_enable_disabled_signal(
    isolated_registry,
):
    registry = isolated_registry

    @registry.register("malformed_disabled")
    def malformed_disabled(df):
        """Missing required Type and Requires metadata.

        Disabled: True
        Disabled-Reason: Not available for runtime use.
        """
        pytest.fail("disabled implementation executed")

    descriptor = registry.describe("malformed_disabled")
    assert descriptor["status"] == "disabled"
    assert not descriptor["composable"]
    assert not descriptor["executable"]
    assert descriptor["reason"] == "Not available for runtime use."
    with pytest.raises(ValueError, match="disabled for execution"):
        malformed_disabled(pd.DataFrame())
    with pytest.raises(ValueError, match="disabled for execution"):
        registry.evaluate({"name": "malformed_disabled"}, pd.DataFrame())
