import logging
import random
from datetime import datetime, timedelta
from typing import Callable, Dict

from .....libs.media_api.params import MediaSearchParams, UserMediaListSearchParams
from .....libs.media_api.types import (
    MediaSort,
    MediaStatus,
    MediaType,
    UserMediaListStatus,
)
from ...session import Context, session
from ...state import InternalDirective, MediaApiState, MenuName, State
from anicat_media.core.theme import ICONS
from ....service.feedback.service import console
from rich.panel import Panel

logger = logging.getLogger(__name__)
MenuAction = Callable[[], State | InternalDirective]


@session.menu
def main(ctx: Context, state: State) -> State | InternalDirective:
    icons = ctx.config.general.icons
    feedback = ctx.feedback
    feedback.clear_console()

    console.print("[bold magenta]  anicat[/bold magenta]\n")

    # ── Dashboard summary (non-blocking, best-effort) ──────────────────
    _print_dashboard_summary(ctx, state)

    # ── Navigation options ─────────────────────────────────────────────
    options: Dict[str, MenuAction] = {
        f"{ICONS.get('RECENT', icons)}Home": _create_recent_anime_action(ctx, state),
        f"{ICONS.get('SEARCH_MANGA', icons)}Manga": _create_manga_dashboard_action(
            ctx, state
        ),
        f"{ICONS.get('SEARCH', icons)}Search": _create_search_media_list(ctx, state),
        f"{ICONS.get('WATCHING', icons)}My Lists": _create_tabbed_user_list_action(
            ctx, state
        ),
        f"{ICONS.get('DOWNLOADS', icons)}Downloads": _create_downloads_action(
            ctx, state
        ),
        f"{ICONS.get('COMPLETED', icons)}Library": _create_user_list_action(
            ctx, state, UserMediaListStatus.COMPLETED
        ),
        f"{ICONS.get('UPCOMING', icons)}Schedule": lambda: State(
            menu_name=MenuName.MEDIA_AIRING_SCHEDULE
        ),
    }

    # Profile and notifications if authenticated
    if ctx.config.anilist.token and ctx.media_api.is_authenticated():
        options[f"{ICONS.get('STATS', icons)}Profile"] = _create_profile_summary_action(
            ctx
        )
        notif_count = _get_notification_count(ctx)
        notif_label = (
            f"{ICONS.get('BELL', icons)}Notifications"
            f"{f' ({notif_count})' if notif_count > 0 else ''}"
        )
        options[notif_label] = lambda: _show_notifications(ctx)

    options[f"{ICONS.get('EDIT', icons)}Settings"] = (
        lambda: InternalDirective.CONFIG_EDIT
    )
    options[f"{ICONS.get('EXIT', icons)}Exit"] = lambda: InternalDirective.EXIT

    if not ctx.config.anilist.token:
        login_label = f"{'🔑' if icons else '>'}Login to AniList"
        options = {login_label: lambda: InternalDirective.LOGIN, **options}

    choice = ctx.selector.choose(
        prompt="Select",
        choices=list(options.keys()),
    )
    if not choice:
        return InternalDirective.MAIN

    selected_action = options[choice]
    next_step = selected_action()
    return next_step


# ── Dashboard Summary ──────────────────────────────────────────────────────


