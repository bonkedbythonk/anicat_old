import os
import re
import shutil
import sys


def is_running_in_termux():
    # Check environment variables
    if os.environ.get("TERMUX_VERSION") is not None:
        return True

    # Check Python installation path
    if sys.prefix.startswith("/data/data/com.termux/files/usr"):
        return True

    # Check for Termux-specific binary
    if os.path.exists("/data/data/com.termux/files/usr/bin/termux-info"):
        return True

    return False


def is_bash_script(text: str) -> bool:
    # Normalize line endings
    text = text.strip()

    # Check for shebang at the top
    if text.startswith("#!/bin/bash") or text.startswith("#!/usr/bin/env bash"):
        return True

    # Look for common bash syntax/keywords
    bash_keywords = [
        r"\becho\b",
        r"\bfi\b",
        r"\bthen\b",
        r"\bfunction\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bdone\b",
        r"\bcase\b",
        r"\besac\b",
        r"\$\(",
        r"\[\[",
        r"\]\]",
        r";;",
    ]

    # Score based on matches
    matches = sum(bool(re.search(pattern, text)) for pattern in bash_keywords)
    return matches >= 2


def is_running_kitty_terminal() -> bool:
    return True if os.environ.get("KITTY_WINDOW_ID") else False


def has_fzf() -> bool:
    return True if shutil.which("fzf") else False


def is_frozen() -> bool:
    """Check if running as a PyInstaller frozen executable."""
    return getattr(sys, "frozen", False)


def get_python_executable() -> str:
    """
    Get the Python executable path.
    
    In frozen (PyInstaller) apps, sys.executable points to the .exe,
    so we need to find the system Python instead.
    
    Returns:
        Path to a Python executable.
    """
    if is_frozen():
        # We're in a frozen app - find system Python
        for python_name in ["python3", "python", "py"]:
            python_path = shutil.which(python_name)
            if python_path:
                return python_path
        # Fallback - this likely won't work but is the best we can do
        return "python"
    else:
        return sys.executable


def get_clean_env() -> dict[str, str]:
    """
    Returns a copy of the environment with LD_LIBRARY_PATH fixed for system subprocesses
    when running as a PyInstaller frozen application.
    Also ensures common macOS paths are present for non-terminal launches.
    """
    env = os.environ.copy()
    
    # 1. Fix library paths for frozen apps
    if is_frozen():
        for var in ["LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FALLBACK_FRAMEWORK_PATH"]:
            orig_var = f"{var}_ORIG"
            if orig_var in env:
                env[var] = env[orig_var]
            else:
                env.pop(var, None)

    # 2. Inject common paths for macOS GUI launches
    if sys.platform == "darwin":
        path = env.get("PATH", "")
        extra_paths = [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
            os.path.expanduser("~/.local/bin")
        ]
        current_paths = path.split(os.pathsep)
        for p in extra_paths:
            if p not in current_paths:
                current_paths.append(p)
        env["PATH"] = os.pathsep.join(current_paths)
        
    return env