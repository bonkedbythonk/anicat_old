#!/bin/bash

# Configuration
PORT=13370
URL="http://localhost:$PORT"

# 1. Determine Project Directory
# First check if we have a saved path
CONFIG_FILE="$HOME/.anicat_path"
if [ -f "$CONFIG_FILE" ]; then
    PROJECT_DIR=$(cat "$CONFIG_FILE")
else
    # Fallback to relative path if no config
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"
fi

# Validate directory
if [ ! -d "$PROJECT_DIR/anicat_media" ]; then
    echo "Error: Project directory not found at $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. Start Backend
if ! lsof -i :$PORT > /dev/null; then
    echo "Starting Anicat Backend..."
    # Use 'anicat dashboard' which is the proper way to start the uvicorn server
    uv run anicat dashboard --no-browser > backend.log 2>&1 &
    
    # Wait for startup (check if the API is actually responding)
    MAX_RETRIES=15
    RETRY_COUNT=0
    while ! curl -sf "http://127.0.0.1:$PORT/api/status/health" > /dev/null && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        sleep 1
        RETRY_COUNT=$((RETRY_COUNT + 1))
    done
fi

# 3. Open Browser
open "$URL"
