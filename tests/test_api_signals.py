"""Tests for signal and indicator REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from kb_server.main import app

client = TestClient(app)


class TestSignalEndpoints:
    def test_list_signals(self):
        resp = client.get("/api/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 247

    def test_list_signals_filter_category(self):
        """Files are named for the ontology class they hold. momentum.py and volume.py each held
        several, and volume.py is gone -- there is no `volume` indicator class."""
        for category, total in (("Momentum", 52), ("Oscillator", 30), ("Averaging", 47),
                                ("Flow", 10), ("Pattern", 40), ("Volatility", 26),
                                ("Trend", 22)):
            resp = client.get(f"/api/signals?category={category}")
            assert resp.status_code == 200
            assert resp.json()["total"] == total, category

    def test_list_signals_filter_type(self):
        resp = client.get("/api/signals?signal_type=TRIGGER")
        assert resp.status_code == 200
        assert resp.json()["total"] == 117

    def test_get_signal(self):
        resp = client.get("/api/signals/rsi_oversold")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "rsi_oversold"
        assert data["type"] == "FILTER"

    def test_get_signal_not_found(self):
        resp = client.get("/api/signals/nonexistent")
        assert resp.status_code == 404


class TestIndicatorEndpoints:
    def test_list_indicators(self):
        resp = client.get("/api/indicators")
        assert resp.status_code == 200
        # 99 - 27 retired pattern indicators + CandleGeometry + CandleRelation.
        assert resp.json()["total"] == 73

    def test_get_indicator(self):
        resp = client.get("/api/indicators/RSI")
        assert resp.status_code == 200
        assert resp.json()["name"] == "RSI"

    def test_get_indicator_not_found(self):
        resp = client.get("/api/indicators/FakeIndicator")
        assert resp.status_code == 404
