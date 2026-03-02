"""
Validation tests for the docstring parser.

Loads the original signals_metadata.json, imports all 5 signal modules
(momentum, trend, volume, volatility, social), parses their docstrings
using the parser, and compares the parsed output to the JSON for every signal.

Reports mismatches in type, requires, param names, param types, param ranges,
and param defaults.

Usage:
    pytest tests/test_docstring_parser.py -v
"""

import json

import pytest

# ---------------------------------------------------------------------------
# Import from mangrove_kb (the standalone open-source package)
# ---------------------------------------------------------------------------

from mangrove_kb.registry import RuleRegistry  # noqa: E402
from mangrove_kb.signals import momentum as momentum_signals  # noqa: E402
from mangrove_kb.signals import trend as trend_signals  # noqa: E402
from mangrove_kb.signals import volume as volume_signals  # noqa: E402
from mangrove_kb.signals import volatility as volatility_signals  # noqa: E402
from mangrove_kb.docstring_parser import (  # noqa: E402
    parse_signal_docstring,
    parse_all_signals,
)

# Social signals are private (not in mangrove_kb). Skip them in tests.
# The JSON has 127 signals (122 enabled + 5 social). We validate the 122 public ones.
SOCIAL_SIGNALS = {
    "x_user_post_trigger",
    "x_topic_mention_trigger",
    "x_social_sentiment_trigger",
    "x_user_influence_filter",
    "x_topic_sentiment_filter",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

METADATA_JSON_PATH = (
    "<LOCAL_PATH_REDACTED>"
    "MangroveAI/src/MangroveAI/domains/signals/signals_metadata.json"
)

ALL_SIGNAL_MODULES = [
    momentum_signals,
    trend_signals,
    volume_signals,
    volatility_signals,
]


@pytest.fixture(scope="session")
def json_metadata() -> dict:
    """Load the original signals_metadata.json, excluding social signals."""
    with open(METADATA_JSON_PATH, "r") as f:
        all_meta = json.load(f)
    return {k: v for k, v in all_meta.items() if k not in SOCIAL_SIGNALS}


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

class TestParserCoverage:
    """Verify that every signal in the JSON is parsed from docstrings."""

    def test_all_json_signals_are_parsed(self, json_metadata, parsed_metadata):
        """Every signal in signals_metadata.json should be found by the parser."""
        json_names = set(json_metadata.keys())
        parsed_names = set(parsed_metadata.keys())

        missing = json_names - parsed_names
        assert not missing, (
            f"Signals in JSON but not parsed from docstrings: {sorted(missing)}"
        )

    def test_no_extra_signals_parsed(self, json_metadata, parsed_metadata):
        """The parser should not find signals that are not in the JSON."""
        json_names = set(json_metadata.keys())
        parsed_names = set(parsed_metadata.keys())

        extra = parsed_names - json_names
        assert not extra, (
            f"Signals parsed from docstrings but not in JSON: {sorted(extra)}"
        )

    def test_signal_count_matches(self, json_metadata, parsed_metadata):
        """Total number of signals should match."""
        assert len(parsed_metadata) == len(json_metadata), (
            f"Parsed {len(parsed_metadata)} signals, "
            f"JSON has {len(json_metadata)}"
        )


# ---------------------------------------------------------------------------
# Test: signal-level fields
# ---------------------------------------------------------------------------

class TestSignalFields:
    """Validate type, requires, and description for each signal."""

    def test_type_matches(self, json_metadata, parsed_metadata):
        """Signal type (TRIGGER/FILTER) should match for every signal."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            expected = json_metadata[name]["type"]
            actual = parsed_metadata[name]["type"]
            if expected != actual:
                mismatches.append(
                    f"  {name}: expected type={expected!r}, got {actual!r}"
                )
        assert not mismatches, (
            "Signal type mismatches:\n" + "\n".join(mismatches)
        )

    def test_requires_matches(self, json_metadata, parsed_metadata):
        """Required columns should match for every signal."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            expected = sorted(json_metadata[name].get("requires", []))
            actual = sorted(parsed_metadata[name].get("requires", []))
            if expected != actual:
                mismatches.append(
                    f"  {name}: expected requires={expected}, got {actual}"
                )
        assert not mismatches, (
            "Requires mismatches:\n" + "\n".join(mismatches)
        )

    def test_rule_name_matches(self, json_metadata, parsed_metadata):
        """Rule name should match the JSON key for every signal."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            expected = json_metadata[name]["rule_name"]
            actual = parsed_metadata[name]["rule_name"]
            if expected != actual:
                mismatches.append(
                    f"  {name}: expected rule_name={expected!r}, got {actual!r}"
                )
        assert not mismatches, (
            "Rule name mismatches:\n" + "\n".join(mismatches)
        )

    def test_disabled_flag_matches(self, json_metadata, parsed_metadata):
        """Disabled flag should match for every signal."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            expected_disabled = json_metadata[name].get("disabled", False)
            actual_disabled = parsed_metadata[name].get("disabled", False)
            if expected_disabled != actual_disabled:
                mismatches.append(
                    f"  {name}: expected disabled={expected_disabled}, "
                    f"got {actual_disabled}"
                )
        assert not mismatches, (
            "Disabled flag mismatches:\n" + "\n".join(mismatches)
        )

    def test_disabled_reason_matches(self, json_metadata, parsed_metadata):
        """Disabled reason should match for disabled signals."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            expected = json_metadata[name].get("disabled_reason", "")
            actual = parsed_metadata[name].get("disabled_reason", "")
            if expected != actual:
                mismatches.append(
                    f"  {name}: expected disabled_reason={expected!r}, "
                    f"got {actual!r}"
                )
        assert not mismatches, (
            "Disabled reason mismatches:\n" + "\n".join(mismatches)
        )


# ---------------------------------------------------------------------------
# Test: parameter-level fields
# ---------------------------------------------------------------------------

class TestParamFields:
    """Validate parameter names, types, ranges, and defaults."""

    def test_param_names_match(self, json_metadata, parsed_metadata):
        """Parameter names should match for every signal."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            expected_params = set(json_metadata[name].get("params", {}).keys())
            actual_params = set(parsed_metadata[name].get("params", {}).keys())
            if expected_params != actual_params:
                missing = expected_params - actual_params
                extra = actual_params - expected_params
                msg = f"  {name}:"
                if missing:
                    msg += f" missing={sorted(missing)}"
                if extra:
                    msg += f" extra={sorted(extra)}"
                mismatches.append(msg)
        assert not mismatches, (
            "Param name mismatches:\n" + "\n".join(mismatches)
        )

    def test_param_types_match(self, json_metadata, parsed_metadata):
        """Parameter types should match for every parameter."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            for pname, pmeta in json_metadata[name].get("params", {}).items():
                if pname not in parsed_metadata[name].get("params", {}):
                    continue
                expected = pmeta["type"]
                actual = parsed_metadata[name]["params"][pname]["type"]
                if expected != actual:
                    mismatches.append(
                        f"  {name}.{pname}: expected type={expected!r}, "
                        f"got {actual!r}"
                    )
        assert not mismatches, (
            "Param type mismatches:\n" + "\n".join(mismatches)
        )

    def test_param_optional_matches(self, json_metadata, parsed_metadata):
        """Parameter optional flag should match for every parameter."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            for pname, pmeta in json_metadata[name].get("params", {}).items():
                if pname not in parsed_metadata[name].get("params", {}):
                    continue
                expected = pmeta.get("optional", False)
                actual = parsed_metadata[name]["params"][pname].get(
                    "optional", False
                )
                if expected != actual:
                    mismatches.append(
                        f"  {name}.{pname}: expected optional={expected}, "
                        f"got {actual}"
                    )
        assert not mismatches, (
            "Param optional mismatches:\n" + "\n".join(mismatches)
        )

    def test_param_defaults_match(self, json_metadata, parsed_metadata):
        """Parameter defaults should match for every parameter that has one."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            for pname, pmeta in json_metadata[name].get("params", {}).items():
                if pname not in parsed_metadata[name].get("params", {}):
                    continue
                if "default" not in pmeta:
                    continue
                expected = pmeta["default"]
                actual_pmeta = parsed_metadata[name]["params"][pname]
                if "default" not in actual_pmeta:
                    mismatches.append(
                        f"  {name}.{pname}: expected default={expected!r}, "
                        f"but parsed has no default"
                    )
                    continue
                actual = actual_pmeta["default"]

                # Compare with type-aware tolerance for floats
                if isinstance(expected, float) and isinstance(actual, float):
                    if abs(expected - actual) > 1e-6:
                        mismatches.append(
                            f"  {name}.{pname}: expected default={expected}, "
                            f"got {actual}"
                        )
                elif expected != actual:
                    mismatches.append(
                        f"  {name}.{pname}: expected default={expected!r}, "
                        f"got {actual!r}"
                    )
        assert not mismatches, (
            "Param default mismatches:\n" + "\n".join(mismatches)
        )

    def test_param_min_matches(self, json_metadata, parsed_metadata):
        """Parameter min values should match for every parameter that has one."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            for pname, pmeta in json_metadata[name].get("params", {}).items():
                if pname not in parsed_metadata[name].get("params", {}):
                    continue
                if "min" not in pmeta:
                    continue
                expected = pmeta["min"]
                actual_pmeta = parsed_metadata[name]["params"][pname]
                if "min" not in actual_pmeta:
                    mismatches.append(
                        f"  {name}.{pname}: expected min={expected}, "
                        f"but parsed has no min"
                    )
                    continue
                actual = actual_pmeta["min"]

                # Compare with type-aware tolerance
                if isinstance(expected, float) and isinstance(actual, float):
                    if abs(expected - actual) > 1e-6:
                        mismatches.append(
                            f"  {name}.{pname}: expected min={expected}, "
                            f"got {actual}"
                        )
                elif expected != actual:
                    mismatches.append(
                        f"  {name}.{pname}: expected min={expected!r}, "
                        f"got {actual!r}"
                    )
        assert not mismatches, (
            "Param min mismatches:\n" + "\n".join(mismatches)
        )

    def test_param_max_matches(self, json_metadata, parsed_metadata):
        """Parameter max values should match for every parameter that has one."""
        mismatches = []
        for name in json_metadata:
            if name not in parsed_metadata:
                continue
            for pname, pmeta in json_metadata[name].get("params", {}).items():
                if pname not in parsed_metadata[name].get("params", {}):
                    continue
                if "max" not in pmeta:
                    continue
                expected = pmeta["max"]
                actual_pmeta = parsed_metadata[name]["params"][pname]
                if "max" not in actual_pmeta:
                    mismatches.append(
                        f"  {name}.{pname}: expected max={expected}, "
                        f"but parsed has no max"
                    )
                    continue
                actual = actual_pmeta["max"]

                # Compare with type-aware tolerance
                if isinstance(expected, float) and isinstance(actual, float):
                    if abs(expected - actual) > 1e-6:
                        mismatches.append(
                            f"  {name}.{pname}: expected max={expected}, "
                            f"got {actual}"
                        )
                elif expected != actual:
                    mismatches.append(
                        f"  {name}.{pname}: expected max={expected!r}, "
                        f"got {actual!r}"
                    )
        assert not mismatches, (
            "Param max mismatches:\n" + "\n".join(mismatches)
        )


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
        assert result["requires"] == ["Close"]
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
        assert result["requires"] == ["Close"]

        window_fast = result["params"]["window_fast"]
        assert window_fast["type"] == "int"
        assert window_fast["optional"] is False
        assert "default" not in window_fast

    @pytest.mark.skip(reason="Social signals are private, not in mangrove_kb")
    def test_parse_disabled_signal(self):
        """Verify parsing of a disabled social signal."""
        pass

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

    @pytest.mark.skip(reason="Social signals are private, not in mangrove_kb")
    def test_parse_requires_none(self):
        """Verify that Requires: None produces an empty list."""
        pass

    def test_parse_requires_multiple(self):
        """Verify parsing of multiple required columns."""
        func = RuleRegistry._registry["uo_overbought"]
        result = parse_signal_docstring(func)
        assert sorted(result["requires"]) == ["Close", "High", "Low"]

    def test_parse_requires_hlcv(self):
        """Verify parsing of High, Low, Close, Volume."""
        func = RuleRegistry._registry["adi_bullish"]
        result = parse_signal_docstring(func)
        assert sorted(result["requires"]) == ["Close", "High", "Low", "Volume"]

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

class TestComprehensiveComparison:
    """Generate a detailed comparison report between parsed and JSON metadata."""

    def test_full_comparison(self, json_metadata, parsed_metadata):
        """Compare every field of every signal and report all mismatches.

        This is the master comparison test. It checks:
        - type
        - requires
        - disabled / disabled_reason
        - param names
        - param type, min, max, optional, default for each param
        """
        all_mismatches = []

        for name in sorted(json_metadata.keys()):
            if name not in parsed_metadata:
                all_mismatches.append(f"MISSING: {name} not in parsed output")
                continue

            jmeta = json_metadata[name]
            pmeta = parsed_metadata[name]

            # Type
            if jmeta.get("type") != pmeta.get("type"):
                all_mismatches.append(
                    f"{name}: type mismatch: "
                    f"json={jmeta.get('type')!r} vs "
                    f"parsed={pmeta.get('type')!r}"
                )

            # Requires
            if sorted(jmeta.get("requires", [])) != sorted(
                pmeta.get("requires", [])
            ):
                all_mismatches.append(
                    f"{name}: requires mismatch: "
                    f"json={sorted(jmeta.get('requires', []))} vs "
                    f"parsed={sorted(pmeta.get('requires', []))}"
                )

            # Disabled
            j_disabled = jmeta.get("disabled", False)
            p_disabled = pmeta.get("disabled", False)
            if j_disabled != p_disabled:
                all_mismatches.append(
                    f"{name}: disabled mismatch: "
                    f"json={j_disabled} vs parsed={p_disabled}"
                )

            # Disabled reason
            j_reason = jmeta.get("disabled_reason", "")
            p_reason = pmeta.get("disabled_reason", "")
            if j_disabled and j_reason != p_reason:
                all_mismatches.append(
                    f"{name}: disabled_reason mismatch: "
                    f"json={j_reason!r} vs parsed={p_reason!r}"
                )

            # Params
            j_params = jmeta.get("params", {})
            p_params = pmeta.get("params", {})

            j_pnames = set(j_params.keys())
            p_pnames = set(p_params.keys())

            if j_pnames != p_pnames:
                missing = j_pnames - p_pnames
                extra = p_pnames - j_pnames
                if missing:
                    all_mismatches.append(
                        f"{name}: missing params: {sorted(missing)}"
                    )
                if extra:
                    all_mismatches.append(
                        f"{name}: extra params: {sorted(extra)}"
                    )

            # Compare each common param
            for pname in sorted(j_pnames & p_pnames):
                jp = j_params[pname]
                pp = p_params[pname]

                # Type
                if jp.get("type") != pp.get("type"):
                    all_mismatches.append(
                        f"{name}.{pname}: type mismatch: "
                        f"json={jp.get('type')!r} vs "
                        f"parsed={pp.get('type')!r}"
                    )

                # Optional
                if jp.get("optional", False) != pp.get("optional", False):
                    all_mismatches.append(
                        f"{name}.{pname}: optional mismatch: "
                        f"json={jp.get('optional', False)} vs "
                        f"parsed={pp.get('optional', False)}"
                    )

                # Min
                if "min" in jp:
                    if "min" not in pp:
                        all_mismatches.append(
                            f"{name}.{pname}: min missing in parsed "
                            f"(json has {jp['min']})"
                        )
                    else:
                        j_min = jp["min"]
                        p_min = pp["min"]
                        if isinstance(j_min, float) and isinstance(
                            p_min, float
                        ):
                            if abs(j_min - p_min) > 1e-6:
                                all_mismatches.append(
                                    f"{name}.{pname}: min mismatch: "
                                    f"json={j_min} vs parsed={p_min}"
                                )
                        elif j_min != p_min:
                            all_mismatches.append(
                                f"{name}.{pname}: min mismatch: "
                                f"json={j_min!r} vs parsed={p_min!r}"
                            )

                # Max
                if "max" in jp:
                    if "max" not in pp:
                        all_mismatches.append(
                            f"{name}.{pname}: max missing in parsed "
                            f"(json has {jp['max']})"
                        )
                    else:
                        j_max = jp["max"]
                        p_max = pp["max"]
                        if isinstance(j_max, float) and isinstance(
                            p_max, float
                        ):
                            if abs(j_max - p_max) > 1e-6:
                                all_mismatches.append(
                                    f"{name}.{pname}: max mismatch: "
                                    f"json={j_max} vs parsed={p_max}"
                                )
                        elif j_max != p_max:
                            all_mismatches.append(
                                f"{name}.{pname}: max mismatch: "
                                f"json={j_max!r} vs parsed={p_max!r}"
                            )

                # Default
                if "default" in jp:
                    if "default" not in pp:
                        all_mismatches.append(
                            f"{name}.{pname}: default missing in parsed "
                            f"(json has {jp['default']!r})"
                        )
                    else:
                        j_def = jp["default"]
                        p_def = pp["default"]
                        if isinstance(j_def, float) and isinstance(
                            p_def, float
                        ):
                            if abs(j_def - p_def) > 1e-6:
                                all_mismatches.append(
                                    f"{name}.{pname}: default mismatch: "
                                    f"json={j_def} vs parsed={p_def}"
                                )
                        elif j_def != p_def:
                            all_mismatches.append(
                                f"{name}.{pname}: default mismatch: "
                                f"json={j_def!r} vs parsed={p_def!r}"
                            )

        # Final assertion
        if all_mismatches:
            report = "\n".join(f"  [{i+1}] {m}" for i, m in enumerate(all_mismatches))
            pytest.fail(
                f"\n{len(all_mismatches)} mismatch(es) found between "
                f"parsed docstrings and signals_metadata.json:\n{report}"
            )
