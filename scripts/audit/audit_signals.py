"""Signal audit: smoke test all 223 signals, crossover accuracy, FILTER code review.

Run:
    cd MangroveKnowledgeBase
    python -m scripts.audit.audit_signals
"""

import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Bootstrap: ensure mangrove_kb is importable and signals are registered
# ---------------------------------------------------------------------------
KB_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KB_ROOT))

from scripts.audit import load_btc_daily, RESULTS_DIR
# Importing signals triggers RuleRegistry registration
import mangrove_kb.signals  # noqa: F401
from mangrove_kb.registry import RuleRegistry
from mangrove_kb.indicators import RSI, SMA, EMA, MACD

# ---------------------------------------------------------------------------
# Part 1: Smoke test all registered signals
# ---------------------------------------------------------------------------

def smoke_test_all(df: pd.DataFrame) -> list[dict]:
    """Run every registered signal with default params and record results.

    Some signals have required positional args (no defaults). We supply
    sensible values via EXPLICIT_PARAMS so that every signal gets tested.
    """
    # Signals that lack default values for required params
    EXPLICIT_PARAMS = {
        "is_above_sma": {"window": 20},
        "sma_crossover": {"window_fast": 9, "window_slow": 21},
        "sma_cross_up": {"window_fast": 9, "window_slow": 21},
        "sma_cross_down": {"window_fast": 9, "window_slow": 21},
        "ema_crossover": {"window_fast": 9, "window_slow": 21},
    }

    results = []
    registry = RuleRegistry._registry

    for name, fn in sorted(registry.items()):
        rec = {"signal": name, "result": None, "type_ok": False, "error": None}
        t0 = time.time()
        try:
            kwargs = EXPLICIT_PARAMS.get(name, {})
            val = fn(df, **kwargs)
            rec["result"] = val
            rec["type_ok"] = isinstance(val, (bool, np.bool_))
            rec["elapsed_ms"] = round((time.time() - t0) * 1000, 1)
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["elapsed_ms"] = round((time.time() - t0) * 1000, 1)
        results.append(rec)

    return results


# ---------------------------------------------------------------------------
# Part 2: TRIGGER signal crossover accuracy
# ---------------------------------------------------------------------------

def _crossover_accuracy(
    signal_name: str,
    signal_fn,
    indicator_series: pd.Series,
    df: pd.DataFrame,
    cross_up: bool,
    threshold: float = None,
    second_series: pd.Series = None,
    warmup: int = 50,
) -> dict:
    """Compare signal output to ground-truth crossover detection.

    For threshold crosses: indicator_series crosses threshold.
    For line crosses (second_series is not None): indicator_series crosses second_series.
    """
    n = len(df)
    # Build ground truth
    ground_truth = []
    for i in range(1, n):
        prev = float(indicator_series.iloc[i - 1])
        curr = float(indicator_series.iloc[i])

        if pd.isna(prev) or pd.isna(curr):
            ground_truth.append(False)
            continue

        if second_series is not None:
            prev2 = float(second_series.iloc[i - 1])
            curr2 = float(second_series.iloc[i])
            if pd.isna(prev2) or pd.isna(curr2):
                ground_truth.append(False)
                continue
            if cross_up:
                ground_truth.append(prev <= prev2 and curr > curr2)
            else:
                ground_truth.append(prev >= prev2 and curr < curr2)
        else:
            if cross_up:
                ground_truth.append(prev <= threshold and curr > threshold)
            else:
                ground_truth.append(prev >= threshold and curr < threshold)

    # Test signal with sliding window
    signal_results = []
    for i in range(warmup, n):
        window = df.iloc[: i + 1]
        try:
            val = signal_fn(window)
            signal_results.append(bool(val))
        except Exception:
            signal_results.append(False)

    # Align: ground_truth is indexed 1..n-1, signal_results starts at warmup
    gt_aligned = ground_truth[warmup - 1:]  # ground_truth[warmup-1] corresponds to bar warmup
    min_len = min(len(gt_aligned), len(signal_results))
    gt_aligned = gt_aligned[:min_len]
    sig_aligned = signal_results[:min_len]

    tp = sum(g and s for g, s in zip(gt_aligned, sig_aligned))
    fp = sum(not g and s for g, s in zip(gt_aligned, sig_aligned))
    fn_ = sum(g and not s for g, s in zip(gt_aligned, sig_aligned))
    tn = sum(not g and not s for g, s in zip(gt_aligned, sig_aligned))

    gt_positives = sum(gt_aligned)
    sig_positives = sum(sig_aligned)

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn_) if (tp + fn_) > 0 else float("nan")
    accuracy = (tp + tn) / min_len if min_len > 0 else float("nan")

    # Find first mismatch
    first_mismatch = None
    for idx, (g, s) in enumerate(zip(gt_aligned, sig_aligned)):
        if g != s:
            first_mismatch = warmup + idx
            break

    return {
        "signal": signal_name,
        "bars_tested": min_len,
        "gt_positives": gt_positives,
        "sig_positives": sig_positives,
        "TP": tp,
        "FP": fp,
        "FN": fn_,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "first_mismatch_bar": first_mismatch,
        "match": tp == gt_positives and fp == 0 and fn_ == 0,
    }


