"""View your AniList — watching, planning, completed, paused, dropped.

Uses the shared Context service layer directly, so it works standalone.
"""

import click
from rich.console import Console
from rich.table import Table
from ...core.config import AppConfig

console = Console()


def _get_ctx(config: AppConfig):
    """Create a Context for standalone CLI commands."""
    from ..interactive.session import Context

    return Context(config)


def _format_title(item) -> str:
    """Extract the best display title from a media item."""
    title_obj = getattr(item, "title", None)
    if title_obj:
        return title_obj.romaji or title_obj.english or "?"
    return "?"


def _display_list(items, label):
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


def _fetch_user_list(config: AppConfig, status: str, mediatype: str = "ANIME"):
    """Fetch a user list via the shared service layer."""
    from ...libs.media_api.params import UserMediaListSearchParams
    from ...libs.media_api.types import MediaType, UserMediaListStatus

    ctx = _get_ctx(config)
    if not ctx.media_api.is_authenticated():
        click.secho("Not logged in. Run: anicat login", fg="red")
        return None

    status_map = {
        "watching": UserMediaListStatus.WATCHING,
        "planning": UserMediaListStatus.PLANNING,
        "completed": UserMediaListStatus.COMPLETED,
        "paused": UserMediaListStatus.PAUSED,
        "dropped": UserMediaListStatus.DROPPED,
    }
    list_status = status_map.get(status, UserMediaListStatus.WATCHING)
    media_type = MediaType(mediatype) if mediatype else None

    with console.status("Loading..."):
        result = ctx.media_api.search_media_list(
            UserMediaListSearchParams(status=list_status, type=media_type)
        )
    return result.media if result else []


@click.group(
    name="list",
    short_help="View your AniList (watching, planning, completed, paused, dropped)",
)
def list_group():
    """View your AniList by status."""
    pass


@list_group.command(short_help="Currently watching")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def watching(config: AppConfig, type: str):
    """Show your currently watching anime."""
    items = _fetch_user_list(config, "watching", type)
    if items is not None:
        _display_list(items, "Watching")


@list_group.command(short_help="Plan to watch")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def planning(config: AppConfig, type: str):
    """Show your plan-to-watch list."""
    items = _fetch_user_list(config, "planning", type)
    if items is not None:
        _display_list(items, "Planning")


@list_group.command(short_help="Completed")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def completed(config: AppConfig, type: str):
    """Show your completed anime."""
    items = _fetch_user_list(config, "completed", type)
    if items is not None:
        _display_list(items, "Completed")


@list_group.command(short_help="Paused")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def paused(config: AppConfig, type: str):
    """Show your paused anime/manga."""
    items = _fetch_user_list(config, "paused", type)
    if items is not None:
        _display_list(items, "Paused")


@list_group.command(short_help="Dropped")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def dropped(config: AppConfig, type: str):
    """Show your dropped anime/manga."""
    items = _fetch_user_list(config, "dropped", type)
    if items is not None:
        _display_list(items, "Dropped")
