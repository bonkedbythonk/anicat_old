import os
from pathlib import Path

def check_any_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    has_any = False
    has_any_import = False
    
    for i, line in enumerate(lines):
        # Ignore comments
        if "#" in line:
            line = line.split("#")[0]
        
        # Check for Any as a word (not part of another word like 'Many')
        import re
        if re.search(r"\bAny\b", line):
            # Check if it's an import
            if "import" in line and "Any" in line:
                has_any_import = True
            else:
                has_any = True
                # print(f"Found Any on line {i+1} in {file_path}: {line.strip()}")
    
    return has_any and not has_any_import

def scan_directory(start_path):
    files_with_missing_any = []
    for root, dirs, files in os.walk(start_path):
        # Skip some directories
        if ".git" in root or "__pycache__" in root or ".venv" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                if check_any_in_file(file_path):
                    files_with_missing_any.append(file_path)
    
    return files_with_missing_any

if __name__ == "__main__":
    start_dir = "/Users/thomas/Documents/randomcode/anicat/anicat_media"
    missing = scan_directory(start_dir)
    if missing:
        print("Files with Any but no Any import:")
        for m in missing:
            print(m)
    else:
        print("No files found with Any but no Any import.")
