import logging
from typing import TYPE_CHECKING, Any, List, Optional

from ..base import BaseApiClient
from ..params import (
    MediaAiringScheduleParams,
    MediaCharactersParams,
    MediaRecommendationParams,
    MediaRelationsParams,
    MediaReviewsParams,
    MediaSearchParams,
    UpdateUserMediaListEntryParams,
    UserMediaListSearchParams,
)
from ..types import (
    AiringScheduleResult,
    CharacterSearchResult,
    MediaFormat,
    MediaGenre,
    MediaImage,
    MediaItem,
    MediaReview,
    MediaSearchResult,
    MediaTitle,
    MediaStatus,
    MediaType,
    Notification,
    UserProfile,
)
from . import mapper

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

JIKAN_ENDPOINT = "https://api.jikan.moe/v4"

JIKAN_GENRE_ID_MAP = {
    MediaGenre.ACTION: 1,
    MediaGenre.ADVENTURE: 2,
    MediaGenre.COMEDY: 4,
    MediaGenre.DRAMA: 8,
    MediaGenre.FANTASY: 10,
    MediaGenre.HORROR: 14,
    MediaGenre.MYSTERY: 7,
    MediaGenre.ROMANCE: 22,
    MediaGenre.SCI_FI: 24,
    MediaGenre.SLICE_OF_LIFE: 36,
    MediaGenre.SPORTS: 30,
    MediaGenre.SUPERNATURAL: 37,
    MediaGenre.THRILLER: 41,
}

JIKAN_ANIME_STATUS_MAP = {
    MediaStatus.FINISHED: "complete",
    MediaStatus.RELEASING: "airing",
    MediaStatus.NOT_YET_RELEASED: "upcoming",
}

JIKAN_MANGA_STATUS_MAP = {
    MediaStatus.FINISHED: "complete",
    MediaStatus.RELEASING: "publishing",
    MediaStatus.NOT_YET_RELEASED: "upcoming",
}

JIKAN_ANIME_FORMAT_MAP = {
    MediaFormat.TV: "tv",
    MediaFormat.TV_SHORT: "tv_short",
    MediaFormat.MOVIE: "movie",
    MediaFormat.SPECIAL: "special",
    MediaFormat.OVA: "ova",
    MediaFormat.ONA: "ona",
    MediaFormat.MUSIC: "music",
}

JIKAN_MANGA_FORMAT_MAP = {
    MediaFormat.MANGA: "manga",
    MediaFormat.NOVEL: "novel",
    MediaFormat.ONE_SHOT: "one_shot",
}