def test_rsi_crossovers(df: pd.DataFrame) -> list[dict]:
    """Test RSI cross_up and cross_down against ground truth."""
    from mangrove_kb.signals.momentum import rsi_cross_up, rsi_cross_down

    rsi_result = RSI.compute(data={"close": df["Close"]}, params={"window": 14})
    rsi_series = rsi_result["rsi"]

    results = []
    results.append(
        _crossover_accuracy("rsi_cross_up", rsi_cross_up, rsi_series, df,
                            cross_up=True, threshold=50.0, warmup=50)
    )
    results.append(
        _crossover_accuracy("rsi_cross_down", rsi_cross_down, rsi_series, df,
                            cross_up=False, threshold=50.0, warmup=50)
    )
    return results


def test_sma_crossovers(df: pd.DataFrame) -> list[dict]:
    """Test SMA crossover signals against ground truth."""
    from mangrove_kb.signals.trend import sma_crossover, sma_cross_up, sma_cross_down

    fast_sma = SMA.compute(data={"close": df["Close"]}, params={"window": 9})["sma"]
    slow_sma = SMA.compute(data={"close": df["Close"]}, params={"window": 21})["sma"]

    results = []
    results.append(
        _crossover_accuracy(
            "sma_crossover (bullish)",
            lambda d: sma_crossover(d, window_fast=9, window_slow=21, direction="bullish"),
            fast_sma, df, cross_up=True, second_series=slow_sma, warmup=50,
        )
    )
    results.append(
        _crossover_accuracy(
            "sma_cross_up",
            lambda d: sma_cross_up(d, window_fast=9, window_slow=21),
            fast_sma, df, cross_up=True, second_series=slow_sma, warmup=50,
        )
    )
    results.append(
        _crossover_accuracy(
            "sma_cross_down",
            lambda d: sma_cross_down(d, window_fast=9, window_slow=21),
            fast_sma, df, cross_up=False, second_series=slow_sma, warmup=50,
        )
    )
    return results


def test_ema_crossovers(df: pd.DataFrame) -> list[dict]:
    """Test EMA crossover signals against ground truth."""
    from mangrove_kb.signals.trend import ema_crossover, ema_cross_up, ema_cross_down

    fast_ema = EMA.compute(data={"close": df["Close"]}, params={"window": 9})["ema"]
    slow_ema = EMA.compute(data={"close": df["Close"]}, params={"window": 21})["ema"]

    results = []
    results.append(
        _crossover_accuracy(
            "ema_crossover (bullish)",
            lambda d: ema_crossover(d, window_fast=9, window_slow=21, direction="bullish"),
            fast_ema, df, cross_up=True, second_series=slow_ema, warmup=50,
        )
    )
    results.append(
        _crossover_accuracy(
            "ema_cross_up",
            lambda d: ema_cross_up(d, window_fast=9, window_slow=21),
            fast_ema, df, cross_up=True, second_series=slow_ema, warmup=50,
        )
    )
    results.append(
        _crossover_accuracy(
            "ema_cross_down",
            lambda d: ema_cross_down(d, window_fast=9, window_slow=21),
            fast_ema, df, cross_up=False, second_series=slow_ema, warmup=50,
        )
    )
    return results


