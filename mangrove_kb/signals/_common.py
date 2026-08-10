"""Predicates shared by signals in more than one class.

Splitting the signal files onto the ontology class put `bop_cross_up` (an `oscillator` signal) and
`mom_cross_up` (a `momentum` one) in different files while they still share one zero-crossing test.
A helper used by two classes belongs to neither, so it lives here rather than being imported across
class files or copied into both.
"""
import functools
import importlib
import warnings

import pandas as pd


def zero_cross(series: pd.Series, direction: str) -> bool:
    """Whether `series` crossed the zero line on the last bar, in `direction` ("up" or "down").

    A crossing reads two consecutive bars, so it is False on the first bar and wherever either is
    undefined. The comparison is `prev <= 0 < curr` rather than `prev < 0 < curr`: a series sitting
    exactly at zero and then rising has crossed.
    """
    if len(series) < 2:
        return False
    prev, curr = series.iloc[-2], series.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False
    if direction == "up":
        return bool(prev <= 0 < curr)
    return bool(prev >= 0 > curr)


def _ma_is_above(df: pd.DataFrame, indicator_cls, output_key: str, window: int) -> bool:
    """Helper: check if current close is above the given MA."""
    closes = df["close"]
    if len(closes) < window:
        return False
    result = indicator_cls.compute(data={'close': closes}, params={'window': window})
    ma = result[output_key]
    if ma.empty or pd.isna(ma.iloc[-1]):
        return False
    return bool(closes.iloc[-1] > ma.iloc[-1])

def _ma_crossover(
    df: pd.DataFrame,
    indicator_cls,
    output_key: str,
    window_fast: int,
    window_slow: int,
    direction: str,
) -> bool:
    """Helper: detect fast/slow MA crossover in the given direction."""
    closes = df["close"]
    if len(closes) < window_slow + 1:
        return False
    fast = indicator_cls.compute(data={'close': closes}, params={'window': window_fast})[output_key]
    slow = indicator_cls.compute(data={'close': closes}, params={'window': window_slow})[output_key]
    if len(fast) < 2 or len(slow) < 2:
        return False
    prev_fast, curr_fast = fast.iloc[-2], fast.iloc[-1]
    prev_slow, curr_slow = slow.iloc[-2], slow.iloc[-1]
    if pd.isna(prev_fast) or pd.isna(curr_fast) or pd.isna(prev_slow) or pd.isna(curr_slow):
        return False
    if direction == "bullish":
        return bool(prev_fast <= prev_slow and curr_fast > curr_slow)
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


def moved_signals(here: str, moved: dict):
    """Build a module-level ``__getattr__`` for signals that moved to another file.

    Reorganising the files onto the ontology class moved signals BETWEEN modules that both still
    exist, which the whole-module shims (`volume`, `patterns`) do not cover:
    ``from mangrove_kb.signals.trend import vortex_bullish`` raised ImportError even though
    `trend.py` was still there. MangroveAI imports exactly that shape.

    PEP 562 rather than assigning the names into the module, deliberately. The attribute is only
    looked up when something asks for it, so the module's own namespace stays exactly the signals it
    defines -- which is what the API reports as a category, and what discovery walks. Binding them
    would make every moved signal appear to live in two places at once.

    `moved` maps destination module -> the names that went there, so the mapping reads as a record
    of the move. A name that never lived here still raises AttributeError.
    """
    lookup = {name: dest for dest, names in moved.items() for name in names}

    def __getattr__(name):
        dest = lookup.get(name)
        if dest is None:
            raise AttributeError(f"module {here!r} has no attribute {name!r}")
        warnings.warn(
            f"{here}.{name} moved to mangrove_kb.signals.{dest}: signal files are named for the "
            f"ontology class they hold, and this signal's class is {dest}. The registered name is "
            f"unchanged, so strategies and RuleRegistry are unaffected.",
            DeprecationWarning, stacklevel=2,
        )
        mod = importlib.import_module(f"mangrove_kb.signals.{dest}")
        if hasattr(mod, name):
            return getattr(mod, name)
        # The signal was RENAMED as well as moved, so the old name is not a function anywhere --
        # it only exists as a registry alias. `chandelier_long_stop_hit` is `cl_below_high_offset`
        # in volatility.py. Resolving the alias here means one deprecation mechanism covers both
        # kinds of change; without it, moving a renamed signal silently broke its old import path.
        from mangrove_kb.registry import RuleRegistry
        renamed = RuleRegistry._aliases.get(name)
        if renamed and hasattr(mod, renamed):
            return getattr(mod, renamed)
        raise AttributeError(f"{here}.{name} moved to {dest}, but is not there under either name")

    return __getattr__


def renamed_signals(here: str):
    """Build a module ``__getattr__`` for signals RENAMED without moving files.

    `RuleRegistry.alias` keeps a retired name evaluating, which covers a stored strategy. It does
    nothing for `from mangrove_kb.signals.volatility import volatility_stop_upper`, because that
    name is no longer a function in the module -- and a rename in place has no `_MOVED` entry to
    catch it either. This resolves any alias whose target is defined here.
    """
    def __getattr__(name):
        from mangrove_kb.registry import RuleRegistry
        target = RuleRegistry._aliases.get(name)
        mod = importlib.import_module(here)
        if target and target in vars(mod):
            warnings.warn(
                f"signal {name!r} has been renamed to {target!r}; the old name still resolves and "
                f"evaluates but will be removed.",
                DeprecationWarning, stacklevel=2,
            )
            return vars(mod)[target]
        raise AttributeError(f"module {here!r} has no attribute {name!r}")

    return __getattr__


def deprecated_signal(reason: str):
    """Mark a signal deprecated without changing what it does.

    These signals read an indicator the ontology excludes -- a verdict output, or a level that is
    only defined relative to a regime the indicator itself decided. They still evaluate, and a
    stored strategy naming one keeps working; they are simply not modelled, and will not gain a
    class. The warning says so at the point of use, which is the only place anyone will look.

    Warns on call rather than on import: these live beside signals that are not deprecated, so an
    import-time warning would fire for reasons the caller cannot act on.
    """
    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            warnings.warn(f"{fn.__name__} is deprecated: {reason}", DeprecationWarning, stacklevel=2)
            return fn(*args, **kwargs)
        return wrapper
    return decorate
