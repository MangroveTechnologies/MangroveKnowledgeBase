"""Signal metadata and evaluation service.

Wraps the mangrove_kb docstring parser and RuleRegistry
to provide signal discovery (free) and evaluation (x402 gated).
"""

import pandas as pd

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.docstring_parser import parse_all_signals
from mangrove_kb.signals import (momentum, trend, volume, volatility, pattern, oscillator,
                                 averaging, onchain, defi_pro)

# Files reorganised onto the ontology class are named for that class; the rest keep their old
# use-case names until they are reorganised too.
_MODULE_CATEGORY = {
    "oscillator": "Oscillator",
    "momentum": "Momentum",
    "averaging": "Averaging",
    "volatility": "Volatility",
    "pattern": "Pattern",
    "trend": "Trend",
    "volume": "Volume",
    "onchain": "On-Chain",
    "defi_pro": "DeFi Pro",
}

_SIGNAL_MODULES = [momentum, trend, volume, volatility, pattern, oscillator, averaging,
                   onchain, defi_pro]


class SignalService:
    """Provides signal metadata and evaluation.

    Metadata methods (list_signals, get_signal) are free.
    Evaluation (evaluate) is x402 gated at the router/tool layer.
    """

    def __init__(self):
        self._metadata = parse_all_signals(_SIGNAL_MODULES)
        self._categories = {}
        for name, meta in self._metadata.items():
            func = RuleRegistry._registry.get(name)
            if func:
                mod = getattr(func, "__module__", "")
                for key, label in _MODULE_CATEGORY.items():
                    if key in mod:
                        self._categories[name] = label
                        break
                else:
                    self._categories[name] = "Other"

    def list_signals(self, category: str = None, signal_type: str = None) -> list[dict]:
        """List signals with optional filtering. Free."""
        results = []
        for name, meta in sorted(self._metadata.items()):
            if category and self._categories.get(name) != category:
                continue
            if signal_type and meta.get("type") != signal_type:
                continue
            results.append({
                "name": name,
                "category": self._categories.get(name, "Other"),
                **meta,
            })
        return results

    def get_signal(self, name: str) -> dict | None:
        """Get full metadata for a signal. Free."""
        meta = self._metadata.get(name)
        if meta is None:
            return None
        return {
            "name": name,
            "category": self._categories.get(name, "Other"),
            **meta,
        }

    def evaluate(self, name: str, df: pd.DataFrame, params: dict) -> bool:
        """Evaluate a signal against data. x402 gated."""
        if name not in RuleRegistry._registry:
            raise ValueError(f"Unknown signal: {name}")
        rule = {"name": name, "params": params}
        return RuleRegistry.evaluate(rule, df)
