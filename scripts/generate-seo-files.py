#!/usr/bin/env python3
"""Generate robots.txt, sitemap.xml, and llms.txt from docs/mint.json.

Usage:
    cd /path/to/MangroveKnowledgeBase
    python scripts/generate-seo-files.py

The output files land in docs/public/. The Dockerfile.docs build step copies
docs/ into the Mintlify build, and nginx-docs.conf serves /public/* and the
three SEO files at their canonical root paths (/robots.txt, /sitemap.xml,
/llms.txt) plus /.well-known/llms.txt for the well-known convention.

Re-run this script after changing docs/mint.json navigation.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DOCS_DIR = PROJECT_ROOT / "docs"
MINT_JSON = DOCS_DIR / "mint.json"
PUBLIC_DIR = DOCS_DIR / "public"

SITE_URL = "https://docs.mangrovedeveloper.ai"


def collect_pages(mint: dict) -> list[str]:
    """Walk mint.json navigation and return every page path (any depth)."""
    paths: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            # Only recurse into the "pages" key inside a group; other string
            # fields (group name, etc.) are not page references.
            for k, v in node.items():
                if k == "pages":
                    walk(v)
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, str) and not node.startswith("http"):
            paths.append(node)

    for group in mint.get("navigation", []):
        walk(group)

    seen = set()
    unique = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def page_title(path: str) -> str:
    """Read a page's frontmatter title; fall back to the slug."""
    for ext in (".mdx", ".md"):
        f = DOCS_DIR / f"{path}{ext}"
        if f.exists():
            text = f.read_text(encoding="utf-8")
            m = re.search(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
            if m:
                tm = re.search(r'^title:\s*"?(.+?)"?\s*$', m.group(1), re.MULTILINE)
                if tm:
                    return tm.group(1).strip()
            return path.rsplit("/", 1)[-1].replace("-", " ").title()
    return path


def main():
    mint = json.loads(MINT_JSON.read_text(encoding="utf-8"))
    pages = collect_pages(mint)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- robots.txt ----------
    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    (PUBLIC_DIR / "robots.txt").write_text(robots, encoding="utf-8")
    print(f"wrote {PUBLIC_DIR / 'robots.txt'}")

    # ---------- sitemap.xml ----------
    today = datetime.now(timezone.utc).date().isoformat()
    urls = [f"{SITE_URL}/{p}" for p in pages]
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        sitemap_lines.append("  <url>")
        sitemap_lines.append(f"    <loc>{url}</loc>")
        sitemap_lines.append(f"    <lastmod>{today}</lastmod>")
        sitemap_lines.append("  </url>")
    sitemap_lines.append("</urlset>")
    (PUBLIC_DIR / "sitemap.xml").write_text("\n".join(sitemap_lines) + "\n", encoding="utf-8")
    print(f"wrote {PUBLIC_DIR / 'sitemap.xml'} ({len(urls)} URLs)")

    # ---------- llms.txt ----------
    site_name = mint.get("name", "Mangrove Developer Docs")
    description = (
        "Developer documentation for the Mangrove ecosystem -- REST APIs, Python and "
        "TypeScript SDKs, MCP servers, Claude Code plugins, and x402-gated service "
        "templates for building agent-native trading and DEX-aggregation applications."
    )
    llms_lines = [f"# {site_name}", "", f"> {description}", ""]

    grouped: dict[str, list[str]] = {}
    for group in mint.get("navigation", []):
        if not isinstance(group, dict):
            continue
        name = group.get("group", "Other")
        for page in group.get("pages", []):
            if isinstance(page, str):
                grouped.setdefault(name, []).append(page)
            elif isinstance(page, dict):
                sub = page.get("group", name)
                for p in page.get("pages", []):
                    if isinstance(p, str):
                        grouped.setdefault(f"{name}: {sub}", []).append(p)

    for group_name, group_pages in grouped.items():
        llms_lines.append(f"## {group_name}")
        llms_lines.append("")
        for p in group_pages:
            title = page_title(p)
            llms_lines.append(f"- [{title}]({SITE_URL}/{p})")
        llms_lines.append("")

    (PUBLIC_DIR / "llms.txt").write_text("\n".join(llms_lines), encoding="utf-8")
    print(f"wrote {PUBLIC_DIR / 'llms.txt'} ({sum(len(v) for v in grouped.values())} entries)")


if __name__ == "__main__":
    main()
