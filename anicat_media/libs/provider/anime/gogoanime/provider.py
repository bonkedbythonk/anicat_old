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
        except Exception as e:
            logger.error(f"Failed to get anime details for '{params.id}': {e}")
            return None

    def episode_streams(
        self, params: EpisodeStreamsParams
    ) -> Optional[Iterator[Server]]:
        """
        Fetch available stream servers for a specific episode.

        The episode page at /watch/{slug}/ep-{N} has server selection buttons
        with data-video attributes pointing to external embed URLs (VibePlayer,
        OtakuVid, etc.). We return the embed URLs directly — the built-in web
        player can load them in an iframe.

        Args:
            params: Episode stream parameters containing anime_id and episode number.

        Yields:
            Server objects with embed URLs as EpisodeStream links.
        """
        try:
            slug = params.anime_id.split("?")[0]
            episode = params.episode
            episode_url = f"{constants.WATCH_URL}/{slug}/ep-{episode}"
            response = self.client.get(episode_url, follow_redirects=True)
            response.raise_for_status()

            if response.status_code == 404:
                logger.warning(
                    f"Episode not found on AniNeko: '{slug}' episode {episode}"
                )
                return None

            # Extract server embed URLs from data-video attributes
            servers = mappers.extract_episode_servers(response.text)

            if not servers:
                logger.warning(
                    f"No stream servers found for '{slug}' episode {episode}"
                )
                return None

            for server_name, embed_url in servers:
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
                        f"'{slug}' episode {episode}: {e}"
                    )
                    continue
        except Exception as e:
            logger.error(
                f"Failed to get episode streams for '{params.anime_id}' "
                f"episode {params.episode}: {e}"
            )
            return None

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
