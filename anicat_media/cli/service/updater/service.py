"""Stub updater service that delegates to the API status endpoint.

Replaced the removed UpdaterService. Calls the dashboard's /status/health
endpoint to check for updates rather than making standalone GitHub requests.
"""

import logging
import httpx
from anicat_media.core.constants import VERSION, LOCAL_API_ORIGIN

logger = logging.getLogger(__name__)


class UpdaterService:
    """Update checker that queries the local API for update status."""

    def __init__(self, config=None):
        self.config = config
        self.remote_version = None
        self.remote_hash = None
        self.local_hash = VERSION

    def check_version(self, force: bool = False) -> bool:
        """Check for updates via the local API health endpoint."""
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
            logger.warning(f"UpdaterService: local API unavailable: {e}")
        return False

    def get_cached_status(self) -> bool:
        """Return cached update status (best-effort, no network)."""
        return False
