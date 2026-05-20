#!/bin/bash

# Find the project root dynamically
IS_PIPED=false
if [[ "$0" == "bash" ]] || [[ "$0" == "/bin/bash" ]] || [[ "$0" == "sh" ]] || [[ "$0" == "/bin/sh" ]] || [[ -z "$0" ]] || [[ "$0" == "-" ]]; then
    IS_PIPED=true
fi

if [ -f "pyproject.toml" ] && [ -d "anicat_media" ]; then
    PROJECT_DIR="$(pwd)"
elif [ -d "anicat" ] && [ -f "anicat/pyproject.toml" ]; then
    cd anicat || exit 1
    PROJECT_DIR="$(pwd)"
elif [ "$IS_PIPED" = true ]; then
    echo "Piped execution detected and no repository found. Cloning Anicat..."
    if ! command -v git &> /dev/null; then
        echo "Error: git is not installed. Please install git first."
        exit 1
    fi
    # If the directory exists but is empty or broken, remove it first
    if [ -d "anicat" ]; then
        echo "Existing 'anicat' directory found but seems incomplete. Removing and re-cloning..."
        rm -rf anicat
    fi
    git clone https://github.com/bonkedbythonk/anicat.git
    cd anicat || exit 1
    PROJECT_DIR="$(pwd)"
else
    # Running from a file
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    # Ensure we are in the project root
    if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
        echo "Error: Could not find pyproject.toml in $PROJECT_DIR"
        exit 1
    fi
    cd "$PROJECT_DIR" || { echo "Error: Could not enter project directory $PROJECT_DIR"; exit 1; }
fi

APP_NAME="Anicat.app"
INSTALL_DIR="$HOME/Applications"

echo "Installing Anicat Desktop App..."
echo ""
echo "NOTE: If this is a fresh Mac, Apple may show a popup asking to install"
echo "'Xcode Command Line Tools.' Please click 'Install' to continue."
echo ""

# 1. Check for System Dependencies (mpv, ffmpeg, chafa)
echo "Checking for system dependencies (mpv, ffmpeg, chafa)..."

# Try to find brew in common locations if command -v fails
BREW_EXE=$(command -v brew || true)
if [ -z "$BREW_EXE" ]; then
    if [ -f "/opt/homebrew/bin/brew" ]; then
        BREW_EXE="/opt/homebrew/bin/brew"
    elif [ -f "/usr/local/bin/brew" ]; then
        BREW_EXE="/usr/local/bin/brew"
    fi
fi

if [ -z "$BREW_EXE" ]; then
    echo "Homebrew not found. It is required to install system dependencies (mpv, ffmpeg, chafa)."
    echo "Would you like to install Homebrew now? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Installing Homebrew... (This may ask for your Mac password)"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Set BREW_EXE after installation
        if [ -f "/opt/homebrew/bin/brew" ]; then
            BREW_EXE="/opt/homebrew/bin/brew"
        elif [ -f "/usr/local/bin/brew" ]; then
            BREW_EXE="/usr/local/bin/brew"
        fi

        if [ -n "$BREW_EXE" ]; then
            eval "$($BREW_EXE shellenv)"
        fi
    else
        echo "Homebrew is required for Anicat to function properly. Please install it manually from https://brew.sh"
        exit 1
    fi
fi

# Now that we (hopefully) have brew, install the tools
if [ -n "$BREW_EXE" ]; then
    echo "Checking system tools (mpv, ffmpeg, chafa)..."
    for cmd in mpv ffmpeg chafa; do
        if ! command -v $cmd &> /dev/null; then
            echo "   - Installing $cmd via Homebrew..."
            $BREW_EXE install $cmd --quiet
        fi
    done
    echo "System tools verified."
else
    echo "Warning: Homebrew is still not found. Skipping tool installation."
fi

# 2. Check for uv (Python manager)
if ! command -v uv &> /dev/null; then
    echo "Installing 'uv' (Python manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Try to add to current path for the rest of the script
    export PATH="$HOME/.local/bin:$PATH"
fi

