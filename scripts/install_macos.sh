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
LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")
DOWNLOAD_URL=$(echo "$LATEST_RELEASE" | grep -o "https://github.com/bonkedbythonk/anicat/releases/download/[^\"]*\.dmg" | head -n 1)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not find a DMG for the latest release."
    exit 1
fi

# 2. Download the DMG
TMP_DMG="/tmp/anicat_latest.dmg"
echo "Downloading Anicat from $DOWNLOAD_URL..."
curl -L -o "$TMP_DMG" "$DOWNLOAD_URL"

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
hdiutil unmount "$MOUNT_POINT"
rm "$TMP_DMG"

# 6. Bypass Gatekeeper (Quarantine)
# Since the app is unsigned, we remove the quarantine flag so it opens without warnings.
echo "Configuring security permissions..."
xattr -d com.apple.quarantine "$INSTALL_PATH" 2>/dev/null || true

# 7. Automatically Restart the Application
echo "Relaunching Anicat..."
open -a "$INSTALL_PATH"

# Wait a brief moment for the new app window to request launch resources, then kill the old one
sleep 1
killall "Anicat" || true
killall "Anicat Dev" || true

echo ""
echo "Installation Complete and Anicat has restarted!"
echo ""
