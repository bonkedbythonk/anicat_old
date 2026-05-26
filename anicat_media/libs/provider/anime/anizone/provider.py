"""AniZone anime provider.

AniZone (anizone.to) is a Laravel Livewire anime streaming site using the
Vidstack player. Stream URLs are direct .m3u8 master playlists served via
Cloudflare (seiryuu.vid-cdn.xyz) — fully MPV-compatible with no anti-bot
byteimg-style blocking.

Architecture:
- Server-rendered HTML with Livewire hydration
- Search: GET /anime?search={query}
- Detail: GET /anime/{slug}
- Episode: GET /anime/{slug}/{ep}
- Stream: embedded in <media-player src="...master.m3u8">
"""

import logging
from typing import Iterator, Optional
from urllib.parse import quote_plus

from ....provider.anime.base import BaseAnimeProvider
from ....provider.anime.params import AnimeParams, EpisodeStreamsParams, SearchParams
from ....provider.anime.types import (
    Anime,
    AnimeEpisodes,
    EpisodeStream,
    SearchResults,
    Server,
)
from . import constants, mappers

logger = logging.getLogger(__name__)


class AniZone(BaseAnimeProvider):
    """Provider for scraping anime data from AniZone (anizone.to)."""

    HEADERS = {"Referer": constants.REFERER_HEADER}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, params: SearchParams) -> Optional[SearchResults]:
        """Search AniZone for anime matching the query.

        Uses GET /anime?search={query}. Results are server-rendered HTML.
        """
        search_url = f"{constants.SEARCH_URL}?search={quote_plus(params.query)}"
        try:
            response = self.client.get(search_url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == 404:
                logger.debug(f"No results found on AniZone for '{params.query}'")
                return None

            results = mappers.map_to_search_results(response.text)
            if results is None:
                logger.debug(
                    f"Failed to parse AniZone search results for '{params.query}'"
                )
            return results
        except Exception:
            logger.exception(
                f"Failed to perform search on AniZone for query '{params.query}'"
            )
            return None

    # ------------------------------------------------------------------
    # Anime detail
    # ------------------------------------------------------------------

    def get(self, params: AnimeParams) -> Optional[Anime]:
        """Fetch anime metadata from the detail page.

        Uses GET /anime/{slug}. If the ID-based lookup fails, falls back
        to searching by query to resolve the correct slug.
        """
        detail_url = f"{constants.WATCH_URL}/{params.id}"
        try:
            response = self.client.get(detail_url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == 404:
                logger.debug(f"AniZone anime not found: {params.id}")
                return None

            anime = mappers.map_to_anime_result(response.text, params.id)
            if anime is None:
                logger.debug(f"Failed to parse AniZone detail for '{params.id}'")
            return anime
        except Exception:
            logger.debug(
                f"AniZone ID lookup failed for '{params.id}', "
                f"trying query-based search..."
            )

        # Fallback: search by query to resolve the correct slug
        if not params.query:
            logger.debug(f"No query provided to fallback search for '{params.id}'")
            return None

        try:
            search_results = self.search(
                SearchParams(
                    query=params.query,
                    translation_type=getattr(params, "translation_type", "sub"),
                )
            )
            if not search_results or not search_results.results:
                logger.debug(f"AniZone search returned no results for '{params.query}'")
                return None

            matched = search_results.results[0]
            logger.info(
                f"AniZone resolved '{params.id}' -> '{matched.id}' "
                f"via query '{params.query}'"
            )

            # Retry with the resolved slug
            resolved_url = f"{constants.WATCH_URL}/{matched.id}"
            response = self.client.get(resolved_url, follow_redirects=True)
            response.raise_for_status()

            anime = mappers.map_to_anime_result(response.text, matched.id)
            if anime is None:
                logger.debug(
                    f"Failed to parse AniZone detail for resolved slug '{matched.id}'"
                )
            return anime
        except Exception as e:
            logger.exception(f"AniZone query fallback failed for '{params.id}': {e}")
            return None

    # ------------------------------------------------------------------
    # Episode streams
    # ------------------------------------------------------------------

    def episode_streams(self, params: EpisodeStreamsParams) -> Iterator[Server]:
        """Yield stream servers for a specific episode.

        Fetches the episode page at /anime/{slug}/{ep} and extracts the
        master.m3u8 URL from the <media-player> element.

        AniZone uses a single server (seiryuu.vid-cdn.xyz) per episode
        with multiple quality levels in the HLS playlist.
        """
        ep_num = params.episode
        slug = params.anime_id

        def _fetch_one(s: str) -> Optional[Server]:
            url = f"{constants.WATCH_URL}/{s}/{ep_num}"
            resp = self.client.get(url, follow_redirects=True)
            resp.raise_for_status()
            if resp.status_code == 404:
                logger.debug(f"AniZone episode not found: {s}/{ep_num}")
                return None
            stream_url = mappers.extract_stream_url(resp.text)
            if not stream_url:
                logger.debug(f"No stream URL on AniZone for {s}/{ep_num}")
                return None
            subtitles = mappers.extract_subtitles(resp.text)
            return Server(
                name="AniZone",
                links=[EpisodeStream(link=stream_url, hls=True)],
                subtitles=subtitles,
            )

        # Try the given slug first
        try:
            server = _fetch_one(slug)
            if server:
                yield server
                return
        except Exception:
            logger.debug(
                f"AniZone episode_streams failed for slug '{slug}', "
                f"trying query fallback..."
            )

        # Fallback: search by query to resolve slug
        if not params.query:
            return
        try:
            search_results = self.search(
                SearchParams(
                    query=params.query,
                    translation_type=getattr(params, "translation_type", "sub"),
                )
            )
            if search_results and search_results.results:
                resolved = search_results.results[0].id
                logger.info(
                    f"AniZone episode_streams resolved '{params.anime_id}' "
                    f"-> '{resolved}' via query"
                )
                server = _fetch_one(resolved)
                if server:
                    yield server
        except Exception as e:
            logger.exception(f"AniZone episode_streams query fallback failed: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_episodes(self, anime_id: str) -> Optional[AnimeEpisodes]:
        """Fetch episode list by loading episode 1 and extracting sidebar."""
        episode_url = f"{constants.WATCH_URL}/{anime_id}/1"
        try:
            response = self.client.get(episode_url, follow_redirects=True)
            response.raise_for_status()
            episodes = mappers.extract_episodes_from_episode_page(
                response.text, anime_id
            )
            if episodes:
                return AnimeEpisodes(sub=[e.episode for e in episodes])
        except Exception:
            logger.exception(f"Failed to fetch episodes for AniZone anime '{anime_id}'")
        return None
