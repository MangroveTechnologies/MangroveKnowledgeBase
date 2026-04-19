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
        assert data["total"] == 182

    def test_list_signals_filter_category(self):
        resp = client.get("/api/signals?category=Momentum")
        assert resp.status_code == 200
        assert resp.json()["total"] == 42

    def test_list_signals_filter_type(self):
        resp = client.get("/api/signals?signal_type=TRIGGER")
        assert resp.status_code == 200
        assert resp.json()["total"] == 94

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
        assert resp.json()["total"] == 84

    def test_get_indicator(self):
        resp = client.get("/api/indicators/RSI")
        assert resp.status_code == 200
        assert resp.json()["name"] == "RSI"

    def test_get_indicator_not_found(self):
        resp = client.get("/api/indicators/FakeIndicator")
        assert resp.status_code == 404
