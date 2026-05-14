import os
import re

def check_any_imports(directory):
    any_usage_pattern = re.compile(r'\bAny\b')
    any_import_pattern = re.compile(r'from typing import .*Any')
    
    issues = []
    
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        if any_usage_pattern.search(content):
                            if not any_import_pattern.search(content):
                                issues.append(path)
                except Exception as e:
                    print(f"Error reading {path}: {e}")
                    
    return issues

if __name__ == "__main__":
    project_dir = "/Users/thomas/Documents/randomcode/anicat/anicat_media"
    missing_imports = check_any_imports(project_dir)
    
    if missing_imports:
        print("Modules missing 'Any' import but using it:")
        for m in missing_imports:
            print(m)
    else:
        print("No modules found missing 'Any' import.")
