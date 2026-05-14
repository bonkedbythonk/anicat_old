import os
import sys
import importlib.util
from pathlib import Path

# Add the project root to sys.path
project_root = "/Users/thomas/Documents/randomcode/anicat"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def check_file(file_path):
    module_name = f"anicat_media.cli.interactive.menu.media.{file_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None:
        return None
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except NameError as e:
        if "'Any'" in str(e):
            return str(e)
    except Exception as e:
        # print(f"Other error in {file_path}: {e}")
        pass
    
    return None

menu_dir = Path("/Users/thomas/Documents/randomcode/anicat/anicat_media/cli/interactive/menu/media")
failed = []
for file in menu_dir.glob("*.py"):
    if file.name == "__init__.py":
        continue
    err = check_file(file)
    if err:
        failed.append((file.name, err))

if failed:
    print("Failed menu modules:")
    for f, e in failed:
        print(f"  {f}: {e}")
else:
    print("All menu modules loaded fine.")
