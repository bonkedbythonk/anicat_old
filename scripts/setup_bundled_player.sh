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
mkdir -p "$CONFIG_DIR/script-opts"
mkdir -p "$CONFIG_DIR/shaders"

echo "=== 4. Fetching Universal OSC (uosc) modern skin ==="
curl -L -o /tmp/uosc.zip https://github.com/tomasklaen/uosc/releases/latest/download/uosc.zip
unzip -q -o /tmp/uosc.zip -d "$CONFIG_DIR/"

echo "=== 5. Fetching Anime4K real-time upscaling shaders ==="
curl -L -o /tmp/anime4k.zip https://github.com/bloc97/Anime4K/releases/download/v4.0.1/Anime4K_v4.0.zip
unzip -q -o /tmp/anime4k.zip "*.glsl" -d "$CONFIG_DIR/shaders/"

echo "=== 6. Generating customized mpv.conf styled for AniCat ==="
cat << 'EOF' > "$CONFIG_DIR/mpv.conf"
# Video Quality Settings
vo=gpu-next
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

# Shaders (Anime4K Real-time Upscaling & Restoration)
# '~~/' prefix resolves dynamically to this isolated config directory at runtime
glsl-shaders="~~/shaders/Anime4K_Upscale_CNN_x2_M.glsl;~~/shaders/Anime4K_Auto_Restore_VL.glsl"
EOF

echo "=== 7. Generating customized uosc.conf styled with AniCat accents ==="
cat << 'EOF' > "$CONFIG_DIR/script-opts/uosc.conf"
# AniCat Vector-based Glassmorphism Theme for uosc
# Matching web UI cyan accents and deep charcoal backgrounds
foreground=00f2fe
foreground_text=ffffff
background=0d0e12
background_text=e4e4e7
active=00f2fe

# Typography and Sleek Timeline
font=Outfit
timeline_style=bar
timeline_size=32
timeline_border=1
timeline_cache=yes

# Smooth animations & layouts
volume_size=32
EOF

echo "=== 8. Generating AniCat Right-Click Context Menu ==="
cat << 'EOF' > "$CONFIG_DIR/contextmenu.json"
[
  { "type": "menu", "title": "AniCat Actions", "items": [
    { "command": "script-message anicat-next-episode", "title": "⏭️ Next Episode" },
    { "command": "script-message anicat-previous-episode", "title": "⏮️ Previous Episode" },
    { "command": "script-message anicat-toggle-auto-next", "title": "🔄 Toggle Auto-Play" },
    { "command": "script-message anicat-toggle-translation", "title": "💬 Toggle Dub / Sub" },
    { "command": "script-message anicat-reload-episode", "title": "🔄 Reload Episode" }
  ]},
  { "type": "divider" },
  { "command": "cycle pause", "title": "Play / Pause" },
  { "command": "cycle fullscreen", "title": "Toggle Fullscreen" }
]
EOF

echo "=== Cleaning up temporary files ==="
rm -rf "$TMP_EXTRACT"
rm -f /tmp/uosc.zip
rm -f /tmp/anime4k.zip

echo ""
echo "=== Bundle Setup Complete! ==="
echo "Files are located in: $RESOURCES_DIR"
ls -la "$RESOURCES_DIR"
