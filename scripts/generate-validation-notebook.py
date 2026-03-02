#!/usr/bin/env python3
"""Generate the signal validation Jupyter notebook.

Creates notebooks/signal_validation.ipynb with one plot per signal,
showing where each signal fires on BTC daily data.

Usage:
    python scripts/generate-validation-notebook.py
    jupyter notebook notebooks/signal_validation.ipynb
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "notebooks", "signal_validation.ipynb")


def code_cell(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().split("\n"),
    }


def md_cell(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().split("\n"),
    }


def fix_newlines(cells):
    """Add newlines to all source lines except the last."""
    for cell in cells:
        src = cell["source"]
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
    return cells


def build_notebook():
    cells = []

    # Title
    cells.append(md_cell("""# Signal Validation Report

Validates all 136 trading signals from `mangrove-kb` against BTC daily data (2022-2026).
Each signal gets one plot showing where it fires (TRIGGER) or is active (FILTER).

**Dataset:** BTC/USD 1D, 1295 bars, 2022-08-01 to 2026-02-14"""))

    # Setup cell
    cells.append(code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from mangrove_kb.registry import RuleRegistry
from mangrove_kb.docstring_parser import parse_all_signals
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns

# Parse all signals
SIGNAL_MODULES = [momentum, trend, volume, volatility, patterns]
all_signals = parse_all_signals(SIGNAL_MODULES)

# Classify by category
MODULE_CAT = {
    "momentum": "Momentum", "trend": "Trend", "volume": "Volume",
    "volatility": "Volatility", "patterns": "Patterns",
}
signal_categories = {}
for name in all_signals:
    func = RuleRegistry._registry.get(name)
    if func:
        mod = getattr(func, "__module__", "")
        for k, v in MODULE_CAT.items():
            if k in mod:
                signal_categories[name] = v
                break

# Load BTC daily data
df = pd.read_csv("../data/btc_2022-08-01_2026-02-15_1d.csv")
df.columns = [c.strip().capitalize() for c in df.columns]
df["Timestamp"] = pd.to_datetime(df["Timestamp"])
df = df.sort_values("Timestamp").reset_index(drop=True)

# Required params for signals that have no defaults
REQUIRED_PARAMS = {
    "ema_crossover": {"window_fast": 12, "window_slow": 26},
    "is_above_sma": {"window": 20},
    "sma_cross_down": {"window_fast": 10, "window_slow": 50},
    "sma_cross_up": {"window_fast": 10, "window_slow": 50},
    "sma_crossover": {"window_fast": 10, "window_slow": 50},
}

print(f"Loaded {len(all_signals)} signals, {len(df)} bars")
print(f"Date range: {df['Timestamp'].iloc[0].date()} to {df['Timestamp'].iloc[-1].date()}")"""))

    # Helper functions
    cells.append(code_cell("""def evaluate_signal_rolling(name, df, warmup=50, params=None):
    \"\"\"Evaluate a signal on every bar from warmup to end. Returns list of fire indices.\"\"\"
    if params is None:
        params = REQUIRED_PARAMS.get(name, {})
    fire_indices = []
    for i in range(warmup, len(df)):
        try:
            result = RuleRegistry.evaluate({"name": name, "params": params}, df.iloc[:i+1])
            if result:
                fire_indices.append(i)
        except Exception:
            pass
    return fire_indices


def plot_trigger_signal(name, df, fire_indices, category, is_pattern=False):
    \"\"\"Plot a TRIGGER signal with markers at fire points.\"\"\"
    fig, ax = plt.subplots(figsize=(14, 4))
    dates = df["Timestamp"]
    ax.plot(dates, df["Close"], color="#555555", linewidth=0.8, alpha=0.7)

    if is_pattern and fire_indices:
        # For patterns, draw candlesticks near fires
        for idx in fire_indices:
            o, h, l, c = df.iloc[idx][["Open", "High", "Low", "Close"]]
            color = "#26a69a" if c >= o else "#ef5350"
            ax.vlines(dates.iloc[idx], l, h, color=color, linewidth=0.8)
            ax.vlines(dates.iloc[idx], min(o, c), max(o, c), color=color, linewidth=3)

    if fire_indices:
        ax.scatter(
            dates.iloc[fire_indices], df["Close"].iloc[fire_indices],
            marker="^", color="#26a69a", s=40, zorder=5, label=f"Fires ({len(fire_indices)})"
        )
    ax.set_title(f"{name}  [{category} / TRIGGER]  --  {len(fire_indices)} fires", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=45, fontsize=8)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_filter_signal(name, df, fire_indices, category):
    \"\"\"Plot a FILTER signal with shaded active regions.\"\"\"
    fig, ax = plt.subplots(figsize=(14, 4))
    dates = df["Timestamp"]
    ax.plot(dates, df["Close"], color="#555555", linewidth=0.8, alpha=0.7)

    if fire_indices:
        # Shade active regions
        active = np.zeros(len(df), dtype=bool)
        active[fire_indices] = True
        ymin, ymax = df["Close"].min() * 0.98, df["Close"].max() * 1.02
        ax.fill_between(dates, ymin, ymax, where=active, color="#42A7C6", alpha=0.15, label=f"Active ({len(fire_indices)} bars)")

    ax.set_title(f"{name}  [{category} / FILTER]  --  {len(fire_indices)} active bars", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=45, fontsize=8)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()"""))

    # Summary scan
    cells.append(md_cell("## Summary Scan\n\nEvaluate all 136 signals and collect fire counts."))
    cells.append(code_cell("""results = {}
errors = {}

for name in sorted(all_signals.keys()):
    meta = all_signals[name]
    cat = signal_categories.get(name, "Other")
    typ = meta.get("type", "?")
    try:
        fires = evaluate_signal_rolling(name, df)
        results[name] = {"category": cat, "type": typ, "fires": len(fires), "indices": fires}
    except Exception as e:
        errors[name] = {"category": cat, "type": typ, "error": str(e)[:80]}
        results[name] = {"category": cat, "type": typ, "fires": 0, "indices": []}

# Summary table
summary = pd.DataFrame([
    {"Signal": n, "Category": r["category"], "Type": r["type"], "Fires": r["fires"]}
    for n, r in sorted(results.items())
])

print(f"Total signals: {len(results)}")
print(f"Signals that fire: {sum(1 for r in results.values() if r['fires'] > 0)}")
print(f"Signals that never fire: {sum(1 for r in results.values() if r['fires'] == 0)}")
print(f"Errors: {len(errors)}")
if errors:
    print("\\nErrors:")
    for n, e in errors.items():
        print(f"  {n}: {e['error']}")

print("\\n--- Fire counts by category ---")
for cat in ["Momentum", "Trend", "Volume", "Volatility", "Patterns"]:
    cat_sigs = {n: r for n, r in results.items() if r["category"] == cat}
    fires = sum(1 for r in cat_sigs.values() if r["fires"] > 0)
    total = len(cat_sigs)
    print(f"  {cat}: {fires}/{total} fire")

summary"""))

    # Per-category sections
    for category in ["Momentum", "Trend", "Volume", "Volatility", "Patterns"]:
        cells.append(md_cell(f"## {category} Signals"))
        is_pattern = category == "Patterns"
        cells.append(code_cell(f"""cat_signals = {{n: r for n, r in results.items() if r["category"] == "{category}"}}

for name in sorted(cat_signals.keys()):
    r = cat_signals[name]
    meta = all_signals[name]
    fire_indices = r["indices"]

    if r["type"] == "TRIGGER":
        plot_trigger_signal(name, df, fire_indices, "{category}", is_pattern={is_pattern})
    else:
        plot_filter_signal(name, df, fire_indices, "{category}")"""))

    # Final report
    cells.append(md_cell("## Final Report"))
    cells.append(code_cell("""never_fire = [n for n, r in sorted(results.items()) if r["fires"] == 0]
print(f"Signals that never fired on BTC daily ({len(never_fire)}):")
print("(Some are expected -- e.g. piercing_line/dark_cloud_cover require session gaps)")
print()
for n in never_fire:
    r = results[n]
    print(f"  {n} ({r['category']}/{r['type']})")

print(f"\\n--- Summary ---")
print(f"Total signals validated: {len(results)}")
print(f"Signals with fires: {sum(1 for r in results.values() if r['fires'] > 0)}")
print(f"Signals never fired: {len(never_fire)}")
print(f"Errors: {len(errors)}")
print(f"\\nDataset: BTC/USD 1D, {len(df)} bars")
print(f"Date range: {df['Timestamp'].iloc[0].date()} to {df['Timestamp'].iloc[-1].date()}")"""))

    cells = fix_newlines(cells)

    notebook = {
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": cells,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(notebook, f, indent=1)

    print(f"Generated {OUTPUT_PATH}")
    print(f"  {len(cells)} cells ({sum(1 for c in cells if c['cell_type'] == 'code')} code, {sum(1 for c in cells if c['cell_type'] == 'markdown')} markdown)")


if __name__ == "__main__":
    build_notebook()
