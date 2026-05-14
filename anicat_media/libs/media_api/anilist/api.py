import logging
from enum import Enum
from typing import Any, List, Optional

from httpx import Client

from ....core.config import AnilistConfig
from ....core.utils.converter import time_to_seconds
from ....core.utils.graphql import (
    execute_graphql,
    invalidate_graphql_cache,
)
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
    MediaItem,
    MediaReview,
    MediaSearchResult,
    Notification,
    UserMediaListStatus,
    UserProfile,
)
from . import gql, mapper

logger = logging.getLogger(__name__)
ANILIST_ENDPOINT = "https://graphql.anilist.co"


user_list_status_map = {
    UserMediaListStatus.WATCHING: "CURRENT",
    UserMediaListStatus.PLANNING: "PLANNING",
    UserMediaListStatus.COMPLETED: "COMPLETED",
    UserMediaListStatus.DROPPED: "DROPPED",
    UserMediaListStatus.PAUSED: "PAUSED",
    UserMediaListStatus.REPEATING: "REPEATING",
}

# TODO: Just remove and have consistent variable naming between the two
search_params_map = {
    # Custom Name: AniList Variable Name
    "query": "query",
    "page": "page",
    "per_page": "per_page",
    "sort": "sort",
    "id_in": "id_in",
    "genre_in": "genre_in",
    "genre_not_in": "genre_not_in",
    "tag_in": "tag_in",
    "tag_not_in": "tag_not_in",
    "status_in": "status_in",
    "status": "status",
    "status_not_in": "status_not_in",
    "popularity_greater": "popularity_greater",
    "popularity_lesser": "popularity_lesser",
    "averageScore_greater": "averageScore_greater",
    "averageScore_lesser": "averageScore_lesser",
    "seasonYear": "seasonYear",
    "season": "season",
    "startDate_greater": "startDate_greater",
    "startDate_lesser": "startDate_lesser",
    "startDate": "startDate",
    "endDate_greater": "endDate_greater",
    "endDate_lesser": "endDate_lesser",
    "format_in": "format_in",
    "type": "type",
    "on_list": "on_list",
}