# 3. Check for Node.js (required for dashboard build)
if ! command -v npm &> /dev/null; then
    echo "Node.js not found. It is required to build the Anicat Dashboard."
    if [ -n "$BREW_EXE" ]; then
        echo "   - Installing Node.js via Homebrew..."
        $BREW_EXE install node --quiet
        # Refresh path to include newly installed node
        eval "$($BREW_EXE shellenv)"
    else
        echo "Error: Node.js is required but Homebrew is not available to install it."
        echo "Please install Node.js manually from https://nodejs.org"
        exit 1
    fi
fi

# 4. Sync dependencies
echo "Setting up the environment and dependencies..."
echo "   (This may take a minute on the first install)"
if ! uv sync --quiet; then
    echo "Error: Failed to install dependencies. Check your internet connection."
    exit 1
fi

# 5. Install the anicat CLI command
    echo "Installing anicat CLI command..."
if ! uv pip install -e . --quiet; then
    echo "Error: Failed to install anicat package. Check your setup."
    exit 1
fi

# 6. Save current project path (resolved)
# Resolve to an absolute canonical path to avoid stale/cached locations
RESOLVED_PROJECT_DIR=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$PROJECT_DIR")
echo "$RESOLVED_PROJECT_DIR" > "$HOME/.anicat_path"
echo "Environment ready."

# 7. Build Frontend (for dashboard)
echo "Building Anicat Dashboard frontend..."
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
    echo "Dashboard built and synced."
else
    echo "Error: Frontend build failed."
    exit 1
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
    echo "Error: Anicat project directory not found. Please reinstall anicat."
    exit 1
fi
PROJECT_DIR=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$RAW_PROJECT_DIR")

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Anicat project directory not found at $PROJECT_DIR. Please reinstall anicat."
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
        echo "Adding ~/.local/bin to PATH in $SHELL_CONFIG..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo "PATH updated. Please run 'source $SHELL_CONFIG' or open a new terminal."
    fi
fi

echo "Global 'anicat' command installed at $HOME/.local/bin/anicat"

# 9. Clean up legacy web dashboard configs & build native Tauri Desktop app on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Cleaning up any legacy web dashboard configurations..."
    launchctl unload "$HOME/Library/LaunchAgents/com.bonkedbythonk.anicat.plist" 2>/dev/null || true
    rm -f "$HOME/Library/LaunchAgents/com.bonkedbythonk.anicat.plist"
    rm -rf "$HOME/Applications/Anicat Dashboard.app"

    echo ""
    echo "🏗️ Building native macOS Tauri Desktop App..."
    echo "   (This compiles the sidecar, frontend, and bundles the native App)"
    
    # Run build_dmg.sh
    if ! bash "$PROJECT_DIR/scripts/build_dmg.sh"; then
        echo "Error: Native Tauri app compilation failed."
        exit 1
    fi

    # Find the built .app
    APP_SOURCE=""
    if [ -d "$PROJECT_DIR/web/src-tauri/target/release/bundle/macos/Anicat.app" ]; then
        APP_SOURCE="$PROJECT_DIR/web/src-tauri/target/release/bundle/macos/Anicat.app"
    elif [ -d "$PROJECT_DIR/web/src-tauri/target/release/bundle/osx/Anicat.app" ]; then
        APP_SOURCE="$PROJECT_DIR/web/src-tauri/target/release/bundle/osx/Anicat.app"
    fi

    if [ -n "$APP_SOURCE" ]; then
        echo "🚚 Installing native Anicat.app to $HOME/Applications..."
        mkdir -p "$HOME/Applications"
        rm -rf "$HOME/Applications/Anicat.app"
        cp -R "$APP_SOURCE" "$HOME/Applications/"
        
        echo "🛡️ Configuring security permissions (bypassing macOS Gatekeeper)..."
        xattr -d com.apple.quarantine "$HOME/Applications/Anicat.app" 2>/dev/null || true
        
        echo "✅ Standalone desktop application installed!"
    else
        echo "Warning: Could not find compiled Anicat.app bundle to copy."
    fi
fi

# 10. Success message
echo ""
echo "✨ Installation Complete! ✨"
echo "Anicat has been successfully installed."
echo ""
echo "💻 CLI / TUI: Run 'anicat' in your terminal to start the interactive interface."
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🖥️  Desktop App: Open 'Anicat' in your Applications folder (~/Applications/Anicat.app)."
fi
echo ""
exit 0
