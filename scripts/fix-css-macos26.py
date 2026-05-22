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
    # Remove translateZ(0) GPU compositing hack — standalone or combined
    css = re.sub(r"\btranslateZ\(0\)\s*", "", css)

    # Remove will-change declarations
    css = re.sub(r"will-change:\s*[^;}\"]+[;\"]?", "", css)

    # Remove backface-visibility declarations
    css = re.sub(r"-?backface-visibility:\s*[^;}\"]+[;\"]?", "", css)

    # Remove backdrop-filter — #1 WKWebView crash trigger on macOS 26
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
