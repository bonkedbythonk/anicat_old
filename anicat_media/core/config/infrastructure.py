"""Selector, player, and background service configuration."""

from pathlib import Path
from typing import Literal

from pydantic import Field

from ..constants import APP_ASCII_ART
from .model import BaseConfig, OtherConfig
from . import defaults
from . import descriptions as desc


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class FzfConfig(OtherConfig):
    """Configuration specific to the FZF selector."""

    opts: str = Field(
        default_factory=lambda: defaults.FZF_OPTS.read_text(encoding="utf-8"),
        description=desc.FZF_OPTS,
    )
    header_color: str = Field(
        default=defaults.FZF_HEADER_COLOR, description=desc.FZF_HEADER_COLOR
    )
    header_ascii_art: str = Field(
        default=APP_ASCII_ART, description=desc.FZF_HEADER_ASCII_ART
    )
    show_header_ascii_art: bool = Field(
        default=True, description=desc.FZF_SHOW_HEADER_ASCII_ART
    )
    preview_header_color: str = Field(
        default=defaults.FZF_PREVIEW_HEADER_COLOR,
        description=desc.FZF_PREVIEW_HEADER_COLOR,
    )
    preview_separator_color: str = Field(
        default=defaults.FZF_PREVIEW_SEPARATOR_COLOR,
        description=desc.FZF_PREVIEW_SEPARATOR_COLOR,
    )


class RofiConfig(OtherConfig):
    """Configuration specific to the Rofi selector."""

    theme_main: Path = Field(
        default_factory=lambda: Path(str(defaults.ROFI_THEME_MAIN)),
        description=desc.ROFI_THEME_MAIN,
    )
    theme_preview: Path = Field(
        default_factory=lambda: Path(str(defaults.ROFI_THEME_PREVIEW)),
        description=desc.ROFI_THEME_PREVIEW,
    )
    theme_confirm: Path = Field(
        default_factory=lambda: Path(str(defaults.ROFI_THEME_CONFIRM)),
        description=desc.ROFI_THEME_CONFIRM,
    )
    theme_input: Path = Field(
        default_factory=lambda: Path(str(defaults.ROFI_THEME_INPUT)),
        description=desc.ROFI_THEME_INPUT,
    )


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------


class MpvConfig(OtherConfig):
    """Configuration specific to the MPV player integration."""

    args: str = Field(default=defaults.MPV_ARGS, description=desc.MPV_ARGS)
    pre_args: str = Field(default=defaults.MPV_PRE_ARGS, description=desc.MPV_PRE_ARGS)


# ---------------------------------------------------------------------------
# Background services
# ---------------------------------------------------------------------------


class WorkerConfig(OtherConfig):
    """Configuration for the background worker service."""

    enabled: bool = Field(
        default=True,
        description="Enable the background worker for notifications and queued downloads.",
    )
    notification_check_interval: int = Field(
        default=15, ge=1,
        description="How often to check for new AniList notifications (in minutes).",
    )
    download_check_interval: int = Field(
        default=5, ge=1,
        description="How often to process the download queue (in minutes).",
    )
    download_check_failed_interval: int = Field(
        default=60, ge=1,
        description="How often to process the failed download queue (in minutes).",
    )
    auto_download_new_episode: bool = Field(
        default=True,
        description="Whether to automatically download a new episode that has been notified",
    )


class SessionsConfig(OtherConfig):
    """Configuration for session persistence."""

    dir: Path = Field(
        default_factory=lambda: defaults.SESSIONS_DIR,
        description=desc.SESSIONS_DIR,
    )