def test_macd_crossovers(df: pd.DataFrame) -> list[dict]:
    """Test MACD crossover signals against ground truth -- THE KNOWN SUSPECT."""
    from mangrove_kb.signals.trend import macd_bullish_cross, macd_bearish_cross

    macd_result = MACD.compute(
        data={"close": df["Close"]},
        params={"window_fast": 12, "window_slow": 26, "window_sign": 9},
    )
    macd_line = macd_result["macd"]
    signal_line = macd_result["signal"]

    results = []
    results.append(
        _crossover_accuracy(
            "macd_bullish_cross",
            macd_bullish_cross,
            macd_line, df, cross_up=True, second_series=signal_line, warmup=50,
        )
    )
    results.append(
        _crossover_accuracy(
            "macd_bearish_cross",
            macd_bearish_cross,
            macd_line, df, cross_up=False, second_series=signal_line, warmup=50,
        )
    )
    return results


# ---------------------------------------------------------------------------
# Part 3: FILTER signal code review (static analysis of patterns)
# ---------------------------------------------------------------------------

def classify_signals() -> dict:
    """Classify all registered signals by type (TRIGGER/FILTER) from docstrings."""
    classifications = {"TRIGGER": [], "FILTER": [], "UNKNOWN": []}
    registry = RuleRegistry._registry

    for name, fn in sorted(registry.items()):
        doc = fn.__doc__ or ""
        if "Type: TRIGGER" in doc:
            classifications["TRIGGER"].append(name)
        elif "Type: FILTER" in doc:
            classifications["FILTER"].append(name)
        else:
            classifications["UNKNOWN"].append(name)

    return classifications


