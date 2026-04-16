#!/usr/bin/env python3
"""Audit momentum indicators against Bukosabino ta reference."""
import sys
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from audit import load_btc_daily
from audit.compare import compare_indicator
from audit.config import get_tolerance

# Reference library
sys.path.insert(0, "/home/darrahts/mangrove/MangroveResearch/ta-master")
import ta.momentum as ta_mom

# Our implementations
from mangrove_kb.indicators.momentum_indicators import (
    RSI, TSI, UltimateOscillator, StochasticOscillator, KAMA,
    ROC, AwesomeOscillator, WilliamsR, StochRSI, PPO, PVO,
)


def run_audit():
    df = load_btc_daily()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    results = []

    # 1. RSI
    tol, tier = get_tolerance("RSI")
    results.append(compare_indicator(
        indicator_name="RSI",
        category="Momentum",
        our_fn=lambda: RSI.compute({"close": close}, {"window": 14}),
        ref_fn=lambda: {"rsi": ta_mom.RSIIndicator(close=close, window=14, fillna=False).rsi()},
        output_keys=["rsi"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 2. TSI
    tol, tier = get_tolerance("TSI")
    results.append(compare_indicator(
        indicator_name="TSI",
        category="Momentum",
        our_fn=lambda: TSI.compute({"close": close}, {"window_slow": 25, "window_fast": 13}),
        ref_fn=lambda: {"tsi": ta_mom.TSIIndicator(close=close, window_slow=25, window_fast=13, fillna=False).tsi()},
        output_keys=["tsi"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 3. UltimateOscillator
    tol, tier = get_tolerance("UltimateOscillator")
    results.append(compare_indicator(
        indicator_name="UltimateOscillator",
        category="Momentum",
        our_fn=lambda: UltimateOscillator.compute(
            {"high": high, "low": low, "close": close},
            {"window1": 7, "window2": 14, "window3": 28,
             "weight1": 4.0, "weight2": 2.0, "weight3": 1.0},
        ),
        ref_fn=lambda: {
            "ultimate_oscillator": ta_mom.UltimateOscillator(
                high=high, low=low, close=close,
                window1=7, window2=14, window3=28,
                weight1=4.0, weight2=2.0, weight3=1.0,
                fillna=False,
            ).ultimate_oscillator()
        },
        output_keys=["ultimate_oscillator"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 4. StochasticOscillator
    tol, tier = get_tolerance("StochasticOscillator")
    results.append(compare_indicator(
        indicator_name="StochasticOscillator",
        category="Momentum",
        our_fn=lambda: StochasticOscillator.compute(
            {"high": high, "low": low, "close": close},
            {"window": 14, "smooth_window": 3},
        ),
        ref_fn=lambda: {
            "stoch_k": ta_mom.StochasticOscillator(
                high=high, low=low, close=close,
                window=14, smooth_window=3, fillna=False,
            ).stoch(),
            "stoch_d": ta_mom.StochasticOscillator(
                high=high, low=low, close=close,
                window=14, smooth_window=3, fillna=False,
            ).stoch_signal(),
        },
        output_keys=["stoch_k", "stoch_d"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 5. KAMA
    tol, tier = get_tolerance("KAMA")
    results.append(compare_indicator(
        indicator_name="KAMA",
        category="Momentum",
        our_fn=lambda: KAMA.compute(
            {"close": close},
            {"window": 10, "pow1": 2, "pow2": 30},
        ),
        ref_fn=lambda: {
            "kama": ta_mom.KAMAIndicator(
                close=close, window=10, pow1=2, pow2=30, fillna=False,
            ).kama()
        },
        output_keys=["kama"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 6. ROC
    tol, tier = get_tolerance("ROC")
    results.append(compare_indicator(
        indicator_name="ROC",
        category="Momentum",
        our_fn=lambda: ROC.compute({"close": close}, {"window": 12}),
        ref_fn=lambda: {"roc": ta_mom.ROCIndicator(close=close, window=12, fillna=False).roc()},
        output_keys=["roc"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 7. AwesomeOscillator
    tol, tier = get_tolerance("AwesomeOscillator")
    results.append(compare_indicator(
        indicator_name="AwesomeOscillator",
        category="Momentum",
        our_fn=lambda: AwesomeOscillator.compute(
            {"high": high, "low": low},
            {"window1": 5, "window2": 34},
        ),
        ref_fn=lambda: {
            "ao": ta_mom.AwesomeOscillatorIndicator(
                high=high, low=low, window1=5, window2=34, fillna=False,
            ).awesome_oscillator()
        },
        output_keys=["ao"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 8. WilliamsR
    tol, tier = get_tolerance("WilliamsR")
    results.append(compare_indicator(
        indicator_name="WilliamsR",
        category="Momentum",
        our_fn=lambda: WilliamsR.compute(
            {"high": high, "low": low, "close": close},
            {"window": 14},
        ),
        ref_fn=lambda: {
            "wr": ta_mom.WilliamsRIndicator(
                high=high, low=low, close=close, lbp=14, fillna=False,
            ).williams_r()
        },
        output_keys=["wr"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 9. StochRSI
    tol, tier = get_tolerance("StochRSI")
    results.append(compare_indicator(
        indicator_name="StochRSI",
        category="Momentum",
        our_fn=lambda: StochRSI.compute(
            {"close": close},
            {"window": 14, "smooth1": 3, "smooth2": 3},
        ),
        ref_fn=lambda: {
            "stochrsi": ta_mom.StochRSIIndicator(
                close=close, window=14, smooth1=3, smooth2=3, fillna=False,
            ).stochrsi(),
            "stochrsi_k": ta_mom.StochRSIIndicator(
                close=close, window=14, smooth1=3, smooth2=3, fillna=False,
            ).stochrsi_k(),
            "stochrsi_d": ta_mom.StochRSIIndicator(
                close=close, window=14, smooth1=3, smooth2=3, fillna=False,
            ).stochrsi_d(),
        },
        output_keys=["stochrsi", "stochrsi_k", "stochrsi_d"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 10. PPO
    tol, tier = get_tolerance("PPO")
    results.append(compare_indicator(
        indicator_name="PPO",
        category="Momentum",
        our_fn=lambda: PPO.compute(
            {"close": close},
            {"window_slow": 26, "window_fast": 12, "window_sign": 9},
        ),
        ref_fn=lambda: {
            "ppo": ta_mom.PercentagePriceOscillator(
                close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False,
            ).ppo(),
            "ppo_signal": ta_mom.PercentagePriceOscillator(
                close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False,
            ).ppo_signal(),
            "ppo_hist": ta_mom.PercentagePriceOscillator(
                close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False,
            ).ppo_hist(),
        },
        output_keys=["ppo", "ppo_signal", "ppo_hist"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 11. PVO
    tol, tier = get_tolerance("PVO")
    results.append(compare_indicator(
        indicator_name="PVO",
        category="Momentum",
        our_fn=lambda: PVO.compute(
            {"volume": volume},
            {"window_slow": 26, "window_fast": 12, "window_sign": 9},
        ),
        ref_fn=lambda: {
            "pvo": ta_mom.PercentageVolumeOscillator(
                volume=volume, window_slow=26, window_fast=12, window_sign=9, fillna=False,
            ).pvo(),
            "pvo_signal": ta_mom.PercentageVolumeOscillator(
                volume=volume, window_slow=26, window_fast=12, window_sign=9, fillna=False,
            ).pvo_signal(),
            "pvo_hist": ta_mom.PercentageVolumeOscillator(
                volume=volume, window_slow=26, window_fast=12, window_sign=9, fillna=False,
            ).pvo_hist(),
        },
        output_keys=["pvo", "pvo_signal", "pvo_hist"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("MOMENTUM INDICATORS AUDIT (11 indicators)")
    print("=" * 60)
    results = run_audit()
    passed = 0
    failed = 0
    for r in results:
        status = "PASS" if r.pass_fail else "FAIL"
        if r.pass_fail:
            passed += 1
        else:
            failed += 1
        errors = ", ".join(f"{k}={v.max_abs_error:.2e}" for k, v in r.outputs.items())
        notes = f" [{r.notes}]" if r.notes else ""
        print(f"  {r.indicator_name}: {status} ({errors}){notes}")
        if not r.pass_fail:
            for k, v in r.outputs.items():
                if not v.pass_fail:
                    print(f"    -> {k}: max_err={v.max_abs_error:.2e}, "
                          f"mean_err={v.mean_abs_error:.2e}, "
                          f"nan_mismatches={v.nan_mismatches}, "
                          f"first_diverge_bar={v.first_divergence_bar}, "
                          f"overlap={v.overlap_bars}")
    print("-" * 60)
    print(f"TOTAL: {passed} PASS, {failed} FAIL out of {len(results)}")
