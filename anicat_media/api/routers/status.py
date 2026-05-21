from datetime import datetime, timedelta
from typing import Optional
import logging
import os
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
from anicat_media.core.constants import VERSION, COMMIT, LOG_FILE, UPDATE_IN_PROGRESS_FILE
from anicat_media.cli.config import ConfigLoader
import shutil
import sys

logger = logging.getLogger(__name__)


class UpdateTriggerRequest(BaseModel):
    branch: Optional[str] = None


class CheckUpdateResponse(BaseModel):
    status: str
    update_available: bool
    message: str
    version: str = ""
    release_notes: str = ""
    release_url: str = ""


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
    updating: bool = False
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
    # Strip leading "v"/"V" and any suffix after "-" (e.g. "v4.6.1-stable" -> "4.6.1")
    return value.strip().removeprefix("v").removeprefix("V").split("-")[0]


def _version_tag_matches(candidate: str, expected: str) -> bool:
    return _normalize_version(candidate).lower() == _normalize_version(expected).lower()


def _current_version_tag() -> str:
    return f"v{_normalize_version(VERSION)}"


def _check_github_update(update_branch: str) -> dict:
    """Check if an update is available from GitHub Releases.

    Returns a dict with keys: available (bool), version (str),
    release_notes (str), release_url (str).

    Uses COMMIT (baked into _version.py at CI build time) for nightly
    comparison instead of a fragile cache file.
    """
    import urllib.request
    import json
    import ssl

    result = {
        "available": False,
        "version": "",
        "release_notes": "",
        "release_url": "",
    }

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
                if not res_data:
                    return result
                latest = res_data[0]
            else:
                latest = res_data

        latest_tag = latest.get("tag_name", "")
        latest_version = _normalize_version(latest_tag)
        release_notes = latest.get("body", "") or ""
        release_url = latest.get("html_url", "") or ""

        if not latest_tag:
            return result

        if update_branch == "nightly" and latest_tag.lower() == "nightly":
            # Use baked-in COMMIT (set by CI at build time) to compare
            # against the release's target_commitish — the exact commit
            # the DMG was built from.
            remote_sha = latest.get("target_commitish", "") or ""
            if remote_sha and COMMIT:
                result["available"] = COMMIT != remote_sha
                result["version"] = f"nightly ({remote_sha[:12]}...)"
                result["release_notes"] = release_notes
                result["release_url"] = release_url
                return result
            # Fallback: compare tag name
            if remote_sha and not COMMIT:
                result["available"] = True
                result["version"] = f"nightly ({remote_sha[:12]}...)"
                result["release_notes"] = release_notes
                result["release_url"] = release_url
                return result
            return result

        # Stable or standard branch: compare version tags
        current_version = _current_version_tag()
        result["available"] = not _version_tag_matches(latest_tag, current_version)
        if result["available"]:
            result["version"] = latest_version
            result["release_notes"] = release_notes
            result["release_url"] = release_url
        return result
    except Exception as e:
        logger.error(f"[UPDATE CHECK] GitHub Releases check failed: {str(e)}")
        return result

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

                # Unified detection: always use GitHub Releases API.
                # This works for both git dev installs and DMG/release installs
                # and avoids the git-vs-API divergence.
                result = _check_github_update(update_branch)
                _cached_update_available = result["available"]
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

        # Detect if an update is in progress (flag file set before the old process exits).
        # If the flag file is stale (>5 minutes old), the update likely failed — clean it up.
        updating = UPDATE_IN_PROGRESS_FILE.exists()
        if updating:
            try:
                mtime = os.path.getmtime(UPDATE_IN_PROGRESS_FILE)
                age = datetime.now().timestamp() - mtime
                if age > 300:  # 5 minutes
                    logger.warning("[UPDATE] Stale update flag detected (>5min). Clearing.")
                    UPDATE_IN_PROGRESS_FILE.unlink()
                    updating = False
            except Exception:
                pass

        return HealthInfo(
            api_connected=api_connected,
            api_authenticated=api_authenticated,
            worker_running=ctx._download is not None,
            is_offline=ctx.is_offline,
            update_available=update_available,
            updating=updating,
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
            updating=UPDATE_IN_PROGRESS_FILE.exists(),
            current_version="unknown",
        )

