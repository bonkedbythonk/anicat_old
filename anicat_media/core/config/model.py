"""Application configuration model — composition root.

This module defines BaseConfig (the shared base with expand_path validator),
OtherConfig (empty base for non-path-expanding configs), and AppConfig
(the top-level composition root).

Individual config groups live in their own modules and are re-exported
here so existing imports continue to work unchanged.
"""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from . import descriptions as desc

# Re-export all config classes from their domain modules so existing
# `from anicat_media.core.config.model import GeneralConfig` imports
# continue to work without modification.
from .general import GeneralConfig  # noqa: F401
from .stream import StreamConfig  # noqa: F401
from .downloads import DownloadsConfig, MediaRegistryConfig  # noqa: F401
from .api import AnilistConfig, JikanConfig  # noqa: F401
from .infrastructure import (  # noqa: F401
    FzfConfig,
    RofiConfig,
    MpvConfig,
    WorkerConfig,
    SessionsConfig,
)


# ---------------------------------------------------------------------------
# Shared base classes
# ---------------------------------------------------------------------------


class BaseConfig(BaseModel):
    """Base config with automatic `~` expansion in any string field."""

    @field_validator("*", mode="before")
    @classmethod
    def expand_path(cls, v, info):
        if isinstance(v, str) and "~" in v:
            return Path(v).expanduser()
        return v


class OtherConfig(BaseConfig):
    """Marker base for configs that don't need their own path expansion."""
    pass


# ---------------------------------------------------------------------------
# Composition root
# ---------------------------------------------------------------------------


class AppConfig(BaseConfig):
    """The root configuration model for the Anicat application."""

    general: GeneralConfig = Field(
        default_factory=GeneralConfig,
        description=desc.APP_GENERAL,
    )
    stream: StreamConfig = Field(
        default_factory=StreamConfig,
        description=desc.APP_STREAM,
    )
    downloads: DownloadsConfig = Field(
        default_factory=DownloadsConfig, description=desc.APP_DOWNLOADS
    )
    anilist: AnilistConfig = Field(
        default_factory=AnilistConfig,
        description=desc.APP_ANILIST,
    )
    jikan: JikanConfig = Field(
        default_factory=JikanConfig,
        description=desc.APP_JIKAN,
    )
    fzf: FzfConfig = Field(
        default_factory=FzfConfig,
        description=desc.APP_FZF,
    )
    rofi: RofiConfig = Field(
        default_factory=RofiConfig,
        description=desc.APP_ROFI,
    )
    mpv: MpvConfig = Field(default_factory=MpvConfig, description=desc.APP_MPV)
    media_registry: MediaRegistryConfig = Field(
        default_factory=MediaRegistryConfig, description=desc.APP_MEDIA_REGISTRY
    )
    sessions: SessionsConfig = Field(
        default_factory=SessionsConfig, description=desc.APP_SESSIONS
    )
    worker: WorkerConfig = Field(
        default_factory=WorkerConfig,
        description="Configuration for the background worker service.",
    )
