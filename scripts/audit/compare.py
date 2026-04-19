"""Core comparison engine for indicator and signal audit."""

from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from typing import Callable, Optional, Any


@dataclass
class AuditResult:
    """Result of comparing one indicator against a reference."""
    indicator_name: str
    category: str
    reference_library: str
    tolerance_tier: str
    tolerance_value: float
    outputs: dict = field(default_factory=dict)  # output_key -> OutputResult
    pass_fail: bool = True
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "indicator": self.indicator_name,
            "category": self.category,
            "reference": self.reference_library,
            "tolerance_tier": self.tolerance_tier,
            "tolerance": self.tolerance_value,
            "pass": self.pass_fail,
            "outputs": {k: v.to_dict() for k, v in self.outputs.items()},
            "notes": self.notes,
        }


@dataclass
class OutputResult:
    """Result for a single output series comparison."""
    output_key: str
    max_abs_error: float = 0.0
    mean_abs_error: float = 0.0
    nan_mismatches: int = 0
    first_divergence_bar: Optional[int] = None
    overlap_bars: int = 0
    pass_fail: bool = True

    def to_dict(self) -> dict:
        return {
            "output": self.output_key,
            "max_abs_error": self.max_abs_error,
            "mean_abs_error": self.mean_abs_error,
            "nan_mismatches": self.nan_mismatches,
            "first_divergence_bar": self.first_divergence_bar,
            "overlap_bars": self.overlap_bars,
            "pass": self.pass_fail,
        }


def compare_series(
    ours: pd.Series,
    ref: pd.Series,
    tolerance: float,
    skip_warmup: int = 0,
    relative: bool = False,
) -> OutputResult:
    """Compare two pandas Series element-wise.

    Args:
        ours: Our implementation's output series
        ref: Reference implementation's output series
        tolerance: Maximum acceptable error (absolute unless relative=True)
        skip_warmup: Skip first N bars (different warmup handling)
        relative: If True, tolerance is relative to |ref| (good for price-space indicators)
    """
    result = OutputResult(output_key="")

    # Align by position (both should be same length)
    min_len = min(len(ours), len(ref))
    o = ours.iloc[skip_warmup:min_len].reset_index(drop=True)
    r = ref.iloc[skip_warmup:min_len].reset_index(drop=True)

    # Find where both are non-NaN
    both_valid = o.notna() & r.notna()
    # Find NaN mismatches (one is NaN, other isn't)
    nan_mismatch = (o.notna() & r.isna()) | (o.isna() & r.notna())
    result.nan_mismatches = int(nan_mismatch.sum())

    # Compare on overlap
    o_valid = o[both_valid].astype(float)
    r_valid = r[both_valid].astype(float)
    result.overlap_bars = len(o_valid)

    if result.overlap_bars == 0:
        result.pass_fail = False
        return result

    abs_diff = np.abs(o_valid.values - r_valid.values)
    result.max_abs_error = float(np.max(abs_diff))
    result.mean_abs_error = float(np.mean(abs_diff))

    if relative:
        # Relative tolerance: |ours - ref| / max(|ref|, epsilon) <= tolerance
        denom = np.maximum(np.abs(r_valid.values), 1e-12)
        rel_diff = abs_diff / denom
        divergent = rel_diff > tolerance
        result.pass_fail = bool(rel_diff.max() <= tolerance)
    else:
        divergent = abs_diff > tolerance
        result.pass_fail = result.max_abs_error <= tolerance

    # First divergence bar
    if divergent.any():
        result.first_divergence_bar = int(np.argmax(divergent)) + skip_warmup

    return result


def compare_indicator(
    indicator_name: str,
    category: str,
    our_fn: Callable,
    ref_fn: Callable,
    output_keys: list[str],
    ref_output_keys: Optional[list[str]] = None,
    tolerance: float = 1e-6,
    tolerance_tier: str = "FLOAT",
    skip_warmup: int = 0,
    reference_library: str = "Bukosabino ta",
    notes: str = "",
    relative: bool = False,
) -> AuditResult:
    """Compare our indicator implementation against a reference.

    Args:
        indicator_name: Name of the indicator
        category: Category (Momentum, Trend, etc.)
        our_fn: Callable returning dict[str, pd.Series]
        ref_fn: Callable returning dict[str, pd.Series]
        output_keys: Our output keys to compare
        ref_output_keys: Reference output keys (if different from ours)
        tolerance: Maximum acceptable absolute error
        tolerance_tier: Name of the tolerance tier
        skip_warmup: Skip first N bars
        reference_library: Name of reference library
        notes: Additional notes
    """
    if ref_output_keys is None:
        ref_output_keys = output_keys

    result = AuditResult(
        indicator_name=indicator_name,
        category=category,
        reference_library=reference_library,
        tolerance_tier=tolerance_tier,
        tolerance_value=tolerance,
        notes=notes,
    )

    try:
        our_outputs = our_fn()
    except Exception as e:
        result.pass_fail = False
        result.notes = f"OUR IMPLEMENTATION RAISED: {e}"
        return result

    try:
        ref_outputs = ref_fn()
    except Exception as e:
        result.pass_fail = False
        result.notes = f"REFERENCE RAISED: {e}"
        return result

    for our_key, ref_key in zip(output_keys, ref_output_keys):
        if our_key not in our_outputs:
            result.pass_fail = False
            result.notes += f" Missing output key '{our_key}' in our implementation."
            continue
        if ref_key not in ref_outputs:
            result.pass_fail = False
            result.notes += f" Missing output key '{ref_key}' in reference."
            continue

        output_result = compare_series(
            our_outputs[our_key],
            ref_outputs[ref_key],
            tolerance=tolerance,
            skip_warmup=skip_warmup,
            relative=relative,
        )
        output_result.output_key = our_key
        result.outputs[our_key] = output_result

        if not output_result.pass_fail:
            result.pass_fail = False

    return result


