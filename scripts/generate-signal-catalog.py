#!/usr/bin/env python3
"""Generate a Mintlify-compatible signal catalog page from docstring metadata.

Usage:
    cd /path/to/MangroveKnowledgeBase
    python scripts/generate-signal-catalog.py

Reads all signal functions registered in the RuleRegistry, parses their
docstrings via the docstring parser, and writes docs/signals/catalog.mdx.
"""

import os
import sys
import json
from collections import OrderedDict

# ---------------------------------------------------------------------------
# Resolve project root so we can import the local package
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Import the package -- this triggers signal registration
# ---------------------------------------------------------------------------
import mangrove_kb  # noqa: E402
from mangrove_kb.registry import RuleRegistry  # noqa: E402
from mangrove_kb.docstring_parser import parse_all_signals  # noqa: E402
from mangrove_kb.signals import momentum, trend, volume, volatility, patterns  # noqa: E402

# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------
# The source module determines category.  We map module name -> display name.
MODULE_CATEGORY = {
    "momentum": "Momentum",
    "trend": "Trend",
    "volume": "Volume",
    "volatility": "Volatility",
    "patterns": "Patterns",
}


def _classify_signal(func) -> str:
    """Return the display category for a signal function based on its module."""
    mod = getattr(func, "__module__", "")
    for key, label in MODULE_CATEGORY.items():
        if key in mod:
            return label
    return "Other"


# ---------------------------------------------------------------------------
# MDX generation helpers
# ---------------------------------------------------------------------------

def _badge(signal_type: str) -> str:
    """Return a Mintlify-style badge string for the signal type."""
    if signal_type == "TRIGGER":
        return '<span style={{color: "#e67e22", fontWeight: "bold"}}>TRIGGER</span>'
    else:
        return '<span style={{color: "#3498db", fontWeight: "bold"}}>FILTER</span>'


def _anchor_id(name: str) -> str:
    """Create an HTML-friendly anchor ID from a signal name."""
    return name.replace("_", "-")


def _format_default(value) -> str:
    """Format a default value for display."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        # Show clean float: 0.0 not 0.0, 70.0 not 70.0
        if value == int(value):
            return f"{value:.1f}"
        return str(value)
    return str(value)


def _format_range(param_meta: dict) -> str:
    """Format the min-max range for display."""
    if "min" not in param_meta and "max" not in param_meta:
        return "-"
    min_v = param_meta.get("min", "")
    max_v = param_meta.get("max", "")
    return f"{min_v} -- {max_v}"


def _format_param_default(param_meta: dict) -> str:
    """Format the default value for display."""
    if "default" in param_meta:
        return f"`{_format_default(param_meta['default'])}`"
    if param_meta.get("optional"):
        return "`None`"
    return "_required_"


def _build_example_python(signal_name: str, params: dict) -> str:
    """Build a Python example snippet."""
    # Build a params dict string
    param_entries = []
    for pname, pmeta in params.items():
        if "default" in pmeta:
            param_entries.append(f'        "{pname}": {json.dumps(pmeta["default"])}')
        elif pmeta.get("min") is not None:
            # Use a sensible value from the middle of the range
            param_entries.append(f'        "{pname}": {json.dumps(pmeta.get("min"))}')

    params_str = ",\n".join(param_entries)
    if params_str:
        params_block = f"""    "parameters": {{\n{params_str}\n    }}"""
    else:
        params_block = '    "parameters": {}'

    return f"""from mangrove_kb import RuleRegistry

rule = {{
    "name": "{signal_name}",
{params_block}
}}
result = RuleRegistry.evaluate(rule, df)
print(result)  # True or False"""


