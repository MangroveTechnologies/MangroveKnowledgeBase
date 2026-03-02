"""Indicator metadata and computation service.

Wraps the mangrove_knowledge_base indicator classes to provide
discovery (free) and computation (x402 gated).
"""

import mangrove_knowledge_base.indicators as ind_module
from mangrove_knowledge_base.indicators.indicator_interface import IndicatorInterface

_INDICATOR_CATEGORIES = {
    "momentum_indicators": "Momentum",
    "trend_indicators": "Trend",
    "volume_indicators": "Volume",
    "volatility_indicators": "Volatility",
    "pattern_indicators": "Patterns",
    "return_indicators": "Returns",
}


class IndicatorService:
    """Provides indicator metadata and computation.

    Metadata methods (list_indicators, get_indicator) are free.
    Computation (compute) is x402 gated at the router/tool layer.
    """

    def __init__(self):
        self._indicators = {}
        for name in ind_module.__all__:
            cls = getattr(ind_module, name, None)
            if cls is None or not hasattr(cls, "compute"):
                continue
            # Skip the base interface itself
            if cls is IndicatorInterface:
                continue
            mod = getattr(cls, "__module__", "")
            category = "Other"
            for key, label in _INDICATOR_CATEGORIES.items():
                if key in mod:
                    category = label
                    break
            self._indicators[name] = {
                "name": name,
                "category": category,
                "data": cls._data,
                "params": cls._params,
                "outputs": cls._outputs,
                "cls": cls,
            }

    def list_indicators(self, category: str = None) -> list[dict]:
        """List indicators with optional category filter. Free."""
        results = []
        for name, info in sorted(self._indicators.items()):
            if category and info["category"] != category:
                continue
            results.append({
                "name": info["name"],
                "category": info["category"],
                "data": info["data"],
                "params": info["params"],
                "outputs": info["outputs"],
            })
        return results

    def get_indicator(self, name: str) -> dict | None:
        """Get full spec for an indicator. Free."""
        info = self._indicators.get(name)
        if info is None:
            return None
        return {
            "name": info["name"],
            "category": info["category"],
            "data": info["data"],
            "params": info["params"],
            "outputs": info["outputs"],
        }

    def compute(self, name: str, data: dict, params: dict) -> dict:
        """Compute an indicator. x402 gated."""
        info = self._indicators.get(name)
        if info is None:
            raise ValueError(f"Unknown indicator: {name}")
        return info["cls"].compute(data=data, params=params)
