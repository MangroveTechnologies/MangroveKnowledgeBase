#!/usr/bin/env python3
"""Audit return indicators against Bukosabino ta reference."""
import sys
sys.path.insert(0, "scripts")

from audit import load_btc_daily
from audit.compare import compare_indicator
from audit.config import get_tolerance

from mangrove_kb.indicators.return_indicators import (
    DailyReturn,
    DailyLogReturn,
    CumulativeReturn,
)
import ta.others


def run_audit():
    df = load_btc_daily()
    close = df['close']
    results = []

    # --- DailyReturn ---
    tol, tier = get_tolerance("DailyReturn")
    results.append(compare_indicator(
        indicator_name="DailyReturn",
        category="Others",
        our_fn=lambda: DailyReturn.compute({'close': close}, {}),
        ref_fn=lambda: {
            'daily_return': ta.others.DailyReturnIndicator(close=close, fillna=False).daily_return()
        },
        output_keys=['daily_return'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- DailyLogReturn ---
    tol, tier = get_tolerance("DailyLogReturn")
    results.append(compare_indicator(
        indicator_name="DailyLogReturn",
        category="Others",
        our_fn=lambda: DailyLogReturn.compute({'close': close}, {}),
        ref_fn=lambda: {
            'daily_log_return': ta.others.DailyLogReturnIndicator(close=close, fillna=False).daily_log_return()
        },
        output_keys=['daily_log_return'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- CumulativeReturn ---
    tol, tier = get_tolerance("CumulativeReturn")
    results.append(compare_indicator(
        indicator_name="CumulativeReturn",
        category="Others",
        our_fn=lambda: CumulativeReturn.compute({'close': close}, {}),
        ref_fn=lambda: {
            'cumulative_return': ta.others.CumulativeReturnIndicator(close=close, fillna=False).cumulative_return()
        },
        output_keys=['cumulative_return'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    return results


if __name__ == "__main__":
    results = run_audit()
    for r in results:
        status = "PASS" if r.pass_fail else "FAIL"
        errors = ", ".join(f"{k}={v.max_abs_error:.2e}" for k, v in r.outputs.items())
        notes = f" [{r.notes}]" if r.notes else ""
        print(f"  {r.indicator_name}: {status} ({errors}){notes}")
