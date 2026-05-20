"""Type definitions for AniNeko (GogoAnime successor) provider responses."""

from typing import TypedDict


class AniNekoSearchResult(TypedDict, total=False):
    """A single search result item."""

    id: str
    title: str
    poster: str | None
    type: str | None  # TV, Movie, OVA, Special, ONA
    sub_count: int
    dub_count: int
    genres: list[str]


class AniNekoAnimeDetail(TypedDict, total=False):
    """Anime detail from the watch page."""

    id: str
    title: str
    type: str | None
    status: str | None
    year: str | None
    episodes: list[str]  # episode numbers as strings
    poster: str | None
    has_sub: bool
    has_dub: bool


class AniNekoEpisodeServer(TypedDict, total=False):
    """A single server entry for an episode."""

    name: str
    embed_url: str
    subtitle_type: str  # "hardsub", "sortsub"
