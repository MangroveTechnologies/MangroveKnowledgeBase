"""MangroveKnowledgeBase Indicator & Signal Audit Framework."""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent.parent.parent / "audit_results"
KB_ROOT = Path(__file__).parent.parent.parent


def load_btc_daily() -> pd.DataFrame:
    """Load BTC daily OHLCV data with both lowercase and capitalized columns."""
    df = pd.read_csv(DATA_DIR / "btc_2022-08-01_2026-02-15_1d.csv")
    df.columns = [c.strip().lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    # Add capitalized aliases for signal functions
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col.capitalize()] = df[col]
    return df