def _print_dashboard_summary(ctx: Context, state: State) -> None:
    """Print a high-level dashboard summary (best-effort, non-blocking)."""
    from rich.table import Table

    authenticated = ctx.config.anilist.token and ctx.media_api.is_authenticated()

    # ── Quick Stats Row ────────────────────────────────────────────────
    stats_parts = []

    # Currently Watching count
    if authenticated:
        try:
            watching = ctx.media_api.search_media_list(
                UserMediaListSearchParams(
                    status=UserMediaListStatus.WATCHING,
                    type=MediaType.ANIME,
                )
            )
            if watching and watching.page_info:
                stats_parts.append(f"[cyan]{watching.page_info.total}[/cyan] watching")
        except Exception:
            pass

    # Notification count
    if authenticated:
        try:
            count = _get_notification_count(ctx)
            if count > 0:
                stats_parts.append(f"[amber]{count}[/amber] notifications")
        except Exception:
            pass

    # Update available
    if state.update_available if hasattr(state, "update_available") else False:
        stats_parts.append("[green]Update available![/green]")

    if stats_parts:
        console.print(f"  {'  |  '.join(stats_parts)}")
        console.print()

    # ── Airing Today ───────────────────────────────────────────────────
    if authenticated:
        try:
            now = datetime.now()
            start_ts = int((now - timedelta(hours=12)).timestamp())
            end_ts = int((now + timedelta(hours=24)).timestamp())
            schedule = ctx.media_api.get_global_airing_schedule(
                airingAt_greater=start_ts,
                airingAt_lesser=end_ts,
                per_page=5,
            )
            if schedule and schedule.media:
                airing_today = [
                    m
                    for m in schedule.media
                    if m.next_airing and m.type == MediaType.ANIME
                ][:5]
                if airing_today:
                    table = Table(
                        title="Airing Soon",
                        show_header=True,
                        header_style="bold cyan",
                        box=None,
                        padding=(0, 1),
                    )
                    table.add_column("Time", style="dim")
                    table.add_column("Title", style="bold white")
                    table.add_column("Ep", justify="right")
                    for m in airing_today:
                        air_time = m.next_airing.airing_at
                        try:
                            dt_obj = datetime.fromtimestamp(int(air_time))
                            time_str = dt_obj.strftime("%H:%M")
                        except (ValueError, TypeError):
                            time_str = "?"
                        title = m.title.romaji or m.title.english or "?"
                        ep = str(m.next_airing.episode)
                        table.add_row(time_str, title, ep)
                    console.print(table)
                    console.print()
        except Exception:
            pass

    # ── Continue Watching ──────────────────────────────────────────────
    try:
        recent = ctx.media_registry.get_recently_watched(limit=5, type=MediaType.ANIME)
        if recent and recent.media:
            # Filter to only show items with actual progress
            in_progress: list = []
            for m in recent.media:
                us = getattr(m, "user_status", None)
                if us is not None and (us.progress or 0) > 0:
                    in_progress.append(m)
            in_progress = in_progress[:3]
            if in_progress:
                console.print(
                    "[bold]Continue Watching[/bold]",
                    style="bold",
                    highlight=False,
                )
                for m in in_progress:
                    title = m.title.romaji or m.title.english or "?"
                    progress = m.user_status.progress if m.user_status else 0
                    total = m.episodes or "?"
                    console.print(f"  [dim]{progress}/{total}[/dim]  {title}")
                console.print()
    except Exception:
        pass


def _get_notification_count(ctx: Context) -> int:
    """Get unread notification count (best-effort)."""
    try:
        if not ctx.media_api.is_authenticated():
            return 0
        result = ctx.media_api.get_notifications()
        if result:
            return len(result)
    except Exception:
        pass
    return 0


