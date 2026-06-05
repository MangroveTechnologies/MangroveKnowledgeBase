"""
Validation and behavioral tests for on-chain signals.

Parses all signal functions in the onchain module and validates structural
correctness (required tags, param types, ranges, defaults), then exercises each
signal against synthetic on-chain data to confirm it fires (and stays quiet)
under the expected conditions.

Usage:
    pytest tests/test_onchain_signals.py -v
"""

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import onchain as onchain_signals
from mangrove_kb.docstring_parser import parse_all_signals


@pytest.fixture(scope="session")
def parsed_onchain() -> dict:
    return parse_all_signals([onchain_signals])


# --------------------------------------------------------------------------- #
# Coverage                                                                    #
# --------------------------------------------------------------------------- #
class TestOnChainCoverage:
    EXPECTED_TRIGGER_COUNT = 4
    EXPECTED_FILTER_COUNT = 6
    EXPECTED_TOTAL = EXPECTED_TRIGGER_COUNT + EXPECTED_FILTER_COUNT

    def test_total_count(self, parsed_onchain):
        assert len(parsed_onchain) == self.EXPECTED_TOTAL, sorted(parsed_onchain)

    def test_trigger_count(self, parsed_onchain):
        triggers = [k for k, v in parsed_onchain.items() if v["type"] == "TRIGGER"]
        assert len(triggers) == self.EXPECTED_TRIGGER_COUNT, sorted(triggers)

    def test_filter_count(self, parsed_onchain):
        filters = [k for k, v in parsed_onchain.items() if v["type"] == "FILTER"]
        assert len(filters) == self.EXPECTED_FILTER_COUNT, sorted(filters)

    def test_all_registered(self, parsed_onchain):
        for name in parsed_onchain:
            assert name in RuleRegistry._registry, name


