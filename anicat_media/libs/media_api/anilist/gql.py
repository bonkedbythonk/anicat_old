from ....core.constants import GRAPHQL_DIR

_ANILIST_PATH = GRAPHQL_DIR / "anilist"
_QUERIES_PATH = _ANILIST_PATH / "queries"
_MUTATIONS_PATH = _ANILIST_PATH / "mutations"


SEARCH_MEDIA = _QUERIES_PATH / "search.gql"
SEARCH_USER_MEDIA_LIST = _QUERIES_PATH / "media-list.gql"

GET_AIRING_SCHEDULE = _QUERIES_PATH / "media-airing-schedule.gql"
AIRING_SCHEDULE = _QUERIES_PATH / "airing-schedule.gql"
GET_MEDIA_CHARACTERS = _QUERIES_PATH / "media-characters.gql"
GET_MEDIA_RECOMMENDATIONS = _QUERIES_PATH / "media-recommendations.gql"
GET_MEDIA_RELATIONS = _QUERIES_PATH / "media-relations.gql"
GET_MEDIA_LIST_ITEM = _QUERIES_PATH / "media-list-item.gql"

GET_LOGGED_IN_USER = _QUERIES_PATH / "logged-in-user.gql"
GET_NOTIFICATIONS = _QUERIES_PATH / "notifications.gql"
GET_REVIEWS = _QUERIES_PATH / "reviews.gql"
GET_USER_INFO = _QUERIES_PATH / "user-info.gql"


DELETE_MEDIA_LIST_ENTRY = _MUTATIONS_PATH / "delete-list-entry.gql"
MARK_NOTIFICATIONS_AS_READ = _MUTATIONS_PATH / "mark-read.gql"
SAVE_MEDIA_LIST_ENTRY = _MUTATIONS_PATH / "media-list.gql"
