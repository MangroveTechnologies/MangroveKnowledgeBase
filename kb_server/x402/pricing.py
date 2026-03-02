"""x402 pricing configuration for gated tools."""

GATED_TOOLS = {
    "evaluate_signal": 0.001,
    "compute_indicator": 0.001,
}

def is_gated(tool_name: str) -> bool:
    return tool_name in GATED_TOOLS

def get_price(tool_name: str) -> float:
    return GATED_TOOLS.get(tool_name, 0.0)