@router.post("/check-update")
async def check_for_updates():
    """Manually trigger an update check, ignoring cache."""
    global _last_update_check, _cached_update_available
    # Respect opt-out environment variable for automated update checks
    if os.environ.get("ANICAT_DISABLE_AUTO_UPDATE", "0") == "1":
        return {"status": "error", "update_available": False, "message": "Auto-updates disabled by environment", "version": "", "release_notes": "", "release_url": ""}

    # Respect user's config setting (allow disabling update checks via AppConfig)
    try:
        loader = ConfigLoader()
        current_config = loader.load(allow_setup=False)
        if not getattr(current_config.general, "check_for_updates", True):
            return {"status": "error", "update_available": False, "message": "Auto-updates disabled in configuration", "version": "", "release_notes": "", "release_url": ""}
        update_branch = getattr(current_config.general, "update_branch", "stable")
    except Exception:
        update_branch = "stable"

    try:
        _last_update_check = datetime.now()

        # Unified detection: always use GitHub Releases API.
        # Works for git dev installs and DMG/release installs alike.
        result = _check_github_update(update_branch)
        _cached_update_available = result["available"]

        if result["available"]:
            version_str = result["version"]
            return {
                "status": "success",
                "update_available": True,
                "message": f"A new version is available: v{version_str}",
                "version": version_str,
                "release_notes": result["release_notes"],
                "release_url": result["release_url"],
            }
        return {
            "status": "success",
            "update_available": False,
            "message": f"You are running the latest version on the {update_branch} branch.",
            "version": VERSION,
            "release_notes": "",
            "release_url": "",
        }
    except Exception as e:
        logger.error(f"[UPDATE CHECK] Error: {str(e)}")
        return {"status": "error", "update_available": False, "message": f"Failed to check for updates: {str(e)}", "version": "", "release_notes": "", "release_url": ""}

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

        # Determine the repo root once
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        is_git_install = os.path.exists(os.path.join(repo_root, ".git"))

        if is_git_install:
            # Git-based install (dev checkout) — pull the latest code regardless of platform
            from anicat_media.utils.subprocess import run_cmd
            rc, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5, cwd=repo_root)
            current_branch = stdout.strip() if (rc == 0 and stdout) else "master"

            if update_branch == "nightly":
                target_branch = "nightly"
            else:
                target_branch = "master"

            subprocess.run(["git", "stash"], cwd=repo_root, capture_output=True)
            if current_branch != target_branch:
                subprocess.run(["git", "checkout", target_branch], cwd=repo_root, capture_output=True)
            result = subprocess.run(["git", "pull", "origin", target_branch], cwd=repo_root, capture_output=True, text=True, timeout=60)
            subprocess.run(["git", "stash", "pop"], cwd=repo_root, capture_output=True)

            _last_update_check = datetime.now()
            _cached_update_available = False

            if result.returncode == 0:
                install_script = os.path.join(repo_root, "scripts", "install.sh")
                if os.path.exists(install_script):
                    subprocess.Popen(["bash", install_script, "--no-launch"], cwd=repo_root, start_new_session=True)
                    return {"status": "success", "message": f"Update in progress (Git branch {target_branch}). Rebuilding frontend..."}
                return {"status": "success", "message": f"Updated successfully (Git branch {target_branch} code only)."}
            else:
                return {"status": "error", "message": f"Git pull failed: {result.stderr.strip() or result.stdout.strip()}"}

        # Release install (DMG/binary) — macOS native app update
        import platform
        if platform.system() == "Darwin":
            UPDATE_IN_PROGRESS_FILE.write_text("1", encoding="utf-8")

            logger.info("[UPDATE] Triggering macOS native update via installer script")
            local_script = os.path.join(repo_root, "scripts", "install_macos.sh")

            branch_name = "nightly" if update_branch == "nightly" else "master"

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
