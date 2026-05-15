import importlib
import importlib.util
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Union

import click

from anicat_media.core.config import AppConfig
from anicat_media.core.constants import APP_DIR, USER_CONFIG
from anicat_media.core.utils.concurrency import thread_manager
from rich import print as rprint
from .state import InternalDirective, MenuName, State

if TYPE_CHECKING:
    from ...libs.media_api.base import BaseApiClient
    from ...libs.provider.anime.base import BaseAnimeProvider
    from ...libs.selectors.base import BaseSelector
    from ..service.auth import AuthService
    from ..service.download.service import DownloadService
    from ..service.feedback import FeedbackService
    from ..service.player import PlayerService
    from ..service.registry import MediaRegistryService
    from ..service.session import SessionsService
    from ..service.updater.service import UpdaterService
    from ..service.watch_history import WatchHistoryService

logger = logging.getLogger(__name__)


MENUS_DIR = APP_DIR / "cli" / "interactive" / "menu"


@dataclass
class Switch:
    "Forces menus to show selector and not just pass through,once viewed it auto sets back to false"

    _provider_results: bool = False
    _episodes: bool = False
    _servers: bool = False
    _dont_play: bool = False

    @property
    def show_provider_results_menu(self):
        if self._provider_results:
            self._provider_results = False
            return True
        return False

    def force_provider_results_menu(self):
        self._provider_results = True

    @property
    def dont_play(self):
        if self._dont_play:
            self._dont_play = False
            return True
        return False

    def force_dont_play(self):
        self._dont_play = True

    @property
    def show_episodes_menu(self):
        if self._episodes:
            self._episodes = False
            return True
        return False

    def force_episodes_menu(self):
        self._episodes = True

    @property
    def servers(self):
        if self._servers:
            self._servers = False
            return True
        return False

    def force_servers_menu(self):
        self._servers = True


@dataclass
class Context:
    config: "AppConfig"
    switch: Switch = field(default_factory=Switch)
    _provider: Optional["BaseAnimeProvider"] = None
    _manga_provider: Optional[Any] = None
    _selector: Optional["BaseSelector"] = None
    _media_api: Optional["BaseApiClient"] = None

    _download: Optional["DownloadService"] = None
    _feedback: Optional["FeedbackService"] = None
    _media_registry: Optional["MediaRegistryService"] = None
    _watch_history: Optional["WatchHistoryService"] = None
    _session: Optional["SessionsService"] = None
    _auth: Optional["AuthService"] = None
    _player: Optional["PlayerService"] = None
    _updater: Optional["UpdaterService"] = None
    
    data_version: int = 0
    is_offline: bool = False

    @property
    def manga_provider(self) -> Any:
        if not self._manga_provider:
            from ...libs.provider.manga.provider import create_manga_provider
            self._manga_provider = create_manga_provider(self.config.general.manga_provider)
        return self._manga_provider

    @property
    def provider(self) -> "BaseAnimeProvider":
        if not self._provider:
            from ...libs.provider.anime.provider import create_provider

            self._provider = create_provider(self.config.general.provider)
        return self._provider

    @property
    def selector(self) -> "BaseSelector":
        if not self._selector:
            from ...libs.selectors.selector import create_selector

            self._selector = create_selector(self.config)
        return self._selector

    @property
    def media_api(self) -> "BaseApiClient":
        if not self._media_api:
            import httpx

            from ...libs.media_api.api import create_api_client

            media_api = create_api_client(self.config.general.media_api, self.config)

            auth = self.auth
            token = self.config.anilist.token
            if token:
                try:
                    p = media_api.authenticate(token)
                    if p:
                        logger.debug(f"Authenticated as {p.name}")
                    else:
                        logger.warning(
                            "Token was rejected by the API — it may be invalid or expired."
                        )
                except httpx.ConnectError as e:
                    logger.warning(f"It seems you are offline: {e}")
                    self.is_offline = True
            else:
                self.feedback.warning(
                    "You are not logged in.",
                    "Please run 'anicat login' to continue."
                )
            self._media_api = media_api

        return self._media_api

    @property
    def download(self) -> "DownloadService":
        if not self._download:
            from ..service.download.service import DownloadService

            self._download = DownloadService(
                self.config, self.media_registry, self.media_api, self.provider
            )
        return self._download

    @property
    def player(self) -> "PlayerService":
        if not self._player:
            from ..service.player import PlayerService

            self._player = PlayerService(
                self.config, self.provider, self.media_registry
            )
        return self._player

    @property
    def feedback(self) -> "FeedbackService":
        if not self._feedback:
            from ..service.feedback.service import FeedbackService

            self._feedback = FeedbackService(self.config)
        return self._feedback

    @property
    def media_registry(self) -> "MediaRegistryService":
        if not self._media_registry:
            from ..service.registry.service import MediaRegistryService

            self._media_registry = MediaRegistryService(
                self.config.general.media_api, self.config.media_registry
            )
        return self._media_registry

    @property
    def watch_history(self) -> "WatchHistoryService":
        if not self._watch_history:
            from ..service.watch_history.service import WatchHistoryService

            self._watch_history = WatchHistoryService(
                self.config, self.media_registry, self.media_api
            )
        return self._watch_history

    @property
    def session(self) -> "SessionsService":
        if not self._session:
            from ..service.session.service import SessionsService

            self._session = SessionsService(self.config.sessions)
        return self._session

    @property
    def auth(self) -> "AuthService":
        if not self._auth:
            from ..service.auth.service import AuthService

            self._auth = AuthService(self.config.general.media_api)
        return self._auth

    @property
    def updater(self) -> "UpdaterService":
        if not self._updater:
            from ..service.updater.service import UpdaterService

            self._updater = UpdaterService()
        return self._updater


