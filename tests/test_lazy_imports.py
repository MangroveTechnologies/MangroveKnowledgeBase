"""`import mangrove_kb.graph` must not drag the signal library in behind it.

`mangrove_kb/__init__.py` used to import `RuleRegistry`, `sample_ohlcv`, `indicators` and `signals`
eagerly -- and `signals/__init__.py` imports every signal module to register it, which is pandas,
not a stray import. A caller who only reads the graph (`mangrove_kb.graph.KnowledgeGraph`) paid for
all of it anyway, because importing any submodule of a package runs that package's `__init__.py`
first. Measured fresh-process via `/proc/self/status`: `import mangrove_kb.graph` alone costs
+10.7 MB RSS; also importing `indicators` and `signals` -- what this package used to do
unconditionally -- costs +98.6 MB, an ~88 MB saving for a graph-only consumer.

The fix is PEP 562's module-level `__getattr__`: the four names resolve lazily, on first access, so
`from mangrove_kb import RuleRegistry` and `from mangrove_kb import indicators` still work -- import
machinery consults `__getattr__` for any attribute not already bound -- but nothing is imported
until something actually asks for one of them.

This has to be checked in a SUBPROCESS. `pandas` is almost certainly already in `sys.modules` by
the time any test in this suite runs, since other tests import the signal library; importing it
here and inspecting *this* process's `sys.modules` would prove nothing.
"""
from __future__ import annotations

import subprocess
import sys

import pytest


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)


def test_import_graph_does_not_import_pandas():
    proc = _run("import mangrove_kb.graph, sys; "
                "assert 'pandas' not in sys.modules, sorted(n for n in sys.modules if 'pandas' in n)")
    assert proc.returncode == 0, proc.stderr


def test_import_graph_does_not_import_numpy_either():
    """numpy backs the signal library too, and graph.py itself never needs it -- only the optional
    dense/semantic indices do, and those are loaded on first query, not on import."""
    proc = _run("import mangrove_kb.graph, sys; "
                "assert 'numpy' not in sys.modules, sorted(n for n in sys.modules if 'numpy' in n)")
    assert proc.returncode == 0, proc.stderr


def test_bare_import_of_the_package_itself_stays_light():
    """`import mangrove_kb` alone -- before anyone touches `.graph` -- must not import pandas."""
    proc = _run("import mangrove_kb, sys; assert 'pandas' not in sys.modules")
    assert proc.returncode == 0, proc.stderr


def test_rule_registry_is_still_reachable_by_the_documented_name():
    from mangrove_kb import RuleRegistry
    from mangrove_kb.registry import RuleRegistry as direct

    assert RuleRegistry is direct


def test_sample_ohlcv_is_still_reachable_by_the_documented_name():
    from mangrove_kb import sample_ohlcv
    from mangrove_kb.sample_data import sample_ohlcv as direct

    assert sample_ohlcv is direct


def test_indicators_module_is_still_reachable_by_the_documented_name():
    from mangrove_kb import indicators
    import mangrove_kb.indicators as direct

    assert indicators is direct


def test_signals_module_is_still_reachable_by_the_documented_name():
    from mangrove_kb import signals
    import mangrove_kb.signals as direct

    assert signals is direct


def test_a_lazy_attribute_resolves_only_once():
    """The second access must not re-import -- it should come back off `globals()`."""
    import importlib

    import mangrove_kb

    for name in ("RuleRegistry", "sample_ohlcv", "indicators", "signals"):
        mangrove_kb.__dict__.pop(name, None)
    importlib.import_module("mangrove_kb")  # no-op; module already in sys.modules

    first = mangrove_kb.RuleRegistry
    assert "RuleRegistry" in vars(mangrove_kb), "did not cache onto the module after first access"
    assert mangrove_kb.RuleRegistry is first


def test_an_unknown_attribute_still_raises_attribute_error():
    import mangrove_kb

    with pytest.raises(AttributeError):
        mangrove_kb.not_a_real_name


def test_dir_lists_the_lazy_names_too():
    import mangrove_kb

    assert {"RuleRegistry", "sample_ohlcv", "indicators", "signals"} <= set(dir(mangrove_kb))
