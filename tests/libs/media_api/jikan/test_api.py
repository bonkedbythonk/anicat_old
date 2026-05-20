from unittest.mock import MagicMock

from anicat_media.libs.media_api.jikan.api import JikanApi
from anicat_media.libs.media_api.params import MediaSearchParams
from anicat_media.libs.media_api.types import MediaFormat, MediaGenre, MediaStatus, MediaType


def test_search_media_translates_shared_filters_and_uses_manga_endpoint():
    captured = {}

    def fake_execute_request(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {
            "data": [],
            "pagination": {
                "items": {"total": 0, "per_page": 5},
                "current_page": 2,
                "has_next_page": False,
            },
        }

    api = JikanApi(config=object(), client=MagicMock())
    api._execute_request = fake_execute_request  # type: ignore[method-assign]

    result = api.search_media(
        MediaSearchParams(
            query="clannad",
            type=MediaType.MANGA,
            page=2,
            per_page=5,
            genre_in=[MediaGenre.DRAMA, MediaGenre.ROMANCE],
            seasonYear=2024,
            averageScore_greater=80,
            status=MediaStatus.FINISHED,
            format_in=[MediaFormat.NOVEL],
        )
    )

    assert captured["endpoint"] == "/manga"
    assert captured["params"] == {
        "q": "clannad",
        "page": 2,
        "limit": 5,
        "genres": "8,22",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "min_score": 80,
        "status": "complete",
        "type": "novel",
    }
    assert result is not None
    assert result.page_info.current_page == 2
    assert result.page_info.per_page == 5
