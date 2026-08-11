import pytest
from kb_server.services.signal_service import SignalService


class TestSignalServiceMetadata:
    def setup_method(self):
        self.service = SignalService()

    def test_list_signals_returns_all(self):
        signals = self.service.list_signals()
        assert len(signals) == 249

    def test_list_signals_filter_by_category(self):
        """Categories follow the file layout, and the files follow the ontology class.

        Two files held several classes at once and were split. momentum.py was 42: the bounded
        oscillators are `oscillator` and the KAMA crossings are `averaging`. volume.py was 33 and is
        gone entirely -- there is no `volume` indicator class, so its signals went four ways by the
        class of the indicator each reads, and `flow` (the cumulative lines: OBV, ADI, VPT, NVI)
        appeared as a file for the first time. trend.py was 88 and is down to the 24 whose class
        cannot be settled: all seven read SuperTrend's `direction` or PSAR's flip flags, which are
        verdicts rather than measurements, so there is nothing for them to inherit a class from."""
        assert len(self.service.list_signals(category="Momentum")) == 56
        assert len(self.service.list_signals(category="Oscillator")) == 30
        assert len(self.service.list_signals(category="Averaging")) == 55
        assert len(self.service.list_signals(category="Flow")) == 10
        assert len(self.service.list_signals(category="Pattern")) == 40
        assert len(self.service.list_signals(category="Volatility")) == 31
        # trend.py is not a class -- what is left there is what cannot be classified yet
        assert len(self.service.list_signals(category="Trend")) == 7

    def test_list_signals_filter_by_type(self):
        triggers = self.service.list_signals(signal_type="TRIGGER")
        assert len(triggers) == 119

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
