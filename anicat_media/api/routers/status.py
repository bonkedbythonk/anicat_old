from datetime import datetime, timedelta
from typing import Optional
import logging
import os
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
from anicat_media.core.constants import VERSION, LOG_FILE
from anicat_media.cli.config import ConfigLoader
import shutil
import sys

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/logs")
async def get_logs(lines: int = 100):
    """Retrieve the last N lines from the log file."""
    if not os.path.exists(LOG_FILE):
        return {"logs": "Log file not found."}
    
    try:
        # Efficient tail implementation that avoids loading entire file into memory
        def tail(path, n=100, buf_size=1024):
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                if file_size == 0:
                    return ""
                blocks = []
                bytes_scanned = 0
                # Read backwards in chunks until we have enough lines or reach file start
                while bytes_scanned < file_size:
                    read_size = min(buf_size, file_size - bytes_scanned)
                    f.seek(max(0, file_size - bytes_scanned - read_size))
                    chunk = f.read(read_size)
                    blocks.insert(0, chunk)
                    bytes_scanned += read_size
                    data = b"".join(blocks)
                    lines_list = data.splitlines()
                    if len(lines_list) >= n:
                        return b"\n".join(lines_list[-n:]).decode("utf-8", errors="replace")
                # If we get here, return what we have
                data = b"".join(blocks)
                lines_list = data.splitlines()
                return b"\n".join(lines_list[-n:]).decode("utf-8", errors="replace")

        return {"logs": tail(LOG_FILE, lines)}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}

def get_ctx():
    from ..main import ctx
    return ctx

class PlaybackInfo(BaseModel):
    media_id: int
    media_title: str
    episode: str
    started_at: str

class HealthInfo(BaseModel):
    api_connected: bool
    api_authenticated: bool
    worker_running: bool
    is_offline: bool
    update_available: bool = False
    unread_notifications: int = 0
    data_version: int = 0
    current_version: str = "unknown"

# Module-level storage for last playback event
_last_playback: Optional[PlaybackInfo] = None
_playback_expiry: Optional[datetime] = None

# Update check cache
_last_update_check: Optional[datetime] = None
_cached_update_available: bool = False

def set_playback(media_id: int, media_title: str, episode: str):
    """Called by the actions router when playback starts."""
    global _last_playback, _playback_expiry
    _last_playback = PlaybackInfo(
        media_id=media_id,
        media_title=media_title,
        episode=episode,
        started_at=datetime.now().isoformat(),
    )
    # Auto-expire after 2 hours
    _playback_expiry = datetime.now() + timedelta(hours=2)

@router.get("/playback", response_model=Optional[PlaybackInfo])
async def get_playback_status():
    """Get the current/last playback status."""
    global _last_playback, _playback_expiry
    # Auto-dismiss if MPV is no longer running
    try:
        # Determine if MPV is currently running in a platform-safe manner
        mpv_running = True
        if sys.platform.startswith("win"):
            try:
                out = subprocess.check_output(["tasklist"], encoding="utf-8")
                if "mpv.exe" not in out:
                    mpv_running = False
            except Exception:
                # Be conservative if we can't determine
                mpv_running = True
        else:
            # Prefer pgrep when available to avoid heavy process listings
            if shutil.which("pgrep"):
                try:
                    subprocess.check_output(["pgrep", "mpv"])  # raises CalledProcessError if none
                except subprocess.CalledProcessError:
                    mpv_running = False
                except Exception:
                    mpv_running = True
            else:
                # pgrep not available (e.g., minimal containers) — don't auto-clear
                mpv_running = True

        if not mpv_running:
            if _last_playback:
                _last_playback = None
                _playback_expiry = None
    except Exception:
        # If process detection fails, be conservative and keep playback info
        pass

    if _last_playback and _playback_expiry and datetime.now() > _playback_expiry:
        _last_playback = None
        _playback_expiry = None
    return _last_playback

@router.delete("/playback")
async def clear_playback():
    """Clear the current playback status (e.g., after marking watched)."""
    global _last_playback, _playback_expiry
    _last_playback = None
    _playback_expiry = None
    return {"status": "cleared"}

