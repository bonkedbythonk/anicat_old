import logging

from httpx import Client

from .base import BaseAnimeProvider
from .types import ProviderName

# Explicit imports — avoids importlib fragility and helps PyInstaller detect modules
from .animepahe.provider import AnimePahe
from .anizone.provider import AniZone
from .gogoanime.provider import GogoAnime
from .hianime.provider import HiAnime

logger = logging.getLogger(__name__)


class AnimeProviderFactory:
    """Factory for creating anime provider instances."""

    _PROVIDER_CLASSES = {
        "animepahe": AnimePahe,
        "anizone": AniZone,
        "gogoanime": GogoAnime,
        "hianime": HiAnime,
    }

    @staticmethod
    def create(provider_name: ProviderName) -> BaseAnimeProvider:
        """
        Creates an instance of the specified anime provider with a pre-configured HTTP client.

        Args:
            provider_name: The name of the provider to create.

        Returns:
            An instance of a class that inherits from BaseAnimeProvider.

        Raises:
            ValueError: If the provider_name is not supported.
        """
        from ....core.utils.networking import random_user_agent

        key = provider_name.value.lower()
        provider_class = AnimeProviderFactory._PROVIDER_CLASSES.get(key)
        if provider_class is None:
            raise ValueError(f"Unsupported anime provider: {provider_name.value}")

        client = Client(
            headers={
                "User-Agent": random_user_agent(),
                "Accept-Encoding": "identity",
                **provider_class.HEADERS,
            }
        )

        return provider_class(client)


# Simple alias for ease of use, consistent with other factories in the codebase.
create_provider = AnimeProviderFactory.create
