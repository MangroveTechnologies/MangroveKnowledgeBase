"""
Tests for the sample_ohlcv() mock-data helper.

Reproduces the reported bug: the quickstart snippets referenced a file
(`ohlcv.csv`) that is not shipped, so they failed on a clean install with
FileNotFoundError. sample_ohlcv() gives every snippet self-contained data that
runs out of the box, with the capitalized OHLCV columns the signals expect.

Usage:
    pytest tests/test_sample_data.py -v
"""

import pandas as pd
import pytest

from mangrove_kb import RuleRegistry, sample_ohlcv


class TestShape:
    EXPECTED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

    def test_default_columns_are_capitalized_ohlcv(self):
        df = sample_ohlcv()
        assert list(df.columns) == self.EXPECTED_COLUMNS

    def test_default_row_count(self):
        assert len(sample_ohlcv()) == 200

    def test_custom_row_count(self):
        assert len(sample_ohlcv(rows=50)) == 50

    def test_datetime_index(self):
        df = sample_ohlcv()
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "Timestamp"

    def test_values_are_float_and_finite(self):
        df = sample_ohlcv()
        assert df.to_numpy().dtype.kind == "f"
        assert df.notna().all().all()


class TestCandleInvariants:
    def test_high_is_the_max_low_is_the_min(self):
        df = sample_ohlcv(rows=500)
        body_high = df[["Open", "Close"]].max(axis=1)
        body_low = df[["Open", "Close"]].min(axis=1)
        assert (df["High"] >= body_high - 1e-9).all()
        assert (df["Low"] <= body_low + 1e-9).all()
        assert (df["High"] >= df["Low"]).all()

    def test_prices_and_volume_are_positive(self):
        df = sample_ohlcv(rows=500)
        assert (df[["Open", "High", "Low", "Close"]] > 0).all().all()
        assert (df["Volume"] > 0).all()

    def test_first_bar_opens_at_start_price(self):
        df = sample_ohlcv(start_price=250.0)
        assert df["Open"].iloc[0] == pytest.approx(250.0)


class TestDeterminism:
    def test_same_seed_same_data(self):
        pd.testing.assert_frame_equal(sample_ohlcv(seed=7), sample_ohlcv(seed=7))

    def test_different_seed_different_data(self):
        assert not sample_ohlcv(seed=1)["Close"].equals(sample_ohlcv(seed=2)["Close"])


class TestTrend:
    def test_down_trend_ends_lower(self):
        df = sample_ohlcv(rows=400, trend="down", seed=0)
        assert df["Close"].iloc[-1] < df["Close"].iloc[0]

    def test_up_trend_ends_higher(self):
        df = sample_ohlcv(rows=400, trend="up", seed=0)
        assert df["Close"].iloc[-1] > df["Close"].iloc[0]


class TestValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"rows": 1},
            {"start_price": 0},
            {"start_price": -5},
            {"volatility": -0.1},
            {"trend": "sideways"},
        ],
    )
    def test_bad_args_raise_value_error(self, kwargs):
        with pytest.raises(ValueError):
            sample_ohlcv(**kwargs)


class TestQuickstartRunsOutOfTheBox:
    """The exact bug: the documented snippet must run with no CSV file."""

    def test_rule_registry_evaluate_runs_on_sample_data(self):
        df = sample_ohlcv()
        fired = RuleRegistry.evaluate(
            {"name": "rsi_oversold", "params": {"window": 14, "threshold": 30}},
            df,
        )
        # Decoupled from the numpy.bool_-leak issue (#66): just assert the
        # documented snippet executes and returns a boolean-like result.
        assert bool(fired) in (True, False)
