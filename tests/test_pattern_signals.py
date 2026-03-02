"""
Standalone validation tests for pattern signal docstrings.

Parses all signal functions in the patterns module using the docstring
parser and validates structural correctness: required tags, param types,
range values, and defaults. Does not depend on signals_metadata.json.

Usage:
    pytest tests/test_pattern_signals.py -v
"""

import pytest

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import patterns as pattern_signals
from mangrove_kb.docstring_parser import (
    parse_signal_docstring,
    parse_all_signals,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def parsed_patterns() -> dict:
    """Parse all pattern signal docstrings."""
    return parse_all_signals([pattern_signals])


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

class TestPatternCoverage:
    """Verify all pattern signals are discovered and parseable."""

    EXPECTED_TRIGGER_COUNT = 32
    EXPECTED_FILTER_COUNT = 8
    EXPECTED_TOTAL = EXPECTED_TRIGGER_COUNT + EXPECTED_FILTER_COUNT

    def test_total_count(self, parsed_patterns):
        assert len(parsed_patterns) == self.EXPECTED_TOTAL, (
            f"Expected {self.EXPECTED_TOTAL} pattern signals, "
            f"got {len(parsed_patterns)}: {sorted(parsed_patterns.keys())}"
        )

    def test_trigger_count(self, parsed_patterns):
        triggers = [k for k, v in parsed_patterns.items() if v["type"] == "TRIGGER"]
        assert len(triggers) == self.EXPECTED_TRIGGER_COUNT, (
            f"Expected {self.EXPECTED_TRIGGER_COUNT} TRIGGER signals, "
            f"got {len(triggers)}: {sorted(triggers)}"
        )

    def test_filter_count(self, parsed_patterns):
        filters = [k for k, v in parsed_patterns.items() if v["type"] == "FILTER"]
        assert len(filters) == self.EXPECTED_FILTER_COUNT, (
            f"Expected {self.EXPECTED_FILTER_COUNT} FILTER signals, "
            f"got {len(filters)}: {sorted(filters)}"
        )

    def test_all_registered_in_registry(self, parsed_patterns):
        """Every parsed signal must be in RuleRegistry."""
        for name in parsed_patterns:
            assert name in RuleRegistry._registry, (
                f"Signal '{name}' parsed but not in RuleRegistry"
            )


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------

class TestPatternFields:
    """Validate required fields in every parsed pattern signal."""

    def test_all_have_type(self, parsed_patterns):
        for name, meta in parsed_patterns.items():
            assert "type" in meta, f"{name} missing 'type'"
            assert meta["type"] in ("TRIGGER", "FILTER"), (
                f"{name} has invalid type: {meta['type']}"
            )

    def test_all_have_requires(self, parsed_patterns):
        for name, meta in parsed_patterns.items():
            assert "requires" in meta, f"{name} missing 'requires'"
            assert isinstance(meta["requires"], list), (
                f"{name} 'requires' should be a list"
            )

    def test_all_have_description(self, parsed_patterns):
        for name, meta in parsed_patterns.items():
            assert "description" in meta, f"{name} missing 'description'"
            assert len(meta["description"]) > 10, (
                f"{name} description too short: '{meta['description']}'"
            )

    def test_all_have_rule_name(self, parsed_patterns):
        for name, meta in parsed_patterns.items():
            assert "rule_name" in meta, f"{name} missing 'rule_name'"
            assert meta["rule_name"] == name, (
                f"{name} rule_name mismatch: {meta['rule_name']}"
            )


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

class TestPatternParams:
    """Validate parameter metadata for pattern signals."""

    def test_params_are_dicts(self, parsed_patterns):
        for name, meta in parsed_patterns.items():
            assert "params" in meta, f"{name} missing 'params'"
            assert isinstance(meta["params"], dict), (
                f"{name} 'params' should be a dict"
            )

    def test_param_types_valid(self, parsed_patterns):
        valid_types = {"int", "float", "str", "bool"}
        for name, meta in parsed_patterns.items():
            for pname, pspec in meta.get("params", {}).items():
                assert "type" in pspec, (
                    f"{name}.{pname} missing 'type'"
                )
                assert pspec["type"] in valid_types, (
                    f"{name}.{pname} has invalid type: {pspec['type']}"
                )

    def test_numeric_params_have_range(self, parsed_patterns):
        """All int/float params must have min and max."""
        for name, meta in parsed_patterns.items():
            for pname, pspec in meta.get("params", {}).items():
                if pspec["type"] in ("int", "float"):
                    assert "min" in pspec, (
                        f"{name}.{pname} ({pspec['type']}) missing 'min'"
                    )
                    assert "max" in pspec, (
                        f"{name}.{pname} ({pspec['type']}) missing 'max'"
                    )
                    assert pspec["min"] < pspec["max"], (
                        f"{name}.{pname} min ({pspec['min']}) >= max ({pspec['max']})"
                    )

    def test_optional_params_have_default(self, parsed_patterns):
        """Optional params must have a default value."""
        for name, meta in parsed_patterns.items():
            for pname, pspec in meta.get("params", {}).items():
                if pspec.get("optional"):
                    assert "default" in pspec, (
                        f"{name}.{pname} is optional but missing 'default'"
                    )

    def test_defaults_within_range(self, parsed_patterns):
        """Default values must be within [min, max]."""
        for name, meta in parsed_patterns.items():
            for pname, pspec in meta.get("params", {}).items():
                if "default" not in pspec or "min" not in pspec:
                    continue
                default = pspec["default"]
                pmin = pspec["min"]
                pmax = pspec["max"]
                assert pmin <= default <= pmax, (
                    f"{name}.{pname} default {default} outside "
                    f"range [{pmin}, {pmax}]"
                )

    def test_df_excluded(self, parsed_patterns):
        """The 'df' parameter must never appear in parsed params."""
        for name, meta in parsed_patterns.items():
            assert "df" not in meta.get("params", {}), (
                f"{name} has 'df' in params -- should be excluded"
            )


# ---------------------------------------------------------------------------
# Requires field validation
# ---------------------------------------------------------------------------

class TestPatternRequires:
    """Validate Requires fields match expected OHLC columns."""

    VALID_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}

    def test_requires_valid_columns(self, parsed_patterns):
        for name, meta in parsed_patterns.items():
            for col in meta["requires"]:
                assert col in self.VALID_COLUMNS, (
                    f"{name} requires unknown column: '{col}'"
                )

    def test_triggers_require_at_least_one(self, parsed_patterns):
        """All TRIGGER signals must require at least one data column."""
        for name, meta in parsed_patterns.items():
            if meta["type"] == "TRIGGER":
                assert len(meta["requires"]) > 0, (
                    f"TRIGGER signal {name} has empty Requires"
                )


