import os
import sys
import importlib.util
from pathlib import Path

def check_file(file_path):
    # Try to load the module
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None:
        return None
    
    module = importlib.util.module_from_spec(spec)
    try:
        # This will execute the module-level code
        spec.loader.exec_module(module)
    except NameError as e:
        if "'Any'" in str(e):
            return str(e)
    except Exception:
        # Ignore other errors during execution
        pass
    
    return None

def scan_directory(start_path):
    failed_files = []
    for root, dirs, files in os.walk(start_path):
        if ".git" in root or "__pycache__" in root or ".venv" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                error = check_file(file_path)
                if error:
                    failed_files.append((file_path, error))
    
    return failed_files

if __name__ == "__main__":
    start_dir = "/Users/thomas/Documents/randomcode/anicat/anicat_media"
    failed = scan_directory(start_dir)
    
    if failed:
        print("Files that failed with NameError: Any:")
        for f, e in failed:
            print(f"  {f}: {e}")
    else:
        print("No files failed with NameError: Any.")
