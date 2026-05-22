#!/usr/bin/env python3
"""Post-build CSS fix for macOS 26 WKWebView compatibility.

Tailwind v4 emits GPU-hint properties (translateZ, will-change,
backface-visibility) that crash WKWebView on macOS 26.

This script strips the offending rules from the compiled CSS output.
Run AFTER `next build`.
"""
import re
import sys
from pathlib import Path

OUT_DIR = Path.cwd() / "out"
if not OUT_DIR.is_dir():
    OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "out"


def strip_css(css: str) -> str:
    # Remove @property CSS Houdini rules
    css = re.sub(r"@property\s+--[\w-]+\s*\{[^}]*\}", "", css)

    # Remove @supports blocks correctly using a brace-counting parser
    # specifically for @supports (color:color-mix(...)
    pattern = "@supports (color:color-mix"
    while True:
        idx = css.find(pattern)
        if idx == -1:
            # Maybe it doesn't have a space
            idx = css.find("@supports(color:color-mix")
            if idx == -1:
                break
        
        # Find the opening brace of this @supports block
        open_idx = css.find("{", idx)
        if open_idx == -1:
            break
            
        # Find the matching closing brace
        depth = 1
        close_idx = -1
        for i in range(open_idx + 1, len(css)):
            if css[i] == '{':
                depth += 1
            elif css[i] == '}':
                depth -= 1
                if depth == 0:
                    close_idx = i
                    break
                    
        if close_idx != -1:
            # Remove the entire block
            css = css[:idx] + css[close_idx + 1:]
        else:
            break

    # Remove translateZ(0) GPU compositing hack
    css = re.sub(r"\btranslateZ\(0\)\s*", "", css)

    # Remove will-change declarations
    css = re.sub(r"will-change:\s*[^;}\"]+[;\"]?", "", css)

    # Remove backface-visibility declarations
    css = re.sub(r"-?backface-visibility:\s*[^;}\"]+[;\"]?", "", css)

    # Remove backdrop-filter
    css = re.sub(r"-webkit-backdrop-filter:\s*[^;}\"]+[;\"]?", "", css)
    css = re.sub(r"backdrop-filter:\s*[^;}\"]+[;\"]?", "", css)

    return css


def main():
    css_files = list(OUT_DIR.glob("_next/static/chunks/*.css"))
    if not css_files:
        print("[postbuild-css-fix] No CSS files found")
        sys.exit(0)

    for css_file in css_files:
        original = css_file.read_text()
        stripped = strip_css(original)
        if stripped != original:
            css_file.write_text(stripped)
            removed = len(original) - len(stripped)
            print(f"[postbuild-css-fix] Stripped {removed} bytes from {css_file.name}")
        else:
            print(f"[postbuild-css-fix] {css_file.name} already clean")

    print("[postbuild-css-fix] Done.")


if __name__ == "__main__":
    main()
