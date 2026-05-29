#!/bin/bash

# Anicat One-Click Setup Script
# This script clones the repository and runs the installer.

set -e

REPO_URL="https://github.com/bonkedbythonk/anicat_old.git"
TARGET_DIR="$HOME/anicat"

echo "🌟 Welcome to Anicat Setup! 🌟"
echo "-------------------------------"

# 1. Check for Git
if ! command -v git &> /dev/null; then
    echo "❌ Error: Git is not installed."
    echo "   Please install Git or contact support."
    exit 1
fi

# 2. Clone or Update
if [ -d "$TARGET_DIR" ]; then
    echo "📂 Anicat folder already exists. Updating..."
    cd "$TARGET_DIR"
    git pull
else
    echo "📥 Downloading Anicat..."
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

# 3. Run the installer
echo "🛠️  Starting installation..."
./scripts/install.sh
