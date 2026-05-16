import os
import sys

# When running as a bundled sidecar (PyInstaller), we use sys._MEIPASS
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_dir = sys._MEIPASS
    # In PyInstaller, the anicat_media package is added to the root of _MEIPASS
    sys.path.insert(0, base_dir)
else:
    # Running in normal python (development)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    sys.path.insert(0, project_root)
    base_dir = current_dir

import uvicorn
from anicat_media.api.main import create_app

print(f"DEBUG: Sidecar base_dir: {base_dir}")
sys.stdout.flush()

def main():
    # When running as a bundled sidecar, we might need to adjust paths
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    else:
        # Running in normal python
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = create_app()
    
    # Run the server on localhost
    # We use 127.0.0.1 for maximum privacy and to avoid firewall prompts
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
