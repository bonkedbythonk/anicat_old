"""Home, Schedule, Profile, Notifications — app-aligned CLI views.

These commands use the shared Context service layer directly,
so they work standalone without the API server running.
"""

import click
from typing import Literal
from rich.console import Console
from rich.table import Table
from ...core.config import AppConfig
from datetime import datetime

console = Console()


def _get_ctx(config: AppConfig):
    """Create a Context for standalone CLI commands.

    Uses lazy import to avoid circular dependencies during module loading.
    """
    from ..interactive.session import Context

    return Context(config)


# ── Shared helpers ─────────────────────────────────────────────────────────


def _format_title(item) -> str:
    """Extract the best display title from a media item."""
    title_obj = getattr(item, "title", None)
    if title_obj:
        return title_obj.romaji or title_obj.english or "?"
    # Raw dict fallback (shouldn't happen with Context)
    if isinstance(item, dict):
        t = item.get("title", {})
        return t.get("romaji") or t.get("english") or "?"
    return "?"


def _make_media_table(
    title: str,
    items: list,
    columns: list[
        tuple[str, str, Literal["default", "left", "center", "right", "full"]]
    ],
    max_rows: int = 15,
) -> Table:
    """Build a rich Table from a list of media items."""
    table = Table(title=title, show_header=True, header_style="bold")
    for col_name, style, justify in columns:
        table.add_column(col_name, style=style, justify=justify)

    for i, item in enumerate(items[:max_rows], 1):
        row = [str(i)]
        for col_name, _style, _justify in columns[1:]:
            if col_name == "Title":
                row.append(_format_title(item))
            elif col_name == "Progress":
                us = getattr(item, "user_status", None)
                if us:
                    prog = us.progress or 0
                    total = (
                        getattr(item, "episodes", None)
                        or getattr(item, "chapters", None)
                        or "?"
                    )
                    row.append(f"{prog}/{total}")
                else:
                    row.append("?")
            elif col_name == "Score":
                us = getattr(item, "user_status", None)
                score = us.score if us else None
                row.append(f"{score}%" if score else "?")
            elif col_name == "Episode":
                na = getattr(item, "next_airing", None)
                ep_num = na.episode if na else "?"
                row.append(f"Ep {ep_num}")
            elif col_name == "Time":
                na = getattr(item, "next_airing", None)
                air_time = na.airing_at if na else None
                if air_time:
                    try:
                        dt = datetime.fromtimestamp(int(air_time))
                        row.append(dt.strftime("%a %H:%M"))
                    except (ValueError, TypeError):
                        row.append("?")
                else:
                    row.append("?")
            elif col_name == "Why":
                reason = getattr(item, "playlist_reason", None) or ""
                row.append(reason)
        table.add_row(*row)
    return table


# ── Home (default `anicat` with no args) ────────────────────────────────────


@click.command(short_help="Home — what to watch next")
@click.pass_obj
def home(config: AppConfig):
    """Home page — Continue Watching, Trending, and Smart Playlist."""
    from ...libs.media_api.params import MediaSearchParams
    from ...libs.media_api.types import MediaSort, MediaType

    ctx = _get_ctx(config)

    console.print("[bold cyan]Home[/bold cyan]\n")

    # Continue Watching
    try:
        with console.status("Loading continue watching..."):
            recent = ctx.media_registry.get_recently_watched(
                limit=5, type=MediaType.ANIME
            )
        if recent and recent.media:
            table = _make_media_table(
                "Continue Watching",
                recent.media,
                [
                    ("#", "dim", "left"),
                    ("Title", "", "left"),
                    ("Progress", "", "right"),
                ],
            )
            console.print(table)
            console.print()
    except Exception:
        pass

    # Trending
    try:
        with console.status("Loading trending..."):
            trending = ctx.media_api.search_media(
                MediaSearchParams(
                    type=MediaType.ANIME,
                    sort=MediaSort.TRENDING_DESC,
                    per_page=5,
                )
            )
        if trending and trending.media:
            table = _make_media_table(
                "Trending Now",
                trending.media,
                [
                    ("#", "dim", "left"),
                    ("Title", "", "left"),
                    ("Score", "", "right"),
                ],
            )
            console.print(table)
    except Exception:
        pass

    console.print(
        "\n[dim]anicat search <title>  |  anicat watching  |  anicat discover  |  anicat schedule[/dim]"
    )


# ── Schedule ───────────────────────────────────────────────────────────────


