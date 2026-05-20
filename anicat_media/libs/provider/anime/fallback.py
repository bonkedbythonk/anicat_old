"""Fallback anime provider that tries multiple providers in sequence.

When a provider fails to return results, the fallback provider automatically
tries the next provider in the configured chain. This ensures users get content
even when their primary provider is down or missing a specific title.
"""

import logging
from typing import TYPE_CHECKING, Iterator, List, Optional

from .params import AnimeParams, EpisodeStreamsParams, SearchParams

if TYPE_CHECKING:
    from .base import BaseAnimeProvider
    from .types import Anime, SearchResults, Server

logger = logging.getLogger(__name__)


class FallbackAnimeProvider:
    """
    Wraps multiple BaseAnimeProvider instances and delegates calls to each
    in order until one returns a successful result.

    Usage:
        providers = [animepahe, gogoanime, hianime]
        fallback = FallbackAnimeProvider(providers)
        results = fallback.search(params)  # tries animepahe first, then gogoanime, etc.
    """

    def __init__(self, providers: List["BaseAnimeProvider"]) -> None:
        if not providers:
            raise ValueError("FallbackAnimeProvider requires at least one provider.")
        self._providers = providers

    @property
    def providers(self) -> List["BaseAnimeProvider"]:
        """The list of wrapped providers, in fallback order."""
        return self._providers

    @property
    def primary(self) -> "BaseAnimeProvider":
        """The first (primary) provider in the chain."""
        return self._providers[0]

    def search(self, params: SearchParams) -> "Optional[SearchResults]":
        """
        Search across providers in fallback order.

        Each provider is tried until one returns non-None results.
        """
        for i, provider in enumerate(self._providers):
            try:
                results = provider.search(params)
                if results and results.results:
                    if i > 0:
                        logger.info(
                            f"Fallback: '{params.query}' not found on primary "
                            f"provider, resolved via {provider.__class__.__name__}"
                        )
                    return results
                elif i == 0:
                    logger.debug(
                        f"Primary provider {provider.__class__.__name__} "
                        f"returned no results for '{params.query}', trying fallbacks..."
                    )
            except Exception as e:
                logger.warning(
                    f"Provider {provider.__class__.__name__} search failed "
                    f"for '{params.query}': {e}"
                )
                continue

        logger.warning(f"No provider returned results for '{params.query}'")
        return None

    def get(self, params: AnimeParams) -> "Optional[Anime]":
        """
        Get anime details across providers in fallback order.
        """
        for i, provider in enumerate(self._providers):
            try:
                anime = provider.get(params)
                if anime is not None:
                    if i > 0:
                        logger.info(
                            f"Fallback: anime details for '{params.id}' resolved "
                            f"via {provider.__class__.__name__}"
                        )
                    return anime
            except Exception as e:
                logger.warning(
                    f"Provider {provider.__class__.__name__} get failed "
                    f"for '{params.id}': {e}"
                )
                continue

        logger.warning(f"No provider returned anime details for '{params.id}'")
        return None

    def episode_streams(
        self, params: EpisodeStreamsParams
    ) -> "Optional[Iterator[Server]]":
        """
        Get episode streams across providers in fallback order.

        Returns the first non-None, non-empty iterator. Since iterators
        are consumed lazily, we peek at the first item to verify the
        provider actually has streams.
        """
        for i, provider in enumerate(self._providers):
            try:
                streams_iter = provider.episode_streams(params)
                if streams_iter is None:
                    continue

                # Peek at the first server to verify we have results
                try:
                    first = next(streams_iter)
                except StopIteration:
                    continue

                if i > 0:
                    logger.info(
                        f"Fallback: streams for '{params.anime_id}' episode "
                        f"{params.episode} resolved via {provider.__class__.__name__}"
                    )

                # Rebuild iterator with the peeked item first
                def _rebuild_iterator(first_item, rest_iterator, p):
                    yield first_item
                    yield from rest_iterator

                return _rebuild_iterator(first, streams_iter, provider)
            except Exception as e:
                logger.warning(
                    f"Provider {provider.__class__.__name__} episode_streams "
                    f"failed for '{params.anime_id}' episode {params.episode}: {e}"
                )
                continue

        logger.warning(
            f"No provider returned streams for '{params.anime_id}' "
            f"episode {params.episode}"
        )
        return None
