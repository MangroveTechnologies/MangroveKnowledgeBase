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
        assert data["total"] == 243

    def test_list_signals_filter_category(self):
        resp = client.get("/api/signals?category=Momentum")
        assert resp.status_code == 200
        assert resp.json()["total"] == 42

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
        assert resp.json()["total"] == 74

    def test_get_indicator(self):
        resp = client.get("/api/indicators/RSI")
        assert resp.status_code == 200
        assert resp.json()["name"] == "RSI"

    def test_get_indicator_not_found(self):
        resp = client.get("/api/indicators/FakeIndicator")
        assert resp.status_code == 404
