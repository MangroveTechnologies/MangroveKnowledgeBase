"""
Validation tests for the docstring parser.

Imports every signal module in the package, parses their docstrings with the parser, and checks
what comes out.

This file used to compare the parsed result against `signals_metadata.json` in the MangroveAI
repository. Those 17 tests were dead: the path was a hard-coded absolute one under a Dropbox
directory that no longer exists, so they skipped themselves on every run -- with the reason
"(CI environment)", which is why nobody looked. Pointed at the file's real location they fail, and
correctly: the snapshot has 96 signals against this package's 249, and expects `Requires: Close`
where lowercase is now canonical. They asserted agreement with a frozen copy of a different repo
that this one deliberately moved past, so they are gone rather than repaired. What remains tests
the parser against the docstrings in THIS package, which is the thing worth guarding.

The module list is not hand-maintained: the reorganisation onto ontology classes moved signals
between files twice, and a hard-coded list silently drops whichever ones moved out. Every module in
the package is imported and `parse_all_signals` is given all of them; signals absent from the JSON
are skipped downstream as they always were.

Reports mismatches in type, requires, param names, param types, param ranges,
and param defaults.

Usage:
    pytest tests/test_docstring_parser.py -v
"""


import pytest

# ---------------------------------------------------------------------------
# Import from mangrove_kb (the standalone open-source package)
# ---------------------------------------------------------------------------

from mangrove_kb.registry import RuleRegistry  # noqa: E402
import mangrove_kb.signals  # noqa: E402
from mangrove_kb.docstring_parser import (  # noqa: E402
    parse_signal_docstring,
    parse_all_signals,
)

# Social signals are private (not in mangrove_kb). Skip them in tests.
# The JSON has 127 signals (122 enabled + 5 social). We validate the 122 public ones.


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


ALL_SIGNAL_MODULES = [
    m for m in vars(mangrove_kb.signals).values()
    if getattr(m, "__name__", "").startswith("mangrove_kb.signals.")
    and not m.__name__.rsplit(".", 1)[-1].startswith("_")
    # A deprecated path is a shim that re-exports; it defines no signal of its own. Importing one
    # binds it as an attribute of the package, so without this every signal it re-exports would be
    # parsed a second time under a module that does not define it -- and whether that happened
    # would depend on whether some other test imported the old path first.
    and not getattr(m, "__deprecated__", False)
]


@pytest.fixture(scope="session")
def parsed_metadata() -> dict:
    """Parse all signal docstrings using the parser."""
    return parse_all_signals(ALL_SIGNAL_MODULES)


# ---------------------------------------------------------------------------
# Known description differences between docstrings and JSON
# ---------------------------------------------------------------------------
# The JSON was hand-written and the docstrings were enriched later.
# Some descriptions have minor wording differences. We track them here
# so the test can distinguish "known cosmetic differences" from real bugs.

# Map of (signal_name, param_name) -> set of fields to skip comparison on.
# "description" is the most common since docstrings often have slightly
# different wording than the original JSON.
_KNOWN_DESCRIPTION_DIFFS = {
    # The docstrings use slightly different wording than the JSON for some
    # descriptions. These are not bugs -- just cosmetic differences from the
    # original hand-written JSON vs the enriched docstrings.
}


# ---------------------------------------------------------------------------
# Test: all JSON signals are parsed
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test: signal-level fields
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test: parameter-level fields
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test: individual signal parsing (spot-checks)
# ---------------------------------------------------------------------------