def _show_notifications(ctx: Context) -> InternalDirective:
    """Display recent notifications in a table."""
    from rich.table import Table

    try:
        notifications = ctx.media_api.get_notifications()
        if not notifications:
            ctx.feedback.info("No notifications.")
            return InternalDirective.MAIN

        table = Table(
            title="Notifications",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Message", style="bold white")

        for i, n in enumerate(notifications[:15], 1):
            msg = getattr(n, "message", str(n))[:100]
            table.add_row(str(i), msg)

        console.print(table)
        console.print()
        click = __import__("click")
        click.pause("Press Enter to return...")
    except Exception as e:
        ctx.feedback.error(f"Failed to load notifications: {e}")

    return InternalDirective.MAIN


# ── Profile Summary Action ─────────────────────────────────────────────────


def _create_profile_summary_action(ctx: Context) -> MenuAction:
    """Show profile summary, then return to main menu."""

    def action():
        try:
            profile = ctx.media_api.get_viewer_profile()
            if profile:
                name = getattr(profile, "name", None) or "?"
                anime = getattr(profile, "anime_count", 0)
                manga = getattr(profile, "manga_count", 0)
                minutes = getattr(profile, "minutes_watched", 0)
                eps = getattr(profile, "episodes_watched", 0)
                chaps = getattr(profile, "chapters_read", 0)

                console.print(f"\n[bold cyan]{name}[/bold cyan]")
                console.print(f"  Anime: {anime}  |  Manga: {manga}")
                console.print(f"  Episodes watched: {eps}  |  Chapters read: {chaps}")
                if minutes:
                    hours = minutes // 60
                    console.print(f"  Watch time: {hours}h ({minutes}m)")
                console.print()
        except Exception:
            pass

        click_mod = __import__("click")
        click_mod.pause("Press Enter to return...")
        return InternalDirective.MAIN

    return action


# ── Tabbed My Lists Action ─────────────────────────────────────────────────


def _create_tabbed_user_list_action(ctx: Context, state: State) -> MenuAction:
    """Show a tabbed My Lists selector matching the App's Watching/Completed/
    Planning/Paused/Dropped tabs."""

    def action():
        feedback = ctx.feedback
        if not ctx.media_api.is_authenticated():
            feedback.error("You haven't logged in")
            return InternalDirective.MAIN

        icons = ctx.config.general.icons
        tabs: Dict[str, UserMediaListStatus] = {
            f"{ICONS.get('WATCHING', icons)}Watching": UserMediaListStatus.WATCHING,
            f"{ICONS.get('COMPLETED', icons)}Completed": UserMediaListStatus.COMPLETED,
            f"{ICONS.get('PLANNED', icons)}Planning": UserMediaListStatus.PLANNING,
            f"{ICONS.get('PAUSED', icons)}Paused": UserMediaListStatus.PAUSED,
            f"{ICONS.get('DROPPED', icons)}Dropped": UserMediaListStatus.DROPPED,
        }
        # Add Back option
        tab_choices = list(tabs.keys()) + [f"{ICONS.get('BACK', icons)}Back"]

        choice = ctx.selector.choose("Select List", tab_choices)
        if not choice or "Back" in choice:
            return InternalDirective.MAIN

        status = tabs[choice]
        search_params = UserMediaListSearchParams(status=status)

        with feedback.progress("Fetching media list"):
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


# ── Manga Dashboard Action ─────────────────────────────────────────────────


def _create_manga_dashboard_action(ctx: Context, state: State) -> MenuAction:
    """Show a Manga dashboard with Continue Reading and Trending,
    then a selector to proceed."""

    def action():
        feedback = ctx.feedback
        icons = ctx.config.general.icons

        feedback.clear_console()
        console.print("[bold cyan]Manga[/bold cyan]\n")

        # ── Continue Reading ──────────────────────────────────────────
        if ctx.media_api.is_authenticated():
            try:
                reading = ctx.media_api.search_media_list(
                    UserMediaListSearchParams(
                        status=UserMediaListStatus.WATCHING,
                        type=MediaType.MANGA,
                    )
                )
                if reading and reading.media:
                    from rich.table import Table

                    table = Table(
                        title="Continue Reading",
                        show_header=True,
                        header_style="bold",
                    )
                    table.add_column("Title")
                    table.add_column("Progress", justify="right")
                    for m in reading.media[:5]:
                        title = m.title.romaji or m.title.english or "?"
                        prog = m.user_status.progress if m.user_status else 0
                        total = m.chapters or "?"
                        table.add_row(title, f"{prog}/{total}")
                    console.print(table)
                    console.print()
            except Exception:
                pass

        # ── Trending Manga ────────────────────────────────────────────
        try:
            trending = ctx.media_api.search_media(
                MediaSearchParams(
                    type=MediaType.MANGA,
                    sort=MediaSort.TRENDING_DESC,
                    per_page=5,
                )
            )
            if trending and trending.media:
                from rich.table import Table

                table = Table(
                    title="Trending Manga",
                    show_header=True,
                    header_style="bold",
                )
                table.add_column("#", style="dim", width=2)
                table.add_column("Title")
                table.add_column("Score", justify="right")
                for i, m in enumerate(trending.media[:5], 1):
                    title = m.title.romaji or m.title.english or "?"
                    score = m.average_score or "?"
                    table.add_row(str(i), title, f"{score}%")
                console.print(table)
                console.print()
        except Exception:
            pass

        # ── Navigation ────────────────────────────────────────────────
        manga_options: Dict[str, MenuAction] = {
            f"{ICONS.get('READING', icons)}Continue Reading": _create_user_list_action(
                ctx, state, UserMediaListStatus.WATCHING, MediaType.MANGA
            ),
            f"{ICONS.get('SEARCH_MANGA', icons)}Search Manga": _create_search_manga_list(
                ctx, state
            ),
            f"{ICONS.get('TRENDING', icons)}Trending Manga": _create_media_list_action(
                ctx,
                state,
                MediaSort.TRENDING_DESC,
            ),
            f"{ICONS.get('BACK', icons)}Back": lambda: InternalDirective.BACK,
        }

        choice = ctx.selector.choose(
            prompt="Manga",
            choices=list(manga_options.keys()),
        )
        if not choice:
            return InternalDirective.MAIN

        return manga_options[choice]()

    return action


# ── Existing action factories (unchanged) ──────────────────────────────────


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
            # Auto-select if single result and config enabled
            if (
                ctx.config.general.auto_select_anime_result
                and result.page_info.total == 1
            ):
                return State(
                    menu_name=MenuName.MEDIA_ACTIONS,
                    media_api=MediaApiState(
                        search_result={
                            media_item.id: media_item for media_item in result.media
                        },
                        media_id=result.media[0].id,
                        search_params=search_params,
                        page_info=result.page_info,
                    ),
                )

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
            # Auto-select if single result and config enabled
            if (
                ctx.config.general.auto_select_anime_result
                and result.page_info.total == 1
            ):
                return State(
                    menu_name=MenuName.MEDIA_ACTIONS,
                    media_api=MediaApiState(
                        search_result={
                            media_item.id: media_item for media_item in result.media
                        },
                        media_id=result.media[0].id,
                        search_params=search_params,
                        page_info=result.page_info,
                    ),
                )

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
    ctx: Context,
    state: State,
    status: UserMediaListStatus,
    type: MediaType | None = None,
) -> MenuAction:
    """A factory to create menu actions for fetching user lists, handling authentication."""

    def action():
        feedback = ctx.feedback
        if not ctx.media_api.is_authenticated():
            feedback.error("You haven't logged in")
            return InternalDirective.MAIN

        search_params = UserMediaListSearchParams(status=status, type=type)

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


