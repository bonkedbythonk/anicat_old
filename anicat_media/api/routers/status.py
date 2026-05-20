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


class UpdateTriggerRequest(BaseModel):
    branch: Optional[str] = None


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

from ..deps import get_ctx

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
    provider_status: Optional[str] = None

# Module-level storage for last playback event
_last_playback: Optional[PlaybackInfo] = None
_playback_expiry: Optional[datetime] = None

# Update check cache
_last_update_check: Optional[datetime] = None
_cached_update_available: bool = False


def _normalize_version(value: str) -> str:
    return value.strip().removeprefix("v").removeprefix("V")


def _version_tag_matches(candidate: str, expected: str) -> bool:
    return _normalize_version(candidate).lower() == _normalize_version(expected).lower()


def _current_version_tag() -> str:
    return f"v{_normalize_version(VERSION)}"


def _check_github_update(update_branch: str) -> bool:
    """Helper to check if an update is available from GitHub Releases, respecting the branch."""
    import urllib.request
    import json
    import ssl
    from anicat_media.core.constants import LAST_COMMIT_FILE

    try:
        ctx_ssl = ssl._create_unverified_context()
        if update_branch == "nightly":
            url = "https://api.github.com/repos/bonkedbythonk/anicat/releases"
        else:
            url = "https://api.github.com/repos/bonkedbythonk/anicat/releases/latest"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Anicat-App"}
        )
        with urllib.request.urlopen(req, timeout=5, context=ctx_ssl) as response:
            res_data = json.loads(response.read().decode())
            if isinstance(res_data, list):
                latest_tag = res_data[0].get("tag_name", "") if res_data else ""
            else:
                latest_tag = res_data.get("tag_name", "")

        if not latest_tag:
            return False

        if update_branch == "nightly" and latest_tag.lower() == "nightly":
            # For nightly, query commit hash to be precise
            remote_sha = ""
            try:
                commit_url = "https://api.github.com/repos/bonkedbythonk/anicat/commits/testbranch"
                commit_req = urllib.request.Request(commit_url, headers={"User-Agent": "Anicat-App"})
                with urllib.request.urlopen(commit_req, timeout=5, context=ctx_ssl) as commit_resp:
                    commit_data = json.loads(commit_resp.read().decode())
                    remote_sha = commit_data.get("sha", "")
            except Exception:
                pass

            if remote_sha:
                local_sha = ""
                if LAST_COMMIT_FILE.exists():
                    try:
                        local_sha = LAST_COMMIT_FILE.read_text(encoding="utf-8").strip()
                    except Exception:
                        pass

                if not local_sha:
                    try:
                        LAST_COMMIT_FILE.write_text(remote_sha, encoding="utf-8")
                    except Exception:
                        pass
                    return False
                return local_sha != remote_sha

        # Stable or standard branch comparison
        current_version = _current_version_tag()
        return not _version_tag_matches(latest_tag, current_version)
    except Exception as e:
        logger.error(f"[UPDATE CHECK] GitHub Releases check failed: {str(e)}")
        return False

# Notifications/profile fetch cache to avoid rate limits
_last_notifications_check: Optional[datetime] = None
_cached_unread_notifications: int = 0

# AniList activity timestamp for cross-device sync detection
_last_anilist_activity: Optional[int] = None

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

    # Trigger Discord Rich Presence update in the background if enabled
    try:
        ctx = get_ctx()
        if ctx.config.general.discord:
            import asyncio
            from ...core.utils.discord_rpc import discord_rpc
            asyncio.create_task(discord_rpc.update_watching(
                title=media_title,
                episode=episode,
                media_id=media_id
            ))
    except Exception as e:
        logger.debug(f"Failed to schedule Discord RPC update: {e}")


def _clear_playback():
    """Clear in-memory playback state. Called on startup to reset stale state."""
    global _last_playback, _playback_expiry
    _last_playback = None
    _playback_expiry = None


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
                
                # Clear Discord RPC
                try:
                    from ...core.utils.discord_rpc import discord_rpc
                    await discord_rpc.clear()
                except Exception:
                    pass
    except Exception:
        # If process detection fails, be conservative and keep playback info
        pass

    if _last_playback and _playback_expiry and datetime.now() > _playback_expiry:
        _last_playback = None
        _playback_expiry = None
        try:
            from ...core.utils.discord_rpc import discord_rpc
            await discord_rpc.clear()
        except Exception:
            pass
            
    return _last_playback

