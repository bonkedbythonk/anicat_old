import os
from pathlib import Path
import re

def check_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple check if "Any" is used
    if not re.search(r'\bAny\b', content):
        return False
    
    # Check if "Any" is imported
    if re.search(r'from typing import .*?\bAny\b', content):
        return False
    if re.search(r'import typing\b', content):
        return False
    if re.search(r'typing\.Any\b', content):
        # If they use typing.Any, they need to import typing
        if re.search(r'import typing\b', content):
            return False
        return True # Uses typing.Any but no import typing
        
    return True # Uses Any but no import from typing

def scan(start_dir):
    results = []
    for root, dirs, files in os.walk(start_dir):
        if any(x in root for x in [".git", "__pycache__", ".venv", "scratch"]):
            continue
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                if check_file(path):
                    results.append(path)
    return results

if __name__ == "__main__":
    start_dir = "/Users/thomas/Documents/randomcode/anicat"
    missing = scan(start_dir)
    if missing:
        print("Files possibly missing 'Any' import:")
        for m in missing:
            print(f"  {m}")
    else:
        print("No files missing 'Any' import found.")
