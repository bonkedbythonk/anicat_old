#!/bin/bash
set -e

# setup_bundled_player.sh
# Automates downloading, extracting, and configuring the portable MPV companion player for AniCat.

RESOURCES_DIR="web/src-tauri/resources"
CONFIG_DIR="$RESOURCES_DIR/mpv_config"

echo "=== 1. Locating official macOS MPV Cask Bottle ==="
BOTTLE_PATH=$(find $(brew --cache) -name "*mpv-*.tar.gz" | head -n 1)

if [ -z "$BOTTLE_PATH" ]; then
    echo "Cask bottle not found in local cache. Fetching via Homebrew..."
    brew fetch --cask mpv
    BOTTLE_PATH=$(find $(brew --cache) -name "*mpv-*.tar.gz" | head -n 1)
fi

echo "Discovered bottle at: $BOTTLE_PATH"

echo "=== 2. Creating resources directory and extracting binary ==="
mkdir -p "$RESOURCES_DIR"
TMP_EXTRACT="/tmp/mpv_bottle_extract"
rm -rf "$TMP_EXTRACT" && mkdir -p "$TMP_EXTRACT"

echo "Extracting Cask contents..."
tar -xf "$BOTTLE_PATH" -C "$TMP_EXTRACT"

APP_DIR=$(find "$TMP_EXTRACT" -name "mpv.app" | head -n 1)
if [ -z "$APP_DIR" ]; then
    echo "Error: Could not find mpv.app inside the extracted bottle."
    exit 1
fi

echo "Copying MPV standalone binary and dynamic libraries..."
cp -R "$APP_DIR/Contents/MacOS/mpv" "$RESOURCES_DIR/"
cp -R "$APP_DIR/Contents/MacOS/lib" "$RESOURCES_DIR/"

echo "=== 3. Setting up isolated themed configuration directories ==="
mkdir -p "$CONFIG_DIR/scripts"
mkdir -p "$CONFIG_DIR/scripts/anicat_ui"
mkdir -p "$CONFIG_DIR/script-opts"
mkdir -p "$CONFIG_DIR/shaders"

echo "=== 4. Fetching ModernZ On-Screen Controller ==="
# Clone the repository locally to get modernz.lua and modernz-icons.ttf
mkdir -p /tmp/modernz_repo
git clone --depth 1 https://github.com/Samillion/ModernZ.git /tmp/modernz_repo
cp /tmp/modernz_repo/modernz.lua "$CONFIG_DIR/scripts/modernz.lua"
mkdir -p "$CONFIG_DIR/fonts"
cp /tmp/modernz_repo/modernz-icons.ttf "$CONFIG_DIR/fonts/modernz-icons.ttf"
rm -rf /tmp/modernz_repo

echo "=== 5. Fetching Anime4K real-time upscaling shaders ==="
curl -L -o /tmp/anime4k.zip https://github.com/bloc97/Anime4K/releases/download/v4.0.1/Anime4K_v4.0.zip
unzip -q -o /tmp/anime4k.zip "*.glsl" -d "$CONFIG_DIR/shaders/"

echo "=== 6. Generating customized mpv.conf styled for AniCat ==="
cat << 'EOF' > "$CONFIG_DIR/mpv.conf"
# Video Quality Settings
vo=gpu
profile=high-quality
hwdec=auto-safe

# Complete Borderless Minimalism
border=no
osc=no

# Subtitles
sub-auto=fuzzy
sub-font="Outfit"
sub-font-size=44
sub-bold=yes
EOF

# Copy overlay and keybindings if they aren't already in place (preventing cp-onto-itself errors)
[ -f "$CONFIG_DIR/scripts/anicat_ui/main.lua" ] || cp web/src-tauri/resources/mpv_config/scripts/anicat_ui/main.lua "$CONFIG_DIR/scripts/anicat_ui/main.lua" 2>/dev/null || true
[ -f "$CONFIG_DIR/input.conf" ] || cp web/src-tauri/resources/mpv_config/input.conf "$CONFIG_DIR/input.conf" 2>/dev/null || true

echo "=== 8. Deploying customized modernz.conf styled with AniCat accents ==="
[ -f "$CONFIG_DIR/script-opts/modernz.conf" ] || cp web/src-tauri/resources/mpv_config/script-opts/modernz.conf "$CONFIG_DIR/script-opts/modernz.conf" 2>/dev/null || true

echo "=== Cleaning up temporary files ==="
rm -rf "$TMP_EXTRACT"
rm -f /tmp/anime4k.zip

echo ""
echo "=== Bundle Setup Complete! ==="
echo "Files are located in: $RESOURCES_DIR"
ls -la "$RESOURCES_DIR"
