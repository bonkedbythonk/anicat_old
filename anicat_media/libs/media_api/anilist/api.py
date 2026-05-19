import logging
from enum import Enum
from typing import Any, List, Optional

from httpx import Client
import httpx

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
        # Temporary storage to test validity
        original_token = self.token
        self.token = token
        self.http_client.headers["Authorization"] = f"Bearer {token}"
        
        try:
            profile = self.get_viewer_profile()
            if profile:
                self.user_profile = profile
                return profile
            else:
                # If profile is None, the token is likely invalid
                self.token = original_token
                if original_token:
                    self.http_client.headers["Authorization"] = f"Bearer {original_token}"
                else:
                    if "Authorization" in self.http_client.headers:
                        del self.http_client.headers["Authorization"]
                return None
        except httpx.RequestError as e:
            logger.warning(f"Failed to fetch viewer profile during auth due to network error: {e}")
            # Keep the token on connection errors.
            raise
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response is not None else 0
            # Invalid/expired token should be handled as auth failure, not offline.
            if status_code in (400, 401, 403):
                logger.warning(
                    f"Failed to fetch viewer profile during auth due to invalid token response ({status_code})."
                )
                self.token = original_token
                if original_token:
                    self.http_client.headers["Authorization"] = f"Bearer {original_token}"
                else:
                    if "Authorization" in self.http_client.headers:
                        del self.http_client.headers["Authorization"]
                return None

            logger.warning(f"Failed to fetch viewer profile during auth due to HTTP error: {e}")
            raise
        except Exception as e:
            logger.warning(f"Failed to fetch viewer profile during auth: {e}")
            self.token = original_token
            if original_token:
                self.http_client.headers["Authorization"] = f"Bearer {original_token}"
            else:
                if "Authorization" in self.http_client.headers:
                    del self.http_client.headers["Authorization"]
            return None

    def is_authenticated(self) -> bool:
        """Returns True if we have a token, regardless of connection status."""
        return self.token is not None

    def is_connected(self) -> bool:
        """Returns True if we have successfully fetched the user profile."""
        return self.user_profile is not None

    def get_viewer_profile(self) -> Optional[UserProfile]:
        if not self.token:
            return None
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_LOGGED_IN_USER, {}
            )
            
            if response.status_code != 200:
                logger.warning(f"AniList profile fetch failed with status {response.status_code}: {response.text}")
                return None
                
            data = response.json()
            if "errors" in data:
                logger.warning(f"AniList profile fetch returned errors: {data['errors']}")
                return None
                
            return mapper.to_generic_user_profile(data)
        except Exception as e:
            logger.warning(f"get_viewer_profile failed: {e}")
            if isinstance(e, (httpx.RequestError, httpx.HTTPStatusError)):
                raise
            return None

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
        try:
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
        except Exception as e:
            logger.warning(f"search_media failed: {e}")
            return None

    def get_media_item(self, media_id: int) -> Optional[MediaItem]:
        """Fetch a single media item by ID, bypassing long-term cache."""
        variables = {
            "id_in": [media_id],
            "per_page": 1,
        }
        try:
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
        except Exception as e:
            logger.warning(f"get_media_item failed: {e}")
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
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT,
                self.http_client,
                gql.SEARCH_USER_MEDIA_LIST,
                variables,
                use_cache=True,
                ttl=300,  # 5 minutes for user lists
            )
            return mapper.to_generic_user_list_result(response.json()) if response else None
        except Exception as e:
            logger.warning(f"search_media_list failed: {e}")
            return None

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
        try:
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
                invalidate_graphql_cache(ANILIST_ENDPOINT, gql.SEARCH_MEDIA, {"id_in": [params.media_id], "per_page": 1})
                
            return success
        except Exception as e:
            logger.warning(f"update_list_entry failed: {e}")
            return False

    def delete_list_entry(self, media_id: int) -> bool:
        if not self.token:
            return False
        try:
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
            deleted = (
                response.json()
                .get("data", {})
                .get("DeleteMediaListEntry", {})
                .get("deleted", False)
                if response
                else False
            )
            if deleted:
                invalidate_graphql_cache(ANILIST_ENDPOINT, gql.SEARCH_MEDIA, {"id_in": [media_id], "per_page": 1})
            return deleted
        except Exception as e:
            logger.warning(f"delete_list_entry failed: {e}")
            return False

    def get_recommendation_for(
        self, params: MediaRecommendationParams
    ) -> Optional[List[MediaItem]]:
        variables = {
            "id": params.id,
            "page": params.page,
            "per_page": params.per_page or 50,
        }
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_MEDIA_RECOMMENDATIONS, variables
            )
            return mapper.to_generic_recommendations(response.json())
        except Exception as e:
            logger.warning(f"get_recommendation_for failed: {e}")
            return None

    def get_characters_of(
        self, params: MediaCharactersParams
    ) -> Optional[CharacterSearchResult]:
        variables = {"id": params.id, "type": params.type.value if params.type else "ANIME"}
        logger.info(f"Fetching characters for media {params.id} (type: {variables['type']})")
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_MEDIA_CHARACTERS, variables
            )
            if response and "errors" not in response.json():
                return mapper.to_generic_characters_result(response.json())
            
            if response and "errors" in response.json():
                logger.error(f"AniList GQL Errors: {response.json()['errors']}")
        except Exception as e:
            logger.warning(f"get_characters_of failed: {e}")
        return None

    def get_related_anime_for(
        self, params: MediaRelationsParams
    ) -> Optional[List[MediaItem]]:
        variables = {"id": params.id, "format_in": None}
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_MEDIA_RELATIONS, variables
            )
            return mapper.to_generic_relations(response.json())
        except Exception as e:
            logger.warning(f"get_related_anime_for failed: {e}")
            return None

    def get_airing_schedule_for(
        self, params: MediaAiringScheduleParams
    ) -> Optional[AiringScheduleResult]:
        variables = {"id": params.id, "type": "ANIME"}
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_AIRING_SCHEDULE, variables
            )
            if response and "errors" not in response.json():
                return mapper.to_generic_airing_schedule_result(response.json())
        except Exception as e:
            logger.warning(f"get_airing_schedule_for failed: {e}")
        return None

    def get_global_airing_schedule(
        self, airingAt_greater: int, airingAt_lesser: int, page: int = 1, per_page: int = 50,
        media_ids: Optional[List[int]] = None
    ) -> Optional[Any]:
        variables: dict[str, Any] = {
            "airingAt_greater": airingAt_greater,
            "airingAt_lesser": airingAt_lesser,
            "page": page,
            "perPage": per_page
        }
        if media_ids:
            variables["mediaId_in"] = media_ids
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.AIRING_SCHEDULE, variables
            )
            if response is not None:
                if not response.is_success:
                    logger.error(f"AniList API error (Status {response.status_code}): {response.text}")
                    return None
                res_json = response.json()
                if "errors" in res_json:
                    logger.error(f"GraphQL errors in schedule: {res_json['errors']}")
                    return None
                return mapper.to_generic_global_schedule(res_json)
        except Exception as e:
            logger.warning(f"get_global_airing_schedule failed: {e}")
        return None

    def get_reviews_for(
        self, params: MediaReviewsParams
    ) -> Optional[List[MediaReview]]:
        variables = {
            "id": params.id,
            "page": params.page,
            "per_page": params.per_page or 10,  # Default to 10 reviews
        }
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_REVIEWS, variables
            )
            if response and "errors" not in response.json():
                return mapper.to_generic_reviews_list(response.json())
        except Exception as e:
            logger.warning(f"get_reviews_for failed: {e}")
        return None

    def get_notifications(self) -> Optional[List[Notification]]:
        """Fetches the user's unread notifications from AniList."""
        if not self.is_authenticated():
            logger.warning("Cannot fetch notifications: user is not authenticated.")
            return None

        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_NOTIFICATIONS, {}
            )
            if response and "errors" not in response.json():
                return mapper.to_generic_notifications(response.json())
            logger.error(f"Failed to fetch notifications: {response.text}")
        except Exception as e:
            logger.warning(f"get_notifications failed: {e}")
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
        
        try:
            response = execute_graphql(
                ANILIST_ENDPOINT, self.http_client, gql.GET_NOTIFICATIONS, variables
            )
            return response.json() is not None and "errors" not in response.json()
        except Exception as e:
            logger.warning(f"mark_notifications_as_read failed: {e}")
            return False
    def transform_raw_search_data(self, raw_data: dict) -> Optional[MediaSearchResult]:
        """
        Transform raw AniList API response data into a MediaSearchResult.

        Args:
            raw_data: Raw response data from the AniList GraphQL API

        Returns:
            MediaSearchResult object or None if transformation fails
        """
        try:
            return mapper.to_generic_search_result(raw_data)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to transform raw search data: {e}")
            return None


if __name__ == "__main__":
    from httpx import Client

    from ....core.config import AnilistConfig
    from ..utils.debug import test_media_api

    anilist = AniListApi(AnilistConfig(), Client())
    test_media_api(anilist)
