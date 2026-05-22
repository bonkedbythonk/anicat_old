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
    
    # Start a background thread to monitor the parent process.
    # If the parent Tauri process dies (e.g. ungraceful shutdown or dev reload),
    # this sidecar will be reparented to PID 1. If that happens, we must exit
    # to avoid leaving ghost processes that block the 13370 port.
    import threading
    import time
    def monitor_parent():
        original_ppid = os.getppid()
        while True:
            time.sleep(2)
            current_ppid = os.getppid()
            if current_ppid == 1 or (current_ppid != original_ppid and current_ppid == 1):
                print("Parent process died. Shutting down sidecar.", flush=True)
                os._exit(0)
    
    # Only monitor if running as a bundled sidecar or if not running directly from terminal
    if getattr(sys, 'frozen', False):
        threading.Thread(target=monitor_parent, daemon=True).start()
    
    # Run the server on localhost
    # We use 127.0.0.1 for maximum privacy and to avoid firewall prompts
    uvicorn.run(app, host="127.0.0.1", port=13370, log_level="info")

if __name__ == "__main__":
    main()
