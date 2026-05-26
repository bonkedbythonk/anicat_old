from unittest.mock import patch
from anicat_media.libs.provider.anime.anizone.mappers import map_to_search_results


def test_map_to_search_results_with_zero_episodes():
    mock_cards = [
        {
            "slug": "test-slug",
            "title": "Test Title",
            "image_url": "https://anizone.to/images/anime/1.jpg",
            "url": "https://anizone.to/anime/test-slug",
            "ep_count": 0,
            "year": "2024",
            "status": "upcoming",
        }
    ]

    with patch(
        "anicat_media.libs.provider.anime.anizone.mappers._extract_search_cards",
        return_value=mock_cards,
    ):
        results = map_to_search_results("<html></html>")
        assert results is not None
        assert len(results.results) == 1
        assert results.results[0].episodes.sub == []
