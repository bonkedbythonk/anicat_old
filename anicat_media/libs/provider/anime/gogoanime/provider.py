"""AniNeko (formerly GogoAnime) anime provider.

AniNeko is the current incarnation of the GogoAnime network, one of the largest
anime streaming sites. It embeds video from external players (VibePlayer, OtakuVid)
and exposes stream URLs via data-video attributes on the episode page.
"""

import logging
import re
from typing import Iterator, Optional

from ....provider.anime.base import BaseAnimeProvider
from ....provider.anime.params import AnimeParams, EpisodeStreamsParams, SearchParams
from ....provider.anime.types import (
    Anime,
    EpisodeStream,
    MediaTranslationType,
    SearchResults,
    Server,
)
from . import constants, mappers

logger = logging.getLogger(__name__)


class GogoAnime(BaseAnimeProvider):
    """
    Provider for scraping anime data from AniNeko (GogoAnime successor).

    Implements search, get, and episode_streams methods to fetch anime
    information and video stream embed URLs from AniNeko's website.
    """

    HEADERS = {"Referer": constants.ANINEKO_BASE_URL}

    def search(self, params: SearchParams) -> Optional[SearchResults]:
        """
        Search AniNeko for anime matching the query.

        The search/browse page at /browser?keyword=... returns HTML with
        <article> elements for each result.
        """
        search_url = f"{constants.SEARCH_URL}?keyword={params.query}"
        try:
            response = self.client.get(search_url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == 404:
                logger.debug(f"No results found on AniNeko for '{params.query}'")
                return None

            results = mappers.map_to_search_results(response.text)
            if not results or not results.results:
                logger.debug(f"No search results parsed for '{params.query}'")
                return None

            return results
        except Exception as e:
            logger.error(f"Failed to search AniNeko for '{params.query}': {e}")
            return None

    def get(self, params: AnimeParams) -> Optional[Anime]:
        """
        Retrieve detailed info and episode list for a specific anime.

        The anime detail page at /watch/{slug} contains title, metadata,
        and a full episode list with links to each episode.

        If the ID-based lookup fails, falls back to searching by query.
        """
        try:
            slug = params.id.split("?")[0]
            detail_url = f"{constants.WATCH_URL}/{slug}"
            response = self.client.get(detail_url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == 404:
                logger.warning(f"AniNeko anime not found: '{slug}'")
                return None

            anime = mappers.map_to_anime_result(slug, response.text)
            if not anime:
                logger.warning(f"Failed to parse anime details for '{slug}'")
                return None

            return anime
        except Exception:
            logger.debug(
                f"GogoAnime ID lookup failed for '{params.id}', "
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
                logger.debug(
                    f"GogoAnime search returned no results for '{params.query}'"
                )
                return None

            matched = search_results.results[0]
            logger.info(
                f"GogoAnime resolved '{params.id}' -> '{matched.id}' "
                f"via query '{params.query}'"
            )

            slug = matched.id.split("?")[0]
            detail_url = f"{constants.WATCH_URL}/{slug}"
            response = self.client.get(detail_url, follow_redirects=True)
            response.raise_for_status()

            anime = mappers.map_to_anime_result(slug, response.text)
            if not anime:
                logger.warning(
                    f"Failed to parse anime details for resolved slug '{slug}'"
                )
                return None

            return anime
        except Exception as e:
            logger.error(
                f"GogoAnime query fallback failed for '{params.id}': {e}"
            )
            return None

    def episode_streams(
        self, params: EpisodeStreamsParams
    ) -> Optional[Iterator[Server]]:
        """
        Fetch available stream servers for a specific episode.

        The episode page at /watch/{slug}/ep-{N} has server selection buttons
        with data-video attributes pointing to external embed URLs (VibePlayer,
        OtakuVid, etc.). If the direct slug lookup fails, falls back to
        searching by query to resolve the correct slug.
        """
        ep_num = params.episode
        slug = params.anime_id.split("?")[0]

        def _fetch_servers(s: str) -> Optional[list]:
            url = f"{constants.WATCH_URL}/{s}/ep-{ep_num}"
            resp = self.client.get(url, follow_redirects=True)
            resp.raise_for_status()
            if resp.status_code == 404:
                logger.warning(
                    f"Episode not found on AniNeko: '{s}' episode {ep_num}"
                )
                return None
            server_list = mappers.extract_episode_servers(resp.text)
            if not server_list:
                logger.warning(
                    f"No stream servers found for '{s}' episode {ep_num}"
                )
                return None
            return server_list

        # Try the given slug first
        server_list = None
        try:
            server_list = _fetch_servers(slug)
        except Exception:
            logger.debug(
                f"GogoAnime episode_streams failed for slug '{slug}', "
                f"trying query fallback..."
            )

        # Fallback: search by query to resolve slug
        if server_list is None and params.query:
            try:
                search_results = self.search(
                    SearchParams(
                        query=params.query,
                        translation_type=getattr(
                            params, "translation_type", "sub"
                        ),
                    )
                )
                if search_results and search_results.results:
                    resolved = search_results.results[0].id.split("?")[0]
                    logger.info(
                        f"GogoAnime episode_streams resolved "
                        f"'{params.anime_id}' -> '{resolved}' via query"
                    )
                    server_list = _fetch_servers(resolved)
            except Exception as e:
                logger.error(
                    f"GogoAnime episode_streams query fallback failed: {e}"
                )

        if server_list is None:
            return None

        for server_name, embed_url in server_list:
            try:
                # Determine translation type from server name
                translation_type = MediaTranslationType.SUB
                if "dub" in server_name.lower():
                    translation_type = MediaTranslationType.DUB
                elif "raw" in server_name.lower():
                    translation_type = MediaTranslationType.RAW

                # Try to extract a direct mp4/m3u8 from the embed page
                direct_url = self._try_extract_direct_url(embed_url)

                yield Server(
                    name=f"AniNeko - {server_name}",
                    links=[
                        EpisodeStream(
                            link=direct_url or embed_url,
                            quality="auto",
                            translation_type=translation_type,
                            hls=bool(direct_url and ".m3u8" in direct_url),
                        )
                    ],
                    headers={"Referer": constants.ANINEKO_BASE_URL},
                )
            except Exception as e:
                logger.warning(
                    f"Failed to process server '{server_name}' for "
                    f"'{slug}' episode {ep_num}: {e}"
                )
                continue

    def _try_extract_direct_url(self, embed_url: str) -> Optional[str]:
        """
        Attempt to extract a direct video URL from an embed page.

        VibePlayer and OtakuVid embed pages are JavaScript SPAs — scraping
        them directly is unreliable. For now, we return None and let the
        embed URL be used directly. In the future, this could integrate
        yt-dlp or a Node.js-based extractor for these providers.
        """
        try:
            response = self.client.get(embed_url, follow_redirects=True)
            response.raise_for_status()

            # Try common patterns for direct video URLs
            for pattern in [
                r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src\s*:\s*["\']([^"\']+(?:\.mp4|\.m3u8)[^"\']*)["\']',
                r'file\s*:\s*["\']([^"\']+(?:\.mp4|\.m3u8)[^"\']*)["\']',
                r'"file"\s*:\s*"([^"]+(?:\.mp4|\.m3u8)[^"]*)"',
            ]:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return None
