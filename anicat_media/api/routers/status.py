from datetime import datetime
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

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
    worker_running: bool
    is_offline: bool
    update_available: bool = False
    unread_notifications: int = 0
    current_version: str = "unknown"

# Module-level storage for last playback event
_last_playback: Optional[PlaybackInfo] = None
_playback_expiry: Optional[datetime] = None

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
    from datetime import timedelta
    _playback_expiry = datetime.now() + timedelta(hours=2)

@router.get("/playback", response_model=Optional[PlaybackInfo])
async def get_playback_status():
    """Get the current/last playback status."""
    global _last_playback, _playback_expiry
    
    # Auto-dismiss if MPV is no longer running
    import subprocess
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
        update_available = False
        import subprocess
        current_version = VERSION
        try:
            # Check if we are behind origin/main
            # We use --quiet to avoid spamming logs
            fetch_res = subprocess.run(["git", "fetch", "--quiet"], capture_output=True, timeout=10)
            if fetch_res.returncode == 0:
                status = subprocess.check_output(["git", "status", "-uno"], encoding="utf-8")
                if "Your branch is behind" in status:
                    update_available = True
        except Exception as e:
            # logger.debug(f"Update check failed: {e}")
            pass

        # Get unread notification count
        unread_notifications = 0
        try:
            notifications = ctx.media_api.get_notifications()
            unread_notifications = len(notifications) if notifications else 0
        except Exception:
            pass

        return HealthInfo(
            api_connected=ctx.media_api.is_authenticated(),
            worker_running=ctx._download is not None,
            is_offline=ctx.is_offline,
            update_available=update_available,
            unread_notifications=unread_notifications,
            current_version=current_version
        )
    except Exception:
        return HealthInfo(
            api_connected=False,
            worker_running=False,
            is_offline=True,
            update_available=False,
            current_version="unknown"
        )

@router.post("/update")
async def trigger_update():
    """Trigger a git pull to update the application."""
    import subprocess
    import os
    try:
        # Get the root of the repository
        # This file is at: anicat_media/api/routers/status.py
        # Root is 4 levels up
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # 1. Run git pull in the repo root
        result = subprocess.run(
            ["git", "pull"], 
            capture_output=True, 
            text=True, 
            timeout=60,
            cwd=repo_root
        )
        
        if result.returncode != 0:
            err_msg = result.stderr or result.stdout
            return {"status": "error", "message": f"Update failed: {err_msg}"}
            
        if "Already up to date." in result.stdout:
            return {"status": "success", "message": "✨ You are already on the latest version."}
        
        # 2. Try to run uv sync if uv is available
        try:
            subprocess.run(["uv", "sync"], capture_output=True, timeout=120, cwd=repo_root)
        except Exception:
            pass # Non-critical if uv is missing
            
        return {"status": "success", "message": "🚀 Updated successfully! Please restart the Anicat server to apply changes."}
        
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "⏳ Update timed out. Please check your internet connection or run 'git pull' manually."}
    except Exception as e:
        return {"status": "error", "message": f"❌ Unexpected error during update: {str(e)}"}