# ---------------------------------------------------------------------------
# Spot-check specific signals
# ---------------------------------------------------------------------------

class TestSpecificPatterns:
    """Spot-check individual pattern signals for correct metadata."""

    def test_doji_trigger(self, parsed_patterns):
        meta = parsed_patterns["doji_trigger"]
        assert meta["type"] == "TRIGGER"
        assert meta["requires"] == ["Open", "High", "Low", "Close"]
        assert "body_threshold" in meta["params"]
        p = meta["params"]["body_threshold"]
        assert p["type"] == "float"
        assert p["default"] == 0.1

    def test_hammer_trigger(self, parsed_patterns):
        meta = parsed_patterns["hammer_trigger"]
        assert meta["type"] == "TRIGGER"
        assert set(meta["params"].keys()) == {"wick_ratio", "upper_wick_max"}

    def test_hanging_man_trigger(self, parsed_patterns):
        meta = parsed_patterns["hanging_man_trigger"]
        assert meta["type"] == "TRIGGER"
        assert set(meta["params"].keys()) == {"wick_ratio", "upper_wick_max"}

    def test_inverted_hammer_trigger(self, parsed_patterns):
        meta = parsed_patterns["inverted_hammer_trigger"]
        assert meta["type"] == "TRIGGER"
        assert set(meta["params"].keys()) == {"wick_ratio", "lower_wick_max"}

    def test_bullish_engulfing_trigger(self, parsed_patterns):
        meta = parsed_patterns["bullish_engulfing_trigger"]
        assert meta["type"] == "TRIGGER"
        assert meta["requires"] == ["Open", "Close"]
        assert meta["params"] == {}

    def test_nr7_trigger(self, parsed_patterns):
        meta = parsed_patterns["nr7_trigger"]
        assert meta["type"] == "TRIGGER"
        assert meta["requires"] == ["High", "Low"]
        p = meta["params"]["lookback"]
        assert p["type"] == "int"
        assert p["default"] == 7

    def test_bullish_pattern_recent(self, parsed_patterns):
        meta = parsed_patterns["bullish_pattern_recent"]
        assert meta["type"] == "FILTER"
        assert "lookback" in meta["params"]

    def test_indecision_pattern_recent(self, parsed_patterns):
        meta = parsed_patterns["indecision_pattern_recent"]
        assert meta["type"] == "FILTER"
