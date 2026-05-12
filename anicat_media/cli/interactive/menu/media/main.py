import logging
import random
from typing import Callable, Dict

from .....libs.media_api.params import MediaSearchParams, UserMediaListSearchParams
from .....libs.media_api.types import (
    MediaSort,
    MediaStatus,
    MediaType,
    UserMediaListStatus,
)
from rich.panel import Panel
from ...session import Context, session
from ...state import InternalDirective, MediaApiState, MenuName, State
from anicat_media.core.theme import ICONS

logger = logging.getLogger(__name__)
MenuAction = Callable[[], State | InternalDirective]


@session.menu
def main(ctx: Context, state: State) -> State | InternalDirective:
    icons = ctx.config.general.icons
    feedback = ctx.feedback
    feedback.clear_console()

    options: Dict[str, MenuAction] = {
        f"{ICONS.get('TRENDING', icons)}Trending": _create_media_list_action(
            ctx, state, MediaSort.TRENDING_DESC
        ),
        f"{ICONS.get('RECENT', icons)}Recent": _create_recent_media_action(ctx, state),
        f"{ICONS.get('WATCHING', icons)}Watching": _create_user_list_action(
            ctx, state, UserMediaListStatus.WATCHING
        ),
        f"{ICONS.get('REWATCHING', icons)}Rewatching": _create_user_list_action(
            ctx, state, UserMediaListStatus.REPEATING
        ),
        f"{ICONS.get('PAUSED', icons)}Paused": _create_user_list_action(
            ctx, state, UserMediaListStatus.PAUSED
        ),
        f"{ICONS.get('PLANNED', icons)}Planned": _create_user_list_action(
            ctx, state, UserMediaListStatus.PLANNING
        ),
        f"{ICONS.get('SEARCH', icons)}Search": _create_search_media_list(ctx, state),
        f"{ICONS.get('SEARCH_MANGA', icons)}Search Manga": _create_search_manga_list(ctx, state),
        f"{ICONS.get('DYNAMIC_SEARCH', icons)}Dynamic Search": _create_dynamic_search_action(
            ctx, state
        ),
        f"{ICONS.get('DOWNLOADS', icons)}Downloads": _create_downloads_action(ctx, state),
        f"{ICONS.get('UPDATED', icons)}Recently Updated": _create_media_list_action(
            ctx, state, MediaSort.UPDATED_AT_DESC
        ),
        f"{ICONS.get('POPULAR', icons)}Popular": _create_media_list_action(
            ctx, state, MediaSort.POPULARITY_DESC
        ),
        f"{ICONS.get('TOP_SCORED', icons)}Top Scored": _create_media_list_action(
            ctx, state, MediaSort.SCORE_DESC
        ),
        f"{ICONS.get('FAVOURITES', icons)}Favourites": _create_media_list_action(
            ctx, state, MediaSort.FAVOURITES_DESC
        ),
        f"{ICONS.get('RANDOM', icons)}Random": _create_random_media_list(ctx, state),
        f"{ICONS.get('UPCOMING', icons)}Upcoming": _create_media_list_action(
            ctx, state, MediaSort.POPULARITY_DESC, MediaStatus.NOT_YET_RELEASED
        ),
        f"{ICONS.get('COMPLETED', icons)}Completed": _create_user_list_action(
            ctx, state, UserMediaListStatus.COMPLETED
        ),
        f"{ICONS.get('DROPPED', icons)}Dropped": _create_user_list_action(
            ctx, state, UserMediaListStatus.DROPPED
        ),
        f"{ICONS.get('EDIT', icons)}Edit Config": lambda: InternalDirective.CONFIG_EDIT,
        f"{ICONS.get('MANAGE', icons)}Manage Categories": _manage_categories_action(ctx, state),
        f"{ICONS.get('UPDATE', icons)}Check for Updates": _check_for_updates_action(ctx, state),
        f"{ICONS.get('LOGOUT' if ctx.media_api.is_authenticated() else 'LOGIN', icons)}{'Logout' if ctx.media_api.is_authenticated() else 'Login'}": _auth_action(
            ctx, state
        ),
        f"{ICONS.get('EXIT', icons)}Exit": lambda: InternalDirective.EXIT,
    }

    if not ctx.config.anilist.token:
        login_label = f"{'🔑 ' if icons else '-> '}Login to AniList"
        new_options = {login_label: lambda: InternalDirective.LOGIN}
        new_options.update(options)
        options = new_options

    # Filter out hidden categories from the menu
    hidden = ctx.config.general.hidden_categories
    if hidden:
        options = {
            k: v
            for k, v in options.items()
            if not any(h.lower() in k.lower() for h in hidden)
        }

    choice = ctx.selector.choose(
        prompt="Select Category",
        choices=list(options.keys()),
    )
    if not choice:
        return InternalDirective.MAIN

    selected_action = options[choice]

    next_step = selected_action()
    return next_step


