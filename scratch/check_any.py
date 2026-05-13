import os
import re

def check_files(directory):
    for root, dirs, files in os.walk(directory):
        if ".venv" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Any" in content:
                        if "from typing import" not in content and "import typing" not in content:
                            # Check if Any is used as a word
                            if re.search(r"\bAny\b", content):
                                print(f"File missing import: {path}")
                        elif "from typing import" in content:
                            # Check if Any is specifically in the import
                            if "Any" not in re.search(r"from typing import (.*)", content).group(1):
                                if re.search(r"\bAny\b", content):
                                     # This check is a bit naive if there are multiple typing imports
                                     print(f"File might be missing Any in typing import: {path}")

check_files("/Users/thomas/Documents/randomcode/anicat/anicat_media")