@click.command(short_help="Upcoming anime & manga episodes")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.option("--days", default=3, help="Days ahead to show")
@click.pass_obj
def schedule(config: AppConfig, days: int, type: str):
    """Airing schedule — upcoming episodes."""
    from ...libs.media_api.types import MediaType
    from datetime import datetime as dt, timedelta

    ctx = _get_ctx(config)

    now = dt.now()
    start_ts = int((now - timedelta(days=0)).timestamp())
    end_ts = int((now + timedelta(days=days)).timestamp())

    with console.status("Fetching schedule..."):
        try:
            data = ctx.media_api.get_global_airing_schedule(
                airingAt_greater=start_ts,
                airingAt_lesser=end_ts,
                per_page=50,
            )
        except Exception:
            click.secho("Failed to fetch schedule. Are you logged in?", fg="red")
            return

    if not data or not data.media:
        click.echo("No upcoming episodes found.")
        return

    # Filter by type if specified
    media_list = data.media
    if type:
        media_type = MediaType(type)
        media_list = [m for m in media_list if m.type == media_type]

    if not media_list:
        click.echo("No upcoming episodes found.")
        return

    table = _make_media_table(
        f"Schedule (next {days} days)",
        media_list[:15],
        [
            ("Time", "dim", "left"),
            ("Title", "bold white", "left"),
            ("Episode", "", "right"),
        ],
    )
    console.print(table)


# ── Profile ────────────────────────────────────────────────────────────────


@click.command(short_help="Your AniList profile & stats")
@click.pass_obj
def profile(config: AppConfig):
    """Show your AniList profile and statistics."""
    ctx = _get_ctx(config)

    with console.status("Loading profile..."):
        try:
            if not ctx.media_api.is_authenticated():
                click.secho("Not logged in. Run: anicat login", fg="red")
                return
            profile_data = ctx.media_api.get_viewer_profile()
        except Exception:
            click.secho("Failed to load profile. Are you offline?", fg="red")
            return

    if not profile_data:
        click.secho("Could not load profile.", fg="red")
        return

    name = getattr(profile_data, "name", None) or "?"
    anime = getattr(profile_data, "anime_count", 0)
    manga = getattr(profile_data, "manga_count", 0)
    minutes = getattr(profile_data, "minutes_watched", 0)
    eps = getattr(profile_data, "episodes_watched", 0)
    chaps = getattr(profile_data, "chapters_read", 0)
    about = getattr(profile_data, "about", None) or ""

    console.print(f"\n[bold cyan]{name}[/bold cyan]")
    console.print(f"  Anime: {anime}  |  Manga: {manga}")
    console.print(f"  Episodes watched: {eps}  |  Chapters read: {chaps}")
    if minutes:
        hours = minutes // 60
        console.print(f"  Watch time: {hours}h ({minutes}m)")
    if about:
        console.print(f"\n  [dim]{about[:200]}[/dim]")


# ── Notifications ──────────────────────────────────────────────────────────


@click.command(short_help="Unread AniList notifications")
@click.pass_obj
def notifications(config: AppConfig):
    """Check your unread AniList notifications."""
    ctx = _get_ctx(config)

    with console.status("Checking..."):
        try:
            if not ctx.media_api.is_authenticated():
                click.secho("Not logged in. Run: anicat login", fg="red")
                return
            # Fetch first page of notifications to count unread
            result = ctx.media_api.get_notifications()
            count = len(result) if result else 0
        except Exception:
            click.secho("Failed to check notifications.", fg="red")
            return

    if count == 0:
        click.echo("No unread notifications.")
    else:
        click.secho(
            f"{count} unread notification{'s' if count != 1 else ''}.", fg="amber"
        )
        click.echo("Open the Dashboard to view them: anicat dashboard")


# ── Shortcuts ──────────────────────────────────────────────────────────────


@click.command(short_help="Currently watching")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def watching(config: AppConfig, type: str):
    """View your currently watching/reading list."""
    from ...libs.media_api.params import UserMediaListSearchParams
    from ...libs.media_api.types import MediaType, UserMediaListStatus

    ctx = _get_ctx(config)
    if not ctx.media_api.is_authenticated():
        click.secho("Not logged in. Run: anicat login", fg="red")
        return

    with console.status("Loading..."):
        result = ctx.media_api.search_media_list(
            UserMediaListSearchParams(
                status=UserMediaListStatus.WATCHING,
                type=MediaType(type) if type else None,
            )
        )
    _display_media_list(
        result.media if result else [],
        f"{'Watching' if type == 'ANIME' else 'Reading'}",
    )


