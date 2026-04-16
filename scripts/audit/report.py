"""Report generation for audit results."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .compare import AuditResult


def generate_markdown_report(
    results: list[AuditResult],
    title: str = "Indicator Audit Report",
    data_description: str = "BTC/USD Daily, 1294 bars (2022-08-01 to 2026-02-14)",
    output_path: Optional[Path] = None,
) -> str:
    """Generate a markdown audit report from results."""
    lines = []
    lines.append(f"# {title}")
    lines.append(f"")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Data**: {data_description}")
    lines.append(f"")

    # Summary table
    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"total": 0, "pass": 0, "fail": 0, "max_err": 0.0}
        categories[cat]["total"] += 1
        if r.pass_fail:
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1
        for out in r.outputs.values():
            categories[cat]["max_err"] = max(categories[cat]["max_err"], out.max_abs_error)

    total_pass = sum(c["pass"] for c in categories.values())
    total_fail = sum(c["fail"] for c in categories.values())
    total = total_pass + total_fail

    lines.append(f"## Summary: {total_pass}/{total} PASS, {total_fail} FAIL")
    lines.append(f"")
    lines.append(f"| Category | Indicators | Pass | Fail | Max Error |")
    lines.append(f"|----------|-----------|------|------|-----------|")
    for cat, stats in sorted(categories.items()):
        lines.append(
            f"| {cat} | {stats['total']} | {stats['pass']} | {stats['fail']} | {stats['max_err']:.2e} |"
        )
    lines.append(f"")

    # Failures first
    failures = [r for r in results if not r.pass_fail]
    if failures:
        lines.append(f"## Failures ({len(failures)})")
        lines.append(f"")
        for r in failures:
            lines.append(f"### {r.indicator_name} ({r.category}) -- FAIL")
            lines.append(f"- Reference: {r.reference_library}")
            lines.append(f"- Tolerance: {r.tolerance_tier} ({r.tolerance_value})")
            if r.notes:
                lines.append(f"- Notes: {r.notes}")
            for key, out in r.outputs.items():
                status = "PASS" if out.pass_fail else "FAIL"
                lines.append(
                    f"- `{key}`: max_err={out.max_abs_error:.2e}, "
                    f"mean_err={out.mean_abs_error:.2e}, "
                    f"nan_mismatch={out.nan_mismatches}, "
                    f"overlap={out.overlap_bars} bars -- **{status}**"
                )
                if out.first_divergence_bar is not None:
                    lines.append(f"  - First divergence at bar {out.first_divergence_bar}")
            lines.append(f"")

    # Detailed results by category
    lines.append(f"## Detailed Results")
    lines.append(f"")
    for cat in sorted(categories.keys()):
        cat_results = [r for r in results if r.category == cat]
        lines.append(f"### {cat}")
        lines.append(f"")
        for r in sorted(cat_results, key=lambda x: x.indicator_name):
            status = "PASS" if r.pass_fail else "FAIL"
            lines.append(f"**{r.indicator_name}** -- {status}")
            lines.append(f"- Reference: {r.reference_library}, Tolerance: {r.tolerance_tier}")
            for key, out in r.outputs.items():
                lines.append(
                    f"- `{key}`: max_err={out.max_abs_error:.2e}, overlap={out.overlap_bars}"
                )
            if r.notes:
                lines.append(f"- Notes: {r.notes}")
            lines.append(f"")

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)

    return report


def generate_json_report(
    results: list[AuditResult],
    output_path: Optional[Path] = None,
) -> dict:
    """Generate a JSON audit report from results."""
    report = {
        "date": datetime.now().isoformat(),
        "total": len(results),
        "pass": sum(1 for r in results if r.pass_fail),
        "fail": sum(1 for r in results if not r.pass_fail),
        "results": [r.to_dict() for r in results],
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, default=str))

    return report
