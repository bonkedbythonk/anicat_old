#!/bin/bash

# Find the project root dynamically (scripts/ parent directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_NAME="Anicat.app"
INSTALL_DIR="$HOME/Applications"

echo "🚀 Installing Anicat Desktop App..."

# 1. Check for uv (Python manager)
if ! command -v uv &> /dev/null; then
    echo "📦 Installing 'uv' (Python manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Try to add to current path for the rest of the script
    export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Sync dependencies
echo "📦 Setting up the environment and dependencies..."
echo "   (This may take a minute on the first install)"
if ! uv sync --quiet; then
    echo "❌ Error: Failed to install dependencies. Check your internet connection."
    exit 1
fi

# 3. Install the anicat CLI command
echo "📦 Installing anicat CLI command..."
if ! uv pip install -e . --quiet; then
    echo "❌ Error: Failed to install anicat package. Check your setup."
    exit 1
fi

# 4. Save current project path
echo "$PROJECT_DIR" > "$HOME/.anicat_path"
echo "✅ Environment ready."

# 5. Create global wrapper script for 'anicat' command
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/anicat" << 'EOF'
#!/bin/bash
# Global anicat command wrapper

# Read project directory from saved path
PROJECT_DIR="$(cat "$HOME/.anicat_path" 2>/dev/null)"

if [ -z "$PROJECT_DIR" ] || [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Anicat project directory not found. Please reinstall anicat."
    exit 1
fi

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Run anicat from the project directory
cd "$PROJECT_DIR"
uv run anicat "$@"
EOF
chmod +x "$HOME/.local/bin/anicat"

# Ensure ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo ""
    echo "⚠️  Please add ~/.local/bin to your PATH by adding this to your shell config:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "✅ Global 'anicat' command installed at $HOME/.local/bin/anicat"

# 6. Generate app icon from logo
cd "$PROJECT_DIR"
ICON_SOURCE="assets/logo-dark.png"
ICONSET_DIR=".anicat.iconset"
ICNS_FILE="applet.icns"

rm -rf "$ICONSET_DIR" "$ICNS_FILE"
mkdir -p "$ICONSET_DIR"

# Generate all required icon sizes
sips -z 16 16 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
cp "$ICON_SOURCE" "$ICONSET_DIR/icon_512x512@2x.png"

# Package into .icns format
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_FILE"
rm -rf "$ICONSET_DIR"

# 7. Create the App bundle with pre-generated icon
rm -rf "$APP_NAME"
osacompile -o "$APP_NAME" -e "do shell script \"$PROJECT_DIR/scripts/launch_anicat.sh > /dev/null 2>&1 &\""

# Replace the default applet icon with our custom icon
cp "$ICNS_FILE" "$APP_NAME/Contents/Resources/applet.icns"
rm -f "$ICNS_FILE"

echo "✅ App bundle created with custom icon."

# 8. Copy to Applications
mkdir -p "$INSTALL_DIR"
cp -R "$APP_NAME" "$INSTALL_DIR/"
echo "✅ $APP_NAME copied to $INSTALL_DIR"

# 9. Success message
echo ""
echo "✨ Installation Complete! ✨"
echo "You can now find 'Anicat' in your Launchpad or Applications folder."
echo "Go ahead and drag it to your Dock for easy access!"