@router.delete("/playback")
async def clear_playback():
    """Clear the current playback status (e.g., after marking watched)."""
    global _last_playback, _playback_expiry
    _last_playback = None
    _playback_expiry = None
    
    # Clear Discord RPC
    try:
        from ...core.utils.discord_rpc import discord_rpc
        await discord_rpc.clear()
    except Exception:
        pass
        
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
                try:
                    loader = ConfigLoader()
                    current_config = loader.load(allow_setup=False)
                    update_branch = getattr(current_config.general, "update_branch", "stable")
                except Exception:
                    update_branch = "stable"

                if os.path.exists(os.path.join(repo_root, ".git")):
                    from anicat_media.utils.subprocess import run_cmd
                    rc, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=2, cwd=repo_root)
                    current_branch = stdout.strip() if (rc == 0 and stdout) else "main"
                    
                    if update_branch == "nightly":
                        target_branch = "testbranch"
                    else:
                        target_branch = "main"

                    try:
                        run_cmd(["git", "fetch", "origin", target_branch, "--quiet"], timeout=8, cwd=repo_root)
                        rc, stdout, _ = run_cmd(["git", "rev-list", "--count", f"HEAD..origin/{target_branch}"], timeout=5, cwd=repo_root)
                        if rc == 0 and stdout:
                            count = int(stdout.strip())
                            if count > 0:
                                _cached_update_available = True
                    except Exception:
                        pass
                else:
                    _cached_update_available = _check_github_update(update_branch)
            except Exception:
                pass

        # Auto-check for updates every hour in the background (fire-and-forget)
        if not _last_update_check or (datetime.now() - _last_update_check) > timedelta(hours=1):
            try:
                if os.path.exists(os.path.join(repo_root, ".git")):
                    subprocess.Popen(["git", "fetch", "--quiet"], cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _last_update_check = datetime.now()
            except Exception:
                pass

        update_available = _cached_update_available

        # Get unread notification count (cached to avoid hitting rate limits)
        global _last_notifications_check, _cached_unread_notifications
        unread_notifications = _cached_unread_notifications
        
        # Refresh token status from config to ensure we aren't using stale memory
        loader = ConfigLoader()
        current_config = loader.load(allow_setup=False)
        api_authenticated = bool(current_config.anilist.token and len(current_config.anilist.token) > 10)
        
        api_connected = ctx.media_api.is_connected()
        
        # Perform the actual AniList query only once every 5 minutes (always fetch in tests)
        is_testing = "pytest" in sys.modules
        if is_testing or not _last_notifications_check or now - _last_notifications_check > timedelta(minutes=5):
            _last_notifications_check = now
            try:
                profile = ctx.media_api.get_viewer_profile()
                if profile:
                    api_connected = True
                    ctx.is_offline = False
                    if hasattr(profile, 'unread_notifications'):
                        _cached_unread_notifications = getattr(profile, 'unread_notifications') or 0
                        unread_notifications = _cached_unread_notifications
                    # Detect external AniList changes by checking the last activity timestamp.
                    # If AniList has newer activity than our last known state, bump data_version
                    # so the frontend re-fetches all views.
                    last_activity = getattr(profile, 'updated_at', None)
                    if last_activity is not None:
                        anilist_unix = int(last_activity)
                        global _last_anilist_activity
                        if _last_anilist_activity is not None and anilist_unix > _last_anilist_activity:
                            ctx.data_version += 1
                        _last_anilist_activity = anilist_unix
            except Exception:
                pass

        # Report provider status so the frontend can show a meaningful message
        provider_status: Optional[str] = None
        try:
            provider = ctx.provider if ctx._provider is not None else None
            if provider and hasattr(provider, 'status_message'):
                provider_status = provider.status_message
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
            current_version=VERSION,
            provider_status=provider_status,
        )
    except Exception:
        return HealthInfo(
            api_connected=False,
            api_authenticated=False,
            worker_running=False,
            is_offline=True,
            update_available=False,
            current_version="unknown",
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
        update_branch = getattr(current_config.general, "update_branch", "stable")
    except Exception:
        # If config can't be read, fall back to env-only opt-out
        update_branch = "stable"

    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if os.path.exists(os.path.join(repo_root, ".git")):
            from anicat_media.utils.subprocess import run_cmd
            rc, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5, cwd=repo_root)
            current_branch = stdout.strip() if (rc == 0 and stdout) else "main"
            
            if update_branch == "nightly":
                target_branch = "testbranch"
            else:
                target_branch = "main"

            run_cmd(["git", "fetch", "origin", target_branch, "--quiet"], timeout=10, cwd=repo_root)
            rc, stdout, _ = run_cmd(["git", "rev-list", "--count", f"HEAD..origin/{target_branch}"], timeout=8, cwd=repo_root)
            _last_update_check = datetime.now()
            if rc == 0 and stdout:
                count = int(stdout.strip())
                if count > 0:
                    _cached_update_available = True
                    return {"status": "success", "update_available": True, "message": f"A new version of Anicat is available on {target_branch}!"}
            _cached_update_available = False
            return {"status": "success", "update_available": False, "message": f"You are running the latest version of the {target_branch} branch."}
        else:
            _last_update_check = datetime.now()
            has_update = _check_github_update(update_branch)
            _cached_update_available = has_update
            if has_update:
                return {"status": "success", "update_available": True, "message": f"A new version is available on the {update_branch} branch!"}
            return {"status": "success", "update_available": False, "message": f"You are running the latest version of the {update_branch} branch."}
    except Exception as e:
        logger.error(f"[UPDATE CHECK] Error: {str(e)}")
        return {"status": "error", "update_available": False, "message": f"Failed to check for updates: {str(e)}"}

