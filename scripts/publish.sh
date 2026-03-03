#!/usr/bin/env bash
# Publish mangrove-kb to PyPI.
#
# Usage:
#   ./scripts/publish.sh patch    # 0.1.0 -> 0.1.1
#   ./scripts/publish.sh minor    # 0.1.0 -> 0.2.0
#   ./scripts/publish.sh major    # 0.1.0 -> 1.0.0
#   ./scripts/publish.sh          # defaults to patch
#
# Prerequisites:
#   pip install build twine
#   PyPI API token in ~/.pypirc or TWINE_PASSWORD env var
#
# What it does:
#   1. Runs tests
#   2. Bumps version in pyproject.toml
#   3. Builds sdist + wheel
#   4. Uploads to PyPI
#   5. Commits the version bump and tags it

set -euo pipefail
cd "$(dirname "$0")/.."

BUMP="${1:-patch}"
PYPROJECT="pyproject.toml"

# --- Validate ---
if [[ ! -f "$PYPROJECT" ]]; then
    echo "ERROR: $PYPROJECT not found. Run from repo root."
    exit 1
fi

for cmd in python twine; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found. Install with: pip install build twine"
        exit 1
    fi
done

# --- Get current version ---
CURRENT=$(grep '^version' "$PYPROJECT" | sed 's/version = "\(.*\)"/\1/')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
    *) echo "ERROR: Invalid bump type '$BUMP'. Use: major, minor, patch"; exit 1 ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
echo "Version: $CURRENT -> $NEW_VERSION ($BUMP)"
echo ""

# --- Run tests ---
echo "Running tests..."
python -m pytest tests/ -x -q --tb=short
echo ""

# --- Bump version ---
sed -i "s/^version = \"$CURRENT\"/version = \"$NEW_VERSION\"/" "$PYPROJECT"
echo "Updated $PYPROJECT to $NEW_VERSION"

# --- Clean and build ---
rm -rf dist/ build/ *.egg-info mangrove_kb.egg-info
echo "Building..."
python -m build --sdist --wheel
echo ""

# --- Upload ---
echo "Uploading to PyPI..."
twine upload dist/*
echo ""

# --- Git tag ---
git add "$PYPROJECT"
git commit -m "release: v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"

echo ""
echo "Published mangrove-kb $NEW_VERSION to PyPI"
echo "Run 'git push origin main --tags' to push the tag"
