import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, computed_field

from ....core.utils import converter
from ....libs.media_api.types import MediaItem, UserMediaListStatus

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    NOT_DOWNLOADED = "not_downloaded"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


REGISTRY_VERSION = "1.0"


class MediaEpisode(BaseModel):
    episode_number: str
    chapter_number: Optional[str] = None
    volume_number: Optional[str] = None

    download_status: DownloadStatus = DownloadStatus.NOT_DOWNLOADED
    file_path: Optional[Path] = None
    download_date: Optional[datetime] = None

    # Additional download metadata
    file_size: Optional[int] = None  # File size in bytes
    quality: Optional[str] = None  # Download quality (e.g., "1080p", "720p")
    provider_name: Optional[str] = None  # Name of the provider used
    server_name: Optional[str] = None  # Name of the server used
    subtitle_paths: list[Path] = Field(default_factory=list)  # Paths to subtitle files
    download_attempts: int = 0  # Number of download attempts
    last_error: Optional[str] = None  # Last error message if failed


class MediaRecord(BaseModel):
    media_item: MediaItem
    media_episodes: list[MediaEpisode] = Field(default_factory=list)
    provider_mapping: Dict[str, str] = Field(default_factory=dict)


class MediaRegistryIndexEntry(BaseModel):
    media_id: int
    media_api: Literal["anilist", "NONE", "jikan"] = "NONE"

    status: UserMediaListStatus = UserMediaListStatus.WATCHING
    progress: str = "0"
    last_watch_position: Optional[str] = None
    last_watched: Optional[datetime] = None
    total_duration: Optional[str] = None
    total_episodes: int = 0
    chapter_number: Optional[str] = None
    volume_number: Optional[str] = None

    score: float = 0
    repeat: int = 0
    notes: str = ""

    last_notified_episode: Optional[str] = None
    
    is_synced: bool = True

    # for first watch only
    start_date: datetime = Field(default_factory=datetime.now)
    completed_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def watch_completion_percentage(self) -> float:
        """Watch completion percentage."""
        if self.total_duration and self.last_watch_position:
            total_secs = converter.time_to_seconds(self.total_duration)
            if total_secs > 0:
                return (
                    converter.time_to_seconds(self.last_watch_position)
                    / total_secs
                ) * 100
        return 0.0


class MediaRegistryIndex(BaseModel):
    version: str = Field(default=REGISTRY_VERSION)
    last_updated: datetime = Field(default_factory=datetime.now)

    media_index: Dict[str, MediaRegistryIndexEntry] = Field(default_factory=dict)

    @computed_field
    @property
    def status_breakdown(self) -> Dict[str, int]:
        """Get breakdown by user status."""
        breakdown = {}
        for entry in self.media_index.values():
            breakdown[entry.status.value] = breakdown.get(entry.status.value, 0) + 1
        return breakdown

    @computed_field
    @property
    def media_count_breakdown(self) -> Dict[str, int]:
        breakdown = {}
        for entry in self.media_index.values():
            breakdown[entry.media_api] = breakdown.get(entry.media_api, 0) + 1
        return breakdown

    @computed_field
    @property
    def media_count(self) -> int:
        """Get the number of media."""
        return len(self.media_index)
