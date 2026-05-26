import logging
import re
from functools import lru_cache
from typing import Iterator, Optional

from ..base import BaseAnimeProvider
from ..params import AnimeParams, EpisodeStreamsParams, SearchParams
from ..types import Anime, AnimeEpisodeInfo, SearchResult, SearchResults, Server
from ..utils.debug import debug_provider
from .constants import (
    ANIMEPAHE_BASE,
    ANIMEPAHE_ENDPOINT,
    JUICY_STREAM_REGEX,
    KWIK_HOST,
    REQUEST_HEADERS,
    SERVER_HEADERS,
)
from .extractor import process_animepahe_embed_page
from .mappers import map_to_anime_result, map_to_search_results
from .types import AnimePaheAnimePage, AnimePaheSearchPage

logger = logging.getLogger(__name__)


class AnimePahe(BaseAnimeProvider):
    HEADERS = REQUEST_HEADERS

    def __init__(self, client):
        super().__init__(client)
        self._available = True
        self._last_error: Optional[str] = None
        try:
            self._solve_ddos_guard()
        except Exception as e:
            self._available = False
            self._last_error = f"AnimePahe is unavailable — {e}"
            logger.error(self._last_error)

    @property
    def is_available(self) -> bool:
        """Whether the provider is currently reachable."""
        return self._available

    @property
    def status_message(self) -> Optional[str]:
        """Human-readable status, or None if operating normally."""
        if self._available:
            return None
        return self._last_error or "AnimePahe is unavailable"

    def _solve_ddos_guard(self):
        """Solve DDoS-Guard challenge to get required session cookies.

        Raises RuntimeError on total failure so callers get a clear message.
        """
        import time

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # First hit the main page to get initial cookies
                self.client.get(ANIMEPAHE_BASE)

                # Fetch check.js without the animepahe.pw Host header
                check_resp = self.client.get(
                    "https://check.ddos-guard.net/check.js",
                    headers={"Host": "check.ddos-guard.net"},
                )
                check_resp.raise_for_status()

                # Extract the image paths that set the __ddg2_ cookie
                paths = re.findall(r"['\"]([^'\"]+id[^'\"]+)['\"]", check_resp.text)

                # Fetch each path to finalize cookie setup
                for path in paths:
                    url = path if path.startswith("http") else f"{ANIMEPAHE_BASE}{path}"
                    # Need to use correct Host header for animepahe domains
                    host_header = (
                        "check.ddos-guard.net"
                        if "ddos-guard.net" in url
                        else "animepahe.pw"
                    )
                    self.client.get(url, headers={"Host": host_header})

                logger.debug("DDoS-Guard bypass successful")
                return
            except Exception as e:
                logger.warning(f"DDoS-Guard bypass attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise RuntimeError(
                        "AnimePahe DDoS-Guard bypass failed after 3 attempts. "
                        "The provider may be temporarily blocking automated access."
                    )

    def _ensure_connection(self):
        """Re-solve DDoS-Guard if the provider is currently marked unavailable."""
        if not self._available:
            try:
                self._solve_ddos_guard()
                self._available = True
                self._last_error = None
            except Exception as e:
                self._last_error = f"AnimePahe is unavailable — {e}"
                logger.warning(f"Retried DDoS-Guard bypass but still failed: {e}")

    def _request_with_retry(self, method, *args, **kwargs):
        """Make an HTTP request, retrying DDoS-Guard bypass on 403."""
        response = method(*args, **kwargs)
        if response.status_code == 403:
            logger.warning("Got 403 from AnimePahe, re-trying DDoS-Guard bypass")
            try:
                self._solve_ddos_guard()
                response = method(*args, **kwargs)
            except Exception as e:
                self._available = False
                self._last_error = f"AnimePahe DDoS-Guard bypass failed on retry: {e}"
                logger.error(self._last_error)
        return response

    @debug_provider
    def search(self, params: SearchParams) -> SearchResults | None:
        self._ensure_connection()
        return self._search(params)

    @lru_cache()
    def _search(self, params: SearchParams) -> SearchResults | None:
        url_params = {"m": "search", "q": params.query}
        response = self.client.get(
            ANIMEPAHE_ENDPOINT,
            params=url_params,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        response.raise_for_status()

        # AnimePahe may return HTML on error or empty text
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type and "text/json" not in content_type:
            logger.warning(
                f"Unexpected content type from AnimePahe search: {content_type}"
            )
            # Try parsing as JSON anyway — some servers omit the content-type
            try:
                data: AnimePaheSearchPage = response.json()
            except Exception:
                logger.error("AnimePahe search returned non-JSON response")
                return None
        else:
            data = response.json()

        if not data.get("data"):
            logger.debug(f"No search results for query: {params.query}")
            return None
        return map_to_search_results(data)

    @debug_provider
    def get(self, params: AnimeParams) -> Anime | None:
        self._ensure_connection()
        return self._get_anime(params)

    @lru_cache()
    def _get_anime(self, params: AnimeParams) -> Anime | None:
        page = 1
        standardized_episode_number = 0

        search_result = self._get_search_result(params)
        if not search_result:
            logger.warning(
                f"No search result found for ID {params.id} using query '{params.query}'. Creating fallback SearchResult."
            )
            from ..types import AnimeEpisodes

            search_result = SearchResult(
                id=params.id,
                title=params.query,
                episodes=AnimeEpisodes(sub=[], dub=[]),
                other_titles=[],
                media_type="Anime",
                score=0.0,
                status="Releasing",
                season="Unknown",
                poster="",
                year="Unknown",
            )

        # Use the resolved ID from search results — the cached ID may be
        # stale if the anime was re-indexed on AnimePahe.
        lookup_id = search_result.id
        if lookup_id != params.id:
            logger.info(
                f"AnimePahe using resolved ID '{lookup_id}' "
                f"instead of cached '{params.id}'"
            )

        anime: Optional[AnimePaheAnimePage] = None

        has_next_page = True
        while has_next_page:
            logger.debug(f"Loading page: {page}")
            _anime_page = self._anime_page_loader(
                m="release",
                id=lookup_id,
                sort="episode_asc",
                page=page,
            )

            has_next_page = True if _anime_page["next_page_url"] else False
            page += 1
            if not anime:
                anime = _anime_page
            else:
                anime["data"].extend(_anime_page["data"])

        if anime:
            for episode in anime.get("data", []):
                if episode["episode"] % 1 == 0:
                    standardized_episode_number += 1
                    episode.update({"episode": standardized_episode_number})
                else:
                    standardized_episode_number += episode["episode"] % 1
                    episode.update({"episode": standardized_episode_number})
                    standardized_episode_number = int(standardized_episode_number)

            return map_to_anime_result(search_result, anime)

    @lru_cache()
    def _get_search_result(self, params: AnimeParams) -> Optional[SearchResult]:
        from anicat_media.core.utils.normalizer import normalize_title

        # Collect the first result from any search as a fallback in case
        # none of the results match the cached ID (anime may have been
        # re-indexed on AnimePahe with a different ID).
        first_result: Optional[SearchResult] = None

        # Try 1: Normalized query
        normalized_query = normalize_title(params.query, "animepahe", True)
        search_results = self._search(SearchParams(query=normalized_query))
        if search_results and search_results.results:
            if first_result is None:
                first_result = search_results.results[0]
            for search_result in search_results.results:
                if search_result.id == params.id:
                    return search_result

        # Try 2: Simplified query (first 4 words)
        words = params.query.split()
        if len(words) > 4:
            simplified_query = " ".join(words[:4])
            search_results = self._search(SearchParams(query=simplified_query))
            if search_results and search_results.results:
                if first_result is None:
                    first_result = search_results.results[0]
                for search_result in search_results.results:
                    if search_result.id == params.id:
                        return search_result

        # Try 3: Original raw query
        search_results = self._search(SearchParams(query=params.query))
        if search_results and search_results.results:
            if first_result is None:
                first_result = search_results.results[0]
            for search_result in search_results.results:
                if search_result.id == params.id:
                    return search_result

        # No exact ID match — if any search returned results, use the first
        # one. The anime may have been re-indexed on AnimePahe with a new ID.
        if first_result is not None:
            logger.warning(
                f"AnimePahe ID mismatch: cached '{params.id}' not found in "
                f"search results. Using first search result '{first_result.id}' "
                f"for query '{params.query}'"
            )
            return first_result

        logger.error(
            f"No search results at all for ID {params.id} with query '{params.query}'"
        )
        return None

    @lru_cache()
    def _anime_page_loader(self, m, id, sort, page) -> AnimePaheAnimePage:
        url_params = {
            "m": m,
            "id": id,
            "sort": sort,
            "page": page,
        }
        response = self.client.get(ANIMEPAHE_ENDPOINT, params=url_params)
        response.raise_for_status()
        return response.json()

    @debug_provider
    def episode_streams(self, params: EpisodeStreamsParams) -> Iterator[Server] | None:
        from ...scraping.html_parser import (
            extract_attributes,
            get_element_by_id,
            get_elements_html_by_class,
        )

        episode = self._get_episode_info(params)
        if not episode:
            logger.error(
                f"Episode {params.episode} doesn't exist for anime {params.anime_id}"
            )
            return

        # Resolve anime_id via search in case the cached ID is stale
        resolved_id = params.anime_id
        search_result = self._get_search_result(
            AnimeParams(id=params.anime_id, query=params.query)
        )
        if search_result and search_result.id != params.anime_id:
            resolved_id = search_result.id
            logger.info(
                f"AnimePahe episode_streams using resolved ID "
                f"'{resolved_id}' instead of cached '{params.anime_id}'"
            )

        url = f"{ANIMEPAHE_BASE}/play/{resolved_id}/{episode.session_id}"
        response = self.client.get(url, follow_redirects=True)
        response.raise_for_status()

        c = get_element_by_id("resolutionMenu", response.text)
        if not c:
            logger.error("Resolution menu not found in the response")
            return
        resolutionMenuItems = get_elements_html_by_class("dropdown-item", c)
        res_dicts = [extract_attributes(item) for item in resolutionMenuItems]
        quality = None
        translation_type = None
        stream_link = None

        links = []
        for res_dict in res_dicts:
            # The actual attributes are data attributes prefixed with 'data-'
            # extract_attributes strips the 'data-' prefix
            embed_url = res_dict.get("src", "")
            data_audio = "dub" if res_dict.get("audio") == "eng" else "sub"

            if data_audio != params.translation_type:
                continue

            if not embed_url:
                logger.warning("embed url not found, please report to the developers")
                continue

            # Ensure the embed URL uses the current Kwik domain
            embed_url = re.sub(r"kwik\.\w+", KWIK_HOST, embed_url)

            embed_response = self.client.get(
                embed_url,
                headers={
                    "User-Agent": self.client.headers["User-Agent"],
                    **SERVER_HEADERS,
                },
                follow_redirects=True,
            )
            embed_response.raise_for_status()
            embed_page = embed_response.text

            decoded_js = process_animepahe_embed_page(embed_page)
            if not decoded_js:
                logger.error("failed to decode embed page")
                continue

            juicy_stream = JUICY_STREAM_REGEX.search(decoded_js)
            if not juicy_stream:
                logger.error("failed to find juicy stream URL in decoded JS")
                continue

            juicy_stream = juicy_stream.group(1)
            quality = res_dict.get("resolution", "720")
            translation_type = data_audio
            stream_link = juicy_stream

            if translation_type and quality and stream_link:
                from .mappers import translation_type_map
                from ..types import EpisodeStream

                links.append(
                    EpisodeStream(
                        link=stream_link,
                        quality=quality,  # type: ignore
                        translation_type=translation_type_map[translation_type],
                    )
                )

        if links:
            cookies_str = "; ".join(
                [f"{k}={v}" for k, v in self.client.cookies.items()]
            )
            headers = {
                "Referer": "https://kwik.cx/",
                "User-Agent": self.client.headers["User-Agent"],
                "Cookie": cookies_str,
            }
            yield Server(
                name="kwik", links=links, episode_title=episode.title, headers=headers
            )

    @lru_cache()
    def _get_episode_info(
        self, params: EpisodeStreamsParams
    ) -> Optional[AnimeEpisodeInfo]:
        anime_info = self._get_anime(
            AnimeParams(id=params.anime_id, query=params.query)
        )
        if not anime_info:
            logger.error(f"No anime info for {params.anime_id}")
            return
        if not anime_info.episodes_info:
            logger.error(f"No episodes info for {params.anime_id}")
            return
        for episode in anime_info.episodes_info:
            if episode.episode == params.episode:
                return episode


if __name__ == "__main__":
    from ..utils.debug import test_anime_provider

    test_anime_provider(AnimePahe)
