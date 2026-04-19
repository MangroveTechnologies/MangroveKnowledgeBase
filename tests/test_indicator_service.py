import pytest
import pandas as pd
import numpy as np
from kb_server.services.indicator_service import IndicatorService


class TestIndicatorServiceMetadata:

    def setup_method(self):
        self.service = IndicatorService()

    def test_list_indicators_returns_all(self):
        indicators = self.service.list_indicators()
        assert len(indicators) == 95

    def test_list_indicators_filter_by_category(self):
        momentum = self.service.list_indicators(category="Momentum")
        assert len(momentum) > 0

    def test_get_indicator_exists(self):
        ind = self.service.get_indicator("RSI")
        assert ind is not None
        assert "data" in ind
        assert "params" in ind
        assert "outputs" in ind

    def test_get_indicator_not_found(self):
        ind = self.service.get_indicator("NonexistentIndicator")
        assert ind is None


class TestIndicatorServiceCompute:

    def setup_method(self):
        self.service = IndicatorService()

    def test_compute_rsi(self):
        np.random.seed(42)
        df = pd.DataFrame({"Close": np.random.uniform(100, 200, 50)})
        result = self.service.compute("RSI", {"close": df["Close"]}, {"window": 14})
        assert "rsi" in result
        assert len(result["rsi"]) == 50

    def test_compute_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown indicator"):
            self.service.compute("FakeIndicator", {}, {})
