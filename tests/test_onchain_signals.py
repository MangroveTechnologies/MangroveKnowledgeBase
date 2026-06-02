"""
Validation and behavioral tests for on-chain signals.

Parses all signal functions in the onchain module using the docstring parser
and validates structural correctness (required tags, param types, ranges,
defaults), then exercises each signal against synthetic on-chain data to
confirm it fires (and stays quiet) under the expected conditions.

Usage:
    pytest tests/test_onchain_signals.py -v
"""

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import onchain as onchain_signals
from mangrove_kb.docstring_parser import parse_all_signals


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def parsed_onchain() -> dict:
    """Parse all on-chain signal docstrings."""
    return parse_all_signals([onchain_signals])


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

class TestOnChainCoverage:
    """Verify all on-chain signals are discovered and parseable."""

    EXPECTED_TRIGGER_COUNT = 5
    EXPECTED_FILTER_COUNT = 7
    EXPECTED_TOTAL = EXPECTED_TRIGGER_COUNT + EXPECTED_FILTER_COUNT

    def test_total_count(self, parsed_onchain):
        assert len(parsed_onchain) == self.EXPECTED_TOTAL, (
            f"Expected {self.EXPECTED_TOTAL} on-chain signals, "
            f"got {len(parsed_onchain)}: {sorted(parsed_onchain.keys())}"
        )

    def test_trigger_count(self, parsed_onchain):
        triggers = [k for k, v in parsed_onchain.items() if v["type"] == "TRIGGER"]
        assert len(triggers) == self.EXPECTED_TRIGGER_COUNT, sorted(triggers)

    def test_filter_count(self, parsed_onchain):
        filters = [k for k, v in parsed_onchain.items() if v["type"] == "FILTER"]
        assert len(filters) == self.EXPECTED_FILTER_COUNT, sorted(filters)

    def test_all_registered(self, parsed_onchain):
        for name in parsed_onchain:
            assert name in RuleRegistry._registry, (
                f"Signal '{name}' parsed but not in RuleRegistry"
            )


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------

