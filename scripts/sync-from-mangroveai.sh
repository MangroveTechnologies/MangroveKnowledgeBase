#!/bin/bash
# Sync content from MangroveAI to MangroveKnowledgeBase.
#
# Run this after making updates in MangroveAI to keep MKB in sync.
# Usage: ./scripts/sync-from-mangroveai.sh
#
# What it syncs:
#   1. MangroveAdmin docs (public/docs/) -> developer-portal/frontend/public/docs/
#   2. Regenerates the signal catalog from docstrings
#   3. Copies knowledge-base content if changed
#
# What it does NOT sync (intentionally):
#   - React source code (developer-portal stays as MangroveAI's copy)
#   - Python signal/indicator source (mangrove_kb is the source of truth)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MKB_ROOT="$(dirname "$SCRIPT_DIR")"
MANGROVE_AI="${MKB_ROOT}/../MangroveAI"

if [ ! -d "$MANGROVE_AI" ]; then
    echo "ERROR: MangroveAI not found at $MANGROVE_AI"
    exit 1
fi

echo "Syncing from MangroveAI to MangroveKnowledgeBase..."
echo ""

# 1. Sync MangroveAdmin docs
echo "[1/3] Syncing MangroveAdmin docs..."
ADMIN_DOCS="$MANGROVE_AI/src/MangroveAdmin/frontend/public/docs"
PORTAL_DOCS="$MKB_ROOT/developer-portal/frontend/public/docs"
if [ -d "$ADMIN_DOCS" ] && [ -d "$PORTAL_DOCS" ]; then
    cp -r "$ADMIN_DOCS"/* "$PORTAL_DOCS/"
    echo "  Copied $(find "$ADMIN_DOCS" -type f | wc -l) files"
else
    echo "  SKIPPED: source or target docs directory not found"
fi

# 2. Regenerate signal catalog
echo "[2/3] Regenerating signal catalog..."
if [ -f "$MKB_ROOT/venv/bin/python" ]; then
    "$MKB_ROOT/venv/bin/python" "$MKB_ROOT/scripts/generate-signal-catalog.py"
elif command -v python3 &>/dev/null; then
    python3 "$MKB_ROOT/scripts/generate-signal-catalog.py"
else
    echo "  SKIPPED: no Python found (need venv or system python3)"
fi

# 3. Sync knowledge-base content
echo "[3/3] Syncing knowledge-base content..."
KB_SRC="$MANGROVE_AI/src/MangroveKnowledgeBase/knowledge-base"
KB_DST="$MKB_ROOT/knowledge-base"
if [ -d "$KB_SRC" ] && [ -d "$KB_DST" ]; then
    cp "$KB_SRC"/*.md "$KB_DST/"
    echo "  Copied $(ls "$KB_SRC"/*.md | wc -l) markdown files"
else
    echo "  SKIPPED: source or target KB directory not found"
fi

echo ""
echo "Sync complete. Review changes with: git diff --stat"
