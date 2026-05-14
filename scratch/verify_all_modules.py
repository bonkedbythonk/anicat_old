import os
import sys
import importlib
import pkgutil
from pathlib import Path

def walk_package(package_name):
    package = importlib.import_module(package_name)
    results = []
    for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
        results.append(module_name)
    return results

if __name__ == "__main__":
    # Add current directory to sys.path
    sys.path.insert(0, os.getcwd())
    
    modules = walk_package("anicat_media")
    
    passed = 0
    failed = 0
    
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            passed += 1
        except NameError as e:
            if "name 'Any' is not defined" in str(e):
                print(f"FAILED: {module_name} - {e}")
                failed += 1
            else:
                # Other NameErrors might be relevant too
                print(f"FAILED (other NameError): {module_name} - {e}")
                failed += 1
        except Exception as e:
            # Other errors might happen during import due to missing dependencies, etc.
            # We mostly care about NameError: Any
            pass

    print(f"\nSummary: {passed} passed, {failed} failed")