def _build_example_curl(signal_name: str, params: dict) -> str:
    """Build a cURL example snippet."""
    param_obj = {}
    for pname, pmeta in params.items():
        if "default" in pmeta:
            param_obj[pname] = pmeta["default"]
        elif pmeta.get("min") is not None:
            param_obj[pname] = pmeta.get("min")

    body = {
        "name": signal_name,
        "parameters": param_obj,
    }
    body_str = json.dumps(body, indent=2)

    return f"""curl -X POST https://api.mangrovedeveloper.ai/api/v1/execution/evaluate \\
  -H "Authorization: Bearer $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{body_str}'"""


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

def generate_catalog():
    """Generate the docs/signals/catalog.mdx file."""

    # Parse all signals
    signal_modules = [momentum, trend, volume, volatility, patterns]
    all_signals = parse_all_signals(signal_modules)

    # Attach category info
    registry = RuleRegistry._registry
    enriched = []
    for name, meta in sorted(all_signals.items()):
        func = registry.get(name)
        category = _classify_signal(func) if func else "Other"
        enriched.append({
            "name": name,
            "category": category,
            **meta,
        })

    # Sort by category then name
    category_order = ["Momentum", "Trend", "Volume", "Volatility", "Patterns", "Other"]
    enriched.sort(key=lambda s: (category_order.index(s["category"]) if s["category"] in category_order else 99, s["name"]))

    # Group by category
    grouped = OrderedDict()
    for sig in enriched:
        cat = sig["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(sig)

    # Count totals
    total = len(enriched)
    trigger_count = sum(1 for s in enriched if s.get("type") == "TRIGGER")
    filter_count = sum(1 for s in enriched if s.get("type") == "FILTER")

    # ---------------------------------------------------------------------------
    # Helpers to build per-signal MDX
    #
    # Each signal is wrapped in a Mintlify <Accordion> so the catalog page
    # renders fast (~tens of KB instead of MBs) and users expand only the
    # signals they care about. Mintlify wraps these inside an <AccordionGroup>
    # at the per-category level.
    # ---------------------------------------------------------------------------
    def _signal_mdx(sig):
        out = []
        signal_name = sig["name"]
        signal_type = sig.get("type", "")
        requires = sig.get("requires", [])
        description = sig.get("description", "")
        params = sig.get("params", {})

        requires_str = ", ".join(requires) if requires else "None"
        # Build a short description label for the accordion header
        # (visible while collapsed). Keep it terse.
        header_desc = f"{signal_type} - requires {requires_str}"

        out.append(f'<Accordion title="{signal_name}" description="{header_desc}">')
        out.append("")
        if description:
            safe_desc = description.replace("<", "&lt;").replace(">", "&gt;")
            out.append(safe_desc)
            out.append("")
        if params:
            out.append("**Parameters**")
            out.append("")
            out.append("| Name | Type | Range | Default | Description |")
            out.append("|------|------|-------|---------|-------------|")
            for pname, pmeta in params.items():
                ptype = pmeta.get("type", "")
                prange = _format_range(pmeta)
                pdefault = _format_param_default(pmeta)
                pdesc = pmeta.get("description", "")
                out.append(f"| `{pname}` | `{ptype}` | {prange} | {pdefault} | {pdesc} |")
            out.append("")
        else:
            out.append("_No configurable parameters._")
            out.append("")
        out.append("**Example**")
        out.append("")
        out.append("<CodeGroup>")
        out.append("")
        out.append('```python Python')
        out.append(_build_example_python(signal_name, params))
        out.append("```")
        out.append("")
        out.append('```bash cURL')
        out.append(_build_example_curl(signal_name, params))
        out.append("```")
        out.append("")
        out.append("</CodeGroup>")
        out.append("")
        out.append("</Accordion>")
        out.append("")
        return out

    # ---------------------------------------------------------------------------
    # Index page (catalog.mdx) — summary table only, links to category pages
    # ---------------------------------------------------------------------------
    index_lines = []
    index_lines.append("---")
    index_lines.append('title: "Signal Catalog"')
    index_lines.append(f'description: "Index of all {total} trading signals across 5 categories."')
    index_lines.append("---")
    index_lines.append("")
    index_lines.append("# Signal Catalog")
    index_lines.append("")
    index_lines.append(f"Complete reference for all **{total}** trading signals ")
    index_lines.append(f"({trigger_count} TRIGGER, {filter_count} FILTER) organized by category.")
    index_lines.append("")
    index_lines.append("See [Signals Overview](/signals/overview) for an introduction to how signals work.")
    index_lines.append("")
    index_lines.append("## Browse by category")
    index_lines.append("")
    index_lines.append("| Category | Count | Page |")
    index_lines.append("|---|---|---|")
    for cat, sigs in grouped.items():
        slug = cat.lower()
        index_lines.append(f"| {cat} | {len(sigs)} | [/signals/catalog/{slug}](/signals/catalog/{slug}) |")
    index_lines.append("")
    index_lines.append("## All signals")
    index_lines.append("")
    index_lines.append("| Name | Type | Category | Requires |")
    index_lines.append("|------|------|----------|----------|")
    for sig in enriched:
        requires_str = ", ".join(sig.get("requires", [])) if sig.get("requires") else "None"
        sig_type = sig.get("type", "")
        slug = sig["category"].lower()
        index_lines.append(
            f"| [`{sig['name']}`](/signals/catalog/{slug}) "
            f"| {sig_type} | {sig['category']} | {requires_str} |"
        )
    index_lines.append("")
    index_lines.append("---")
    index_lines.append("")
    index_lines.append(f"_Generated from docstring metadata. {total} signals total ({trigger_count} TRIGGER, {filter_count} FILTER)._")
    index_lines.append("")

    output_index = os.path.join(PROJECT_ROOT, "docs", "signals", "catalog.mdx")
    os.makedirs(os.path.dirname(output_index), exist_ok=True)
    with open(output_index, "w") as f:
        f.write("\n".join(index_lines))
    print(f"Generated {output_index}")

    # ---------------------------------------------------------------------------
    # Per-category pages (catalog/<slug>.mdx)
    # ---------------------------------------------------------------------------
    category_dir = os.path.join(PROJECT_ROOT, "docs", "signals", "catalog")
    os.makedirs(category_dir, exist_ok=True)

    for cat, sigs in grouped.items():
        slug = cat.lower()
        cat_lines = []
        cat_lines.append("---")
        cat_lines.append(f'title: "{cat} Signals"')
        cat_lines.append(f'description: "{len(sigs)} {cat.lower()} trading signals with parameters, descriptions, and examples."')
        cat_lines.append("---")
        cat_lines.append("")
        cat_lines.append(f"# {cat} Signals")
        cat_lines.append("")
        cat_lines.append(f"_{len(sigs)} signals in this category._")
        cat_lines.append("")
        cat_lines.append(f"See the full [Signal Catalog](/signals/catalog) for the cross-category index, or the [Signals Overview](/signals/overview) for an introduction.")
        cat_lines.append("")
        cat_lines.append("Click a signal to expand parameters and examples.")
        cat_lines.append("")
        cat_lines.append("<AccordionGroup>")
        cat_lines.append("")
        for sig in sigs:
            cat_lines.extend(_signal_mdx(sig))
        cat_lines.append("</AccordionGroup>")
        cat_lines.append("")

        cat_path = os.path.join(category_dir, f"{slug}.mdx")
        with open(cat_path, "w") as f:
            f.write("\n".join(cat_lines))
        print(f"Generated {cat_path} ({len(sigs)} signals)")

    print(f"  Total signals: {total}")
    print(f"  TRIGGER: {trigger_count}")
    print(f"  FILTER: {filter_count}")
    print(f"  Categories: {', '.join(f'{cat} ({len(sigs)})' for cat, sigs in grouped.items())}")

    return total


if __name__ == "__main__":
    total = generate_catalog()
    if total == 0:
        print("WARNING: No signals were found. Check that the package is installed correctly.")
        sys.exit(1)
