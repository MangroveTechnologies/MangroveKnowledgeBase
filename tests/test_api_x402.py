import pytest
import json
import numpy as np
from fastapi.testclient import TestClient
from kb_server.main import app

client = TestClient(app)

class TestEvaluateEndpoint:
    def test_evaluate_without_payment_returns_402(self):
        body = {
            "name": "rsi_oversold",
            "ohlcv": {"Close": [100 + i for i in range(50)]},
            "params": {"window": 14, "threshold": 30}
        }
        resp = client.post("/api/evaluate", json=body)
        assert resp.status_code == 402

    def test_evaluate_with_payment_returns_result(self):
        np.random.seed(42)
        body = {
            "name": "rsi_oversold",
            "ohlcv": {
                "Open": np.random.uniform(100, 200, 50).tolist(),
                "High": np.random.uniform(150, 250, 50).tolist(),
                "Low": np.random.uniform(50, 150, 50).tolist(),
                "Close": np.random.uniform(100, 200, 50).tolist(),
                "Volume": np.random.uniform(1000, 5000, 50).tolist(),
            },
            "params": {"window": 14, "threshold": 30}
        }
        resp = client.post("/api/evaluate", json=body, headers={"X-402-Payment": "test_proof"})
        assert resp.status_code == 200
        assert "result" in resp.json()
        assert isinstance(resp.json()["result"], bool)

class TestComputeEndpoint:
    def test_compute_without_payment_returns_402(self):
        body = {
            "name": "RSI",
            "data": {"close": [100 + i for i in range(50)]},
            "params": {"window": 14}
        }
        resp = client.post("/api/compute", json=body)
        assert resp.status_code == 402

    def test_compute_with_payment_returns_result(self):
        np.random.seed(42)
        body = {
            "name": "RSI",
            "data": {"close": np.random.uniform(100, 200, 50).tolist()},
            "params": {"window": 14}
        }
        resp = client.post("/api/compute", json=body, headers={"X-402-Payment": "test_proof"})
        assert resp.status_code == 200
        assert "result" in resp.json()
        assert "rsi" in resp.json()["result"]
