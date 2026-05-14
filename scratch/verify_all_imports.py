import os
import sys
import importlib
import pkgutil
from pathlib import Path

def test_imports(package_name, package_path):
    print(f"Testing imports for {package_name} in {package_path}")
    
    # Add the parent directory of anicat_media to sys.path
    sys.path.insert(0, str(Path(package_path).parent))
    
    # Recursively find all modules
    failed_modules = []
    for loader, module_name, is_pkg in pkgutil.walk_packages([package_path], package_name + "."):
        try:
            # print(f"Importing {module_name}...")
            importlib.import_module(module_name)
        except NameError as e:
            print(f"FAILED: {module_name} raised NameError: {e}")
            failed_modules.append((module_name, str(e)))
        except Exception as e:
            # print(f"Skipping {module_name} due to other error: {type(e).__name__}: {e}")
            pass
            
    return failed_modules

if __name__ == "__main__":
    package_path = "/Users/thomas/Documents/randomcode/anicat/anicat_media"
    failed = test_imports("anicat_media", package_path)
    
    if failed:
        print("\nSUMMARY: The following modules failed to import due to NameError:")
        for mod, err in failed:
            print(f"  - {mod}: {err}")
    else:
        print("\nSUMMARY: No modules failed to import due to NameError.")
