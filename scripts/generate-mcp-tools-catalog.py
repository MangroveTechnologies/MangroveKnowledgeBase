#!/usr/bin/env python3
"""Generate the MCP tools catalog page from the agent's tools.py source.

Usage:
    cd /path/to/MangroveKnowledgeBase
    python scripts/generate-mcp-tools-catalog.py

Reads `mangrove-agent/server/src/mcp/tools.py` via `ast.parse` (no imports of
the agent's code — robust to its runtime dependencies), walks every
`_register_<domain>(server)` function for `register_tool(ToolEntry(...))`
calls, and writes `docs/mangrove-agent/mcp-tools.mdx` as a static prologue
plus 1 `<AccordionGroup>` per domain with 1 `<Accordion>` per tool.

Why generated, not hand-written:
    The agent registers ~90 tools; hand-syncing args tables drifts on the
    first new parameter. The signal catalog already follows this generator
    pattern (see `generate-signal-catalog.py`). When `tools.py` changes,
    re-run this script and commit the regenerated MDX.

Cross-repo path:
    Expects sibling layout:
        ~/mangrove/MangroveKnowledgeBase/scripts/  <- this script
        ~/mangrove/mangrove-agent/server/src/mcp/tools.py  <- input
    Override with --agent-tools <path>.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Domain display names — _register_<key> -> human-readable
# Keys not in this map fall back to title-case of the suffix.
# ---------------------------------------------------------------------------
DOMAIN_DISPLAY_NAMES: dict[str, str] = {
    "discovery": "Discovery",
    "wallet": "Wallet",
    "dex": "DEX",
    "market": "Market data",
    "signals": "Signals",
    "on_chain": "On-chain (Nansen + WhaleAlert)",
    "defi": "DeFi",
    "social": "Social",
    "strategy": "Strategy",
    "logs": "Logs",
    "kb": "Knowledge base",
    "oracle": "Oracle",
    "docs": "Documentation",
    "hello_mangrove": "x402 demo (hello_mangrove)",
}

# Order domains in the rendered MDX — anything not listed here goes to the end.
DOMAIN_ORDER = [
    "discovery",
    "wallet",
    "dex",
    "market",
    "on_chain",
    "oracle",
    "signals",
    "strategy",
    "logs",
    "kb",
    "defi",
    "social",
    "docs",
    "hello_mangrove",
]


@dataclass
class ToolParam:
    name: str
    type: str
    required: bool
    description: str = ""


@dataclass
class ToolEntry:
    name: str
    description: str
    access: str  # "free" | "auth" | "x402"
    parameters: list[ToolParam] = field(default_factory=list)
    price: str | None = None
    network: str | None = None
    domain: str = ""


def _literal(node: ast.AST) -> Any:
    """Return the Python literal for a constant / list / tuple AST node.

    We only need to support what shows up in ToolEntry / ToolParam call
    sites: strings, bools, integers, None. Anything else returns the
    raw node so the caller can detect and skip it.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal(elt) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_literal(elt) for elt in node.elts)
    # JoinedStr (f-string) — render the constant chunks; descriptions sometimes
    # use f-string concatenation but never with dynamic values.
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                out.append(str(v.value))
            else:
                out.append("…")
        return "".join(out)
    # Parenthesised concatenation: ast.BinOp(Add) on two strings, etc.
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return f"{_literal(node.left)}{_literal(node.right)}"
    # Name reference (e.g. `_APIKEY`) — we don't resolve cross-tool aliases here.
    if isinstance(node, ast.Name):
        return node  # caller filters
    return node


def _build_tool_param(call: ast.Call) -> ToolParam | None:
    """Parse a ToolParam(...) call into a ToolParam dataclass."""
    kw = {k.arg: _literal(k.value) for k in call.keywords if k.arg is not None}
    name = kw.get("name")
    if not isinstance(name, str):
        return None
    return ToolParam(
        name=name,
        type=str(kw.get("type", "")),
        required=bool(kw.get("required", False)) if isinstance(kw.get("required"), bool) else False,
        description=str(kw.get("description", "")),
    )


def _resolve_apikey_param(module_tree: ast.Module) -> ToolParam | None:
    """Find `_APIKEY = ToolParam(...)` at module scope and parse it.

    `tools.py` defines `_APIKEY` once near the top and re-uses it across every
    auth-gated tool's parameter list. We resolve it so the rendered Args
    tables actually show the `api_key` row instead of an opaque reference.
    """
    for node in module_tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != "_APIKEY":
            continue
        if isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "ToolParam":
            return _build_tool_param(node.value)
    return None


