"""
Return-type contract tests for the signal registry.

Signal functions compute their result by comparing numpy/pandas scalars
(e.g. ``close.iloc[-1] > sma.iloc[-1]``), which yields a ``numpy.bool_`` rather
than a native Python ``bool``. ``numpy.bool_`` is not JSON-serializable, so a
signal result passed straight into ``json.dumps()`` or a webhook payload raises
``TypeError: Object of type bool_ is not JSON serializable`` and silently halts
downstream automation.

These tests assert the public contract: every registered signal returns a
native Python ``bool`` (or a ``pd.Series``) that is JSON-serializable, both when
called directly and via :meth:`RuleRegistry.evaluate`. Regression guard for the
numpy primitive-leakage bug.

Usage:
    pytest tests/test_signal_return_types.py -v
"""

import inspect
import json

import numpy as np
import pandas as pd
import pytest

import mangrove_kb.signals  # noqa: F401  -- triggers signal registration
from mangrove_kb.registry import RuleRegistry, _to_native


# --------------------------------------------------------------------------- #
# Realistic OHLCV + alt-data frame                                            #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    # A deterministic but non-trivial price path so signals reach their
    # comparison return paths (not just the early "insufficient data" guard).
    drift = np.linspace(100.0, 160.0, n)
    wiggle = 5.0 * np.sin(np.linspace(0.0, 12.0, n))
    close = drift + wiggle
    frame = pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.linspace(1_000.0, 2_000.0, n),
        },
        index=idx,
    )
    # On-chain signals consume alternative-data columns time-aligned to bars.
    for col in (
        "SmartMoneyNetflow",
        "SmartMoneyHoldings",
        "ExchangeNetflow",
        "WhaleNetInflow",
        "HolderConcentration",
    ):
        frame[col] = wiggle
    return frame


# Signals explicitly called out in the bug report, with the args each needs to
# reach its comparison return path (is_above_sma has no default window).
REPORTED = [
    ("rsi_cross_up", {"window": 14, "threshold": 50.0}),
    ("rsi_cross_down", {"window": 14, "threshold": 50.0}),
    ("is_above_sma", {"window": 50}),
    ("supertrend_long", {"window": 10, "multiplier": 3.0}),
    ("supertrend_short", {"window": 10, "multiplier": 3.0}),
]


def _native_type(value) -> bool:
    return isinstance(value, (bool, pd.Series))


# Plausible values for the parameters that have no default, so that every signal can actually be
# called. Without this the registry sweep below has to skip them, which silently left four
# crossover signals covered by nothing at all.
_REQUIRED_DEFAULTS = {
    "window": 14, "window_fast": 10, "window_slow": 30, "window_signal": 9,
    "threshold": 50.0, "multiplier": 3.0,
}


def _required_kwargs(fn) -> dict:
    """Bind every parameter of `fn` that has no default, skipping the leading DataFrame arg."""
    params = list(inspect.signature(fn).parameters.values())[1:]
    return {p.name: _REQUIRED_DEFAULTS.get(p.name, 14)
            for p in params if p.default is inspect.Parameter.empty}


class TestToNativeHelper:
    def test_numpy_bool_becomes_native_bool(self):
        coerced = _to_native(np.bool_(True))
        assert coerced is True
        assert type(coerced) is bool

    def test_native_bool_passes_through(self):
        assert _to_native(True) is True
        assert _to_native(False) is False

    def test_numpy_array_becomes_series(self):
        out = _to_native(np.array([True, False]))
        assert isinstance(out, pd.Series)

    def test_series_passes_through(self):
        s = pd.Series([True, False])
        assert _to_native(s) is s


class TestReportedSignals:
    """The five signals named in the bug report must honor the contract."""

    @pytest.mark.parametrize("name,kwargs", REPORTED)
    def test_returns_native_and_json_serializable(self, name, kwargs, df):
        value = RuleRegistry._registry[name](df, **kwargs)
        assert _native_type(value), f"{name} returned {type(value)!r}"
        assert not isinstance(value, np.generic), f"{name} leaked a numpy scalar"
        # The exact downstream failure mode from the report.
        json.dumps(value if not isinstance(value, pd.Series) else value.tolist())


class TestEverySignalContract:
    """No registered signal may leak a numpy primitive on realistic data."""

    def test_no_numpy_leakage_across_registry(self, df):
        offenders = []
        checked = 0
        for name, fn in RuleRegistry._registry.items():
            # Every signal is called, including those with required parameters. This used to
            # `except TypeError: continue`, which skipped them -- and a blanket catch would also
            # have swallowed a genuine TypeError raised inside a signal on valid data.
            value = fn(df, **_required_kwargs(fn))
            checked += 1
            if isinstance(value, np.generic) or not _native_type(value):
                offenders.append((name, type(value).__name__))
        assert not offenders, f"signals leaking non-native return types: {offenders}"
        # Guards the contract's reach: if a signal ever stops being callable, that is a failure
        # rather than a silent gap in coverage.
        assert checked == len(RuleRegistry._registry)

    def test_every_signal_returns_a_plain_bool(self, df):
        """The stated contract is `-> bool`, so nothing may return a Series or a numpy scalar."""
        wrong = {name: type(fn(df, **_required_kwargs(fn))).__name__
                 for name, fn in RuleRegistry._registry.items()
                 if type(fn(df, **_required_kwargs(fn))) is not bool}
        assert not wrong, f"signals not returning a native bool: {wrong}"

    def test_declared_return_annotation_is_bool(self):
        """A signal whose annotation drifts from `bool` is the first sign of the contract slipping."""
        wrong = {name: ann for name, fn in RuleRegistry._registry.items()
                 if (ann := inspect.signature(fn).return_annotation) not in (bool, "bool")}
        assert not wrong, f"signals not annotated `-> bool`: {wrong}"


class TestEvaluatePath:
    """The same contract must hold through RuleRegistry.evaluate()."""

    def test_evaluate_returns_native_bool(self, df):
        rule = {"name": "rsi_cross_down", "params": {"window": 14, "threshold": 50.0}}
        value = RuleRegistry.evaluate(rule, df)
        assert type(value) is bool
        json.dumps(value)
