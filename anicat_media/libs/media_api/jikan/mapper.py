from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..types import (
    MediaImage,
    MediaItem,
    MediaSearchResult,
    MediaStatus,
    MediaTitle,
    PageInfo,
    Studio,
)

if TYPE_CHECKING:
    # Jikan doesn't have a formal schema like GraphQL, so we work with dicts.
    pass

# Jikan uses specific strings for status, we can map them to our generic enum.
JIKAN_STATUS_MAP = {
    "Finished Airing": MediaStatus.FINISHED,
    "Currently Airing": MediaStatus.RELEASING,
    "Not yet aired": MediaStatus.NOT_YET_RELEASED,
}


def _to_generic_title(jikan_titles: list[dict]) -> MediaTitle:
    """Extracts titles from Jikan's list of title objects."""
    # Initialize with default values
    romaji = None
    english = None
    native = None

    # Jikan's default title is often the romaji one.
    # We prioritize specific types if available.
    for t in jikan_titles:
        type_ = t.get("type")
        title_ = t.get("title")
        if type_ == "Default":
            romaji = title_
        elif type_ == "English":
            english = title_
        elif type_ == "Japanese":
            native = title_

    return MediaTitle(
        romaji=romaji,
        english=english or romaji or native or "NOT AVAILABLE",
        native=native,
    )


def _to_generic_image(jikan_images: dict) -> MediaImage:
    """Maps Jikan's image structure."""
    if not jikan_images:
        return MediaImage(large="")  # Provide empty string as fallback
    # Jikan provides different image formats under a 'jpg' key.
    jpg_images = jikan_images.get("jpg", {})
    return MediaImage(
        large=jpg_images.get("large_image_url", ""),  # Fallback to empty string
        medium=jpg_images.get("image_url"),
    )


import re
from ..types import MediaGenre


def _parse_duration(duration_str: Optional[str]) -> Optional[int]:
    """Parses a Jikan duration string (e.g. '24 min per ep' or '1 hr 45 min') into minutes (int)."""
    if not duration_str:
        return None
    try:
        s = duration_str.lower().strip()
        total_minutes = 0
        hr_match = re.search(r"(\d+)\s*(?:hr|hour|h)", s)
        min_match = re.search(r"(\d+)\s*(?:min|minute|m)", s)

        if hr_match:
            total_minutes += int(hr_match.group(1)) * 60
        if min_match:
            total_minutes += int(min_match.group(1))

        if not hr_match and not min_match:
            # Fallback to extracting the first integer sequence if no units match
            num_match = re.search(r"\d+", s)
            if num_match:
                return int(num_match.group(0))
            return None

        return total_minutes
    except Exception:
        return None


def _to_generic_media_item(data: dict) -> MediaItem:
    """Maps a single Jikan anime entry to our generic MediaItem."""

    # Jikan score is 0-10, our generic model is 0-10, so we can use it directly.
    # AniList was 0-100, so its mapper had to divide by 10.
    score = data.get("score")

    # Clean and filter genres to match the exact MediaGenre Enum values
    genres = []
    for g in data.get("genres", []):
        name = g.get("name")
        if not name:
            continue
        # Check against available MediaGenre enums (case-insensitive)
        for genre_enum in MediaGenre:
            if genre_enum.value.lower() == name.lower():
                genres.append(genre_enum)
                break

    return MediaItem(
        id=data["mal_id"],
        id_mal=data["mal_id"],
        title=_to_generic_title(data.get("titles", [])),
        cover_image=_to_generic_image(data.get("images", {})),
        status=JIKAN_STATUS_MAP.get(data.get("status", ""), MediaStatus.UNKNOWN),
        episodes=data.get("episodes"),
        duration=_parse_duration(data.get("duration")),
        average_score=score,
        popularity=data.get("popularity"),
        favourites=data.get("favorites"),
        description=data.get("synopsis"),
        genres=genres,
        studios=[
            Studio(id=s["mal_id"], name=s["name"]) for s in data.get("studios", [])
        ],
        # Jikan doesn't provide streaming episodes
        streaming_episodes={},
        # Jikan doesn't provide user list status in its search results.
        user_status=None,
        seasonYear=None,
        next_airing=None,
    )


def to_generic_search_result(
    api_response: dict, original_query: Optional[str] = None
) -> Optional[MediaSearchResult]:
    """Top-level mapper for Jikan search results.

    If `original_query` is provided, perform a lightweight fuzzy re-ranking
    of results so strong matches for long/natural-language queries are
    promoted higher in the returned list. Uses stdlib `difflib` to avoid
    new dependencies and applies reordering conservatively.
    """
    if not api_response or "data" not in api_response:
        return None

    media_items = [_to_generic_media_item(item) for item in api_response["data"]]

    # Attempt conservative fuzzy promotion when an explicit query is supplied
    try:
        if original_query and isinstance(original_query, str):
            import difflib

            # Normalize query: lowercase, remove non-alphanumerics, collapse spaces
            q = re.sub(r"[^a-z0-9 ]+", " ", original_query.lower()).strip()
            # Remove common stopwords to improve matching on long natural-language queries
            STOPWORDS = {
                "the",
                "a",
                "an",
                "what",
                "was",
                "that",
                "is",
                "are",
                "was",
                "were",
                "it",
                "of",
                "for",
                "in",
                "on",
                "at",
                "by",
                "with",
                "about",
                "again",
                "release",
                "blu",
                "ray",
            }
            tokens = [
                t for t in q.split() if t and t not in STOPWORDS and not t.isdigit()
            ]
            q = " ".join(tokens)
            if len(q) >= 3:
                scores: list[float] = []
                for mi in media_items:
                    # Build a searchable candidate string from title fields
                    parts = [
                        mi.title.english or "",
                        mi.title.romaji or "",
                        mi.title.native or "",
                    ]
                    cand = " ".join(parts).lower()
                    cand = re.sub(r"[^a-z0-9 ]+", " ", cand).strip()
                    # Compute similarity ratio
                    ratio = difflib.SequenceMatcher(None, q, cand).ratio()
                    scores.append(ratio)

                max_score = max(scores) if scores else 0.0
                # Only reorder if there's a reasonably strong match. Use a conservative
                # but permissive threshold so long noisy queries can still promote exact
                # title matches.
                if max_score >= 0.4:
                    indexed = list(enumerate(media_items))
                    # Sort by score desc, then original index asc to remain stable
                    indexed.sort(key=lambda x: (-scores[x[0]], x[0]))
                    media_items = [it for (_, it) in indexed]
    except Exception:
        # Be conservative: if our post-processing fails, fall back to original order
        pass

    pagination = api_response.get("pagination", {})
    page_info = PageInfo(
        total=pagination.get("items", {}).get("total", 0),
        current_page=pagination.get("current_page", 1),
        has_next_page=pagination.get("has_next_page", False),
        per_page=pagination.get("items", {}).get("per_page", 25),
    )

    return MediaSearchResult(page_info=page_info, media=media_items)
