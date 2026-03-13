#!/usr/bin/env bash
# Publish mangrove-kb to PyPI (local fallback).
#
# PREFERRED: Use the GitHub Actions "Release to PyPI" workflow instead.
#   Go to Actions > Release to PyPI > Run workflow > pick bump type.
#
# This script is for local publishing when CI is unavailable.
#
# Usage:
#   ./scripts/publish.sh patch    # 1.0.0 -> 1.0.1
#   ./scripts/publish.sh minor    # 1.0.0 -> 1.1.0
#   ./scripts/publish.sh major    # 1.0.0 -> 2.0.0
#   ./scripts/publish.sh          # defaults to patch
#
# Prerequisites:
#   pip install build twine setuptools-scm
#   PyPI API token in ~/.pypirc or TWINE_PASSWORD env var
#
# How it works:
#   1. Runs tests
#   2. Computes next version from latest git tag
#   3. Creates git tag (setuptools-scm reads this at build time)
#   4. Builds sdist + wheel
#   5. Uploads to PyPI
#   6. Pushes the tag

set -euo pipefail
cd "$(dirname "$0")/.."

BUMP="${1:-patch}"

# --- Validate ---
for cmd in python twine git; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found."
        exit 1
    fi
done

if [[ "$BUMP" != "patch" && "$BUMP" != "minor" && "$BUMP" != "major" ]]; then
    echo "ERROR: Invalid bump type '$BUMP'. Use: major, minor, patch"
    exit 1
fi

# --- Get current version from latest git tag ---
LATEST_TAG=$(git tag -l 'v*' --sort=-v:refname | head -1)
if [ -z "$LATEST_TAG" ]; then
    LATEST_TAG="v0.0.0"
fi

CURRENT="${LATEST_TAG#v}"
IFS='.' read -r MAJOR MINOR PATCH_NUM <<< "$CURRENT"

case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH_NUM=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH_NUM=0 ;;
    patch) PATCH_NUM=$((PATCH_NUM + 1)) ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH_NUM}"
NEW_TAG="v${NEW_VERSION}"
echo "Version: $CURRENT -> $NEW_VERSION ($BUMP)"
echo ""

# --- Run tests ---
echo "Running tests..."
python -m pytest tests/ -x -q --tb=short
echo ""

# --- Ensure working tree is clean ---
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree is dirty. Commit or stash changes first."
    exit 1
fi

# --- Tag (setuptools-scm reads version from git tags) ---
echo "Creating tag $NEW_TAG..."
git tag -a "$NEW_TAG" -m "Release $NEW_TAG"

# --- Clean and build ---
rm -rf dist/ build/ *.egg-info mangrove_kb.egg-info
echo "Building..."
python -m build --sdist --wheel
echo ""

# --- Verify version in built package ---
BUILT_VERSION=$(unzip -p dist/*.whl '*/METADATA' | grep '^Version:' | cut -d' ' -f2)
if [ "$BUILT_VERSION" != "$NEW_VERSION" ]; then
    echo "ERROR: Built version ($BUILT_VERSION) != expected ($NEW_VERSION)"
    echo "Removing tag..."
    git tag -d "$NEW_TAG"
    exit 1
fi

# --- Upload ---
echo "Uploading to PyPI..."
twine upload dist/*
echo ""

# --- Push tag ---
echo "Pushing tag..."
git push origin "$NEW_TAG"

echo ""
echo "Published mangrove-kb $NEW_VERSION to PyPI"
echo "Tag $NEW_TAG pushed to origin"