@router.post("/update")
async def trigger_update(req: Optional[UpdateTriggerRequest] = None):
    """Trigger the official installation script to update the application."""
    global _last_update_check, _cached_update_available
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
            update_branch = getattr(current_config.general, "update_branch", "stable")
        except Exception:
            # If config can't be read, continue with env-only check
            update_branch = "stable"

        if req and req.branch in ("stable", "nightly"):
            update_branch = req.branch

        # For macOS, the most reliable way to update the native app is via the installer script
        # which downloads the latest release and replaces the binary.
        import platform
        if platform.system() == "Darwin":
            logger.info("[UPDATE] Triggering macOS native update via installer script")
            # If we are running in local dev and the local installer script exists, run it directly!
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            local_script = os.path.join(repo_root, "scripts", "install_macos.sh")
            
            branch_name = "testbranch" if update_branch == "nightly" else "main"
            
            if os.path.exists(local_script):
                logger.info(f"[UPDATE] Running local installer script: {local_script}")
                subprocess.Popen(
                    ["bash", local_script],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(
                    f"curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/{branch_name}/scripts/install_macos.sh | bash",
                    shell=True,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            _last_update_check = datetime.now()
            _cached_update_available = False
            return {"status": "success", "message": "Native update triggered! The application will download the latest version and restart shortly. Please wait a few moments."}

        # Fallback for dev/git-based installations
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if os.path.exists(os.path.join(repo_root, ".git")):
            from anicat_media.utils.subprocess import run_cmd
            rc, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5, cwd=repo_root)
            current_branch = stdout.strip() if (rc == 0 and stdout) else "main"
            
            if update_branch == "nightly":
                target_branch = "testbranch"
            else:
                target_branch = "main"

            subprocess.run(["git", "stash"], cwd=repo_root, capture_output=True)
            if current_branch != target_branch:
                subprocess.run(["git", "checkout", target_branch], cwd=repo_root, capture_output=True)
            result = subprocess.run(["git", "pull", "origin", target_branch], cwd=repo_root, capture_output=True, text=True, timeout=60)
            subprocess.run(["git", "stash", "pop"], cwd=repo_root, capture_output=True)
            
            if result.returncode == 0:
                install_script = os.path.join(repo_root, "scripts", "install.sh")
                if os.path.exists(install_script):
                    subprocess.Popen(["bash", install_script, "--no-launch"], cwd=repo_root, start_new_session=True)
                    _last_update_check = datetime.now()
                    _cached_update_available = False
                    return {"status": "success", "message": f"Update in progress (Git branch {target_branch}). Rebuilding frontend..."}
                _last_update_check = datetime.now()
                _cached_update_available = False
                return {"status": "success", "message": f"Updated successfully (Git branch {target_branch} code only)."}
        
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
