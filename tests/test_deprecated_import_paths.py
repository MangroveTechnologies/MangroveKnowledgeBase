"""The old signal module paths must keep working.

`patterns.py` became `pattern.py` and `volume.py` was split four ways, because signal files are
named for the ontology class they hold and there is no `volume` indicator class. Both old paths
survive as shims that re-export from the new homes.

These are not incidental imports. Every one of the statements below is copied from a service that
would fail *at import time* -- the process does not start -- if the path disappeared:

    MangroveOracle  src/services/signal.py, src/services/leaderboard.py, src/services/backtest.py,
                    src/api/routes/results.py   (pins mangrove-kb==1.3.4)
    MangroveAI      src/MangroveAI/domains/signals/registry.py,
                    src/MangroveAI/domains/signals/kb_signal_parser.py (imports by string path),
                    src/MangroveAI/examples/test_indicator_param_fixes.py

The name lists are the public API as released, taken from the modules at the point they were moved.
They may grow, never shrink: dropping one is the breaking change these shims exist to prevent.
"""

import importlib
import warnings

import pytest

from mangrove_kb.registry import RuleRegistry

VOLUME_API = (
    "adi_bearish", "adi_bullish", "adosc_bearish", "adosc_bullish", "adosc_cross_down",
    "adosc_cross_up", "cmf_bearish", "cmf_bullish", "cumulative_return_positive",
    "cumulative_return_target", "daily_return_negative", "daily_return_positive", "eom_bearish",
    "eom_bullish", "force_bearish", "force_bullish", "is_above_vwma", "kvo_bearish",
    "kvo_bearish_cross", "kvo_bullish", "kvo_bullish_cross", "mfi_overbought", "mfi_oversold",
    "nvi_bearish", "nvi_bullish", "obv_bearish", "obv_bullish", "vpt_bearish", "vpt_bullish",
    "vwap_above", "vwap_below", "vwma_cross_down", "vwma_cross_up",
)

PATTERNS_API = (
    "bearish_engulfing_trigger", "bearish_harami_trigger", "bearish_pattern_recent",
    "bearish_pin_bar_trigger", "bullish_engulfing_trigger", "bullish_harami_trigger",
    "bullish_pattern_recent", "bullish_pin_bar_trigger", "continuation_pattern_bearish",
    "continuation_pattern_bullish", "dark_cloud_cover_trigger", "doji_trigger",
    "dragonfly_doji_trigger", "evening_star_trigger", "gravestone_doji_trigger", "hammer_trigger",
    "hanging_man_trigger", "indecision_pattern_recent", "inside_bar_trigger",
    "inverted_hammer_trigger", "long_legged_doji_trigger", "marubozu_bearish_trigger",
    "marubozu_bullish_trigger", "morning_star_trigger", "nr7_trigger", "outside_bar_trigger",
    "piercing_line_trigger", "reversal_pattern_bearish", "reversal_pattern_bullish",
    "shooting_star_trigger", "spinning_top_trigger", "strong_body_recent",
    "three_black_crows_trigger", "three_inside_down_trigger", "three_inside_up_trigger",
    "three_white_soldiers_trigger", "two_bar_reversal_bearish_trigger",
    "two_bar_reversal_bullish_trigger", "tweezer_bottoms_trigger", "tweezer_tops_trigger",
)

DEPRECATED = (("mangrove_kb.signals.volume", VOLUME_API),
              ("mangrove_kb.signals.patterns", PATTERNS_API))


@pytest.mark.parametrize("path,api", DEPRECATED)
def test_old_path_still_imports_and_exports_its_whole_api(path, api):
    mod = importlib.import_module(path)
    missing = [n for n in api if not hasattr(mod, n)]
    assert not missing, f"{path} no longer exports {missing}"
    assert set(mod.__all__) == set(api), f"{path}.__all__ drifted from the released API"


@pytest.mark.parametrize("path,api", DEPRECATED)
def test_old_path_binds_the_same_function_object(path, api):
    """A shim re-exports; it must never define a second copy that can drift from the real one."""
    mod = importlib.import_module(path)
    for name in api:
        fn = getattr(mod, name)
        home = importlib.import_module(fn.__module__)
        assert getattr(home, name) is fn, f"{path}.{name} is not {fn.__module__}.{name}"


@pytest.mark.parametrize("path,api", DEPRECATED)
def test_old_path_warns(path, api):
    """Fires once per process, at first import -- Python caches modules in sys.modules."""
    import sys
    sys.modules.pop(path, None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module(path)
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), \
        f"{path} imported without a DeprecationWarning"


def test_shims_do_not_register_anything():
    """Registration is keyed by name and happens in the real module, so importing a shim is inert.

    If a shim ever declared its own `@RuleRegistry.register`, it would silently shadow the real
    signal -- the registry is a plain dict and last write wins.
    """
    import mangrove_kb.signals  # noqa: F401  -- registers every real module
    before = RuleRegistry.names()
    importlib.import_module("mangrove_kb.signals.volume")
    importlib.import_module("mangrove_kb.signals.patterns")
    assert RuleRegistry.names() == before