# --------------------------------------------------------------------------- #
# Structural validation                                                       #
# --------------------------------------------------------------------------- #
class TestOnChainMetadata:
    VALID_COLUMNS = {
        "SmartMoneyNetflow",
        "SmartMoneyHoldings",
        "ExchangeNetflow",
        "WhaleNetInflow",
        "HolderConcentration",
    }

    def test_type_and_requires(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            assert meta["type"] in ("TRIGGER", "FILTER"), name
            assert isinstance(meta["requires"], list) and meta["requires"], name
            for col in meta["requires"]:
                assert col in self.VALID_COLUMNS, f"{name} requires unknown column '{col}'"

    def test_no_total_holder_count(self, parsed_onchain):
        # TokenHolderCount has no upstream series and must not be required by any signal.
        for name, meta in parsed_onchain.items():
            assert "TokenHolderCount" not in meta["requires"], name

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
                    assert pspec["min"] <= pspec["default"] <= pspec["max"], f"{name}.{pname}"

    def test_df_excluded(self, parsed_onchain):
        for name, meta in parsed_onchain.items():
            assert "df" not in meta.get("params", {}), name


# --------------------------------------------------------------------------- #
# Behavioral tests                                                            #
# --------------------------------------------------------------------------- #
def _evaluate(name, df, params=None):
    return RuleRegistry.evaluate({"name": name, "params": params or {}}, df)


def _noisy(center, n, seed=0):
    """Deterministic small-variance baseline (nonzero std so a z-score is defined)."""
    rng = np.random.default_rng(seed)
    return list(center + rng.normal(0, 1.0, n))


class TestOnChainBehavior:
    def test_smart_money_inflow_spike(self):
        flow = _noisy(10.0, 25) + [500.0]
        df = pd.DataFrame({"SmartMoneyNetflow": flow})
        assert _evaluate("smart_money_inflow_spike", df, {"window": 20, "z_threshold": 2.0})
        # No spike -> no fire.
        assert not _evaluate("smart_money_inflow_spike",
                             pd.DataFrame({"SmartMoneyNetflow": _noisy(10.0, 26, seed=1)}))

    def test_inflow_spike_excludes_current_bar_from_baseline(self):
        # Regression for the z-score bug: the latest bar must NOT be part of its own
        # baseline. Baseline = five tight bars (mean 10, std 1); a 12.5 spike is z=2.5
        # against the prior bars (fires), but only z~1.5 if the spike inflates its own
        # mean/std (the old buggy behavior), which would NOT fire.
        df = pd.DataFrame({"SmartMoneyNetflow": [9.0, 11.0, 9.0, 11.0, 10.0, 12.5]})
        assert _evaluate("smart_money_inflow_spike", df, {"window": 5, "z_threshold": 2.0})

    def test_smart_money_holdings_cross(self):
        holdings = [100.0] * 25 + [400.0]
        assert _evaluate("smart_money_holdings_cross",
                         pd.DataFrame({"SmartMoneyHoldings": holdings}), {"window": 20})

    def test_smart_money_net_positive(self):
        assert _evaluate("smart_money_net_positive", pd.DataFrame({"SmartMoneyNetflow": [5.0] * 14}))
        assert not _evaluate("smart_money_net_positive", pd.DataFrame({"SmartMoneyNetflow": [-5.0] * 14}))

    def test_smart_money_holdings_rising(self):
        assert _evaluate("smart_money_holdings_rising",
                         pd.DataFrame({"SmartMoneyHoldings": list(np.arange(20, dtype=float))}), {"window": 14})
        assert not _evaluate("smart_money_holdings_rising",
                             pd.DataFrame({"SmartMoneyHoldings": list(np.arange(20, 0, -1, dtype=float))}), {"window": 14})

    def test_exchange_outflow_spike(self):
        df = pd.DataFrame({"ExchangeNetflow": _noisy(0.0, 25, seed=2) + [-500.0]})
        assert _evaluate("exchange_outflow_spike", df, {"window": 20, "z_threshold": 2.0})
        # A large *inflow* must not fire this bullish (outflow) signal.
        assert not _evaluate("exchange_outflow_spike",
                             pd.DataFrame({"ExchangeNetflow": _noisy(0.0, 25, seed=3) + [500.0]}),
                             {"window": 20, "z_threshold": 2.0})

    def test_exchange_net_outflow(self):
        assert _evaluate("exchange_net_outflow", pd.DataFrame({"ExchangeNetflow": [-3.0] * 14}))
        assert not _evaluate("exchange_net_outflow", pd.DataFrame({"ExchangeNetflow": [3.0] * 14}))

    def test_whale_accumulation_trigger(self):
        flow = [-10.0] * 10 + [5.0, 5.0, 5.0]
        assert _evaluate("whale_accumulation_trigger", pd.DataFrame({"WhaleNetInflow": flow}), {"window": 3})

    def test_whale_net_accumulation(self):
        assert _evaluate("whale_net_accumulation", pd.DataFrame({"WhaleNetInflow": [2.0] * 14}))
        assert not _evaluate("whale_net_accumulation", pd.DataFrame({"WhaleNetInflow": [-2.0] * 14}))

    def test_holder_concentration_low(self):
        assert _evaluate("holder_concentration_low", pd.DataFrame({"HolderConcentration": [0.3]}), {"threshold": 0.5})
        assert not _evaluate("holder_concentration_low", pd.DataFrame({"HolderConcentration": [0.8]}), {"threshold": 0.5})

    def test_holder_concentration_falling(self):
        falling = pd.DataFrame({"HolderConcentration": list(np.linspace(0.8, 0.4, 20))})
        assert _evaluate("holder_concentration_falling", falling, {"window": 14})

    def test_missing_column_returns_false(self):
        empty = pd.DataFrame({"Close": [1.0, 2.0, 3.0]})
        for name in parse_all_signals([onchain_signals]):
            assert _evaluate(name, empty) is False, f"{name} should fail closed on missing data"
