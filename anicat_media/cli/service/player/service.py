import logging
from typing import Optional

from anicat_media.core.config import AppConfig
from ....libs.media_api.types import MediaItem
from ....libs.player.base import BasePlayer
from ....libs.player.params import PlayerParams
from ....libs.player.player import create_player
from ....libs.player.types import PlayerResult
from ....libs.provider.anime.base import BaseAnimeProvider
from ....libs.provider.anime.types import Anime
from ..registry import MediaRegistryService

logger = logging.getLogger(__name__)


class PlayerService:
    app_config: AppConfig
    provider: BaseAnimeProvider
    player: BasePlayer
    registry: Optional[MediaRegistryService] = None
    local: bool = False

    def __init__(
        self,
        app_config: AppConfig,
        provider: BaseAnimeProvider,
        registry: Optional[MediaRegistryService] = None,
    ):
        self.app_config = app_config
        self.provider = provider
        self.registry = registry
        self.player = create_player(app_config)

    def play(
        self,
        params: PlayerParams,
        anime: Optional[Anime] = None,
        media_item: Optional[MediaItem] = None,
        local: bool = False,
    ) -> PlayerResult:
        self.local = local

        # Inject the active shader profile configuration from stream config dynamically
        if hasattr(params, "shader_profile") and params.shader_profile is None:
            from dataclasses import replace
            params = replace(params, shader_profile=self.app_config.stream.shader_profile)

        if self.app_config.stream.use_ipc:
            if anime or self.registry:
                return self._play_with_ipc(params, anime, media_item)
            else:
                logger.warning(
                    f"Ipc player won't be used since Anime Object has not been given for url={params.url}"
                )
        return self.player.play(params)

    def _play_with_ipc(
        self,
        params: PlayerParams,
        anime: Optional[Anime] = None,
        media_item: Optional[MediaItem] = None,
    ) -> PlayerResult:
        if self.app_config.stream.player == "mpv":
            from .ipc.mpv import MpvIPCPlayer

            registry = self.registry if self.local else None
            return MpvIPCPlayer(self.app_config.stream).play(
                self.player, params, self.provider, anime, registry, media_item
            )
        else:
            logger.warning(
                f"IPC tracking is not supported for player '{self.app_config.stream.player}'. Falling back to standard playback."
            )
            return self.player.play(params)
