import sys

# Reconfigure stdout and stderr on Windows to UTF-8 to prevent any potential Unicode encoding issues
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

if sys.version_info < (3, 11):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python 3.11 or newer is supported by Anicat"
    )


def Cli():
    from .cli import run_cli

    run_cli()