def _create_media_list_action(
    ctx: Context, state: State, sort: MediaSort, status: MediaStatus | None = None
) -> MenuAction:
    def action():
        feedback = ctx.feedback
        search_params = MediaSearchParams(sort=sort, status=status)

        loading_message = "Fetching media list"
        result = None
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media(search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=search_params,
                    page_info=result.page_info,
                ),
            )
        else:
            return InternalDirective.MAIN

    return action


def _create_random_media_list(ctx: Context, state: State) -> MenuAction:
    def action():
        feedback = ctx.feedback
        search_params = MediaSearchParams(id_in=random.sample(range(1, 15000), k=50))

        loading_message = "Fetching media list"
        result = None
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media(search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=search_params,
                    page_info=result.page_info,
                ),
            )
        else:
            return InternalDirective.MAIN

    return action


def _create_search_media_list(ctx: Context, state: State) -> MenuAction:
    def action():
        feedback = ctx.feedback

        query = ctx.selector.ask("Search for Anime")
        if not query:
            return InternalDirective.MAIN

        search_params = MediaSearchParams(query=query)

        loading_message = "Fetching media list"
        result = None
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media(search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=search_params,
                    page_info=result.page_info,
                ),
            )
        else:
            return InternalDirective.MAIN

    return action


def _create_search_manga_list(ctx: Context, state: State) -> MenuAction:
    def action():
        feedback = ctx.feedback

        query = ctx.selector.ask("Search for Manga")
        if not query:
            return InternalDirective.MAIN

        search_params = MediaSearchParams(query=query, type=MediaType.MANGA)

        loading_message = "Fetching media list"
        result = None
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media(search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=search_params,
                    page_info=result.page_info,
                ),
            )
        else:
            return InternalDirective.MAIN

    return action

def _create_user_list_action(
    ctx: Context, state: State, status: UserMediaListStatus
) -> MenuAction:
    """A factory to create menu actions for fetching user lists, handling authentication."""

    def action():
        feedback = ctx.feedback
        if not ctx.media_api.is_authenticated():
            feedback.error("You haven't logged in")
            return InternalDirective.MAIN

        search_params = UserMediaListSearchParams(status=status)

        loading_message = "Fetching media list"
        result = None
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media_list(search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=search_params,
                    page_info=result.page_info,
                ),
            )
        else:
            return InternalDirective.MAIN

    return action


def _create_recent_media_action(ctx: Context, state: State) -> MenuAction:
    def action():
        result = ctx.media_registry.get_recently_watched()
        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    page_info=result.page_info,
                ),
            )
        else:
            return InternalDirective.MAIN

    return action


def _create_downloads_action(ctx: Context, state: State) -> MenuAction:
    """Create action to navigate to the downloads menu."""

    def action():
        return State(menu_name=MenuName.DOWNLOADS)

    return action


def _create_dynamic_search_action(ctx: Context, state: State) -> MenuAction:
    """Create action to navigate to the dynamic search menu."""

    def action():
        return State(menu_name=MenuName.DYNAMIC_SEARCH)

    return action


def _manage_categories_action(ctx: Context, state: State) -> MenuAction:
    """Action to interactively manage hidden categories."""

    def action():
        from anicat_media.core.constants import USER_CONFIG
        from ....config.generate import generate_config_toml_from_app_model
        from InquirerPy import inquirer

        # All categories available in the main menu
        all_categories = [
            "Trending", "Recent", "Watching", "Rewatching", "Paused", 
            "Planned", "Search", "Search Manga", "Dynamic Search", 
            "Downloads", "Recently Updated", "Popular", "Top Scored", 
            "Favourites", "Random", "Upcoming", "Completed", "Dropped"
        ]
        
        current_hidden = [h.lower() for h in (ctx.config.general.hidden_categories or [])]
        
        # Create choices for the checkbox: enabled if NOT in hidden_categories
        choices = [
            {"name": cat, "value": cat, "enabled": cat.lower() not in current_hidden}
            for cat in all_categories
        ]

        selected = inquirer.checkbox(
            message="Select categories to SHOW (uncheck to hide):",
            choices=choices,
            instruction="(Space to toggle, Enter to confirm)",
            transformer=lambda result: f"{len(result)} categories visible",
        ).execute()

        if selected is not None:
            # Hidden categories are those NOT in the selected list
            new_hidden = [cat for cat in all_categories if cat not in selected]
            ctx.config.general.hidden_categories = new_hidden
            
            # Save the updated configuration
            try:
                toml_content = generate_config_toml_from_app_model(ctx.config)
                USER_CONFIG.write_text(toml_content, encoding="utf-8")
                ctx.feedback.success(f"Categories updated. {len(new_hidden)} items hidden.")
            except Exception as e:
                ctx.feedback.error(f"Failed to save categories: {e}")
            
        return InternalDirective.RELOAD
    return action