class JikanApi(BaseApiClient):
    """
    Jikan API (MyAnimeList) implementation of the BaseApiClient contract.
    Note: Jikan is a read-only API for public data. All authentication and
    list modification methods will be no-ops.
    """

    def _execute_request(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        """Executes a GET request to a Jikan endpoint."""
        try:
            response = self.http_client.get(
                f"{JIKAN_ENDPOINT}{endpoint}", params=params, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Jikan API request failed for endpoint '{endpoint}': {e}")
            return None

    # --- Read-Only Method Implementations ---

    def search_media(self, params: MediaSearchParams) -> Optional[MediaSearchResult]:
        """Searches for anime on MyAnimeList via Jikan."""
        endpoint = "/manga" if params.type == MediaType.MANGA else "/anime"
        jikan_params: dict[str, Any] = {
            "q": params.query,
            "page": params.page,
            "limit": params.per_page,
        }

        if params.genre_in:
            genre_ids = [JIKAN_GENRE_ID_MAP[g] for g in params.genre_in if g in JIKAN_GENRE_ID_MAP]
            if genre_ids:
                jikan_params["genres"] = ",".join(str(genre_id) for genre_id in genre_ids)

        if params.seasonYear:
            jikan_params["start_date"] = f"{params.seasonYear}-01-01"
            jikan_params["end_date"] = f"{params.seasonYear}-12-31"

        if params.averageScore_greater is not None:
            jikan_params["min_score"] = params.averageScore_greater

        status_map = JIKAN_MANGA_STATUS_MAP if params.type == MediaType.MANGA else JIKAN_ANIME_STATUS_MAP
        if params.status in status_map:
            jikan_params["status"] = status_map[params.status]

        if params.format_in:
            format_map = JIKAN_MANGA_FORMAT_MAP if params.type == MediaType.MANGA else JIKAN_ANIME_FORMAT_MAP
            for media_format in params.format_in:
                if media_format in format_map:
                    jikan_params["type"] = format_map[media_format]
                    break

        raw_data = self._execute_request(endpoint, params=jikan_params)
        return mapper.to_generic_search_result(raw_data, original_query=params.query) if raw_data else None
    
    def get_media_item(self, media_id: int) -> Optional[MediaItem]:
        """Fetch a single media item by ID via Jikan."""
        raw_data = self._execute_request(f"/anime/{media_id}")
        if raw_data and "data" in raw_data:
            return mapper._to_generic_media_item(raw_data["data"])
        return None

    def fetch_trending_media(
        self, page: int, per_page: int
    ) -> Optional[MediaSearchResult]:
        """Jikan doesn't have a 'trending' sort, so we'll use 'bypopularity'."""
        jikan_params = {"order_by": "popularity", "page": page, "limit": per_page}
        raw_data = self._execute_request("/anime", params=jikan_params)
        return mapper.to_generic_search_result(raw_data) if raw_data else None

    def fetch_popular_media(
        self, page: int, per_page: int
    ) -> Optional[MediaSearchResult]:
        """Alias for trending in Jikan's case."""
        return self.fetch_trending_media(page, per_page)

    def fetch_favourite_media(
        self, page: int, per_page: int
    ) -> Optional[MediaSearchResult]:
        """Fetches the most favorited media."""
        jikan_params = {"order_by": "favorites", "page": page, "limit": per_page}
        raw_data = self._execute_request("/anime", params=jikan_params)
        return mapper.to_generic_search_result(raw_data) if raw_data else None

    # --- No-Op Methods (Jikan is Read-Only) ---

    def is_authenticated(self) -> bool:
        """Jikan is a public API that doesn't require authentication."""
        return False

    def authenticate(self, token: str) -> Optional[UserProfile]:
        logger.warning("Jikan API does not support authentication.")
        return None

    def get_viewer_profile(self) -> Optional[UserProfile]:
        logger.warning("Jikan API does not support user profiles.")
        return None

    def search_media_list(
        self, params: UserMediaListSearchParams
    ) -> Optional[MediaSearchResult]:
        logger.warning("Jikan API does not support fetching user lists.")
        return None

    def update_list_entry(self, params: UpdateUserMediaListEntryParams) -> bool:
        logger.warning("Jikan API does not support updating list entries.")
        return False

    def delete_list_entry(self, media_id: int) -> bool:
        logger.warning("Jikan API does not support deleting list entries.")
        return False

    def get_recommendation_for(
        self, params: MediaRecommendationParams
    ) -> Optional[List[MediaItem]]:
        """Fetches anime recommendations for a given media ID."""
        try:
            endpoint = f"/anime/{params.id}/recommendations"
            raw_data = self._execute_request(endpoint)
            if not raw_data or "data" not in raw_data:
                return None

            recommendations = []
            for item in raw_data["data"]:
                # Jikan recommendation structure has an 'entry' field with anime data
                entry = item.get("entry", {})
                if entry:
                    media_item = mapper._to_generic_media_item(entry)
                    recommendations.append(media_item)

            return recommendations
        except Exception as e:
            logger.error(f"Failed to fetch recommendations for media {params.id}: {e}")
            return None

    def get_characters_of(
        self, params: MediaCharactersParams
    ) -> Optional[CharacterSearchResult]:
        """Fetches characters for a given anime."""
        logger.warning(
            "Jikan API does not support fetching character data in the standardized format."
        )
        return None

    def get_related_anime_for(
        self, params: MediaRelationsParams
    ) -> Optional[List[MediaItem]]:
        """Fetches related anime for a given media ID."""
        try:
            endpoint = f"/anime/{params.id}/relations"
            raw_data = self._execute_request(endpoint)
            if not raw_data or "data" not in raw_data:
                return None

            related_anime = []
            for relation in raw_data["data"]:
                entries = relation.get("entry", [])
                for entry in entries:
                    if entry.get("type") == "anime":
                        # Create a minimal MediaItem from the relation data
                        media_item = MediaItem(
                            id=entry["mal_id"],
                            id_mal=entry["mal_id"],
                            title=MediaTitle(
                                english=entry["name"], romaji=entry["name"], native=None
                            ),
                            cover_image=MediaImage(large=""),
                            description=None,
                            genres=[],
                            studios=[],
                            streaming_episodes={},
                            user_status=None,
                            seasonYear=None,
                        )
                        related_anime.append(media_item)

            return related_anime
        except Exception as e:
            logger.error(f"Failed to fetch related anime for media {params.id}: {e}")
            return None

    def get_notifications(self) -> Optional[List[Notification]]:
        """Jikan is a public API and does not support user notifications."""
        logger.warning("Jikan API does not support fetching user notifications.")
        return None

    def get_airing_schedule_for(
        self, params: MediaAiringScheduleParams
    ) -> Optional[AiringScheduleResult]:
        """Jikan doesn't provide a direct airing schedule endpoint per anime."""
        logger.warning(
            "Jikan API does not support fetching airing schedules for individual anime."
        )
        return None

    def get_global_airing_schedule(
        self, airingAt_greater: int, airingAt_lesser: int, page: int = 1, per_page: int = 50
    ) -> Optional[Any]:
        logger.warning("Jikan API does not support global airing schedules.")
        return None

    def get_reviews_for(
        self, params: MediaReviewsParams
    ) -> Optional[List[MediaReview]]:
        logger.warning("Jikan API does not support reviews.")
        return None

    def mark_notifications_as_read(self) -> bool:
        logger.warning("Jikan API does not support marking notifications.")
        return False

    def transform_raw_search_data(self, raw_data: dict) -> Optional[MediaSearchResult]:
        return mapper.to_generic_search_result(raw_data) if raw_data else None
