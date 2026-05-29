"""Updater service that checks GitHub Releases for new versions.

Delegates to the local API /status/check-update endpoint when available,
falls back to a direct GitHub Releases API check when the backend is not running.
"""

import logging
import httpx
from anicat_media.core.constants import VERSION, LOCAL_API_ORIGIN

logger = logging.getLogger(__name__)


def _normalize_version(value: str) -> str:
    return value.strip().removeprefix("v").removeprefix("V").split("-")[0]


def _direct_github_check() -> tuple[bool, str]:
    """Check GitHub Releases directly for a newer version.

    Returns (update_available, latest_version).
    """
    import urllib.request
    import json
    import ssl

    try:
        ctx_ssl = ssl._create_unverified_context()
        url = "https://api.github.com/repos/bonkedbythonk/anicat_old/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Anicat-CLI"})
        with urllib.request.urlopen(req, timeout=5, context=ctx_ssl) as response:
            data = json.loads(response.read().decode())
            latest_tag = data.get("tag_name", "")
            if not latest_tag:
                return False, ""
            latest_version = _normalize_version(latest_tag)
            current_version = _normalize_version(VERSION)
            return latest_version != current_version, latest_version
    except Exception as e:
        logger.debug(f"Direct GitHub update check failed: {e}")
        return False, ""


class UpdaterService:
    """Update checker that queries the local API for update status,
    falling back to a direct GitHub Releases check when the API is down."""

    def __init__(self, config=None):
        self.config = config
        self.remote_version = None
        self.remote_hash = None
        self.local_hash = VERSION

    def check_version(self, force: bool = False) -> bool:
        """Check for updates via the local API health endpoint.

        Falls back to a direct GitHub Releases check if the local API
        is unreachable (e.g. CLI running without the backend).
        """
        # -- Tier 1: Ask the local API (when backend is running) --
        try:
            resp = httpx.get(
                f"{LOCAL_API_ORIGIN}/api/status/check-update",
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.remote_version = data.get("version", "Unknown")
                return data.get("update_available", False)
        except Exception as e:
            logger.debug(
                f"UpdaterService: local API unavailable, trying direct check: {e}"
            )

        # -- Tier 2: Direct GitHub Releases check (CLI standalone mode) --
        available, version = _direct_github_check()
        if available:
            self.remote_version = version
        return available

    def get_cached_status(self) -> bool:
        """Return cached update status (best-effort, no network)."""
        return False