def _check_for_updates_action(ctx: Context, state: State) -> MenuAction:
    """Action to manually check for updates."""

    def action():
        feedback = ctx.feedback
        with feedback.progress("Checking for updates..."):
            is_available = ctx.updater.check_version(force=True)
        
        from ....service.feedback.service import console
        from rich.table import Table
        from anicat_media.core.constants import VERSION, LAST_COMMIT_FILE, UPDATE_STATUS_FILE, APP_DIR

        # Get values from updater service
        remote_version = ctx.updater.remote_version or "Unknown"
        local_version = VERSION
        remote_hash = ctx.updater.remote_hash or "Unknown"
        local_hash = ctx.updater.local_hash or "Unknown"

        # Create detailed table
        table = Table(title="Update Comparison", show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Property", style="dim")
        table.add_column("Local", justify="right")
        table.add_column("Remote", justify="right")
        
        table.add_row("Version", local_version, remote_version)
        table.add_row("Commit Hash", local_hash[:8] if local_hash != "Unknown" else local_hash, 
                      remote_hash[:8] if remote_hash != "Unknown" else remote_hash)

        if is_available:
            panel = Panel(
                table,
                title="[bold green]✨ New Update Available![/bold green]",
                subtitle="A newer version or commit is available on GitHub.",
                border_style="yellow",
                expand=False
            )
            console.print(panel)
            
            # Check for Dev Mode
            is_dev_mode = (APP_DIR.parent / ".git").exists()
            if is_dev_mode:
                console.print("\n[bold yellow]Dev Mode Detected:[/bold yellow] New changes are available on GitHub.")
                console.print("Please run [bold cyan]git pull[/bold cyan] to update your local development environment.")
                feedback.pause_for_user("return to menu")
                return state.model_copy(update={"update_available": True})

            from InquirerPy import inquirer
            if inquirer.confirm(message="Would you like to update Anicat now?", default=True).execute():
                console.print("\n[bold cyan]Updating Anicat... This will take a moment.[/]")
                import subprocess
                import sys
                try:
                    # Run the update command
                    subprocess.run(["uv", "tool", "install", "--force", "git+https://github.com/bonkedbythonk/anicat.git"], check=True)
                    
                    # Update local hash and clear status to prevent update loop
                    if ctx.updater.remote_hash:
                        LAST_COMMIT_FILE.write_text(ctx.updater.remote_hash, encoding="utf-8")
                        UPDATE_STATUS_FILE.write_text("0", encoding="utf-8")
                        logger.info(f"Updated local hash to {ctx.updater.remote_hash}")

                    console.print("\n[bold green]Anicat has been updated! Please restart the app to apply changes.[/]")
                    sys.exit(0)
                except Exception as e:
                    error_panel = Panel(
                        f"[bold red]Update Failed![/bold red]\n\n{e}\n\nPlease try running the command manually:\n[bold yellow]uv tool install --force git+https://github.com/bonkedbythonk/anicat.git[/bold yellow]",
                        title="Error",
                        border_style="red"
                    )
                    console.print(error_panel)
                    feedback.pause_for_user("return to menu")
            
            # Return updated state so the ✨ appears immediately
            return state.model_copy(update={"update_available": True})
        else:
            panel = Panel(
                table,
                title="[bold blue]Up to Date[/bold blue]",
                subtitle="Everything is current.",
                border_style="green",
                expand=False
            )
            console.print(panel)
            feedback.pause_for_user("return to menu")
            return state.model_copy(update={"update_available": False})
            
    return action


def _auth_action(ctx: Context, state: State) -> MenuAction:
    """Action to handle login/logout from the TUI."""

    def action():
        auth = ctx.auth
        if ctx.media_api.is_authenticated():
            if ctx.selector.confirm("Are you sure you want to log out?"):
                auth.clear_user_profile()
                ctx.feedback.success("Logged out successfully.")
                return InternalDirective.RELOAD
        else:
            from .....core.constants import ANILIST_AUTH
            import webbrowser

            ctx.feedback.info("Opening browser for AniList authorization...")
            webbrowser.open(ANILIST_AUTH)
            ctx.feedback.info(
                "After authorizing, run 'anicat anilist auth --token <your_token>' in your terminal."
            )
            ctx.selector.ask("Press Enter to continue...")

        return InternalDirective.MAIN

    return action
    return action
