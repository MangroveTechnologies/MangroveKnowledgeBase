import pytest
from kb_server.services.signal_service import SignalService


class TestSignalServiceMetadata:
    def setup_method(self):
        self.service = SignalService()

    def test_list_signals_returns_all(self):
        signals = self.service.list_signals()
        assert len(signals) == 166

    def test_list_signals_filter_by_category(self):
        momentum = self.service.list_signals(category="Momentum")
        assert len(momentum) == 26

    def test_list_signals_filter_by_type(self):
        triggers = self.service.list_signals(signal_type="TRIGGER")
        assert len(triggers) == 86

    def test_get_signal_exists(self):
        signal = self.service.get_signal("rsi_oversold")
        assert signal is not None
        assert signal["type"] == "FILTER"
        assert "window" in signal["params"]

    def test_get_signal_not_found(self):
        signal = self.service.get_signal("nonexistent_signal")
        assert signal is None

    def test_get_signal_has_required_fields(self):
        signal = self.service.get_signal("rsi_oversold")
        assert "type" in signal
        assert "requires" in signal
        assert "description" in signal
        assert "params" in signal


class TestSignalServiceEvaluation:
    def setup_method(self):
        self.service = SignalService()

    def test_evaluate_signal_returns_bool(self):
        import pandas as pd
        import numpy as np
        np.random.seed(42)
        df = pd.DataFrame({
            "Open": np.random.uniform(100, 200, 50),
            "High": np.random.uniform(150, 250, 50),
            "Low": np.random.uniform(50, 150, 50),
            "Close": np.random.uniform(100, 200, 50),
            "Volume": np.random.uniform(1000, 5000, 50),
        })
        result = self.service.evaluate("rsi_oversold", df, {"window": 14, "threshold": 30})
        assert isinstance(result, bool)

    def test_evaluate_unknown_signal_raises(self):
        import pandas as pd
        df = pd.DataFrame({"Close": [1, 2, 3]})
        with pytest.raises(ValueError, match="Unknown signal"):
            self.service.evaluate("nonexistent", df, {})