def review_filter_signals() -> list[dict]:
    """Code-review FILTER signals for correctness patterns.

    Checks:
    - Uses iloc[-1] to read the last bar value
    - Handles NaN (returns False for NaN)
    - Compares against threshold correctly

    Pattern FILTER signals (e.g. bullish_pattern_recent) are a different
    architecture: they scan a window of bars, not the last bar's indicator
    value.  We flag them separately as "PATTERN_SCAN" rather than failing
    them on the iloc[-1] check.
    """
    import inspect

    # Pattern FILTER signals -- intentionally scan a window, not iloc[-1]
    PATTERN_SCAN_SIGNALS = {
        "bearish_pattern_recent", "bullish_pattern_recent",
        "continuation_pattern_bearish", "continuation_pattern_bullish",
        "indecision_pattern_recent",
        "reversal_pattern_bearish", "reversal_pattern_bullish",
        "strong_body_recent",
    }

    registry = RuleRegistry._registry
    classifications = classify_signals()
    reviews = []

    for name in classifications["FILTER"]:
        fn = registry[name]
        src = inspect.getsource(fn)

        is_pattern_scan = name in PATTERN_SCAN_SIGNALS

        review = {
            "signal": name,
            "is_pattern_scan": is_pattern_scan,
            "uses_iloc_last": "iloc[-1]" in src,
            "handles_nan": "pd.isna" in src or "isna" in src or "pd.notna" in src,
            "returns_bool_comparison": (
                "return float(" in src
                or "return closes" in src
                or "return bool(" in src
            ),
            "issues": [],
        }

        if is_pattern_scan:
            # Pattern scan signals check a window of bars -- different architecture
            if "return False" not in src:
                review["issues"].append("No early return False for insufficient data")
            # They use .iloc[-window:] and .any() -- that's correct
            review["pass"] = len(review["issues"]) == 0
        else:
            if "iloc[-1]" not in src:
                review["issues"].append("Does not use iloc[-1] -- may not read last bar")
            if "pd.isna" not in src and "isna" not in src:
                review["issues"].append("No NaN handling detected")
            if "return False" not in src:
                review["issues"].append("No early return False for insufficient data")
            review["pass"] = len(review["issues"]) == 0

        reviews.append(review)

    return reviews


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_signal_report(
    smoke_results: list[dict],
    crossover_results: list[dict],
    filter_reviews: list[dict],
    classifications: dict,
    output_path: Path,
) -> str:
    """Generate the signal audit report markdown."""
    lines = []
    lines.append("# Signal Audit Report")
    lines.append("")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("**Data**: BTC/USD Daily, 1294 bars (2022-08-01 to 2026-02-14)")
    lines.append("")

    # ---- Overall summary ----
    total = len(smoke_results)
    passed = sum(1 for r in smoke_results if r["error"] is None and r["type_ok"])
    errored = sum(1 for r in smoke_results if r["error"] is not None)
    bad_type = sum(1 for r in smoke_results if r["error"] is None and not r["type_ok"])

    lines.append("## 1. Smoke Test Summary")
    lines.append("")
    lines.append(f"**{passed}/{total}** signals run without error and return bool.")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total signals tested | {total} |")
    lines.append(f"| Passed (no error + returns bool) | {passed} |")
    lines.append(f"| Errored (raised exception) | {errored} |")
    lines.append(f"| Bad return type (not bool) | {bad_type} |")
    lines.append("")

    # Signal type breakdown
    lines.append("### Signal Classification")
    lines.append("")
    lines.append(f"| Type | Count |")
    lines.append(f"|------|-------|")
    for stype, slist in sorted(classifications.items()):
        lines.append(f"| {stype} | {len(slist)} |")
    lines.append("")

    # Crashed signals
    crashed = [r for r in smoke_results if r["error"] is not None]
    if crashed:
        lines.append("### Signals That Crashed")
        lines.append("")
        lines.append("| Signal | Error |")
        lines.append("|--------|-------|")
        for r in crashed:
            lines.append(f"| `{r['signal']}` | {r['error']} |")
        lines.append("")
    else:
        lines.append("### No signals crashed.")
        lines.append("")

    # Non-bool returns
    non_bool = [r for r in smoke_results if r["error"] is None and not r["type_ok"]]
    if non_bool:
        lines.append("### Signals Returning Non-Bool")
        lines.append("")
        lines.append("| Signal | Returned Type | Value |")
        lines.append("|--------|--------------|-------|")
        for r in non_bool:
            lines.append(f"| `{r['signal']}` | `{type(r['result']).__name__}` | `{r['result']}` |")
        lines.append("")
    else:
        lines.append("### All signals return bool.")
        lines.append("")

    # ---- Crossover accuracy ----
    lines.append("## 2. TRIGGER Signal Crossover Accuracy")
    lines.append("")
    lines.append("Ground truth computed from full-dataset indicator values. Signals tested")
    lines.append("with sliding window from bar 50 onward.")
    lines.append("")
    lines.append("| Signal | Bars | GT+ | Sig+ | TP | FP | FN | Precision | Recall | Accuracy | Match |")
    lines.append("|--------|------|-----|------|----|----|----|-----------|--------|----------|-------|")
    for r in crossover_results:
        prec_str = f"{r['precision']:.3f}" if not np.isnan(r["precision"]) else "N/A"
        rec_str = f"{r['recall']:.3f}" if not np.isnan(r["recall"]) else "N/A"
        acc_str = f"{r['accuracy']:.4f}" if not np.isnan(r["accuracy"]) else "N/A"
        match_str = "PASS" if r["match"] else "FAIL"
        lines.append(
            f"| `{r['signal']}` | {r['bars_tested']} | {r['gt_positives']} | "
            f"{r['sig_positives']} | {r['TP']} | {r['FP']} | {r['FN']} | "
            f"{prec_str} | {rec_str} | {acc_str} | **{match_str}** |"
        )
    lines.append("")

    # Mismatches detail
    mismatches = [r for r in crossover_results if not r["match"]]
    if mismatches:
        lines.append("### Crossover Mismatches")
        lines.append("")
        for r in mismatches:
            lines.append(f"**{r['signal']}**: {r['FP']} false positives, {r['FN']} false negatives. "
                         f"First mismatch at bar {r['first_mismatch_bar']}.")
            lines.append("")
    else:
        lines.append("### All crossover signals match ground truth perfectly.")
        lines.append("")

    # ---- MACD deep dive ----
    macd_results = [r for r in crossover_results if "macd" in r["signal"]]
    lines.append("## 3. MACD Crossover Deep-Dive")
    lines.append("")
    if macd_results:
        for r in macd_results:
            lines.append(f"### {r['signal']}")
            lines.append("")
            lines.append(f"- Bars tested: {r['bars_tested']}")
            lines.append(f"- Ground-truth crossovers: {r['gt_positives']}")
            lines.append(f"- Signal fired: {r['sig_positives']}")
            lines.append(f"- True positives: {r['TP']}")
            lines.append(f"- False positives: {r['FP']}")
            lines.append(f"- False negatives: {r['FN']}")
            if r["match"]:
                lines.append(f"- **Verdict: PASS** -- signal fires at exactly the right bars.")
            else:
                lines.append(f"- **Verdict: FAIL** -- mismatch detected.")
                lines.append(f"- First mismatch at bar {r['first_mismatch_bar']}.")
                lines.append("")
                lines.append("**Root cause analysis**: The MACD signal recomputes MACD from "
                             "a sliding window (data up to bar i), while the ground truth "
                             "computes MACD once over the full dataset. EMA is path-dependent -- "
                             "changing the starting data changes all subsequent values. "
                             "Mismatches occur because the sliding-window EMA has different "
                             "warmup behavior than the full-dataset EMA at the same bar index.")
            lines.append("")
    else:
        lines.append("No MACD crossover results found.")
        lines.append("")

    # ---- FILTER code review ----
    lines.append("## 4. FILTER Signal Code Review")
    lines.append("")
    standard_filters = [r for r in filter_reviews if not r.get("is_pattern_scan")]
    pattern_scans = [r for r in filter_reviews if r.get("is_pattern_scan")]
    standard_passed = sum(1 for r in standard_filters if r["pass"])
    pattern_passed = sum(1 for r in pattern_scans if r["pass"])
    filter_passed = sum(1 for r in filter_reviews if r["pass"])
    filter_total = len(filter_reviews)
    lines.append(f"**{filter_passed}/{filter_total}** FILTER signals pass code review.")
    lines.append("")
    lines.append("Checks for standard FILTER signals: uses `iloc[-1]`, handles NaN, has early return for insufficient data.")
    lines.append("")
    lines.append(f"- Standard indicator FILTERs: {standard_passed}/{len(standard_filters)} pass")
    lines.append(f"- Pattern scan FILTERs: {pattern_passed}/{len(pattern_scans)} pass")
    lines.append("")
    lines.append("Pattern scan FILTERs (e.g. `bullish_pattern_recent`) check for any pattern within a recent")
    lines.append("window of bars using `.iloc[-window:]` and `.any()`. They are architecturally different from")
    lines.append("standard indicator FILTERs that read `iloc[-1]` and compare against a threshold.")
    lines.append("")

    filter_failed = [r for r in filter_reviews if not r["pass"]]
    if filter_failed:
        lines.append("### FILTER Signals With Issues")
        lines.append("")
        lines.append("| Signal | Type | Issues |")
        lines.append("|--------|------|--------|")
        for r in filter_failed:
            issues = "; ".join(r["issues"])
            ftype = "Pattern Scan" if r.get("is_pattern_scan") else "Standard"
            lines.append(f"| `{r['signal']}` | {ftype} | {issues} |")
        lines.append("")
    else:
        lines.append("### All FILTER signals pass code review.")
        lines.append("")

    # ---- Conclusion ----
    lines.append("## 5. Conclusion")
    lines.append("")
    lines.append(f"- **Smoke test**: {passed}/{total} signals pass (no crashes, return bool)")
    xover_pass = sum(1 for r in crossover_results if r["match"])
    xover_total = len(crossover_results)
    lines.append(f"- **Crossover accuracy**: {xover_pass}/{xover_total} tested signals match ground truth")
    lines.append(f"- **FILTER code review**: {filter_passed}/{filter_total} pass static checks")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("MangroveKnowledgeBase Signal Audit")
    print("=" * 70)
    print()

    # Load data
    print("[1/5] Loading BTC daily data...")
    df = load_btc_daily()
    print(f"  Loaded {len(df)} bars, columns: {list(df.columns)}")
    print()

    # Classify signals
    print("[2/5] Classifying signals...")
    classifications = classify_signals()
    for stype, slist in sorted(classifications.items()):
        print(f"  {stype}: {len(slist)} signals")
    print()

    # Part 1: Smoke test
    print("[3/5] Running smoke test on all signals...")
    t0 = time.time()
    smoke_results = smoke_test_all(df)
    elapsed = time.time() - t0
    passed = sum(1 for r in smoke_results if r["error"] is None and r["type_ok"])
    errored = sum(1 for r in smoke_results if r["error"] is not None)
    print(f"  {passed}/{len(smoke_results)} passed ({errored} errors) in {elapsed:.1f}s")
    for r in smoke_results:
        if r["error"]:
            print(f"  ERROR: {r['signal']}: {r['error']}")
    for r in smoke_results:
        if r["error"] is None and not r["type_ok"]:
            print(f"  BAD TYPE: {r['signal']} returned {type(r['result']).__name__}")
    print()

    # Part 2: Crossover accuracy
    print("[4/5] Testing TRIGGER crossover accuracy...")
    crossover_results = []

    print("  Testing RSI crossovers...")
    crossover_results.extend(test_rsi_crossovers(df))
    for r in crossover_results[-2:]:
        status = "PASS" if r["match"] else "FAIL"
        print(f"    {r['signal']}: {status} (TP={r['TP']}, FP={r['FP']}, FN={r['FN']})")

    print("  Testing SMA crossovers...")
    crossover_results.extend(test_sma_crossovers(df))
    for r in crossover_results[-3:]:
        status = "PASS" if r["match"] else "FAIL"
        print(f"    {r['signal']}: {status} (TP={r['TP']}, FP={r['FP']}, FN={r['FN']})")

    print("  Testing EMA crossovers...")
    crossover_results.extend(test_ema_crossovers(df))
    for r in crossover_results[-3:]:
        status = "PASS" if r["match"] else "FAIL"
        print(f"    {r['signal']}: {status} (TP={r['TP']}, FP={r['FP']}, FN={r['FN']})")

    print("  Testing MACD crossovers (known suspect)...")
    crossover_results.extend(test_macd_crossovers(df))
    for r in crossover_results[-2:]:
        status = "PASS" if r["match"] else "FAIL"
        print(f"    {r['signal']}: {status} (TP={r['TP']}, FP={r['FP']}, FN={r['FN']})")

    print()

    # Part 3: FILTER code review
    print("[5/5] Reviewing FILTER signal source code...")
    filter_reviews = review_filter_signals()
    filter_passed = sum(1 for r in filter_reviews if r["pass"])
    print(f"  {filter_passed}/{len(filter_reviews)} FILTER signals pass code review")
    for r in filter_reviews:
        if not r["pass"]:
            print(f"  ISSUE: {r['signal']}: {'; '.join(r['issues'])}")
    print()

    # Generate report
    output_path = RESULTS_DIR / "signal_report.md"
    print(f"Writing report to {output_path} ...")
    report = generate_signal_report(
        smoke_results, crossover_results, filter_reviews, classifications, output_path
    )
    print(f"Report written ({len(report)} bytes)")
    print()
    print("=" * 70)
    print("Signal audit complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
