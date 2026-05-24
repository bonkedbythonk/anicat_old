"""
Defines the PlayerParams dataclass, which encapsulates all parameters required to launch a media player session.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class PlayerParams:
    """
    Parameters for launching a media player session.

    Attributes:
        url: The media URL to play.
        title: The title to display in the player.
        query: The original search query or context.
        episode: The episode identifier or label.
        syncplay: Whether to enable syncplay (synchronized playback).
        subtitles: List of subtitle file paths or URLs.
        headers: HTTP headers to include in the request.
        start_time: The time offset to start playback from.
    """

    url: str
    title: str
    query: str
    episode: str
    syncplay: bool = False
    subtitles: list[str] | None = None
    headers: dict[str, str] | None = None
    start_time: str | None = None
    shader_profile: str | None = None
    skip_times: list[dict] | None = None
    fullscreen: bool = False
    auto_next: bool = False

