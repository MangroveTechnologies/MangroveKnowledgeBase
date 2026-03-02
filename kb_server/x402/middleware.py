"""x402 payment validation middleware for REST and MCP."""

from kb_server.x402.pricing import is_gated, get_price


def validate_x402_payment(headers: dict, tool_name: str) -> dict:
    """Validate x402 payment for a tool invocation."""
    if not is_gated(tool_name):
        return {"valid": True}

    payment_header = headers.get("X-402-Payment") or headers.get("x-402-payment")
    if not payment_header:
        price = get_price(tool_name)
        return {
            "valid": False,
            "error": f"Payment required. Cost: ${price} USD. Include X-402-Payment header with payment proof.",
            "price": price,
            "tool": tool_name,
        }

    # TODO: Validate payment proof against facilitator
    return {"valid": True, "payment": payment_header}