@router.get("/health", response_model=HealthInfo)
async def get_health():
    """Get system health status."""
    try:
        ctx = get_ctx()
        # Check for updates (cached logic)
        global _last_update_check, _cached_update_available

        now = datetime.now()
        # Determine repository root once
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        if _last_update_check is None or now - _last_update_check > timedelta(minutes=15):
            _last_update_check = now
            _cached_update_available = False
            try:
                # Check if we are behind origin/main using a safer wrapper
                from anicat_media.utils.subprocess import run_cmd
                rc, _, _ = run_cmd(["git", "fetch", "--quiet"], timeout=8, cwd=repo_root)
                rc, stdout, _ = run_cmd(["git", "status", "-uno"], timeout=5, cwd=repo_root)
                if stdout and "behind" in stdout:
                    _cached_update_available = True
            except Exception:
                pass

        # Auto-check for updates every hour in the background (fire-and-forget)
        if not _last_update_check or (datetime.now() - _last_update_check) > timedelta(hours=1):
            try:
                subprocess.Popen(["git", "fetch", "--quiet"], cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _last_update_check = datetime.now()
            except Exception:
                pass

        update_available = _cached_update_available

        # Get unread notification count
        unread_notifications = 0
        try:
            profile = ctx.media_api.get_viewer_profile()
            if profile and hasattr(profile, 'unread_notifications'):
                unread_notifications = getattr(profile, 'unread_notifications') or 0
        except Exception:
            pass


        # Refresh token status from config to ensure we aren't using stale memory
        loader = ConfigLoader()
        current_config = loader.load(allow_setup=False)
        api_authenticated = bool(current_config.anilist.token and len(current_config.anilist.token) > 10)
        
        # The most accurate connection status is whether the media_api was able to fetch data
        api_connected = ctx.media_api.is_connected()
        
        # If not connected, but we have a token, let's try a quick verify to see if we can go online
        if not api_connected and api_authenticated:
            try:
                # This will trigger a lazy re-auth if _media_api is None
                profile = ctx.media_api.get_viewer_profile()
                if profile:
                    api_connected = True
                    ctx.is_offline = False
            except Exception:
                pass

        return HealthInfo(
            api_connected=api_connected,
            api_authenticated=api_authenticated,
            worker_running=ctx._download is not None,
            is_offline=ctx.is_offline,
            update_available=update_available,
            unread_notifications=unread_notifications,
            data_version=ctx.data_version,
            current_version=VERSION
        )
    except Exception:
        return HealthInfo(
            api_connected=False,
            api_authenticated=False,
            worker_running=False,
            is_offline=True,
            update_available=False,
            current_version="unknown"
        )

@router.post("/check-update")
async def check_for_updates():
    """Manually trigger an update check, ignoring cache."""
    global _last_update_check, _cached_update_available
    # Respect opt-out environment variable for automated update checks
    if os.environ.get("ANICAT_DISABLE_AUTO_UPDATE", "0") == "1":
        return {"status": "error", "update_available": False, "message": "Auto-updates disabled by environment"}

    # Respect user's config setting (allow disabling update checks via AppConfig)
    try:
        loader = ConfigLoader()
        current_config = loader.load(allow_setup=False)
        if not getattr(current_config.general, "check_for_updates", True):
            return {"status": "error", "update_available": False, "message": "Auto-updates disabled in configuration"}
    except Exception:
        # If config can't be read, fall back to env-only opt-out
        pass

    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from anicat_media.utils.subprocess import run_cmd

        run_cmd(["git", "fetch", "--quiet"], timeout=10, cwd=repo_root)
        rc, stdout, _ = run_cmd(["git", "status", "-uno"], timeout=8, cwd=repo_root)
        _last_update_check = datetime.now()
        if stdout and "behind" in stdout:
            _cached_update_available = True
            return {"status": "success", "update_available": True, "message": "A new version of Anicat is available!"}

        _cached_update_available = False
        return {"status": "success", "update_available": False, "message": "You are running the latest version."}
    except Exception as e:
        logger.error(f"[UPDATE CHECK] Error: {str(e)}")
        return {"status": "error", "update_available": False, "message": f"Failed to check for updates: {str(e)}"}

@router.post("/update")
async def trigger_update():
    """Trigger the official installation script to update the application."""
    try:
        # Respect opt-out environment variable for automated updates
        if os.environ.get("ANICAT_DISABLE_AUTO_UPDATE", "0") == "1":
            return {"status": "error", "message": "Auto-updates disabled by environment"}

        # Respect user's config setting (allow disabling update actions via AppConfig)
        try:
            loader = ConfigLoader()
            current_config = loader.load(allow_setup=False)
            if not getattr(current_config.general, "check_for_updates", True):
                return {"status": "error", "message": "Auto-updates disabled in configuration"}
        except Exception:
            # If config can't be read, continue with env-only check
            pass
        # For macOS, the most reliable way to update the native app is via the installer script
        # which downloads the latest release and replaces the binary.
        import platform
        if platform.system() == "Darwin":
            logger.info("[UPDATE] Triggering macOS native update via installer script")
            subprocess.Popen(
                "curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install_macos.sh | bash",
                shell=True,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {"status": "success", "message": "Native update triggered! The application will download the latest version and restart shortly. Please wait a few moments."}

        # Fallback for dev/git-based installations
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if os.path.exists(os.path.join(repo_root, ".git")):
            subprocess.run(["git", "stash"], cwd=repo_root, capture_output=True)
            result = subprocess.run(["git", "pull"], cwd=repo_root, capture_output=True, text=True, timeout=60)
            subprocess.run(["git", "stash", "pop"], cwd=repo_root, capture_output=True)
            
            if result.returncode == 0:
                install_script = os.path.join(repo_root, "scripts", "install.sh")
                if os.path.exists(install_script):
                    subprocess.Popen(["bash", install_script, "--no-launch"], cwd=repo_root, start_new_session=True)
                    return {"status": "success", "message": "Update in progress (Git). Rebuilding frontend..."}
                return {"status": "success", "message": "Updated successfully (Git code only)."}
        
        return {"status": "error", "message": "Could not determine update method for this platform."}
        
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Update timed out. Please try running 'git pull' manually in the terminal."}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

@router.post("/reconnect")
async def reconnect():
    """Force a reconnection attempt to the media API."""
    ctx = get_ctx()
    try:
        ctx.is_offline = False
        # Force a reset of _media_api to re-trigger auth with current config
        ctx._media_api = None
        
        # Accessing media_api property triggers initialization and authentication
        api = ctx.media_api
        
        # Attempt to fetch profile to verify real connectivity
        profile = api.get_viewer_profile()
        
        if profile:
            ctx.is_offline = False
            return {"status": "success", "message": f"Successfully reconnected! Welcome back, {profile.name}."}
        else:
            ctx.is_offline = True
            return {"status": "error", "message": "Reconnection failed: Token invalid or AniList unreachable."}
    except Exception as e:
        ctx.is_offline = True
        return {"status": "error", "message": f"Reconnection error: {str(e)}"}
