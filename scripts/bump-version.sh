#!/usr/bin/env bash
# bump-version.sh — Single source of truth for version bumps.
#
# Usage:  bash scripts/bump-version.sh 4.0.1
#         bash scripts/bump-version.sh 4.1.0
#         bash scripts/bump-version.sh 5.0.0
#
# Updates version.txt (canonical), pyproject.toml, web/package.json,
# web/src-tauri/tauri.conf.json, and flake.nix in one shot.

set -euo pipefail

NEW_VERSION="${1:-}"

if ! echo "$NEW_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Usage: $0 <MAJOR.MINOR.PATCH>"
    echo "  e.g. $0 4.0.1  (bug fix)"
    echo "       $0 4.1.0  (new feature)"
    echo "       $0 5.0.0  (breaking change)"
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 1. Canonical source
echo "$NEW_VERSION" > version.txt
echo "[1/5] version.txt  -> $NEW_VERSION"

# 2. pyproject.toml
sed -i '' "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml
echo "[2/5] pyproject.toml  -> $NEW_VERSION"

# 3. web/package.json
node -e "
  const p = require('./web/package.json');
  p.version = '$NEW_VERSION';
  require('fs').writeFileSync('./web/package.json', JSON.stringify(p, null, 2) + '\n');
"
echo "[3/5] web/package.json  -> $NEW_VERSION"

# 4. web/src-tauri/tauri.conf.json
node -e "
  const t = require('./web/src-tauri/tauri.conf.json');
  t.version = '$NEW_VERSION';
  require('fs').writeFileSync('./web/src-tauri/tauri.conf.json', JSON.stringify(t, null, 2) + '\n');
"
echo "[4/5] web/src-tauri/tauri.conf.json  -> $NEW_VERSION"

# 5. flake.nix
sed -i '' "s/version = \"[0-9]*\.[0-9]*\.[0-9]*\"/version = \"$NEW_VERSION\"/" flake.nix
echo "[5/5] flake.nix  -> $NEW_VERSION"

echo ""
echo "All files bumped to $NEW_VERSION."
echo "Review with: git diff"
