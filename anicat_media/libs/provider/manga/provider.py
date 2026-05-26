import importlib
import logging

from httpx import Client

from .base import BaseMangaProvider
from .types import MangaProviderName

logger = logging.getLogger(__name__)

PROVIDERS_AVAILABLE = {
    "mangadex": "api.MangaDexApi",
    "mangakatana": "api.MangaKatanaApi",
}


class MangaProviderFactory:
    """Factory for creating manga provider instances."""

    @staticmethod
    def create(provider_name: MangaProviderName) -> BaseMangaProvider:
        """
        Dynamically creates an instance of the specified manga provider.
        """
        from ....core.utils.networking import random_user_agent

        # Correctly determine module and class name from the map
        import_path = PROVIDERS_AVAILABLE[provider_name.value.lower()]
        module_name, class_name = import_path.split(".", 1)

        # Construct the full package path for dynamic import
        package_path = f"anicat_media.libs.provider.manga.{provider_name.value.lower()}"

        try:
            provider_module = importlib.import_module(f".{module_name}", package_path)
            provider_class = getattr(provider_module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(
                f"Failed to load manga provider '{provider_name.value.lower()}': {e}"
            )
            raise ImportError(
                f"Could not load manga provider '{provider_name.value.lower()}'. "
                "Check the module path and class name in PROVIDERS_AVAILABLE."
            ) from e

        # Each provider class requires an httpx.Client, which we set up here.
        client = Client(
            headers={
                "User-Agent": random_user_agent(),
                "Accept-Encoding": "identity",
                **getattr(provider_class, "HEADERS", {}),
            }
        )

        return provider_class(client)


# Simple alias for ease of use
create_manga_provider = MangaProviderFactory.create