@click.command(short_help="Plan to watch")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def planning(config: AppConfig, type: str):
    """View your plan-to-watch/read list."""
    from ...libs.media_api.params import UserMediaListSearchParams
    from ...libs.media_api.types import MediaType, UserMediaListStatus

    ctx = _get_ctx(config)
    if not ctx.media_api.is_authenticated():
        click.secho("Not logged in. Run: anicat login", fg="red")
        return

    with console.status("Loading..."):
        result = ctx.media_api.search_media_list(
            UserMediaListSearchParams(
                status=UserMediaListStatus.PLANNING,
                type=MediaType(type) if type else None,
            )
        )
    _display_media_list(result.media if result else [], "Planning")


@click.command(short_help="Finished watching")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def completed(config: AppConfig, type: str):
    """View your completed anime/manga."""
    from ...libs.media_api.params import UserMediaListSearchParams
    from ...libs.media_api.types import MediaType, UserMediaListStatus

    ctx = _get_ctx(config)
    if not ctx.media_api.is_authenticated():
        click.secho("Not logged in. Run: anicat login", fg="red")
        return

    with console.status("Loading..."):
        result = ctx.media_api.search_media_list(
            UserMediaListSearchParams(
                status=UserMediaListStatus.COMPLETED,
                type=MediaType(type) if type else None,
            )
        )
    _display_media_list(result.media if result else [], "Completed")


# ── Manga ──────────────────────────────────────────────────────────────────


@click.command(short_help="Trending & popular manga")
@click.pass_obj
def manga(config: AppConfig):
    """Manga homepage — trending, popular, and currently reading."""
    from ...libs.media_api.params import MediaSearchParams, UserMediaListSearchParams
    from ...libs.media_api.types import MediaSort, MediaType, UserMediaListStatus

    ctx = _get_ctx(config)

    console.print("[bold cyan]Manga[/bold cyan]\n")

    # Currently Reading
    if ctx.media_api.is_authenticated():
        with console.status("Loading manga data..."):
            try:
                reading = ctx.media_api.search_media_list(
                    UserMediaListSearchParams(
                        status=UserMediaListStatus.WATCHING,
                        type=MediaType.MANGA,
                    )
                )
                if reading and reading.media:
                    table = _make_media_table(
                        "Currently Reading",
                        reading.media[:5],
                        [
                            ("Title", "", "left"),
                            ("Progress", "", "right"),
                            ("Score", "", "right"),
                        ],
                    )
                    console.print(table)
                    console.print()
            except Exception:
                pass

    # Trending Manga
    with console.status("Loading trending manga..."):
        try:
            trending = ctx.media_api.search_media(
                MediaSearchParams(
                    type=MediaType.MANGA,
                    sort=MediaSort.TRENDING_DESC,
                    per_page=5,
                )
            )
            if trending and trending.media:
                table = _make_media_table(
                    "Trending Manga",
                    trending.media[:5],
                    [
                        ("#", "dim", "left"),
                        ("Title", "", "left"),
                        ("Score", "", "right"),
                    ],
                )
                console.print(table)
        except Exception:
            pass

    console.print("\n[dim]anicat search -t MANGA <title>  |  anicat lists[/dim]")


# ── Library ────────────────────────────────────────────────────────────────


@click.command(short_help="Your completed library")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.option("--page", "-p", default=1, help="Page number")
@click.pass_obj
def library(config: AppConfig, type: str, page: int):
    """Browse your completed anime/manga library."""
    from ...libs.media_api.params import UserMediaListSearchParams
    from ...libs.media_api.types import MediaType, UserMediaListStatus

    ctx = _get_ctx(config)
    if not ctx.media_api.is_authenticated():
        click.secho("Not logged in. Run: anicat login", fg="red")
        return

    with console.status("Loading..."):
        result = ctx.media_api.search_media_list(
            UserMediaListSearchParams(
                status=UserMediaListStatus.COMPLETED,
                type=MediaType(type) if type else None,
                page=page,
            )
        )
    _display_media_list(result.media if result else [], f"{type} Library")


def _display_media_list(items, label: str):
    """Render a media list as a rich table."""
    if not items:
        click.echo(f"Nothing in {label}.")
        return
    table = Table(title=label, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Progress", justify="right")
    table.add_column("Score", justify="right")
    for i, item in enumerate(items[:20], 1):
        title = _format_title(item)
        us = getattr(item, "user_status", None)
        prog = str(us.progress or "-") if us else "-"
        total = (
            getattr(item, "episodes", None) or getattr(item, "chapters", None) or "?"
        )
        score = str(us.score or "-") if us and us.score is not None else "-"
        table.add_row(str(i), title, f"{prog}/{total}", score)
    console.print(table)
