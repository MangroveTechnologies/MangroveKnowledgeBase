#!/usr/bin/env python3
"""Generate Mintlify-compatible KB docs from the source knowledge-base/ files.

Usage:
    cd /path/to/MangroveKnowledgeBase
    python scripts/generate-kb-docs.py

Copies knowledge-base/*.md files (01-10) into docs/knowledge-base-source/,
ensuring the Mintlify docs always reflect the current source of truth.

The source files in knowledge-base/ already contain YAML frontmatter (title,
description) so no transformation is needed beyond the copy.  This script
exists so that docs/knowledge-base-source/ can be .gitignored and regenerated
at build time, eliminating the maintenance burden of keeping two copies in sync.

Run this before Mintlify builds or deploys.
"""

import os
import re
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

KB_SOURCE_DIR = os.path.join(PROJECT_ROOT, "knowledge-base")
DOCS_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "knowledge-base-source")

# Files to include (skip 00-table-of-contents -- not in Mintlify nav)
INCLUDE_PREFIX = [
    "01-", "02-", "03-", "04-", "05-",
    "06-", "07-", "08-", "09-", "10-",
]


def _sanitize_for_mdx(content):
    """Clean HTML/markdown constructs that break Mintlify's MDX parser."""
    # <details markdown="1"> -> <details>
    content = re.sub(r'<details\s+markdown="1">', '<details>', content)
    # <summary><strong>text</strong> ...  -> clean summary
    # MDX needs self-consistent JSX; strip inline HTML from summary tags
    content = re.sub(
        r'<summary><strong>(.*?)</strong>\s*(?:--|-{1,3})\s*(.*?)</summary>',
        r'<summary>\1 -- \2</summary>',
        content,
    )
    return content


def generate():
    """Copy KB source files to the Mintlify docs output directory."""
    os.makedirs(DOCS_OUTPUT_DIR, exist_ok=True)

    # Clean existing generated files
    for existing in os.listdir(DOCS_OUTPUT_DIR):
        filepath = os.path.join(DOCS_OUTPUT_DIR, existing)
        if os.path.isfile(filepath):
            os.remove(filepath)

    copied = 0
    for filename in sorted(os.listdir(KB_SOURCE_DIR)):
        if not any(filename.startswith(p) for p in INCLUDE_PREFIX):
            continue
        if not filename.endswith(".md"):
            continue

        src = os.path.join(KB_SOURCE_DIR, filename)
        dst = os.path.join(DOCS_OUTPUT_DIR, filename)

        with open(src, "r") as f:
            content = f.read()
        content = _sanitize_for_mdx(content)
        with open(dst, "w") as f:
            f.write(content)

        copied += 1
        print(f"  {filename}")

    print(f"\nCopied {copied} files to {DOCS_OUTPUT_DIR}")
    return copied


if __name__ == "__main__":
    print("Generating Mintlify KB docs from knowledge-base/ source files...\n")
    count = generate()
    if count == 0:
        print("WARNING: No files were copied. Check that knowledge-base/ exists.")
        sys.exit(1)
