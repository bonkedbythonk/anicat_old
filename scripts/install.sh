#!/bin/bash

# Find the project root dynamically (scripts/ parent directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_NAME="Anicat.app"
INSTALL_DIR="$HOME/Applications"

echo "🚀 Installing Anicat Desktop App..."

# 1. Check for System Dependencies (mpv, ffmpeg, chafa)
echo "🔍 Checking for system dependencies (mpv, ffmpeg, chafa)..."
if ! command -v brew &> /dev/null; then
    echo "⚠️  Homebrew not found. System dependencies might be missing."
    echo "   (For the best experience, we recommend installing Homebrew from https://brew.sh)"
else
    # Ensure brew is updated if it's been a while (optional, but keep it fast)
    for cmd in mpv ffmpeg chafa; do
        if ! command -v $cmd &> /dev/null; then
            echo "📦 Installing $cmd via Homebrew..."
            brew install $cmd
        fi
    done
    echo "✅ System dependencies verified."
fi

# 2. Check for uv (Python manager)
if ! command -v uv &> /dev/null; then
    echo "📦 Installing 'uv' (Python manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Try to add to current path for the rest of the script
    export PATH="$HOME/.local/bin:$PATH"
fi

# 3. Sync dependencies
echo "📦 Setting up the environment and dependencies..."
echo "   (This may take a minute on the first install)"
if ! uv sync --quiet; then
    echo "❌ Error: Failed to install dependencies. Check your internet connection."
    exit 1
fi

# 4. Install the anicat CLI command
echo "📦 Installing anicat CLI command..."
if ! uv pip install -e . --quiet; then
    echo "❌ Error: Failed to install anicat package. Check your setup."
    exit 1
fi

# 5. Save current project path (resolved)
# Resolve to an absolute canonical path to avoid stale/cached locations
RESOLVED_PROJECT_DIR=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$PROJECT_DIR")
echo "$RESOLVED_PROJECT_DIR" > "$HOME/.anicat_path"
echo "✅ Environment ready."

# 6. Build Frontend (for dashboard)
echo "📦 Building Anicat Dashboard frontend..."
if ! command -v npm &> /dev/null; then
    echo "⚠️  Warning: 'npm' not found. Dashboard frontend will not be updated."
    echo "   Please install Node.js (https://nodejs.org) to build the dashboard."
else
    cd "$PROJECT_DIR/web"
    echo "   - Installing frontend dependencies..."
    npm install --quiet
    echo "   - Building static export..."
    if npm run build; then
        echo "   - Syncing static files to backend..."
        STATIC_DIR="$PROJECT_DIR/anicat_media/api/static"
        rm -rf "$STATIC_DIR"/*
        mkdir -p "$STATIC_DIR"
        cp -R out/* "$STATIC_DIR/"
        echo "✅ Dashboard built and synced."
    else
        echo "❌ Error: Frontend build failed."
        exit 1
    fi
fi

cd "$PROJECT_DIR"

# 7. Create global wrapper script for 'anicat' command
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/anicat" << 'EOF'
#!/bin/bash
# Global anicat command wrapper

# Read project directory from saved path and resolve it to an absolute path
RAW_PROJECT_DIR="$(cat "$HOME/.anicat_path" 2>/dev/null)"
if [ -z "$RAW_PROJECT_DIR" ]; then
    echo "❌ Error: Anicat project directory not found. Please reinstall anicat."
    exit 1
fi
PROJECT_DIR=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$RAW_PROJECT_DIR")

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Anicat project directory not found at $PROJECT_DIR. Please reinstall anicat."
    exit 1
fi

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Run anicat from the project directory
cd "$PROJECT_DIR"
uv run anicat "$@"
EOF
chmod +x "$HOME/.local/bin/anicat"

# 8. Ensure ~/.local/bin is in PATH
SHELL_CONFIG=""
if [[ "$SHELL" == */zsh ]]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [[ "$SHELL" == */bash ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SHELL_CONFIG="$HOME/.bash_profile"
    else
        SHELL_CONFIG="$HOME/.bashrc"
    fi
fi

if [ -n "$SHELL_CONFIG" ]; then
    if ! grep -q ".local/bin" "$SHELL_CONFIG" 2>/dev/null; then
        echo "📝 Adding ~/.local/bin to PATH in $SHELL_CONFIG..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo "✅ PATH updated. Please run 'source $SHELL_CONFIG' or open a new terminal."
    fi
fi

echo "✅ Global 'anicat' command installed at $HOME/.local/bin/anicat"

# 9. Success message
echo ""
echo "✨ Installation Complete! ✨"
echo "Anicat is now installed and ready to go."
echo ""
echo "🚀 Launching Anicat Dashboard for you..."
echo ""

# Ensure the new PATH is available for this session
export PATH="$HOME/.local/bin:$PATH"

# Give a tiny delay so the user can read the success message
sleep 2

# Launch the dashboard
anicat dashboard
