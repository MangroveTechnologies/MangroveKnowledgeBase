#!/usr/bin/env python3
"""Generate docs/mint.json from docs/mint.template.json with environment-specific URLs.

Usage:
    # Local dev (defaults)
    python scripts/generate-mint-config.py

    # Production
    PORTAL_URL=https://mangrovedeveloper.ai python scripts/generate-mint-config.py

    # Dev
    PORTAL_URL=https://dev.mangrovedeveloper.ai python scripts/generate-mint-config.py

Environment variables:
    PORTAL_URL  -- MangroveAdmin base URL (default: http://localhost:3589)

Run this before 'mintlify dev' or Mintlify deployment.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "docs", "mint.template.json")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", "mint.json")

DEFAULTS = {
    "PORTAL_URL": "http://localhost:3589",
}


def generate():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"ERROR: Template not found: {TEMPLATE_PATH}")
        sys.exit(1)

    with open(TEMPLATE_PATH, "r") as f:
        content = f.read()

    for var, default in DEFAULTS.items():
        value = os.environ.get(var, default)
        content = content.replace(f"${{{var}}}", value)
        print(f"  {var} = {value}")

    with open(OUTPUT_PATH, "w") as f:
        f.write(content)

    print(f"\nGenerated {OUTPUT_PATH}")


if __name__ == "__main__":
    print("Generating mint.json from template...\n")
    generate()
