#!/bin/bash
set -e

# Anicat Easy macOS Installer
# This script downloads the latest release from GitHub, installs it, and bypasses Gatekeeper.

REPO="bonkedbythonk/anicat"
APP_NAME="Anicat.app"
INSTALL_PATH="/Applications/$APP_NAME"

echo "Starting Anicat installation..."

# 1. Get latest release version and download URL
echo "Finding latest release..."
UPDATE_BRANCH="stable"
if [ -f "$HOME/.config/anicat/config.toml" ]; then
    if grep -q 'update_branch = "nightly"' "$HOME/.config/anicat/config.toml"; then
        UPDATE_BRANCH="nightly"
    fi
fi

if [ "$UPDATE_BRANCH" = "nightly" ]; then
    echo "Tracking nightly branch update..."
    LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data[0]) if data else '')" 2>/dev/null || curl -s "https://api.github.com/repos/$REPO/releases/latest")
else
    LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")
fi

DOWNLOAD_URL=$(echo "$LATEST_RELEASE" | grep -o "https://github.com/bonkedbythonk/anicat/releases/download/[^\"]*\.dmg" | head -n 1)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not find a DMG for the latest release."
    exit 1
fi

# 2. Download the DMG
TMP_DMG="/tmp/anicat_latest.dmg"
echo "Downloading Anicat from $DOWNLOAD_URL..."
curl -L -o "$TMP_DMG" "$DOWNLOAD_URL"

# Pre-cleanup: Detach any previously stuck Anicat mounts to keep the desktop pristine
echo "Cleaning up any existing mounted volumes..."
for volume in /Volumes/Anicat*; do
    if [ -d "$volume" ]; then
        echo "Detaching stuck volume: $volume"
        hdiutil detach -force "$volume" 2>/dev/null || true
    fi
done

# 3. Mount the DMG
echo "Mounting DMG..."
MOUNT_POINT=$(hdiutil mount "$TMP_DMG" | tail -n 1 | awk -F '\t' '{print $3}')

# 4. Copy to Applications
echo "Installing to $INSTALL_PATH..."
if [ -d "$INSTALL_PATH" ]; then
    echo "Existing version found. Replacing..."
    rm -rf "$INSTALL_PATH"
fi
cp -R "$MOUNT_POINT/$APP_NAME" "/Applications/"

# 5. Unmount and Cleanup
echo "Cleaning up..."
hdiutil detach -force "$MOUNT_POINT" 2>/dev/null || hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
rm -f "$TMP_DMG"

# 6. Bypass Gatekeeper (Quarantine)
# Since the app is unsigned, we remove the quarantine flag so it opens without warnings.
echo "Configuring security permissions..."
xattr -d com.apple.quarantine "$INSTALL_PATH" 2>/dev/null || true

# 7. Automatically Restart the Application
echo "Relaunching Anicat..."

# Kill the old running instances first to unblock a clean relaunch
killall "Anicat" 2>/dev/null || true
killall "Anicat Dev" 2>/dev/null || true

# Wait a brief moment for processes to release resources, then boot it fresh
sleep 1
open -a "$INSTALL_PATH"

echo ""
echo "Installation Complete and Anicat has restarted!"
echo ""
