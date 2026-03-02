import pytest
from kb_server.x402.pricing import get_price, is_gated
from kb_server.x402.middleware import validate_x402_payment


class TestPricing:
    def test_evaluate_signal_is_gated(self):
        assert is_gated("evaluate_signal") is True

    def test_compute_indicator_is_gated(self):
        assert is_gated("compute_indicator") is True

    def test_kb_search_is_free(self):
        assert is_gated("kb_search") is False

    def test_gated_tool_has_price(self):
        price = get_price("evaluate_signal")
        assert price > 0

class TestPaymentValidation:
    def test_missing_payment_header_rejected(self):
        result = validate_x402_payment(headers={}, tool_name="evaluate_signal")
        assert result["valid"] is False
        assert "payment required" in result["error"].lower()

    def test_free_tool_no_payment_needed(self):
        result = validate_x402_payment(headers={}, tool_name="kb_search")
        assert result["valid"] is True

    def test_valid_payment_accepted(self):
        result = validate_x402_payment(
            headers={"X-402-Payment": "proof_abc123"},
            tool_name="evaluate_signal"
        )
        assert result["valid"] is True
