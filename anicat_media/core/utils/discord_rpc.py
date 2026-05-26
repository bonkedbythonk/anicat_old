from __future__ import annotations
import time
import logging
from typing import Optional, TYPE_CHECKING
from ..constants import DISCORD_CLIENT_ID

if TYPE_CHECKING:
    from pypresence import AioPresence

logger = logging.getLogger(__name__)

try:
    import pypresence

    PYPRESENCE_AVAILABLE = True
except ImportError:
    PYPRESENCE_AVAILABLE = False
    logger.warning(
        "pypresence package is not installed. Discord Rich Presence is disabled."
    )


class DiscordPresenceManager:
    def __init__(self, client_id: str = DISCORD_CLIENT_ID):
        self.client_id = client_id
        self.client: Optional[AioPresence] = None
        self.connected = False
        self._current_media_id: Optional[int] = None
        self._current_episode: Optional[str] = None

    async def connect(self) -> bool:
        if not PYPRESENCE_AVAILABLE:
            return False
        if self.connected and self.client:
            return True
        try:
            from pypresence import AioPresence

            self.client = AioPresence(self.client_id)
            await self.client.connect()
            self.connected = True
            logger.info("Successfully connected to Discord Rich Presence (IPC).")
            return True
        except Exception as e:
            logger.debug(f"Could not establish connection to Discord IPC: {e}")
            self.connected = False
            self.client = None
            return False

    async def update_watching(self, title: str, episode: str, media_id: int):
        """Update Discord Rich Presence to show active anime watching."""
        if not PYPRESENCE_AVAILABLE:
            return

        # Avoid redundant updates if we are already playing this exact media/episode
        if (
            self.connected
            and self._current_media_id == media_id
            and self._current_episode == episode
        ):
            return

        try:
            connected = await self.connect()
            if not connected or not self.client:
                return

            self._current_media_id = media_id
            self._current_episode = episode

            # Discord RPC expects details/state up to 128 characters
            truncated_title = title[:128]
            state_str = f"Watching Episode {episode}"

            await self.client.update(
                state=state_str,
                details=truncated_title,
                start=int(time.time()),
                large_image="logo",  # Standard asset key for AniCat
                large_text="AniCat",
                small_image="play",
                small_text="Watching",
            )
            logger.info(f"[Discord RPC] Updated: {truncated_title} - {state_str}")
        except Exception as e:
            logger.warning(f"Failed to update Discord Rich Presence activity: {e}")
            # Mark as disconnected to retry connection on next update
            self.connected = False
            self.client = None
            self._current_media_id = None
            self._current_episode = None

    async def update_reading(self, title: str, chapter: str, media_id: int):
        """Update Discord Rich Presence to show active manga reading."""
        if not PYPRESENCE_AVAILABLE:
            return

        # Avoid redundant updates if we are already reading this exact media/chapter
        if (
            self.connected
            and self._current_media_id == media_id
            and self._current_episode == f"chapter_{chapter}"
        ):
            return

        try:
            connected = await self.connect()
            if not connected or not self.client:
                return

            self._current_media_id = media_id
            self._current_episode = f"chapter_{chapter}"

            # Discord RPC expects details/state up to 128 characters
            truncated_title = title[:128]
            state_str = f"Reading Chapter {chapter}"

            await self.client.update(
                state=state_str,
                details=truncated_title,
                start=int(time.time()),
                large_image="logo",  # Standard asset key for AniCat
                large_text="AniCat",
                small_image="book",  # Distinctive book icon for reading
                small_text="Reading",
            )
            logger.info(f"[Discord RPC] Updated: {truncated_title} - {state_str}")
        except Exception as e:
            logger.warning(f"Failed to update Discord Rich Presence activity: {e}")
            self.connected = False
            self.client = None
            self._current_media_id = None
            self._current_episode = None

    async def clear(self):
        """Clear Discord Rich Presence activity."""
        if not PYPRESENCE_AVAILABLE or not self.connected or not self.client:
            return
        try:
            await self.client.clear()
            logger.info("[Discord RPC] Cleared activity presence.")
        except Exception as e:
            logger.debug(f"Failed to clear Discord Rich Presence: {e}")
        finally:
            self._current_media_id = None
            self._current_episode = None


# Global Singleton Manager
discord_rpc = DiscordPresenceManager()
