from datetime import datetime, timedelta
from typing import Optional
import logging
import os
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
from anicat_media.core.constants import VERSION
from anicat_media.cli.config import ConfigLoader

logger = logging.getLogger(__name__)

router = APIRouter()

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
        # Check if any mpv process is running
        subprocess.check_output(["pgrep", "mpv"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        # MPV not running, check if we should clear
        if _last_playback:
             _last_playback = None
             _playback_expiry = None
    
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
        if _last_update_check is None or now - _last_update_check > timedelta(minutes=15):
            _last_update_check = now
            _cached_update_available = False
            try:
                # Check if we are behind origin/main
                # We use --quiet to avoid spamming logs
                subprocess.run(["git", "fetch", "--quiet"], capture_output=True, timeout=5)
                status = subprocess.check_output(["git", "status", "-uno"], encoding="utf-8")
                if "Your branch is behind" in status:
                    _cached_update_available = True
            except Exception:
                pass
        
        # Auto-check for updates every hour in the background
        if not _last_update_check or (datetime.now() - _last_update_check) > timedelta(hours=1):
            # Run a quiet fetch in the background
            try:
                repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                subprocess.Popen(["git", "fetch", "--quiet"], cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # We don't wait for it here to keep the health check fast, 
                # but we'll see the results in the NEXT health check.
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
    
    _last_update_check = datetime.now()
    _cached_update_available = False
    try:
        # Get the root of the repository
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Run fetch and status with explicit CWD
        subprocess.run(["git", "fetch", "--quiet"], capture_output=True, timeout=10, cwd=repo_root)
        status = subprocess.check_output(["git", "status", "-uno"], encoding="utf-8", cwd=repo_root)
        
        if "Your branch is behind" in status:
            _cached_update_available = True
            return {"status": "success", "update_available": True, "message": "A new version of Anicat is available!"}
        return {"status": "success", "update_available": False, "message": "You are running the latest version."}
    except Exception as e:
        logger.error(f"[UPDATE CHECK] Error: {str(e)}")
        return {"status": "error", "update_available": False, "message": f"Failed to check for updates: {str(e)}"}

@router.post("/update")
async def trigger_update():
    """Trigger the official installation script to update the application."""
    try:
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
