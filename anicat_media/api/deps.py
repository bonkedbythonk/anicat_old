"""Shared API dependencies.

Centralized dependency injection for FastAPI routers.
Provides a single source of truth for accessing the application context
and its most frequently used services.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anicat_media.core.config.model import AppConfig
    from anicat_media.libs.media_api.base import BaseApiClient
    from anicat_media.libs.provider.anime.base import BaseAnimeProvider


def get_ctx():
    """Return the global application context.

    Uses a lazy import to avoid circular dependencies during module loading.
    """
    from ..main import ctx  # noqa: PLC0415

    return ctx


# ---------------------------------------------------------------------------
# Typed FastAPI dependencies — use `Depends(get_config)` in route signatures
# instead of `ctx = get_ctx(); config = ctx.config`.
# ---------------------------------------------------------------------------


def get_config() -> "AppConfig":
    """Return the loaded application configuration."""
    ctx = get_ctx()
    return ctx.config


def get_media_api() -> "BaseApiClient":
    """Return the media API client (AniList)."""
    ctx = get_ctx()
    return ctx.media_api


def get_provider() -> "BaseAnimeProvider":
    """Return the streaming anime provider."""
    ctx = get_ctx()
    return ctx.provider