# =============================================================================
# Signal Verification
# =============================================================================
# A signal passes verification if, for every bar in the dataset (after warmup),
# its boolean output matches ground truth computed from the full-dataset
# indicator output. Ground truth is built externally and passed in as a
# boolean array; this module runs the signal bar-by-bar with a sliding window
# and compares.


@dataclass
class SignalAuditResult:
    """Result of verifying a signal's boolean output against ground truth."""
    signal_name: str
    params: dict
    start_bar: int
    evaluated_bars: int
    fires: int
    expected_fires: int
    true_positives: int
    false_positives: int
    false_negatives: int
    pass_fail: bool = True
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "signal": self.signal_name,
            "params": self.params,
            "start_bar": self.start_bar,
            "evaluated_bars": self.evaluated_bars,
            "fires": self.fires,
            "expected_fires": self.expected_fires,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "pass": self.pass_fail,
            "notes": self.notes,
        }


def verify_signal(
    signal_name: str,
    params: dict,
    df: pd.DataFrame,
    truth: np.ndarray,
    start_bar: int = 100,
) -> SignalAuditResult:
    """Verify a registered signal's output matches ground truth bar-by-bar.

    Runs the signal with a sliding window at every bar from `start_bar` to end,
    then compares to the pre-computed ground truth boolean array. Zero false
    positives AND zero false negatives are required to pass.

    Args:
        signal_name: Name of the signal registered in RuleRegistry.
        params: Parameters to pass to the signal.
        df: Full dataset DataFrame (with capitalized OHLCV column names).
        truth: Boolean ndarray same length as df, True where signal should fire.
        start_bar: Skip the warmup region; default 100 bars.
    """
    # Import here to avoid module-level cycles
    from mangrove_kb.registry import RuleRegistry
    import mangrove_kb.signals  # ensure registration

    n = len(df)
    if len(truth) != n:
        raise ValueError(f"truth length {len(truth)} != df length {n}")

    signal_out = np.zeros(n, dtype=bool)
    for i in range(start_bar, n):
        window_df = df.iloc[: i + 1]
        try:
            signal_out[i] = bool(RuleRegistry.evaluate({"name": signal_name, "params": params}, window_df))
        except Exception as e:
            return SignalAuditResult(
                signal_name=signal_name,
                params=params,
                start_bar=start_bar,
                evaluated_bars=i - start_bar,
                fires=int(signal_out.sum()),
                expected_fires=int(truth[start_bar:i].sum()),
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                pass_fail=False,
                notes=f"RAISED at bar {i}: {e}",
            )

    s = signal_out[start_bar:]
    t = truth[start_bar:].astype(bool)
    tp = int((s & t).sum())
    fp = int((s & ~t).sum())
    fn = int((~s & t).sum())

    return SignalAuditResult(
        signal_name=signal_name,
        params=params,
        start_bar=start_bar,
        evaluated_bars=n - start_bar,
        fires=int(s.sum()),
        expected_fires=int(t.sum()),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        pass_fail=(fp == 0 and fn == 0),
    )


def truth_is_above(series: pd.Series, indicator: pd.Series) -> np.ndarray:
    """Ground truth for is_above_<ma> filter: price > indicator, NaN -> False."""
    return (series > indicator).fillna(False).to_numpy()


def truth_crossover(fast: pd.Series, slow: pd.Series, direction: str) -> np.ndarray:
    """Ground truth for fast/slow crossover signals.

    Args:
        direction: "up" = fast crosses above slow; "down" = fast crosses below.
    """
    prev_f, curr_f = fast.shift(1), fast
    prev_s, curr_s = slow.shift(1), slow
    if direction == "up":
        cond = (prev_f <= prev_s) & (curr_f > curr_s)
    elif direction == "down":
        cond = (prev_f >= prev_s) & (curr_f < curr_s)
    else:
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")
    return cond.fillna(False).to_numpy()
