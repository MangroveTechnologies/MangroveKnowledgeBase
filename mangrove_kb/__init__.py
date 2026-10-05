"""mangrove-kb: Open-source trading signals and technical indicators library.

Provides a comprehensive library of trading signals and technical indicators
for quantitative finance and algorithmic trading.

Signal Categories:
    - Momentum signals (RSI, Stochastic, KAMA, ROC, Williams %R, etc.)
    - Trend signals (SMA, EMA, MACD, ADX, Aroon, Ichimoku, PSAR, etc.)
    - Volume signals (OBV, MFI, CMF, VWAP, ADI, etc.)
    - Volatility signals (Bollinger Bands, ATR, Keltner Channel, Donchian, etc.)

Indicator Categories:
    - Momentum indicators
    - Trend indicators
    - Volume indicators
    - Volatility indicators
    - Return indicators
"""

from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("mangrove-kb")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

# Lazy, via PEP 562's module `__getattr__`. `RuleRegistry`, `sample_ohlcv`, `indicators` and
# `signals` pull in pandas -- the whole signal/indicator library -- which costs ~88 MB RSS a
# consumer who only reads the graph should not pay (measured fresh-process, `/proc/self/status`:
# `import mangrove_kb.graph` alone is +10.7 MB; also importing `indicators` and `signals`, which is
# what this package used to do unconditionally, is +98.6 MB). `import mangrove_kb.graph` imports
# this package first regardless of what it then imports, so an eager import here was an eager
# import of pandas for every caller of the graph, whether or not they ever evaluate a signal.
#
# `from mangrove_kb import RuleRegistry` and `from mangrove_kb import indicators` still work --
# `__getattr__` is consulted for any name not already bound at module level, so the first access
# imports the real module and the result is cached in `globals()` for every access after.
# `tests/test_lazy_imports.py` proves `import mangrove_kb.graph` loads none of this.
__all__ = ["__version__", "RuleRegistry", "sample_ohlcv", "indicators", "signals"]

_LAZY_ATTRS = {
    "RuleRegistry": ("mangrove_kb.registry", "RuleRegistry"),
    "sample_ohlcv": ("mangrove_kb.sample_data", "sample_ohlcv"),
}
_LAZY_MODULES = ("indicators", "signals")


def __getattr__(name: str):
    if name in _LAZY_ATTRS:
        import importlib

        module_name, attr = _LAZY_ATTRS[name]
        value = getattr(importlib.import_module(module_name), attr)
        globals()[name] = value
        return value
    if name in _LAZY_MODULES:
        import importlib

        module = importlib.import_module(f"mangrove_kb.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_LAZY_ATTRS) | set(_LAZY_MODULES))