MenuFunction = Callable[[Context, State], Union[State, InternalDirective]]


@dataclass(frozen=True)
class Menu:
    name: MenuName
    execute: MenuFunction


class Session:
    _context: Context
    _history: List[State] = []
    _menus: dict[MenuName, Menu] = {}

    def _shutdown_download_worker(self):
        if hasattr(self, "_context") and self._context._download:
            thread_manager.shutdown_worker("download_worker", wait=False, timeout=5.0)

    def _load_context(self, config: AppConfig):
        self._shutdown_download_worker()
        self._context = Context(config)
        logger.info("Application context reloaded.")

    def _edit_config(self):
        import subprocess
        import sys
        from ..config import ConfigLoader

        if sys.platform == "darwin":
            import subprocess
            rprint("\n[bold yellow]Opening your config file in your text editor...[/]")
            rprint(f"[dim]If it doesn't open, please find it at: {USER_CONFIG}[/]")
            subprocess.run(["open", "-t", str(USER_CONFIG)])
            click.pause("Press Enter here after you have saved your changes...")
        elif sys.platform == "win32":
            subprocess.run(["start", str(USER_CONFIG)], shell=True)
            click.pause("Config opened in your default editor. Press Enter here after you have saved your changes...")
        else:
            click.edit(filename=str(USER_CONFIG))
            
        logger.debug("Config changed; Reloading context")
        loader = ConfigLoader()
        config = loader.load()
        self._load_context(config)

    def _login(self):
        """Triggers the login flow and reloads the context."""
        from ..commands.login import login_flow
        
        # We invoke the login flow directly
        # It handles browser opening, editor opening, and waiting for user.
        try:
            login_flow(self._context.config)
            
            # After login, we must reload the config as it was saved to disk
            from ..config import ConfigLoader
            loader = ConfigLoader()
            config = loader.load()
            self._load_context(config)
        except Exception as e:
            self._context.feedback.error(f"Login failed: {e}")

    def run(
        self,
        config: AppConfig,
        resume: bool = False,
        history: Optional[List[State]] = None,
    ):
        self._load_context(config)
        
        from rich.console import Console
        from ...core.constants import USER_NAME
        Console().print(f"[bold green]Welcome back, {USER_NAME}![/bold green]")

        if resume:
            if history := self._context.session.get_default_session_history():
                self._history = history
            else:
                logger.warning("Failed to continue from history. No sessions found")

        if history:
            self._history = history
        else:
            update_available = self._context.updater.get_cached_status()
            main_state = State(menu_name=MenuName.MAIN, update_available=update_available)
            self._history.append(main_state)
            
            # Trigger a background check for updates if enabled
            def background_check():
                if not self._context.config.general.check_for_updates:
                    return
                try:
                    if self._context.updater.check_version():
                        # If update found, update the initial state in history
                        if self._history and self._history[0].menu_name == MenuName.MAIN:
                            self._history[0] = self._history[0].model_copy(update={"update_available": True})
                            logger.info("Background update check found a new version! Update indicator set.")
                except Exception as e:
                    logger.debug(f"Background update check failed: {e}")

            # Trigger a background sync for offline watches
            def background_sync():
                try:
                    
                    if not self._context.is_offline and self._context.media_api.is_authenticated():
                        # Only sync unsynced entries
                        registry = self._context.media_registry
                        api = self._context.media_api
                        
                        all_records = registry.get_all_media_records()
                        uploaded_count = 0
                        
                        for record in all_records:
                            index_entry = registry.get_media_index_entry(record.media_item.id)
                            # Sync if is_synced is False or if it's an old entry without the field (it defaults to True so it won't be synced unnecessarily)
                            if index_entry and getattr(index_entry, "is_synced", True) is False and index_entry.status:
                                from ...libs.media_api.params import UpdateUserMediaListEntryParams
                                update_params = UpdateUserMediaListEntryParams(
                                    media_id=record.media_item.id,
                                    status=index_entry.status,
                                    progress=index_entry.progress,
                                    score=index_entry.score,
                                )
                                if api.update_list_entry(update_params):
                                    registry.update_media_index_entry(media_id=record.media_item.id, is_synced=True)
                                    uploaded_count += 1
                        
                        if uploaded_count > 0:
                            logger.info(f"Background sync uploaded {uploaded_count} offline watches.")
                except Exception as e:
                    logger.debug(f"Background sync failed: {e}")

            import threading
            threading.Thread(target=background_check, daemon=True).start()
            threading.Thread(target=background_sync, daemon=True).start()

        try:
            self._run_main_loop()
        except Exception:
            self._context.session.create_crash_backup(self._history)
            raise
        finally:
            self._shutdown_download_worker()
            # Clean up preview workers when session ends
            self._cleanup_preview_workers()
        self._context.session.save_session(self._history)

    def _cleanup_preview_workers(self):
        """Clean up preview workers when session ends."""
        try:
            from ..utils.preview import shutdown_preview_workers

            shutdown_preview_workers(wait=False, timeout=5.0)
            logger.debug("Preview workers cleaned up successfully")
        except Exception as e:
            logger.warning(f"Failed to cleanup preview workers: {e}")

    def _run_main_loop(self):
        """Run the main session loop."""
        while self._history:
            current_state = self._history[-1]

            next_step = self._menus[current_state.menu_name].execute(
                self._context, current_state
            )

            if isinstance(next_step, InternalDirective):
                if next_step == InternalDirective.MAIN:
                    self._history = [self._history[0]]
                elif next_step == InternalDirective.RELOAD:
                    continue
                elif next_step == InternalDirective.CONFIG_EDIT:
                    self._edit_config()
                elif next_step == InternalDirective.LOGIN:
                    self._login()
                    continue
                elif next_step == InternalDirective.BACK:
                    if len(self._history) > 1:
                        self._history.pop()
                elif next_step == InternalDirective.BACKX2:
                    if len(self._history) > 2:
                        self._history.pop()
                        self._history.pop()
                elif next_step == InternalDirective.BACKX3:
                    if len(self._history) > 3:
                        self._history.pop()
                        self._history.pop()
                        self._history.pop()
                elif next_step == InternalDirective.BACKX4:
                    if len(self._history) > 4:
                        self._history.pop()
                        self._history.pop()
                        self._history.pop()
                        self._history.pop()
                elif next_step == InternalDirective.EXIT:
                    break
            else:
                self._history.append(next_step)

    @property
    def menu(self) -> Callable[[MenuFunction], MenuFunction]:
        """A decorator to register a function as a menu."""

        def decorator(func: MenuFunction) -> MenuFunction:
            menu_name = MenuName(func.__name__.upper())
            if menu_name in self._menus:
                logger.warning(f"Menu '{menu_name}' is being redefined.")
            self._menus[menu_name] = Menu(name=menu_name, execute=func)
            return func

        return decorator

    def load_menus_from_folder(self, package: str):
        """Load menu modules from a subfolder.
        
        Uses pkgutil to discover modules for regular Python, and falls back
        to the package's __all__ list for PyInstaller frozen executables.
        """
        full_package_name = f"anicat_media.cli.interactive.menu.{package}"
        logger.debug(f"Loading menus from package '{full_package_name}'...")

        try:
            # Import the parent package first
            parent_package = importlib.import_module(full_package_name)
        except ImportError as e:
            logger.error(f"Failed to import menu package '{full_package_name}': {e}")
            return

        # Try pkgutil first (works in regular Python)
        package_path = getattr(parent_package, "__path__", None)
        module_names = []
        
        if package_path:
            module_names = [
                name for _, name, ispkg in pkgutil.iter_modules(package_path)
                if not ispkg and not name.startswith("_")
            ]
        
        # Fallback to __all__ for PyInstaller frozen executables
        if not module_names:
            module_names = getattr(parent_package, "__all__", [])
            logger.debug(f"Using __all__ fallback with {len(module_names)} modules")

        for module_name in module_names:
            full_module_name = f"{full_package_name}.{module_name}"
            try:
                # Simply importing the module will execute it,
                # which runs the @session.menu decorators
                importlib.import_module(full_module_name)
            except Exception as e:
                logger.error(
                    f"Failed to load menu module '{full_module_name}': {e}"
                )


# Create a single, global instance of the Session to be imported by menu modules.
session = Session()
