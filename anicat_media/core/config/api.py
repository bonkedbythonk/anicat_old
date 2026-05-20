"""External API integration configuration (AniList, Jikan)."""

from typing import Literal

from pydantic import Field

from ...libs.media_api.types import MediaSort, UserMediaListSort
from .model import BaseConfig
from . import defaults
from . import descriptions as desc


class AnilistConfig(BaseConfig):
    """Configuration for interacting with the AniList API."""

    per_page: int = Field(
        default=defaults.ANILIST_PER_PAGE,
        gt=0,
        le=50,
        description=desc.ANILIST_PER_PAGE,
    )
    sort_by: MediaSort = Field(
        default=MediaSort.SEARCH_MATCH,
        description=desc.ANILIST_SORT_BY,
    )
    media_list_sort_by: UserMediaListSort = Field(
        default=UserMediaListSort.MEDIA_POPULARITY_DESC,
        description=desc.ANILIST_MEDIA_LIST_SORT_BY,
    )
    preferred_language: Literal["english", "romaji"] = Field(
        default=defaults.ANILIST_PREFERRED_LANGUAGE,
        description=desc.ANILIST_PREFERRED_LANGUAGE,
    )
    token: str = Field(default=defaults.ANILIST_TOKEN, description="Your AniList OAuth token.")


class JikanConfig(BaseConfig):
    """Configuration for the Jikan API."""

    per_page: int = Field(
        default=defaults.ANILIST_PER_PAGE,
        gt=0,
        le=50,
        description=desc.ANILIST_PER_PAGE,
    )
    sort_by: MediaSort = Field(
        default=MediaSort.SEARCH_MATCH,
        description=desc.ANILIST_SORT_BY,
    )
    media_list_sort_by: UserMediaListSort = Field(
        default=UserMediaListSort.MEDIA_POPULARITY_DESC,
        description=desc.ANILIST_MEDIA_LIST_SORT_BY,
    )
    preferred_language: Literal["english", "romaji"] = Field(
        default=defaults.ANILIST_PREFERRED_LANGUAGE,
        description=desc.ANILIST_PREFERRED_LANGUAGE,
    )
