#!/bin/bash
set -e

# Release helper: builds the DMG locally and uploads to GitHub Releases.
#
# Usage:
#   bash scripts/release.sh --nightly         # Build + upload to "nightly" tag (pre-release)
#   bash scripts/release.sh --stable          # Build + upload to "v{version}" tag (from version.txt)
#   bash scripts/release.sh --dry-run         # Build only, no upload
#
# Prerequisites:
#   gh auth login  (one-time setup, or set GH_TOKEN in your env)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --nightly|--stable|--dry-run) MODE="$1"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$MODE" ]]; then
    echo "Usage: bash scripts/release.sh [--nightly|--stable|--dry-run]"
    exit 1
fi

VERSION=$(cat "$PROJECT_ROOT/version.txt")
DMG_NAME="Anicat_${VERSION}_aarch64.dmg"
DMG_PATH="$PROJECT_ROOT/web/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/${DMG_NAME}"

echo "=============================="
echo "  Anicat Release Builder"
echo "  Version: $VERSION"
echo "  Mode:    $MODE"
echo "=============================="
echo ""

# Step 1: Build
echo "[1/2] Building DMG..."
bash "$SCRIPT_DIR/build_dmg.sh"

if [[ ! -f "$DMG_PATH" ]]; then
    echo "ERROR: DMG not found at expected path: $DMG_PATH"
    echo "Look in: web/src-tauri/target/*/release/bundle/dmg/"
    ls -la "$PROJECT_ROOT/web/src-tauri/target/"*/release/bundle/dmg/ 2>/dev/null || true
    exit 1
fi

echo ""
echo "  DMG built: $DMG_PATH"
echo "  Size: $(du -h "$DMG_PATH" | cut -f1)"
echo ""

# Step 2: Upload
if [[ "$MODE" == "--dry-run" ]]; then
    echo "[2/2] DRY RUN - skipping upload."
    echo "Would upload to: $( [[ "$MODE" == "--nightly" ]] && echo "nightly (pre-release)" || echo "v${VERSION} (stable)" )"
    exit 0
fi

# Determine tag and prerelease flag
if [[ "$MODE" == "--nightly" ]]; then
    TAG="nightly"
    RELEASE_NAME="Anicat Nightly Build"
    PRERELEASE="--prerelease"
    NOTES="Automated nightly build from local machine. Version: ${VERSION}"
else
    TAG="v${VERSION}"
    RELEASE_NAME="Anicat v${VERSION}"
    PRERELEASE=""
    NOTES="Stable release of Anicat v${VERSION}."
fi

echo "[2/2] Uploading to GitHub Releases (tag: ${TAG})..."

# Delete existing release + tag if they exist (for nightly, we replace)
if gh release view "$TAG" &>/dev/null; then
    echo "  Removing existing release: $TAG"
    gh release delete "$TAG" --yes --cleanup-tag 2>/dev/null || true
    # Wait a moment for cleanup
    sleep 2
fi

# Create the release and upload the DMG
gh release create "$TAG" \
    "$DMG_PATH" \
    --title "$RELEASE_NAME" \
    --notes "$NOTES" \
    $PRERELEASE \
    --draft

echo ""
echo "==================================="
echo "  Release uploaded successfully!"
echo "  Tag:  $TAG"
echo "  DMG:  $DMG_NAME"
echo "==================================="
