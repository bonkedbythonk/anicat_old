"""Video streaming and playback configuration."""

from typing import Literal

from pydantic import Field

from ...libs.provider.anime.types import ProviderServer
from .model import BaseConfig
from . import defaults
from . import descriptions as desc


class StreamConfig(BaseConfig):
    """Configuration specific to video streaming and playback."""

    player: Literal["mpv"] = Field(
        default=defaults.STREAM_PLAYER,
        description=desc.STREAM_PLAYER,
    )
    player_type: Literal["embedded", "external"] = Field(
        default=defaults.STREAM_PLAYER_TYPE,
        description=desc.STREAM_PLAYER_TYPE,
    )
    quality: Literal["360", "480", "720", "1080"] = Field(
        default=defaults.STREAM_QUALITY,
        description=desc.STREAM_QUALITY,
    )
    translation_type: Literal["sub", "dub"] = Field(
        default=defaults.STREAM_TRANSLATION_TYPE,
        description=desc.STREAM_TRANSLATION_TYPE,
    )
    server: ProviderServer = Field(
        default=ProviderServer.TOP,
        description=desc.STREAM_SERVER,
    )
    auto_next: bool = Field(
        default=defaults.STREAM_AUTO_NEXT,
        description=desc.STREAM_AUTO_NEXT,
    )
    continue_from_watch_history: bool = Field(
        default=defaults.STREAM_CONTINUE_FROM_WATCH_HISTORY,
        description=desc.STREAM_CONTINUE_FROM_WATCH_HISTORY,
    )
    preferred_watch_history: Literal["local", "remote"] = Field(
        default=defaults.STREAM_PREFERRED_WATCH_HISTORY,
        description=desc.STREAM_PREFERRED_WATCH_HISTORY,
    )
    auto_skip: bool = Field(
        default=defaults.STREAM_AUTO_SKIP,
        description=desc.STREAM_AUTO_SKIP,
    )
    shader_profile: Literal["off", "balanced", "high", "ultra"] = Field(
        default="balanced",
        description="The real-time GPU upscaling shader profile to use for anime playback.",
    )
    episode_complete_at: int = Field(
        default=defaults.STREAM_EPISODE_COMPLETE_AT,
        ge=0,
        le=100,
        description=desc.STREAM_EPISODE_COMPLETE_AT,
    )
    ytdlp_format: str = Field(
        default=defaults.STREAM_YTDLP_FORMAT,
        description=desc.STREAM_YTDLP_FORMAT,
    )
    force_forward_tracking: bool = Field(
        default=defaults.STREAM_FORCE_FORWARD_TRACKING,
        description=desc.STREAM_FORCE_FORWARD_TRACKING,
    )
    default_media_list_tracking: Literal["track", "disabled", "prompt"] = Field(
        default=defaults.STREAM_DEFAULT_MEDIA_LIST_TRACKING,
        description=desc.STREAM_DEFAULT_MEDIA_LIST_TRACKING,
    )
    sub_lang: str = Field(
        default=defaults.STREAM_SUB_LANG,
        description=desc.STREAM_SUB_LANG,
    )
    use_ipc: bool = Field(
        default_factory=defaults.STREAM_USE_IPC,
        description=desc.STREAM_USE_IPC,
    )
