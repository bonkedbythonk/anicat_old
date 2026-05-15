import os
import sys

# Add project root to path so we can find anicat_media
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
sys.path.insert(0, project_root)

import uvicorn
from anicat_media.api.main import create_app

import sys
print(f"DEBUG: Sidecar project root: {project_root}")
sys.stdout.flush()

def main():
    # When running as a bundled sidecar, we might need to adjust paths
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        base_dir = sys._MEIPASS
    else:
        # Running in normal python
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = create_app()
    
    # Run the server on localhost
    # We use 127.0.0.1 for maximum privacy and to avoid firewall prompts
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
