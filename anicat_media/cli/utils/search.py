"""Search functionality."""

import re
from typing import Union

from anicat_media.core.utils.fuzzy import fuzz
from anicat_media.core.utils.normalizer import normalize_title
from anicat_media.libs.media_api.types import MediaItem
from anicat_media.libs.provider.anime.types import ProviderName, SearchResult
from anicat_media.libs.provider.manga.types import MangaProviderName


def _extract_trailing_season_number(title: str) -> int | None:
    # Match season number, e.g. "Season 2", "2nd Season", "2", "II"
    title_clean = title.strip().lower()

    # 1. Look for "2nd season", "2 season", "season 2", "season: 2", etc.
    match = re.search(r"\b(?:season|s)\s*[:#-]?\s*(\d+)", title_clean)
    if match:
        return int(match.group(1))

    match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+season\b", title_clean)
    if match:
        return int(match.group(1))

    # 2. Look for trailing number
    match = re.search(r"(?:\bseason\s*)?(\d+)(?:st|nd|rd|th)?\s*$", title_clean)
    if match:
        return int(match.group(1))

    # 3. Look for Roman numerals like "II", "III", "IV" at the end of the title
    roman_map = {
        "i": 1,
        "ii": 2,
        "iii": 3,
        "iv": 4,
        "v": 5,
        "vi": 6,
        "vii": 7,
        "viii": 8,
        "ix": 9,
        "x": 10,
    }
    words = title_clean.split()
    if words:
        last_word = words[-1].strip(".,()[]-")
        if last_word in roman_map:
            return roman_map[last_word]

    return None


def _normalize_season(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def _score_candidate(
    provider_title: str,
    provider_result: SearchResult,
    provider: Union[ProviderName, MangaProviderName],
    media_item: MediaItem,
) -> tuple[int, int, int, int, int]:
    normalized_title = normalize_title(provider_title, provider.value).lower()
    title_score = max(
        fuzz.ratio(normalized_title, (media_item.title.romaji or "").lower()),
        fuzz.ratio(normalized_title, (media_item.title.english or "").lower()),
    )

    season_match = (
        1
        if _normalize_season(provider_result.season)
        == _normalize_season(media_item.season)
        and provider_result.season
        else 0
    )

    year_match = 0
    if media_item.season_year and provider_result.year:
        try:
            year_match = (
                1 if int(provider_result.year) == int(media_item.season_year) else 0
            )
        except (TypeError, ValueError):
            year_match = 0

    media_sequel = _extract_trailing_season_number(
        media_item.title.english or media_item.title.romaji or ""
    )
    provider_sequel = _extract_trailing_season_number(provider_title)
    sequel_match = (
        1 if media_sequel and provider_sequel and media_sequel == provider_sequel else 0
    )

    exact_title_match = (
        1
        if normalized_title
        in {
            (media_item.title.romaji or "").lower(),
            (media_item.title.english or "").lower(),
        }
        else 0
    )

    return (sequel_match, season_match, year_match, exact_title_match, title_score)


def find_best_match_title(
    provider_results_map: dict[str, SearchResult],
    provider: Union[ProviderName, MangaProviderName],
    media_item: MediaItem,
) -> str:
    """Find the best match title using fuzzy matching for both the english AND romaji title.

    Parameters:
        provider_results_map (dict[str, SearchResult]): The map of provider results.
        provider (ProviderName): The provider name from the config.
        media_item (MediaItem): The media item to match.

    Returns:
        str: The best match title.
    """
    return max(
        provider_results_map.keys(),
        key=lambda p_title: _score_candidate(
            p_title,
            provider_results_map[p_title],
            provider,
            media_item,
        ),
    )
