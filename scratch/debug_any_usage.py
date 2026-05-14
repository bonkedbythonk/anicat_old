import os
from pathlib import Path
import re

def check_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    has_any = False
    for i, line in enumerate(lines):
        if re.search(r'\bAny\b', line):
            has_any = True
            break
            
    if not has_any:
        return
        
    # Check if Any is imported
    imported = False
    for line in lines:
        if re.search(r'from typing import .*?\bAny\b', line):
            imported = True
            break
        if re.search(r'import typing\b', line):
            imported = True
            break
            
    if not imported:
        print(f"FILE: {path}")
        for i, line in enumerate(lines):
            if re.search(r'\bAny\b', line):
                print(f"  {i+1}: {line.strip()}")

def scan(start_dir):
    for root, dirs, files in os.walk(start_dir):
        if any(x in root for x in [".git", "__pycache__", ".venv", "scratch"]):
            continue
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                check_file(path)

if __name__ == "__main__":
    start_dir = "/Users/thomas/Documents/randomcode/anicat/anicat_media"
    scan(start_dir)