def _build_tool_entry(call: ast.Call, *, apikey: ToolParam | None) -> ToolEntry | None:
    """Parse a ToolEntry(...) call into a ToolEntry dataclass.

    Resolves the `_APIKEY` reference in `parameters` to its actual ToolParam
    so the args table renders correctly.
    """
    kw = {k.arg: k.value for k in call.keywords if k.arg is not None}
    name_node = kw.get("name")
    if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
        return None
    name = name_node.value

    description = _literal(kw.get("description", ast.Constant("")))
    access = _literal(kw.get("access", ast.Constant("auth")))
    price_node = kw.get("price")
    price = _literal(price_node) if price_node is not None else None
    network_node = kw.get("network")
    network = _literal(network_node) if network_node is not None else None

    params: list[ToolParam] = []
    params_node = kw.get("parameters")
    if isinstance(params_node, ast.List):
        for elt in params_node.elts:
            if isinstance(elt, ast.Call) and getattr(elt.func, "id", "") == "ToolParam":
                p = _build_tool_param(elt)
                if p is not None:
                    params.append(p)
            elif isinstance(elt, ast.Name) and elt.id == "_APIKEY" and apikey is not None:
                params.append(apikey)

    # Defensive: description/access may not be strings if exotic; coerce.
    return ToolEntry(
        name=name,
        description=description if isinstance(description, str) else str(description),
        access=access if isinstance(access, str) else str(access),
        parameters=params,
        price=price if isinstance(price, str) else None,
        network=network if isinstance(network, str) else None,
    )


def _walk_register_calls(func_node: ast.FunctionDef, *, apikey: ToolParam | None) -> list[ToolEntry]:
    """Find all `register_tool(ToolEntry(...))` calls inside a function body."""
    tools: list[ToolEntry] = []
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if not (isinstance(callee, ast.Name) and callee.id == "register_tool"):
            continue
        if not node.args or not isinstance(node.args[0], ast.Call):
            continue
        inner = node.args[0]
        if getattr(inner.func, "id", "") != "ToolEntry":
            continue
        t = _build_tool_entry(inner, apikey=apikey)
        if t is not None:
            tools.append(t)
    return tools


def parse_tools_file(path: str) -> list[ToolEntry]:
    """Parse the agent's tools.py and return every registered tool.

    Each tool's `.domain` is set to the suffix of its enclosing
    `_register_<domain>(server)` function — that's how we group in the MDX.
    """
    with open(path) as f:
        source = f.read()
    tree = ast.parse(source, filename=path)
    apikey = _resolve_apikey_param(tree)

    tools: list[ToolEntry] = []
    seen_functions: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("_register_"):
            continue
        domain = node.name[len("_register_"):]
        seen_functions.add(domain)
        for t in _walk_register_calls(node, apikey=apikey):
            t.domain = domain
            tools.append(t)

    assert tools, f"No tools parsed from {path} — file structure may have changed"
    return tools


def _display_name(domain: str) -> str:
    if domain in DOMAIN_DISPLAY_NAMES:
        return DOMAIN_DISPLAY_NAMES[domain]
    return domain.replace("_", " ").title()


def _domain_sort_key(domain: str) -> tuple[int, str]:
    try:
        return (DOMAIN_ORDER.index(domain), domain)
    except ValueError:
        return (len(DOMAIN_ORDER), domain)


def _escape_attr(text: str) -> str:
    """Escape a string for use inside an MDX attribute value (`"..."`)."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _md_escape(text: str) -> str:
    """Escape pipes for use inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _render_tool_accordion(t: ToolEntry) -> list[str]:
    out: list[str] = []
    # Short header description: <access tier> — <truncated tool description>
    header_desc = t.description.split("\n", 1)[0]
    if len(header_desc) > 100:
        header_desc = header_desc[:97].rstrip() + "…"
    header_desc = f"{t.access} — {header_desc}" if t.access else header_desc

    out.append(f'<Accordion title="{t.name}" description="{_escape_attr(header_desc)}">')
    out.append("")
    if t.description:
        out.append(t.description.strip())
        out.append("")

    # Args table
    if t.parameters:
        out.append("**Args**")
        out.append("")
        out.append("| Name | Type | Required | Description |")
        out.append("|---|---|---|---|")
        for p in t.parameters:
            req = "**yes**" if p.required else "no"
            out.append(
                f"| `{p.name}` | `{_md_escape(p.type)}` | {req} "
                f"| {_md_escape(p.description)} |"
            )
        out.append("")
    else:
        out.append("_No arguments._")
        out.append("")

    # Pricing footer (only when set)
    meta_bits = []
    if t.access:
        meta_bits.append(f"**Access:** {t.access}")
    if t.price:
        meta_bits.append(f"**Price:** {t.price}")
    if t.network:
        meta_bits.append(f"**Network:** {t.network}")
    if meta_bits:
        out.append(" · ".join(meta_bits))
        out.append("")

    # REST mirror hint — derivable from the tool's name + the catalog's
    # convention `/api/v1/agent/<resource>/...`.
    out.append(f"REST mirror: `/api/v1/agent/...` (see [REST mirror](#rest-mirror) for the pattern).")
    out.append("")
    out.append("</Accordion>")
    out.append("")
    return out


