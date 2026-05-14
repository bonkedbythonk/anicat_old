import os
import sys
import importlib.util
from pathlib import Path

def test_imports(start_path):
    # Add start_path to sys.path
    sys.path.insert(0, str(start_path))
    
    count = 0
    failed = 0
    
    for root, dirs, files in os.walk(start_path / "anicat_media"):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = Path(root) / file
                relative_path = file_path.relative_to(start_path)
                module_name = str(relative_path.with_suffix("")).replace(os.sep, ".")
                
                try:
                    # Use importlib to load the module
                    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        count += 1
                except NameError as e:
                    if "name 'Any' is not defined" in str(e):
                        print(f"FAILED (NameError: Any): {module_name} in {file_path}")
                        failed += 1
                except Exception as e:
                    # Ignore other errors for now as some modules might require complex setup
                    pass
                    
    print(f"\nTested {count} modules. Found {failed} modules with missing Any.")

if __name__ == "__main__":
    test_imports(Path("/Users/thomas/Documents/randomcode/anicat"))
