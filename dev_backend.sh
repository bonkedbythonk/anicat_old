#!/bin/bash
# Shortcut to start the Anicat backend with auto-reload enabled

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo "Starting Anicat Backend with Auto-Reload..."
uv run uvicorn anicat_media.api.main:create_app --factory --reload --port 8000
