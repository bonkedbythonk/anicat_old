from anicat_media.cli.cli import cli
import sys

if __name__ == "__main__":
    try:
        cli()
    except SystemExit:
        pass
