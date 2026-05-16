import os
import sys
import argparse

# Handle PyInstaller paths
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS.
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Add the project root to sys.path so we can import anicat_media
# In the bundle, anicat_media is at the root of bundle_dir
sys.path.insert(0, bundle_dir)

import uvicorn
try:
    from anicat_media.api.main import create_app
except ImportError as e:
    print(f"Error: Could not import anicat_media. sys.path: {sys.path}")
    print(f"Import error: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Anicat API Server (Sidecar)")
    parser.add_argument("--port", type=int, default=13370, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    print(f"Starting Anicat Sidecar on http://{args.host}:{args.port}")
    sys.stdout.flush()
    
    app = create_app()
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

if __name__ == "__main__":
    main()
