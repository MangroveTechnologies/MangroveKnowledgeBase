"""Core comparison engine for indicator audit."""

from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from typing import Callable, Optional


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
) -> OutputResult:
    """Compare two pandas Series element-wise.

    Args:
        ours: Our implementation's output series
        ref: Reference implementation's output series
        tolerance: Maximum acceptable absolute error
        skip_warmup: Skip first N bars (different warmup handling)
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

    # First divergence bar
    divergent = abs_diff > tolerance
    if divergent.any():
        result.first_divergence_bar = int(np.argmax(divergent)) + skip_warmup

    result.pass_fail = result.max_abs_error <= tolerance
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
        )
        output_result.output_key = our_key
        result.outputs[our_key] = output_result

        if not output_result.pass_fail:
            result.pass_fail = False

    return result