def test_strategies_never_depended_on_the_file_layout():
    """The reason the reorg is not a breaking change for users: strategies name signals."""
    from mangrove_kb.sample_data import sample_ohlcv
    df = sample_ohlcv(300)
    # obv_bullish moved volume.py -> flow.py; a stored strategy cannot tell
    assert RuleRegistry.evaluate({"name": "obv_bullish", "parameters": {"window": 20}}, df) in (True, False)
    assert RuleRegistry.has("cmf_bearish")   # volume.py -> oscillator.py
    assert RuleRegistry.has("doji_trigger")  # patterns.py -> pattern.py


# ---------------------------------------------------------------------------
# Signals that moved BETWEEN modules that both still exist
# ---------------------------------------------------------------------------
# The whole-module shims above do not cover this: `trend.py` is still there, but 64 of its signals
# are not, so `from mangrove_kb.signals.trend import vortex_bullish` raised ImportError. This is
# the exact statement in MangroveAI's examples/test_indicator_param_fixes.py.

MOVED_AWAY = [
    ("mangrove_kb.signals.trend", ["adx_bullish_di", "vortex_bullish", "vortex_bearish",
                                   "vortex_crossover", "sma_cross_up", "macd_bullish_cross"]),
    ("mangrove_kb.signals.momentum", ["rsi_overbought", "rsi_oversold", "kama_cross_up"]),
]


@pytest.mark.parametrize("path,names", MOVED_AWAY)
def test_names_that_moved_out_still_resolve_from_the_old_module(path, names):
    mod = importlib.import_module(path)
    for n in names:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fn = getattr(mod, n)
        assert callable(fn)
        assert any(issubclass(w.category, DeprecationWarning) for w in caught), n


@pytest.mark.parametrize("path,names", MOVED_AWAY)
def test_a_name_that_never_lived_there_still_raises(path, names):
    mod = importlib.import_module(path)
    with pytest.raises(AttributeError):
        getattr(mod, "doji_trigger" if "trend" in path else "bullish_engulfing_trigger")


@pytest.mark.parametrize("path,names", MOVED_AWAY)
def test_a_moved_name_does_not_join_the_old_module_namespace(path, names):
    """PEP 562, not a re-export: binding them would make each signal appear to live in two files,
    and the module a function is defined in is what the API reports as its category."""
    mod = importlib.import_module(path)
    for n in names:
        getattr(mod, n)                       # resolve it
    assert not (set(names) & set(vars(mod)))  # still not in the namespace


def test_the_mangroveai_import_statement_verbatim():
    """Copied from MangroveAI/src/MangroveAI/examples/test_indicator_param_fixes.py.

    Deliberately a MIX of destinations: Ichimoku became `averaging` once it was classed, the other
    four are `momentum`. Not one of the seven is still defined in trend.py, and the statement has to
    keep working anyway -- which is the shape that broke.
    """
    from mangrove_kb.signals.trend import (      # noqa: F401
        ichimoku_bullish, ichimoku_bearish, ichimoku_tk_cross,
        adx_bullish_di, vortex_bullish, vortex_bearish, vortex_crossover,
    )
    assert ichimoku_bullish.__module__ == "mangrove_kb.signals.averaging"
    assert vortex_bullish.__module__ == "mangrove_kb.signals.momentum"


# ---------------------------------------------------------------------------
# Signals the ontology will never model, marked deprecated but still working
# ---------------------------------------------------------------------------
# Eleven signals read an indicator that emits a verdict (SuperTrend's `direction`, PSAR's flip
# flags, ATRTrailingStop's `direction`), or a level that is only defined relative to a regime the
# indicator decided. They have no measurement to inherit a class from, so they will not enter the
# graph -- but they are registered signals and a stored strategy may name any of them.

NOT_MODELLED = [
    "supertrend_long", "supertrend_short", "supertrend_flip_up", "supertrend_flip_down",
    "psar_bullish", "psar_bearish", "psar_reversal",
    "atr_trailing_stop_long", "atr_trailing_stop_short",
    "atr_trailing_stop_flip_up", "atr_trailing_stop_flip_down",
]


@pytest.mark.parametrize("name", NOT_MODELLED)
def test_not_modelled_signals_still_evaluate_and_warn(name):
    from mangrove_kb.sample_data import sample_ohlcv
    df = sample_ohlcv(200)
    assert RuleRegistry.has(name)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = RuleRegistry.evaluate({"name": name, "params": {}}, df)
    assert result in (True, False), name
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), name


def test_the_three_excluded_indicators_are_importable_but_uncatalogued():
    """Deprecated, not deleted. Out of __all__ so they are not offered as indicators; still
    importable so anything already calling them keeps working."""
    import mangrove_kb.indicators as I
    for n in ("SuperTrend", "PSAR", "ATRTrailingStop"):
        assert getattr(I, n, None) is not None, n
        assert n not in I.__all__, n
