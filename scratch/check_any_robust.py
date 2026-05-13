import os
import re

def check_files(directory):
    for root, dirs, files in os.walk(directory):
        if "__pycache__" in root or ".venv" in root or ".git" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    has_any = False
                    imports_any = False
                    
                    for line in lines:
                        # Skip comments
                        if line.strip().startswith("#"):
                            continue
                            
                        # Check for Any usage
                        if re.search(r"\bAny\b", line):
                            # Check if it's an import line
                            if "from typing import" in line or "import typing" in line:
                                if "Any" in line:
                                    imports_any = True
                            else:
                                # It's a usage (not an import)
                                has_any = True
                    
                    if has_any and not imports_any:
                        # Check if it might be a multi-line import or imported differently
                        content = "".join(lines)
                        if not re.search(r"from typing import.*Any", content, re.DOTALL) and not "import typing" in content:
                            print(f"MISSING IMPORT: {path}")
                            
                except Exception as e:
                    print(f"Error reading {path}: {e}")

check_files("/Users/thomas/Documents/randomcode/anicat/anicat_media")
