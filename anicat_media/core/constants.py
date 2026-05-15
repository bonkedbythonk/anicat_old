import os
import sys
from importlib import metadata, resources
from pathlib import Path

PLATFORM = sys.platform
CLI_NAME = "ANICAT"
CLI_NAME_LOWER = "anicat"
PROJECT_NAME = "anicat_media"
APP_NAME = os.environ.get(f"{CLI_NAME}_APP_NAME", CLI_NAME_LOWER)

USER_NAME = os.environ.get("USERNAME", os.environ.get("USER", "User"))


try:
    __version__ = metadata.version("anicat")
except Exception:
    try:
        # Fallback for standalone/dev builds
        project_root = Path(__file__).resolve().parent.parent.parent
        version_file = project_root / "version.txt"
        if version_file.exists():
            content = version_file.read_text().split('\n')[0]
            # Extract "1.2.5" from "# Version 1.2.5 - ..."
            import re
            match = re.search(r"(\d+\.\d+\.\d+)", content)
            if match:
                __version__ = match.group(1)
            else:
                __version__ = "3.4.5"
        else:
            __version__ = "3.4.5"
    except Exception:
        __version__ = "3.4.5"

VERSION = __version__

AUTHOR = "bonkedbythonk"
GIT_REPO = "github.com"
GIT_PROTOCOL = "https://"
REPO_HOME = f"https://{GIT_REPO}/{AUTHOR}/anicat"

DISCORD_INVITE = "https://discord.gg/C4rhMA4mmK"

ANILIST_AUTH = (
    "https://anilist.co/api/v2/oauth/authorize?client_id=20148&response_type=token"
)

try:
    APP_DIR = Path(str(resources.files(PROJECT_NAME.lower())))

except ModuleNotFoundError:
    from pathlib import Path

    APP_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = APP_DIR / "assets"
DEFAULTS_DIR = ASSETS_DIR / "defaults"
SCRIPTS_DIR = ASSETS_DIR / "scripts"
GRAPHQL_DIR = ASSETS_DIR / "graphql"
ICONS_DIR = ASSETS_DIR / "icons"

ICON_PATH = ICONS_DIR / ("logo.ico" if PLATFORM == "Win32" else "logo.png")
APP_ASCII_ART = r""" /\_/\
( o.o )
 > ^ <  [ a n i c a t ]
"""

try:
    import click

    APP_DATA_DIR = Path(click.get_app_dir(APP_NAME, roaming=False))
except ModuleNotFoundError:
    if PLATFORM == "win32":
        folder = os.environ.get("LOCALAPPDATA")
        if folder is None:
            folder = Path.home()
        APP_DATA_DIR = Path(folder) / APP_NAME
    if PLATFORM == "darwin":
        APP_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        APP_DATA_DIR = (
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
        )

if PLATFORM == "win32":
    APP_CACHE_DIR = APP_DATA_DIR / "cache"
    USER_VIDEOS_DIR = Path.home() / "Videos" / APP_NAME

elif PLATFORM == "darwin":
    APP_CACHE_DIR = Path.home() / "Library" / "Caches" / APP_NAME
    USER_VIDEOS_DIR = Path.home() / "Movies" / APP_NAME

else:
    xdg_cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    APP_CACHE_DIR = xdg_cache_home / APP_NAME

    xdg_videos_dir = Path(os.environ.get("XDG_VIDEOS_DIR", Path.home() / "Videos"))
    USER_VIDEOS_DIR = xdg_videos_dir / APP_NAME

USER_APPLICATIONS = Path.home() / ".local" / "share" / "applications"
LOG_FOLDER = APP_CACHE_DIR / "logs"

# USER_APPLICATIONS.mkdir(parents=True,exist_ok=True)
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
APP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOG_FOLDER.mkdir(parents=True, exist_ok=True)
USER_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

USER_CONFIG = APP_DATA_DIR / "config.toml"

LOG_FILE = LOG_FOLDER / "app.log"
SUPPORT_PROJECT_URL = "https://github.com/bonkedbythonk/anicat"
UPDATE_STATUS_FILE = APP_CACHE_DIR / ".update_status"
LAST_COMMIT_FILE = APP_CACHE_DIR / ".last_commit"
