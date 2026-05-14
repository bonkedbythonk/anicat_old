import os
import re

def check_missing_any_imports(directory):
    missing_files = []
    # Pattern to find Any usage (not as part of a word, and not in strings/comments roughly)
    any_usage_pattern = re.compile(r'(?<!\w)Any(?!\w)')
    # Patterns for imports
    import_patterns = [
        re.compile(r'from typing import.*Any'),
        re.compile(r'import typing'),
    ]

    for root, _, files in os.walk(directory):
        if '__pycache__' in root or '.git' in root or '.gemini' in root or '.venv' in root:
            continue
        for file in files:
            if not file.endswith('.py'):
                continue
            
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if Any is used
                if any_usage_pattern.search(content):
                    # Check if Any is imported
                    is_imported = any(p.search(content) for p in import_patterns)
                    
                    if not is_imported:
                        # Double check if it's used as typing.Any
                        if 'typing.Any' not in content:
                            missing_files.append(path)
            except Exception as e:
                print(f"Error reading {path}: {e}")
                
    return missing_files

if __name__ == "__main__":
    workspace = "/Users/thomas/Documents/randomcode/anicat"
    missing = check_missing_any_imports(workspace)
    if missing:
        print("Files using 'Any' without explicit import:")
        for m in missing:
            print(m)
    else:
        print("No files found with missing 'Any' imports in anicat_media.")
