#!/usr/bin/env python3
"""Audit trend indicators against Bukosabino ta reference."""
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
import ta.trend as ta_trend

# Our implementations
from mangrove_kb.indicators.trend_indicators import (
    SMA, EMA, WMA, MACD, Aroon, TRIX, MassIndex, Ichimoku,
    KST, DPO, CCI, ADX, Vortex, PSAR, STC,
)


def run_audit():
    df = load_btc_daily()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    results = []

    # 1. SMA
    tol, tier = get_tolerance("SMA")
    results.append(compare_indicator(
        indicator_name="SMA",
        category="Trend",
        our_fn=lambda: SMA.compute({"close": close}, {"window": 20}),
        ref_fn=lambda: {
            "sma": ta_trend.SMAIndicator(close=close, window=20, fillna=False).sma_indicator()
        },
        output_keys=["sma"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 2. EMA
    tol, tier = get_tolerance("EMA")
    results.append(compare_indicator(
        indicator_name="EMA",
        category="Trend",
        our_fn=lambda: EMA.compute({"close": close}, {"window": 20}),
        ref_fn=lambda: {
            "ema": ta_trend.EMAIndicator(close=close, window=20, fillna=False).ema_indicator()
        },
        output_keys=["ema"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 3. WMA
    tol, tier = get_tolerance("WMA")
    results.append(compare_indicator(
        indicator_name="WMA",
        category="Trend",
        our_fn=lambda: WMA.compute({"close": close}, {"window": 9}),
        ref_fn=lambda: {
            "wma": ta_trend.WMAIndicator(close=close, window=9, fillna=False).wma()
        },
        output_keys=["wma"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 4. MACD
    tol, tier = get_tolerance("MACD")
    ref_macd = ta_trend.MACD(
        close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False,
    )
    results.append(compare_indicator(
        indicator_name="MACD",
        category="Trend",
        our_fn=lambda: MACD.compute(
            {"close": close},
            {"window_slow": 26, "window_fast": 12, "window_sign": 9},
        ),
        ref_fn=lambda: {
            "macd": ref_macd.macd(),
            "signal": ref_macd.macd_signal(),
            "histogram": ref_macd.macd_diff(),
        },
        output_keys=["macd", "signal", "histogram"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 5. Aroon
    tol, tier = get_tolerance("Aroon")
    ref_aroon = ta_trend.AroonIndicator(high=high, low=low, window=25, fillna=False)
    results.append(compare_indicator(
        indicator_name="Aroon",
        category="Trend",
        our_fn=lambda: Aroon.compute(
            {"high": high, "low": low},
            {"window": 25},
        ),
        ref_fn=lambda: {
            "aroon_up": ref_aroon.aroon_up(),
            "aroon_down": ref_aroon.aroon_down(),
            "aroon_indicator": ref_aroon.aroon_indicator(),
        },
        output_keys=["aroon_up", "aroon_down", "aroon_indicator"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 6. TRIX -- suspected fill_value divergence
    tol, tier = get_tolerance("TRIX")
    results.append(compare_indicator(
        indicator_name="TRIX",
        category="Trend",
        our_fn=lambda: TRIX.compute({"close": close}, {"window": 15}),
        ref_fn=lambda: {
            "trix": ta_trend.TRIXIndicator(close=close, window=15, fillna=False).trix()
        },
        output_keys=["trix"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Suspected fill_value divergence in shift -- both use fill_value=ema3.mean()",
    ))

    # 7. MassIndex
    tol, tier = get_tolerance("MassIndex")
    results.append(compare_indicator(
        indicator_name="MassIndex",
        category="Trend",
        our_fn=lambda: MassIndex.compute(
            {"high": high, "low": low},
            {"window_fast": 9, "window_slow": 25},
        ),
        ref_fn=lambda: {
            "mass_index": ta_trend.MassIndex(
                high=high, low=low, window_fast=9, window_slow=25, fillna=False,
            ).mass_index()
        },
        output_keys=["mass_index"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 8. Ichimoku (non-visual mode for direct comparison)
    tol, tier = get_tolerance("Ichimoku")
    ref_ichimoku = ta_trend.IchimokuIndicator(
        high=high, low=low, window1=9, window2=26, window3=52, visual=False, fillna=False,
    )
    results.append(compare_indicator(
        indicator_name="Ichimoku",
        category="Trend",
        our_fn=lambda: Ichimoku.compute(
            {"high": high, "low": low},
            {"window1": 9, "window2": 26, "window3": 52, "visual": False},
        ),
        ref_fn=lambda: {
            "conversion_line": ref_ichimoku.ichimoku_conversion_line(),
            "base_line": ref_ichimoku.ichimoku_base_line(),
            "span_a": ref_ichimoku.ichimoku_a(),
            "span_b": ref_ichimoku.ichimoku_b(),
        },
        output_keys=["conversion_line", "base_line", "span_a", "span_b"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Ichimoku span_b: ref uses min_periods=0 vs ours uses min_periods=window3",
    ))

    # 9. KST -- suspected fill_value divergence
    tol, tier = get_tolerance("KST")
    ref_kst = ta_trend.KSTIndicator(
        close=close, roc1=10, roc2=15, roc3=20, roc4=30,
        window1=10, window2=10, window3=10, window4=15, nsig=9, fillna=False,
    )
    results.append(compare_indicator(
        indicator_name="KST",
        category="Trend",
        our_fn=lambda: KST.compute(
            {"close": close},
            {"roc1": 10, "roc2": 15, "roc3": 20, "roc4": 30,
             "window1": 10, "window2": 10, "window3": 10, "window4": 15, "nsig": 9},
        ),
        ref_fn=lambda: {
            "kst": ref_kst.kst(),
            "kst_signal": ref_kst.kst_sig(),
            "kst_diff": ref_kst.kst_diff(),
        },
        output_keys=["kst", "kst_signal", "kst_diff"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Suspected fill_value divergence; ref uses min_periods=0 for kst_sig rolling",
    ))

    # 10. DPO -- suspected fill_value divergence
    tol, tier = get_tolerance("DPO")
    results.append(compare_indicator(
        indicator_name="DPO",
        category="Trend",
        our_fn=lambda: DPO.compute({"close": close}, {"window": 20}),
        ref_fn=lambda: {
            "dpo": ta_trend.DPOIndicator(close=close, window=20, fillna=False).dpo()
        },
        output_keys=["dpo"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Suspected fill_value divergence -- both use fill_value=close.mean()",
    ))

    # 11. CCI
    tol, tier = get_tolerance("CCI")
    results.append(compare_indicator(
        indicator_name="CCI",
        category="Trend",
        our_fn=lambda: CCI.compute(
            {"high": high, "low": low, "close": close},
            {"window": 20, "constant": 0.015},
        ),
        ref_fn=lambda: {
            "cci": ta_trend.CCIIndicator(
                high=high, low=low, close=close, window=20, constant=0.015, fillna=False,
            ).cci()
        },
        output_keys=["cci"],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # 12. ADX -- highest complexity
    tol, tier = get_tolerance("ADX")
    ref_adx = ta_trend.ADXIndicator(
        high=high, low=low, close=close, window=14, fillna=False,
    )
    results.append(compare_indicator(
        indicator_name="ADX",
        category="Trend",
        our_fn=lambda: ADX.compute(
            {"high": high, "low": low, "close": close},
            {"window": 14},
        ),
        ref_fn=lambda: {
            "adx": ref_adx.adx(),
            "adx_pos": ref_adx.adx_pos(),
            "adx_neg": ref_adx.adx_neg(),
        },
        output_keys=["adx", "adx_pos", "adx_neg"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Highest complexity indicator -- Wilder smoothing with manual loops",
    ))

    # 13. Vortex -- suspected fill_value divergence
    tol, tier = get_tolerance("Vortex")
    ref_vortex = ta_trend.VortexIndicator(
        high=high, low=low, close=close, window=14, fillna=False,
    )
    results.append(compare_indicator(
        indicator_name="Vortex",
        category="Trend",
        our_fn=lambda: Vortex.compute(
            {"high": high, "low": low, "close": close},
            {"window": 14},
        ),
        ref_fn=lambda: {
            "vortex_pos": ref_vortex.vortex_indicator_pos(),
            "vortex_neg": ref_vortex.vortex_indicator_neg(),
            "vortex_diff": ref_vortex.vortex_indicator_diff(),
        },
        output_keys=["vortex_pos", "vortex_neg", "vortex_diff"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Suspected fill_value divergence in close_shift",
    ))

    # 14. PSAR -- suspected copy-paste bug on psar_down_indicator
    tol, tier = get_tolerance("PSAR")
    ref_psar = ta_trend.PSARIndicator(
        high=high, low=low, close=close, step=0.02, max_step=0.20, fillna=False,
    )
    results.append(compare_indicator(
        indicator_name="PSAR",
        category="Trend",
        our_fn=lambda: {
            "psar": PSAR.compute(
                {"high": high, "low": low, "close": close},
                {"step": 0.02, "max_step": 0.20},
            )["psar"],
            "psar_up": PSAR.compute(
                {"high": high, "low": low, "close": close},
                {"step": 0.02, "max_step": 0.20},
            )["psar_up"],
            "psar_down": PSAR.compute(
                {"high": high, "low": low, "close": close},
                {"step": 0.02, "max_step": 0.20},
            )["psar_down"],
        },
        ref_fn=lambda: {
            "psar": ref_psar.psar(),
            "psar_up": ref_psar.psar_up(),
            "psar_down": ref_psar.psar_down(),
        },
        output_keys=["psar", "psar_up", "psar_down"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="Suspected copy-paste bug on psar_down_indicator (uses psar_up in where clause); comparing psar/psar_up/psar_down only",
    ))

    # 15. STC -- state machine, use RELAXED tolerance
    tol, tier = get_tolerance("STC")
    results.append(compare_indicator(
        indicator_name="STC",
        category="Trend",
        our_fn=lambda: STC.compute(
            {"close": close},
            {"window_slow": 50, "window_fast": 23, "cycle": 10, "smooth1": 3, "smooth2": 3},
        ),
        ref_fn=lambda: {
            "stc": ta_trend.STCIndicator(
                close=close, window_slow=50, window_fast=23,
                cycle=10, smooth1=3, smooth2=3, fillna=False,
            ).stc()
        },
        output_keys=["stc"],
        tolerance=tol,
        tolerance_tier=tier,
        notes="State machine -- RELAXED tolerance tier",
    ))

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("TREND INDICATORS AUDIT (15 indicators)")
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
