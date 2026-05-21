#!/bin/bash
set -e

# Anicat CLI Installer — single-command install for the terminal version
#
# Usage:  curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/master/scripts/install_cli.sh | bash
#
# Installs the `anicat` CLI command via uv (recommended) or pip.
# After installation you can run: anicat --help

REPO="bonkedbythonk/anicat"
CLONE_URL="https://github.com/$REPO.git"

echo "=== Anicat CLI Installer ==="
echo ""

# ── 1. Detect package manager ──
if command -v uv &>/dev/null; then
    PKG_MANAGER="uv"
    INSTALL_CMD="uv tool install --force $CLONE_URL"
elif command -v pip3 &>/dev/null; then
    PKG_MANAGER="pip3"
    echo "NOTE: uv is recommended for faster, isolated installs."
    echo "      Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    INSTALL_CMD="pip3 install --upgrade --break-system-packages git+$CLONE_URL"
elif command -v pip &>/dev/null; then
    PKG_MANAGER="pip"
    INSTALL_CMD="pip install --upgrade --break-system-packages git+$CLONE_URL"
else
    echo "Error: No Python package manager found."
    echo "Install uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Or install pip: python3 -m ensurepip"
    exit 1
fi

echo "[1/3] Installing Anicat CLI via $PKG_MANAGER..."
eval "$INSTALL_CMD"

echo ""
echo "[2/3] Verifying installation..."
if command -v anicat &>/dev/null; then
    INSTALLED_VERSION=$(anicat --version 2>&1 | head -1)
    echo "  $INSTALLED_VERSION"
else
    echo "  Warning: 'anicat' not found in PATH."
    echo "  You may need to add ~/.local/bin to your PATH:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "  Or restart your terminal."
fi

echo ""
echo "[3/3] Installation complete!"
echo ""
echo "Quick start:"
echo "  anicat --help          # See all commands"
echo "  anicat config          # Set up AniList token"
echo "  anicat search -t <title>  # Search and play"
echo "  anicat status          # Check if the dashboard is running"
echo ""
echo "For the full GUI (macOS):  $CLONE_URL#readme"
