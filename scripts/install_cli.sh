#!/usr/bin/env bash
set -e

# Anicat CLI Installer — single-command install for the terminal version
#
# Usage:  curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat_old/master/scripts/install_cli.sh | bash
#
# Installs the `anicat` CLI command globally via uv (recommended) or pip.
# After installation you can run: anicat --help

REPO="bonkedbythonk/anicat_old"
CLONE_URL="git+https://github.com/$REPO.git@nightly"

echo "=== Anicat CLI Installer ==="
echo ""

# ── 1. Ensure a package manager is available ──
if ! command -v uv &>/dev/null && ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
    echo "[1/3] No package manager found. Installing uv (recommended)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source it for the current shell
    if [ -f "$HOME/.cargo/env" ]; then
        . "$HOME/.cargo/env"
    fi
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

# ── 2. Install ──
if command -v uv &>/dev/null; then
    PKG_MANAGER="uv"
    echo "[1/3] Installing Anicat CLI via uv..."
    uv tool install --force "$CLONE_URL"
elif command -v pip3 &>/dev/null; then
    PKG_MANAGER="pip3"
    echo "[1/3] Installing Anicat CLI via pip3..."
    pip3 install --upgrade --break-system-packages "$CLONE_URL"
else
    echo "[1/3] Installing Anicat CLI via pip..."
    pip install --upgrade --break-system-packages "$CLONE_URL"
fi

echo ""
echo "[2/3] Verifying installation..."
# Refreshing PATH for uv-installed tools
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
if command -v anicat &>/dev/null; then
    INSTALLED_VERSION=$(anicat --version 2>&1 | head -1)
    echo "  $INSTALLED_VERSION"
else
    echo "  Warning: 'anicat' not found in PATH."
    if [ "$PKG_MANAGER" = "uv" ]; then
        echo "  Run: eval \"\$(cat \$HOME/.cargo/env)\"  or restart your terminal"
    else
        echo "  Add ~/.local/bin to your PATH and restart your terminal"
    fi
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