def _create_recent_anime_action(ctx: Context, state: State) -> MenuAction:
    def action():
        result = ctx.media_registry.get_recently_watched(type=MediaType.ANIME)
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
            ctx.feedback.info("No recently watched anime found.")
            return InternalDirective.MAIN

    return action


def _create_recent_manga_action(ctx: Context, state: State) -> MenuAction:
    def action():
        result = ctx.media_registry.get_recently_watched(type=MediaType.MANGA)
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
            ctx.feedback.info("No recently read manga found.")
            return InternalDirective.MAIN

    return action


def _create_downloads_action(ctx: Context, state: State) -> MenuAction:
    """Create action to navigate to the local library (downloads) menu."""

    def action():
        return State(menu_name=MenuName.LOCAL_LIBRARY)

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
            "Trending",
            "Recent",
            "Watching",
            "Reading",
            "Rewatching",
            "Paused",
            "Planned",
            "Search",
            "Search Manga",
            "Dynamic Search",
            "Downloads",
            "Recently Updated",
            "Popular",
            "Top Scored",
            "Favourites",
            "Random",
            "Upcoming",
            "Completed",
            "Dropped",
        ]

        current_hidden = [
            h.lower() for h in (ctx.config.general.hidden_categories or [])
        ]

        # Create choices for the checkbox: enabled if NOT in hidden_categories
        choices = [
            {"name": cat, "value": cat, "enabled": cat.lower() not in current_hidden}
            for cat in all_categories
        ]

        selected = inquirer.checkbox(  # type: ignore
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
                ctx.feedback.success(
                    f"Categories updated. {len(new_hidden)} items hidden."
                )
            except Exception as e:
                ctx.feedback.error(f"Failed to save categories: {e}")

        return InternalDirective.RELOAD

    return action


def _check_for_updates_action(ctx: Context, state: State) -> MenuAction:
    """Action to manually check for updates."""

    def action():
        feedback = ctx.feedback
        feedback.clear_console()
        with feedback.progress("Checking for updates..."):
            is_available = ctx.updater.check_version(force=True)

        from rich.table import Table
        from anicat_media.core.constants import (
            VERSION,
            LAST_COMMIT_FILE,
            UPDATE_STATUS_FILE,
            APP_DIR,
        )

        # Get values from updater service
        remote_version = ctx.updater.remote_version or "Unknown"
        local_version = VERSION
        remote_hash = ctx.updater.remote_hash or "Unknown"
        local_hash = ctx.updater.local_hash or "Unknown"

        # Create detailed table
        table = Table(
            title="Update Comparison",
            show_header=True,
            header_style="bold magenta",
            expand=True,
        )
        table.add_column("Property", style="dim")
        table.add_column("Local", justify="right")
        table.add_column("Remote", justify="right")

        table.add_row("Version", local_version, remote_version)
        table.add_row(
            "Commit Hash",
            local_hash[:8] if local_hash != "Unknown" else local_hash,
            remote_hash[:8] if remote_hash != "Unknown" else remote_hash,
        )

        if is_available:
            panel = Panel(
                table,
                title="[bold green]✨ New Update Available![/bold green]",
                subtitle="A newer version or commit is available on GitHub.",
                border_style="yellow",
                expand=False,
            )
            console.print(panel)

            # Check for Dev Mode
            is_dev_mode = (APP_DIR.parent / ".git").exists()
            if is_dev_mode:
                console.print(
                    "\n[bold yellow]Dev Mode Detected:[/bold yellow] New changes are available on GitHub."
                )
                console.print(
                    "Please run [bold cyan]git pull[/bold cyan] to update your local development environment."
                )
                feedback.pause_for_user("return to menu")
                return state.model_copy(update={"update_available": True})

            from InquirerPy import inquirer

            if inquirer.confirm(
                message="Would you like to update Anicat now?", default=True
            ).execute():  # type: ignore
                console.print("\n[bold cyan]Updating Anicat...[/]")
                import subprocess
                import sys
                from datetime import datetime

                try:
                    start = datetime.now()
                    with console.status(
                        "[bold cyan]Downloading and installing latest version...[/]"
                    ) as status:
                        proc = subprocess.Popen(
                            [
                                "uv",
                                "tool",
                                "install",
                                "--force",
                                "git+https://github.com/bonkedbythonk/anicat_old.git",
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                        )
                        # Show output lines in status while respecting a 5-minute timeout
                        line_count = 0
                        for line in proc.stdout or []:
                            line = line.strip()
                            if line and line_count % 10 == 0:
                                # Show short excerpts to indicate progress
                                short = line[:80] + ("..." if len(line) > 80 else "")
                                status.update(f"[dim]{short}[/]")
                            line_count += 1
                        proc.wait(timeout=300)

                    elapsed = int((datetime.now() - start).total_seconds())

                    if proc.returncode != 0:
                        raise RuntimeError(
                            f"uv tool install failed with exit code {proc.returncode}"
                        )

                    # Update local hash and clear status to prevent update loop
                    if ctx.updater.remote_hash:
                        LAST_COMMIT_FILE.write_text(
                            ctx.updater.remote_hash, encoding="utf-8"
                        )
                        UPDATE_STATUS_FILE.write_text("0", encoding="utf-8")
                        logger.info(f"Updated local hash to {ctx.updater.remote_hash}")

                    console.print(
                        f"\n[bold green]Anicat has been updated in {elapsed}s! Please restart the app to apply changes.[/]"
                    )
                    sys.exit(0)
                except subprocess.TimeoutExpired:
                    console.print(
                        "\n[bold red]Update timed out after 5 minutes.[/bold red]"
                    )
                    console.print(
                        "The download or build may be taking longer than expected."
                    )
                    console.print(
                        "Try upgrading manually with:\n[bold yellow]uv tool install --force git+https://github.com/bonkedbythonk/anicat_old.git[/bold yellow]"
                    )
                    feedback.pause_for_user("return to menu")
                except Exception as e:
                    error_panel = Panel(
                        f"[bold red]Update Failed![/bold red]\n\n{e}\n\nPlease try running the command manually:\n[bold yellow]uv tool install --force git+https://github.com/bonkedbythonk/anicat_old.git[/bold yellow]",
                        title="Error",
                        border_style="red",
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
                expand=False,
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