class TestOnChainMetadata:
    """Validate required fields and parameter metadata."""

    VALID_COLUMNS = {
        "SmartMoneyNetflow",
        "SmartMoneyHoldings",
        "ExchangeNetflow",
        "WhaleNetInflow",
        "TokenHolderCount",
        "HolderConcentration",
    }

    def test_type_and_requires(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            assert meta["type"] in ("TRIGGER", "FILTER"), name
            assert isinstance(meta["requires"], list) and meta["requires"], (
                f"{name} must require at least one column"
            )
            for col in meta["requires"]:
                assert col in self.VALID_COLUMNS, (
                    f"{name} requires unknown column: '{col}'"
                )

    def test_description_present(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            assert len(meta["description"]) > 10, name

    def test_numeric_params_have_valid_range(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            for pname, pspec in meta.get("params", {}).items():
                if pspec["type"] in ("int", "float"):
                    assert "min" in pspec and "max" in pspec, f"{name}.{pname}"
                    assert pspec["min"] < pspec["max"], f"{name}.{pname}"

    def test_defaults_within_range(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            for pname, pspec in meta.get("params", {}).items():
                if "default" in pspec and "min" in pspec:
                    assert pspec["min"] <= pspec["default"] <= pspec["max"], (
                        f"{name}.{pname} default {pspec['default']} out of range"
                    )

    def test_df_excluded(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            assert "df" not in meta.get("params", {}), name


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------

def _evaluate(name, df, params=None):
    return RuleRegistry.evaluate({"name": name, "params": params or {}}, df)


class TestOnChainBehavior:
    """Exercise each signal against synthetic data with a known outcome."""

    def test_smart_money_inflow_spike(self):
        flow = [10.0] * 25 + [500.0]  # large spike on the last bar
        df = pd.DataFrame({"SmartMoneyNetflow": flow})
        assert _evaluate("smart_money_inflow_spike", df, {"window": 20, "z_threshold": 2.0})

        flat = pd.DataFrame({"SmartMoneyNetflow": [10.0] * 26})
        assert not _evaluate("smart_money_inflow_spike", flat)

    def test_smart_money_holdings_cross(self):
        # Holdings sit below their MA then jump above it on the last bar.
        holdings = [100.0] * 25 + [400.0]
        df = pd.DataFrame({"SmartMoneyHoldings": holdings})
        assert _evaluate("smart_money_holdings_cross", df, {"window": 20})

    def test_smart_money_net_positive(self):
        assert _evaluate(
            "smart_money_net_positive",
            pd.DataFrame({"SmartMoneyNetflow": [5.0] * 14}),
        )
        assert not _evaluate(
            "smart_money_net_positive",
            pd.DataFrame({"SmartMoneyNetflow": [-5.0] * 14}),
        )

    def test_smart_money_holdings_rising(self):
        rising = pd.DataFrame({"SmartMoneyHoldings": list(np.arange(20, dtype=float))})
        assert _evaluate("smart_money_holdings_rising", rising, {"window": 14})
        falling = pd.DataFrame({"SmartMoneyHoldings": list(np.arange(20, 0, -1, dtype=float))})
        assert not _evaluate("smart_money_holdings_rising", falling, {"window": 14})

    def test_exchange_outflow_spike(self):
        flow = [0.0] * 25 + [-500.0]  # large outflow on the last bar
        df = pd.DataFrame({"ExchangeNetflow": flow})
        assert _evaluate("exchange_outflow_spike", df, {"window": 20, "z_threshold": 2.0})
        # A large *inflow* must not fire this bullish signal.
        inflow = pd.DataFrame({"ExchangeNetflow": [0.0] * 25 + [500.0]})
        assert not _evaluate("exchange_outflow_spike", inflow)

    def test_exchange_net_outflow(self):
        assert _evaluate(
            "exchange_net_outflow",
            pd.DataFrame({"ExchangeNetflow": [-3.0] * 14}),
        )
        assert not _evaluate(
            "exchange_net_outflow",
            pd.DataFrame({"ExchangeNetflow": [3.0] * 14}),
        )

    def test_whale_accumulation_trigger(self):
        # Net flow negative for a stretch, then positive bars fill the window
        # so the smoothed flow crosses zero on the last bar.
        flow = [-10.0] * 10 + [5.0, 5.0, 5.0]
        df = pd.DataFrame({"WhaleNetInflow": flow})
        assert _evaluate("whale_accumulation_trigger", df, {"window": 3})

    def test_whale_net_accumulation(self):
        assert _evaluate(
            "whale_net_accumulation",
            pd.DataFrame({"WhaleNetInflow": [2.0] * 14}),
        )
        assert not _evaluate(
            "whale_net_accumulation",
            pd.DataFrame({"WhaleNetInflow": [-2.0] * 14}),
        )

    def test_holder_growth_breakout(self):
        counts = list(range(100, 130)) + [200]  # new high on the last bar
        df = pd.DataFrame({"TokenHolderCount": [float(c) for c in counts]})
        assert _evaluate("holder_growth_breakout", df, {"window": 30})
        flat = pd.DataFrame({"TokenHolderCount": [100.0] * 31})
        assert not _evaluate("holder_growth_breakout", flat, {"window": 30})

    def test_holder_base_expanding(self):
        rising = pd.DataFrame({"TokenHolderCount": list(np.arange(100, 120, dtype=float))})
        assert _evaluate("holder_base_expanding", rising, {"window": 14})

    def test_holder_concentration_low(self):
        low = pd.DataFrame({"HolderConcentration": [0.3]})
        assert _evaluate("holder_concentration_low", low, {"threshold": 0.5})
        high = pd.DataFrame({"HolderConcentration": [0.8]})
        assert not _evaluate("holder_concentration_low", high, {"threshold": 0.5})

    def test_holder_concentration_falling(self):
        falling = pd.DataFrame({"HolderConcentration": list(np.linspace(0.8, 0.4, 20))})
        assert _evaluate("holder_concentration_falling", falling, {"window": 14})

    def test_missing_column_returns_false(self):
        """Every signal must fail closed when its column is absent."""
        empty = pd.DataFrame({"Close": [1.0, 2.0, 3.0]})
        for name, meta in parse_all_signals([onchain_signals]).items():
            result = _evaluate(name, empty)
            assert result is False, f"{name} should return False on missing data"