def render_mdx(tools: list[ToolEntry]) -> str:
    grouped: OrderedDict[str, list[ToolEntry]] = OrderedDict()
    for domain in sorted({t.domain for t in tools}, key=_domain_sort_key):
        grouped[domain] = [t for t in tools if t.domain == domain]

    total_tools = len(tools)
    total_domains = len(grouped)

    lines: list[str] = []
    lines.append("---")
    lines.append('title: "MCP tools catalog"')
    lines.append(
        f'description: "All {total_tools} MCP tools the agent exposes, '
        f'grouped into {total_domains} domains. Each tool documents its '
        f'arguments and access tier. REST mirrors at /api/v1/agent/*."'
    )
    lines.append("---")
    lines.append("")
    lines.append("# MCP tools catalog")
    lines.append("")
    lines.append(
        f"The agent registers **{total_tools} MCP tools** across "
        f"**{total_domains} domains**. Every tool is exposed over Streamable "
        "HTTP MCP **and** as a mirrored REST endpoint at `/api/v1/agent/*` — "
        "pick whichever fits your caller. Both paths call the same service "
        "layer."
    )
    lines.append("")
    lines.append(
        "Each domain section below renders as a collapsed accordion list. "
        "Click a tool to expand its description, argument table, and access "
        "tier. Use your browser's find-in-page (ctrl-F / cmd-F) to locate a "
        "tool by name — collapsed accordions are still text-searchable."
    )
    lines.append("")
    lines.append("## How to read this catalog")
    lines.append("")
    lines.append("- **Access** is one of:")
    lines.append("    - `free` — no auth, no charge (discovery, status, demo)")
    lines.append("    - `auth` — requires `X-API-Key` (or Bearer JWT)")
    lines.append("    - `x402` — pay-per-call via x402 micropayment; check the tool's price field")
    lines.append("- **Args** with `required = yes` must be supplied; the rest fall back to server defaults.")
    lines.append("- **Type** strings (`string`, `integer`, `array<Strategy>`, …) reflect the agent's MCP schema, not Python types.")
    lines.append("")
    lines.append('<Note>')
    lines.append(
        "This page is **generated** from "
        "[`mangrove-agent/server/src/mcp/tools.py`](https://github.com/MangroveTechnologies/mangrove-agent/blob/main/server/src/mcp/tools.py) "
        "via `scripts/generate-mcp-tools-catalog.py`. When the agent adds or "
        "renames a tool, re-run the generator and commit the regenerated MDX."
    )
    lines.append("</Note>")
    lines.append("")

    # Per-domain sections
    for domain, ds_tools in grouped.items():
        display = _display_name(domain)
        lines.append(f"## {display}")
        lines.append("")
        lines.append(f"_{len(ds_tools)} tool(s) in this domain._")
        lines.append("")
        lines.append("<AccordionGroup>")
        lines.append("")
        for t in sorted(ds_tools, key=lambda x: x.name):
            lines.extend(_render_tool_accordion(t))
        lines.append("</AccordionGroup>")
        lines.append("")

    # REST mirror section
    lines.append("## REST mirror")
    lines.append("")
    lines.append(
        "Every MCP tool above has a mirrored REST endpoint at "
        "`/api/v1/agent/<resource>/...`. HTTP method matches the underlying "
        "call — typically `POST` for actions, `GET` for reads. Same service "
        "layer, same auth, same response shape. Use REST when the caller "
        "isn't an MCP client."
    )
    lines.append("")
    lines.append("Examples:")
    lines.append("")
    lines.append("- `POST /api/v1/agent/oracle/experiments` mirrors the `oracle_create_experiment` MCP tool.")
    lines.append("- `POST /api/v1/agent/on-chain/smart-money/historical-holdings` mirrors `get_smart_money_historical_holdings`.")
    lines.append("- `GET /api/v1/agent/oracle/datasets` mirrors `oracle_list_datasets`.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"_Generated from `mangrove-agent/server/src/mcp/tools.py`. "
        f"{total_tools} tools across {total_domains} domains. "
        "Re-run `python scripts/generate-mcp-tools-catalog.py` to refresh._"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--agent-tools",
        default=None,
        help="Path to mangrove-agent/server/src/mcp/tools.py "
        "(default: sibling checkout at ~/mangrove/mangrove-agent/server/src/mcp/tools.py)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output MDX path (default: docs/mangrove-agent/mcp-tools.mdx)",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    agent_tools = args.agent_tools or os.path.expanduser(
        "~/mangrove/mangrove-agent/server/src/mcp/tools.py"
    )
    if not os.path.exists(agent_tools):
        print(f"ERROR: agent tools file not found at {agent_tools}", file=sys.stderr)
        print("Pass --agent-tools <path> if mangrove-agent lives elsewhere.", file=sys.stderr)
        return 2

    output = args.output or os.path.join(project_root, "docs", "mangrove-agent", "mcp-tools.mdx")

    tools = parse_tools_file(agent_tools)
    mdx = render_mdx(tools)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        f.write(mdx)

    domain_counts = {}
    for t in tools:
        domain_counts[t.domain] = domain_counts.get(t.domain, 0) + 1
    print(f"Generated {output}")
    print(f"  Total tools: {len(tools)}")
    print(f"  Domains: {len(domain_counts)}")
    for d, c in sorted(domain_counts.items(), key=lambda kv: _domain_sort_key(kv[0])):
        print(f"    {_display_name(d):<35} {c} tool(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
