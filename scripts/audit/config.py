"""Tolerance tiers and indicator configuration for the audit."""

# Tolerance tiers
EXACT = 1e-10
FLOAT = 1e-6
RELAXED = 1e-3

# Indicator -> tolerance tier mapping
TOLERANCE_MAP = {
    # EXACT tier - simple arithmetic
    "SMA": EXACT, "EMA": EXACT, "WMA": EXACT, "ROC": EXACT,
    "OBV": EXACT,
    "DailyReturn": EXACT, "DailyLogReturn": EXACT, "CumulativeReturn": EXACT,
    # FLOAT tier - chained floating point
    "RSI": FLOAT, "TSI": FLOAT, "UltimateOscillator": FLOAT,
    "StochasticOscillator": FLOAT, "KAMA": FLOAT,
    "AwesomeOscillator": FLOAT, "WilliamsR": FLOAT,
    "StochRSI": FLOAT, "PPO": FLOAT, "PVO": FLOAT,
    "MACD": FLOAT, "Aroon": FLOAT, "TRIX": FLOAT,
    "MassIndex": FLOAT, "Ichimoku": FLOAT, "KST": FLOAT,
    "DPO": FLOAT, "CCI": FLOAT, "ADX": FLOAT, "Vortex": FLOAT,
    "ATR": FLOAT, "BollingerBands": FLOAT,
    "KeltnerChannel": FLOAT, "DonchianChannel": FLOAT, "UlcerIndex": FLOAT,
    "ADI": FLOAT, "CMF": FLOAT, "ForceIndex": FLOAT,
    "EaseOfMovement": FLOAT, "VPT": FLOAT, "NVI": FLOAT,
    "MFI": FLOAT, "VWAP": FLOAT,
    # RELAXED tier - state machines
    "PSAR": RELAXED, "STC": RELAXED,
}


def get_tolerance(indicator_name: str) -> tuple[float, str]:
    """Get tolerance value and tier name for an indicator."""
    if indicator_name in TOLERANCE_MAP:
        val = TOLERANCE_MAP[indicator_name]
        if val == EXACT:
            return val, "EXACT"
        elif val == FLOAT:
            return val, "FLOAT"
        else:
            return val, "RELAXED"
    return FLOAT, "FLOAT"  # default
