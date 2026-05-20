"""Download and media management configuration."""

from pathlib import Path
from typing import Literal

from pydantic import Field

from ...libs.provider.anime.types import ProviderServer
from .model import BaseConfig
from . import defaults
from . import descriptions as desc


class DownloadsConfig(BaseConfig):
    """Configuration for download related options."""

    downloader: Literal["auto", "default", "yt-dlp"] = Field(
        default=defaults.DOWNLOADS_DOWNLOADER, description=desc.DOWNLOADS_DOWNLOADER
    )
    downloads_dir: Path = Field(
        default_factory=lambda: defaults.DOWNLOADS_DOWNLOADS_DIR,
        description=desc.DOWNLOADS_DOWNLOADS_DIR,
    )
    enable_tracking: bool = Field(
        default=defaults.DOWNLOADS_ENABLE_TRACKING,
        description=desc.DOWNLOADS_ENABLE_TRACKING,
    )
    max_concurrent_downloads: int = Field(
        default=defaults.DOWNLOADS_MAX_CONCURRENT,
        ge=1,
        description=desc.DOWNLOADS_MAX_CONCURRENT,
    )
    max_retry_attempts: int = Field(
        default=defaults.DOWNLOADS_RETRY_ATTEMPTS,
        ge=0,
        description=desc.DOWNLOADS_RETRY_ATTEMPTS,
    )
    retry_delay: int = Field(
        default=defaults.DOWNLOADS_RETRY_DELAY,
        ge=0,
        description=desc.DOWNLOADS_RETRY_DELAY,
    )
    merge_subtitles: bool = Field(
        default=defaults.DOWNLOADS_MERGE_SUBTITLES,
        description=desc.DOWNLOADS_MERGE_SUBTITLES,
    )
    cleanup_after_merge: bool = Field(
        default=defaults.DOWNLOADS_CLEANUP_AFTER_MERGE,
        description=desc.DOWNLOADS_CLEANUP_AFTER_MERGE,
    )
    server: ProviderServer = Field(
        default=ProviderServer.TOP,
        description=desc.STREAM_SERVER,
    )
    ytdlp_format: str = Field(
        default=defaults.STREAM_YTDLP_FORMAT,
        description=desc.STREAM_YTDLP_FORMAT,
    )
    no_check_certificate: bool = Field(
        default=defaults.DOWNLOADS_NO_CHECK_CERTIFICATE,
        description=desc.DOWNLOADS_NO_CHECK_CERTIFICATE,
    )


class MediaRegistryConfig(BaseConfig):
    """Configuration for media registry storage paths."""

    media_dir: Path = Field(
        default=defaults.MEDIA_REGISTRY_DIR,
        description=desc.MEDIA_REGISTRY_DIR,
    )
    index_dir: Path = Field(
        default=defaults.MEDIA_REGISTRY_INDEX_DIR,
        description=desc.MEDIA_REGISTRY_INDEX_DIR,
    )
