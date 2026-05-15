#!/bin/bash
set -e

# This script builds the Python sidecar as a standalone binary for macOS DMG bundling.
# It uses PyInstaller to freeze the Python environment and code.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TAURI_BIN_DIR="$PROJECT_ROOT/web/src-tauri/binaries"
BUILD_DIR="$PROJECT_ROOT/build_sidecar"

echo "🚀 Building Anicat Sidecar Binary..."

# 1. Prepare build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 2. Copy the server entry point
cp "$TAURI_BIN_DIR/anicat-server.py" .

# 3. Build the binary using PyInstaller
# We include the anicat_media package and all necessary uvicorn protocols
echo "📦 Freezing Python environment (this may take a minute)..."

# Determine architecture for naming
ARCH=$(uname -m)
if [ "$ARCH" == "arm64" ]; then
    TARGET_NAME="anicat-server-aarch64-apple-darwin"
else
    TARGET_NAME="anicat-server-x86_64-apple-darwin"
fi

uv run pyinstaller --noconfirm --onefile --clean \
    --paths "$PROJECT_ROOT" \
    --add-data "$PROJECT_ROOT/anicat_media:anicat_media" \
    --hidden-import "uvicorn.protocols.http.h11_impl" \
    --hidden-import "uvicorn.protocols.http.httptools_impl" \
    --hidden-import "uvicorn.protocols.websockets.websockets_impl" \
    --hidden-import "uvicorn.protocols.websockets.wsproto_impl" \
    --hidden-import "uvicorn.loop.asyncio" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "fastapi" \
    --hidden-import "pydantic_core._pydantic_core" \
    --name "anicat-server-temp" \
    "anicat-server.py"

# 4. Move the resulting binary to the Tauri binaries folder
echo "🚚 Moving binary to Tauri..."
mkdir -p "$TAURI_BIN_DIR"
cp "dist/anicat-server-temp" "$TAURI_BIN_DIR/$TARGET_NAME"
chmod +x "$TAURI_BIN_DIR/$TARGET_NAME"

echo "✅ Sidecar build complete: $TAURI_BIN_DIR/$TARGET_NAME"
