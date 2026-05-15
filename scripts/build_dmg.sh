#!/bin/bash
set -e

# This script performs a full production build of Anicat and packages it as a .dmg for macOS.
# 1. Builds the Python sidecar binary
# 2. Builds the Next.js frontend
# 3. Bundles everything into a macOS Application and DMG using Tauri

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🏗️ Starting Full Production Build of Anicat..."

# 1. Build Sidecar
echo "📡 Step 1: Building Python Sidecar..."
bash "$SCRIPT_DIR/build_sidecar.sh"

# 2. Build Frontend & Tauri App
echo "💻 Step 2: Building Frontend and Bundling App..."
cd "$PROJECT_ROOT/web"

# Ensure dependencies are installed
npm install

# Run the Tauri build command
# This will trigger 'npm run build' (Next.js) internally as defined in tauri.conf.json
npx tauri build

echo "✨ Build Complete!"
echo "📂 Your DMG is waiting in: web/src-tauri/target/release/bundle/dmg/"
