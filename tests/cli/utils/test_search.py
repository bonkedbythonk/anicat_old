from anicat_media.cli.utils.search import find_best_match_title
from anicat_media.libs.media_api.types import MediaItem, MediaTitle
from anicat_media.libs.provider.anime.types import AnimeEpisodes, ProviderName, SearchResult


def _search_result(title: str, season: str, year: str) -> SearchResult:
    return SearchResult(
        id=f"{title}:{season}:{year}",
        title=title,
        episodes=AnimeEpisodes(sub=["1"], dub=["1"], raw=["1"]),
        season=season,
        year=year,
    )


def test_find_best_match_title_prefers_matching_season_year():
    media_item = MediaItem(
        id=1,
        title=MediaTitle(english="The Angel Next Door Spoils Me Rotten"),
        season="SPRING",
        seasonYear=2024,
    )

    results_map = {
        "The Angel Next Door Spoils Me Rotten": _search_result(
            "The Angel Next Door Spoils Me Rotten", "spring", "2023"
        ),
        "The Angel Next Door Spoils Me Rotten 2": _search_result(
            "The Angel Next Door Spoils Me Rotten 2", "spring", "2024"
        ),
    }

    best_title = find_best_match_title(results_map, ProviderName.ANIMEPAHE, media_item)

    assert best_title == "The Angel Next Door Spoils Me Rotten 2"


def test_find_best_match_title_prefers_matching_sequel_number():
    media_item = MediaItem(
        id=2,
        title=MediaTitle(english="The Angel Next Door Spoils Me Rotten 2"),
        seasonYear=None,
    )

    results_map = {
        "The Angel Next Door Spoils Me Rotten": _search_result(
            "The Angel Next Door Spoils Me Rotten", "spring", "2023"
        ),
        "The Angel Next Door Spoils Me Rotten 2": _search_result(
            "The Angel Next Door Spoils Me Rotten 2", "spring", "2024"
        ),
    }

    best_title = find_best_match_title(results_map, ProviderName.ANIMEPAHE, media_item)

    assert best_title == "The Angel Next Door Spoils Me Rotten 2"