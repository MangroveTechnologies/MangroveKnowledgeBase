"""
Validation + behavioral tests for the DeFiLlama Pro signal families.

Mirrors tests/test_onchain_signals.py: structural checks via the docstring
parser (Type/Requires tags, registration) plus synthetic-data exercises that
confirm each signal fires under its intended condition and fails closed when
its Pro column is absent.
"""
import numpy as np
import pandas as pd
import pytest

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.signals import defi_pro as defi_pro_signals
from mangrove_kb.docstring_parser import parse_all_signals


@pytest.fixture(scope="session")
def parsed() -> dict:
    return parse_all_signals([defi_pro_signals])


# --------------------------------------------------------------------------- #
# Coverage                                                                    #
# --------------------------------------------------------------------------- #
class TestDefiProCoverage:
    EXPECTED_TRIGGER_COUNT = 5  # cliff_ahead, funding_flip, etf_spike, treasury_trigger, spread_widening
    EXPECTED_FILTER_COUNT = 5   # unlock_low, funding_negative, etf_streak, treasury_growing, spread_low
    EXPECTED_TOTAL = 10

    def test_total_count(self, parsed):
        assert len(parsed) == self.EXPECTED_TOTAL, sorted(parsed)

    def test_trigger_count(self, parsed):
        triggers = [k for k, v in parsed.items() if v["type"] == "TRIGGER"]
        assert len(triggers) == self.EXPECTED_TRIGGER_COUNT, sorted(triggers)

    def test_filter_count(self, parsed):
        filters = [k for k, v in parsed.items() if v["type"] == "FILTER"]
        assert len(filters) == self.EXPECTED_FILTER_COUNT, sorted(filters)

    def test_all_registered(self, parsed):
        for name in parsed:
            assert name in RuleRegistry._registry, name


# --------------------------------------------------------------------------- #
# Structural validation -- every signal requires exactly one known Pro column #
# --------------------------------------------------------------------------- #
class TestDefiProMetadata:
    VALID_COLUMNS = {
        "TokenUnlockPressure",
        "PerpFundingRate",
        "EtfNetFlow",
        "TreasuryUsd",
        "LendingRateSpread",
    }

    def test_requires_known_columns(self, parsed):
        for name, meta in parsed.items():
            cols = set(meta["requires"])
            assert cols, f"{name} declares no Requires column"
            assert cols <= self.VALID_COLUMNS, f"{name} requires unknown column(s): {cols - self.VALID_COLUMNS}"


# --------------------------------------------------------------------------- #
# Behavioral -- fires under intended condition, stays quiet / fails closed     #
# --------------------------------------------------------------------------- #
class TestDefiProBehavior:
    def test_fail_closed_when_column_absent(self):
        # An OHLCV-only frame (no Pro columns) must make every signal return False.
        df = pd.DataFrame({"Close": np.linspace(100, 110, 40)})
        for name in (
            "token_unlock_pressure_low", "token_unlock_cliff_ahead",
            "funding_negative_regime", "funding_flip_positive",
            "etf_inflow_streak", "etf_inflow_spike",
            "treasury_growing", "treasury_accumulation_trigger",
            "lending_spread_low", "lending_spread_widening",
        ):
            assert RuleRegistry._registry[name](df) is False, name

    def test_token_unlock_pressure_low(self):
        assert defi_pro_signals.token_unlock_pressure_low(pd.DataFrame({"TokenUnlockPressure": [0.01]})) is True
        assert defi_pro_signals.token_unlock_pressure_low(pd.DataFrame({"TokenUnlockPressure": [0.10]})) is False

    def test_token_unlock_cliff_ahead(self):
        vals = [0.005] * 30 + [0.20]  # flat baseline, then a big cliff
        assert defi_pro_signals.token_unlock_cliff_ahead(pd.DataFrame({"TokenUnlockPressure": vals})) is True

    def test_funding_negative_regime(self):
        assert defi_pro_signals.funding_negative_regime(pd.DataFrame({"PerpFundingRate": [-0.01] * 14})) is True
        assert defi_pro_signals.funding_negative_regime(pd.DataFrame({"PerpFundingRate": [0.01] * 14})) is False

    def test_funding_flip_positive(self):
        assert defi_pro_signals.funding_flip_positive(pd.DataFrame({"PerpFundingRate": [-0.002, 0.003]})) is True
        assert defi_pro_signals.funding_flip_positive(pd.DataFrame({"PerpFundingRate": [0.001, 0.003]})) is False

    def test_etf_inflow_streak(self):
        assert defi_pro_signals.etf_inflow_streak(pd.DataFrame({"EtfNetFlow": [1e6] * 5})) is True
        assert defi_pro_signals.etf_inflow_streak(pd.DataFrame({"EtfNetFlow": [1e6, 1e6, -1e6, 1e6, 1e6]})) is False

    def test_etf_inflow_spike(self):
        # Baseline needs variance (std>0) for a z-score, like smart_money_inflow_spike.
        vals = list(np.linspace(1.0e5, 1.2e5, 20)) + [5.0e6]
        assert defi_pro_signals.etf_inflow_spike(pd.DataFrame({"EtfNetFlow": vals})) is True

    def test_treasury_growing(self):
        assert defi_pro_signals.treasury_growing(pd.DataFrame({"TreasuryUsd": np.linspace(1e8, 2e8, 20)})) is True
        assert defi_pro_signals.treasury_growing(pd.DataFrame({"TreasuryUsd": np.linspace(2e8, 1e8, 20)})) is False

    def test_treasury_accumulation_trigger(self):
        vals = [1.0e8] * 20 + [1.5e8]  # below flat MA, then jumps above
        assert defi_pro_signals.treasury_accumulation_trigger(pd.DataFrame({"TreasuryUsd": vals})) is True

    def test_lending_spread_low(self):
        assert defi_pro_signals.lending_spread_low(pd.DataFrame({"LendingRateSpread": [0.01]})) is True
        assert defi_pro_signals.lending_spread_low(pd.DataFrame({"LendingRateSpread": [0.08]})) is False

    def test_lending_spread_widening(self):
        vals = [0.02] * 20 + [0.06]
        assert defi_pro_signals.lending_spread_widening(pd.DataFrame({"LendingRateSpread": vals})) is True