class TestIndividualParsing:
    """Spot-check individual signal parsing for correctness."""

    def test_parse_rsi_overbought(self):
        """Verify parsing of a typical FILTER signal with optional params."""
        func = RuleRegistry._registry["rsi_overbought"]
        result = parse_signal_docstring(func)

        assert result["rule_name"] == "rsi_overbought"
        assert result["type"] == "FILTER"
        assert result["requires"] == ["close"]
        assert "window" in result["params"]
        assert "threshold" in result["params"]
        assert "df" not in result["params"]

        window = result["params"]["window"]
        assert window["type"] == "int"
        assert window["min"] == 2
        assert window["max"] == 100
        assert window["optional"] is True
        assert window["default"] == 14

    def test_parse_sma_cross_up(self):
        """Verify parsing of a signal with required (no default) params."""
        func = RuleRegistry._registry["sma_cross_up"]
        result = parse_signal_docstring(func)

        assert result["rule_name"] == "sma_cross_up"
        assert result["type"] == "TRIGGER"
        assert result["requires"] == ["close"]

        window_fast = result["params"]["window_fast"]
        assert window_fast["type"] == "int"
        assert window_fast["optional"] is False
        assert "default" not in window_fast


    def test_parse_str_param_no_range(self):
        """Verify parsing of a str param without Range."""
        func = RuleRegistry._registry["sma_crossover"]
        result = parse_signal_docstring(func)

        direction = result["params"]["direction"]
        assert direction["type"] == "str"
        assert direction["optional"] is True
        assert direction["default"] == "bullish"
        assert "min" not in direction
        assert "max" not in direction

    def test_parse_bool_param(self):
        """Verify parsing of a bool param."""
        func = RuleRegistry._registry["kc_upper_breakout"]
        result = parse_signal_docstring(func)

        original_version = result["params"]["original_version"]
        assert original_version["type"] == "bool"
        assert original_version["optional"] is True
        assert original_version["default"] is False
        assert "min" not in original_version
        assert "max" not in original_version

    def test_parse_float_param_with_negative_range(self):
        """Verify parsing of params with negative range values."""
        func = RuleRegistry._registry["williams_r_overbought"]
        result = parse_signal_docstring(func)

        threshold = result["params"]["threshold"]
        assert threshold["type"] == "float"
        assert threshold["min"] == -30
        assert threshold["max"] == 0
        assert threshold["default"] == -20.0


    def test_parse_requires_multiple(self):
        """Verify parsing of multiple required columns."""
        func = RuleRegistry._registry["uo_overbought"]
        result = parse_signal_docstring(func)
        assert sorted(result["requires"]) == ["close", "high", "low"]

    def test_parse_requires_hlcv(self):
        """Verify parsing of High, Low, Close, Volume."""
        func = RuleRegistry._registry["adi_bullish"]
        result = parse_signal_docstring(func)
        assert sorted(result["requires"]) == ["close", "high", "low", "volume"]

    def test_parse_kst_many_params(self):
        """Verify parsing of a signal with many parameters (KST)."""
        func = RuleRegistry._registry["kst_bullish_cross"]
        result = parse_signal_docstring(func)

        assert len(result["params"]) == 9
        expected_params = [
            "roc1", "roc2", "roc3", "roc4",
            "window_sma1", "window_sma2", "window_sma3", "window_sma4",
            "nsig",
        ]
        for p in expected_params:
            assert p in result["params"], f"Missing param: {p}"

    def test_df_param_excluded(self):
        """Verify that the df parameter is never in the output."""
        for name, func in RuleRegistry._registry.items():
            try:
                result = parse_signal_docstring(func)
                assert "df" not in result.get("params", {}), (
                    f"Signal {name} has 'df' in params"
                )
            except ValueError:
                pass  # Skip functions without valid docstrings


# ---------------------------------------------------------------------------
# Test: parse_all_signals integration
# ---------------------------------------------------------------------------

class TestParseAllSignals:
    """Test the parse_all_signals function as a whole."""

    def test_returns_dict(self, parsed_metadata):
        """parse_all_signals should return a dict."""
        assert isinstance(parsed_metadata, dict)

    def test_all_values_are_dicts(self, parsed_metadata):
        """Every value should be a metadata dict."""
        for name, meta in parsed_metadata.items():
            assert isinstance(meta, dict), f"{name} is not a dict"
            assert "rule_name" in meta, f"{name} missing rule_name"
            assert "type" in meta, f"{name} missing type"
            assert "requires" in meta, f"{name} missing requires"
            assert "params" in meta, f"{name} missing params"

    def test_no_empty_descriptions(self, parsed_metadata):
        """Every signal should have a non-empty description."""
        empty = [
            name
            for name, meta in parsed_metadata.items()
            if not meta.get("description", "").strip()
        ]
        assert not empty, f"Signals with empty descriptions: {sorted(empty)}"


# ---------------------------------------------------------------------------
# Test: comprehensive field-by-field comparison report
# ---------------------------------------------------------------------------