class AniListApi(BaseApiClient):
    """AniList API implementation of the BaseApiClient contract."""

    def __init__(self, config: AnilistConfig, client: Client):
        super().__init__(config, client)
        self.token: Optional[str] = None
        self.user_profile: Optional[UserProfile] = None

    def authenticate(self, token: str) -> Optional[UserProfile]:
        self.token = token
        self.http_client.headers["Authorization"] = f"Bearer {token}"
        
        # We try to fetch the profile, but we DON'T clear the token if it fails.
        # Failing to fetch profile usually means we are offline, not that the token is bad.
        try:
            self.user_profile = self.get_viewer_profile()
        except Exception as e:
            logger.warning(f"Failed to fetch viewer profile during auth (likely offline): {e}")
            self.user_profile = None
            
        return self.user_profile

    def is_authenticated(self) -> bool:
        """Returns True if we have a token, regardless of connection status."""
        return self.token is not None

    def is_connected(self) -> bool:
        """Returns True if we have successfully fetched the user profile."""
        return self.user_profile is not None

    def get_viewer_profile(self) -> Optional[UserProfile]:
        if not self.token:
            return None
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_LOGGED_IN_USER, {}
        )
        return mapper.to_generic_user_profile(response.json())

    def search_media(self, params: MediaSearchParams) -> Optional[MediaSearchResult]:
        variables = {
            search_params_map[k]: v
            for k, v in params.__dict__.items()
            if v is not None and not isinstance(v, Enum)
        }

        # handle case where value is an enum
        variables.update(
            {
                search_params_map[k]: v.value
                for k, v in params.__dict__.items()
                if v is not None and isinstance(v, Enum)
            }
        )

        # handle case where is a list of enums
        variables.update(
            {
                search_params_map[k]: list(map(lambda item: item.value, v))
                for k, v in params.__dict__.items()
                if v is not None and isinstance(v, list) and isinstance(v[0], Enum)
            }
        )

        variables["per_page"] = params.per_page or self.config.per_page

        # ignore hentai by default
        variables["genre_not_in"] = (
            list(map(lambda item: item.value, params.genre_not_in))
            if params.genre_not_in
            else ["Hentai"]
        )

        # anime by default
        variables["type"] = params.type.value if params.type else "ANIME"
        response = execute_graphql(
            ANILIST_ENDPOINT,
            self.http_client,
            gql.SEARCH_MEDIA,
            variables,
            use_cache=True,
            ttl=time_to_seconds(self.config.parent.general.max_cache_lifetime)  # type: ignore
            if hasattr(self.config, "parent")
            else 10800,
        )
        return mapper.to_generic_search_result(response.json())

    def get_media_item(self, media_id: int) -> Optional[MediaItem]:
        """Fetch a single media item by ID, bypassing long-term cache."""
        variables = {
            "id_in": [media_id],
            "per_page": 1,
        }
        response = execute_graphql(
            ANILIST_ENDPOINT,
            self.http_client,
            gql.SEARCH_MEDIA,
            variables,
            use_cache=True,
            ttl=300,  # 5 minutes for individual item refresh
        )
        result = mapper.to_generic_search_result(response.json())
        if result and result.media:
            return result.media[0]
        return None

    def search_media_list(
        self, params: UserMediaListSearchParams
    ) -> Optional[MediaSearchResult]:
        if not self.user_profile:
            logger.error("Cannot fetch user list: user is not authenticated.")
            return None

        # TODO: use consistent variable naming btw graphql and params
        # so variables can be dynamically filled
        variables = {
            "sort": params.sort.value
            if params.sort
            else self.config.media_list_sort_by.value,
            "userId": self.user_profile.id,
            "status": user_list_status_map[params.status] if params.status else None,
            "page": params.page,
            "perPage": params.per_page or self.config.per_page,
            "type": params.type.value if params.type else "ANIME",
        }
        response = execute_graphql(
            ANILIST_ENDPOINT,
            self.http_client,
            gql.SEARCH_USER_MEDIA_LIST,
            variables,
            use_cache=True,
            ttl=300,  # 5 minutes for user lists
        )
        return mapper.to_generic_user_list_result(response.json()) if response else None

    def update_list_entry(self, params: UpdateUserMediaListEntryParams) -> bool:
        if not self.token:
            return False
        score_raw = int(params.score * 10) if params.score is not None else None
        variables = {
            "mediaId": params.media_id,
            "status": user_list_status_map[params.status] if params.status else None,
            "progress": int(float(params.progress)) if params.progress is not None else None,
            "scoreRaw": score_raw,
        }
        variables = {k: v for k, v in variables.items() if v is not None}
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.SAVE_MEDIA_LIST_ENTRY, variables
        )
        success = response.json() is not None and "errors" not in response.json()
        if success:
            # Invalidate the user list cache because it's now stale
            # We don't know the exact variables used for list fetching,
            # but we can at least ensure future fetches for this media are fresh
            # or just rely on the 5-minute TTL.
            # For now, let's invalidate the specific list item if possible.
            invalidate_graphql_cache(ANILIST_ENDPOINT, gql.GET_MEDIA_LIST_ITEM, {"mediaId": params.media_id})
            invalidate_graphql_cache(ANILIST_ENDPOINT, gql.SEARCH_MEDIA, {"id": params.media_id})
            
        return success

    def delete_list_entry(self, media_id: int) -> bool:
        if not self.token:
            return False
        response = execute_graphql(
            ANILIST_ENDPOINT,
            self.http_client,
            gql.GET_MEDIA_LIST_ITEM,
            {"mediaId": media_id},
        )
        entry_data = response.json()

        list_id = (
            entry_data.get("data", {}).get("MediaList", {}).get("id")
            if entry_data
            else None
        )
        if not list_id:
            return False
        response = execute_graphql(
            ANILIST_ENDPOINT,
            self.http_client,
            gql.DELETE_MEDIA_LIST_ENTRY,
            {"id": list_id},
        )
        return (
            response.json()
            .get("data", {})
            .get("DeleteMediaListEntry", {})
            .get("deleted", False)
            if response
            else False
        )

    def get_recommendation_for(
        self, params: MediaRecommendationParams
    ) -> Optional[List[MediaItem]]:
        variables = {
            "id": params.id,
            "page": params.page,
            "per_page": params.per_page or 50,
        }
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_MEDIA_RECOMMENDATIONS, variables
        )
        return mapper.to_generic_recommendations(response.json())

    def get_characters_of(
        self, params: MediaCharactersParams
    ) -> Optional[CharacterSearchResult]:
        variables = {"id": params.id, "type": params.type.value if params.type else "ANIME"}
        logger.info(f"Fetching characters for media {params.id} (type: {variables['type']})")
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_MEDIA_CHARACTERS, variables
        )
        if response and "errors" not in response.json():
            return mapper.to_generic_characters_result(response.json())
        
        if response and "errors" in response.json():
            logger.error(f"AniList GQL Errors: {response.json()['errors']}")
            
        return None

    def get_related_anime_for(
        self, params: MediaRelationsParams
    ) -> Optional[List[MediaItem]]:
        variables = {"id": params.id, "format_in": None}
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_MEDIA_RELATIONS, variables
        )
        return mapper.to_generic_relations(response.json())

    def get_airing_schedule_for(
        self, params: MediaAiringScheduleParams
    ) -> Optional[AiringScheduleResult]:
        variables = {"id": params.id, "type": "ANIME"}
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_AIRING_SCHEDULE, variables
        )
        if response and "errors" not in response.json():
            return mapper.to_generic_airing_schedule_result(response.json())
        return None

    def get_reviews_for(
        self, params: MediaReviewsParams
    ) -> Optional[List[MediaReview]]:
        variables = {
            "id": params.id,
            "page": params.page,
            "per_page": params.per_page or 10,  # Default to 10 reviews
        }
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_REVIEWS, variables
        )
        if response and "errors" not in response.json():
            return mapper.to_generic_reviews_list(response.json())
        return None

    def get_notifications(self) -> Optional[List[Notification]]:
        """Fetches the user's unread notifications from AniList."""
        if not self.is_authenticated():
            logger.warning("Cannot fetch notifications: user is not authenticated.")
            return None

        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_NOTIFICATIONS, {}
        )
        if response and "errors" not in response.json():
            return mapper.to_generic_notifications(response.json())
        logger.error(f"Failed to fetch notifications: {response.text}")
        return None

    def mark_notifications_as_read(self) -> bool:
        """Mark all notifications as read on AniList by performing a reset fetch."""
        if not self.token:
            return False
        
        # We fetch a tiny page just to trigger the reset flag on AniList's end
        variables = {
            "resetNotificationCount": True,
            "type": "AIRING",
            "perPage": 1
        }
        
        response = execute_graphql(
            ANILIST_ENDPOINT, self.http_client, gql.GET_NOTIFICATIONS, variables
        )
        return response.json() is not None and "errors" not in response.json()
    def transform_raw_search_data(self, raw_data: dict) -> Optional[MediaSearchResult]:
        """
        Transform raw AniList API response data into a MediaSearchResult.

        Args:
            raw_data: Raw response data from the AniList GraphQL API

        Returns:
            MediaSearchResult object or None if transformation fails
        """
        try:
            return mapper.to_generic_search_result(raw_data)
        except Exception as e:
            logger.error(f"Failed to transform raw search data: {e}")
            return None


if __name__ == "__main__":
    from httpx import Client

    from ....core.config import AnilistConfig
    from ..utils.debug import test_media_api

    anilist = AniListApi(AnilistConfig(), Client())
    test_media_api(anilist)
