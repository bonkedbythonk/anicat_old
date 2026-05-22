"""Quick-access CLI commands that use the shared Context service layer."""

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


@click.command(short_help="Binge all episodes of an anime")
@click.option(
    "--anime-title", "-t", required=True, multiple=True, help="Anime title to binge"
)
@click.pass_obj
def binge(config: AppConfig, anime_title: tuple[str, ...]):
    """Binge all episodes of an anime (alias for search -t <title> -r ':')."""
    click.echo("Use: anicat search -t <title> -r ':'")
    raise SystemExit(0)


@click.command(short_help="Get personalized recommendations")
@click.pass_obj
def discover(config: AppConfig):
    """Get a personalized Smart Playlist of recommendations."""
    from ...libs.media_api.params import MediaSearchParams
    from ...libs.media_api.types import MediaSort, MediaType

    ctx = _get_ctx(config)

    with console.status("Fetching your personalized playlist..."):
        try:
            trending = ctx.media_api.search_media(
                MediaSearchParams(
                    type=MediaType.ANIME,
                    sort=MediaSort.TRENDING_DESC,
                    per_page=15,
                )
            )
            media = trending.media if trending else []
            if not media:
                click.echo(
                    "No recommendations available. Try adding shows to your watchlist."
                )
                return
        except Exception:
            click.secho("Failed to fetch recommendations. Are you logged in?", fg="red")
            return

    table = Table(title="Smart Playlist", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Score", justify="right")

    for i, item in enumerate(media[:15], 1):
        title = _format_title(item)
        score = getattr(item, "average_score", None) or "?"
        table.add_row(str(i), title, f"{score}%")

    console.print(table)


@click.command(short_help="View details about a media entry")
@click.argument("media_id", type=int)
@click.pass_obj
def details(config: AppConfig, media_id: int):
    """View details about a media entry by its AniList ID."""
    ctx = _get_ctx(config)

    with console.status(f"Fetching details for #{media_id}..."):
        try:
            item = ctx.media_api.get_media_item(media_id)
        except Exception:
            click.secho("Failed to fetch details.", fg="red")
            return

    if not item:
        click.secho(f"Media #{media_id} not found.", fg="red")
        return

    title = _format_title(item)
    episodes = getattr(item, "episodes", None) or "?"
    score = getattr(item, "average_score", None) or "?"
    status = getattr(item, "status", None) or "?"
    desc = getattr(item, "description", None) or ""

    console.print(f"\n[bold cyan]{title}[/bold cyan]", highlight=False)
    console.print(f"  Episodes: {episodes}  |  Score: {score}%  |  Status: {status}")
    if desc:
        desc = desc[:500].replace("<br>", "\n").replace("<i>", "").replace("</i>", "")
        console.print(f"\n  [dim]{desc}[/dim]")
    console.print(f"\n  [dim]AniList ID: {media_id}[/dim]")


@click.command(short_help="Track your watch progress")
@click.argument("media_id", type=int)
@click.option("--episode", "-e", type=int, help="Episode number you watched")
@click.option(
    "--status",
    "-s",
    type=click.Choice(
        ["watching", "completed", "planning", "dropped", "paused", "repeating"]
    ),
    help="Update list status",
)
@click.option("--score", type=int, help="Score (1-10)")
@click.pass_obj
def track(
    config: AppConfig,
    media_id: int,
    episode: int | None,
    status: str | None,
    score: int | None,
):
    """Update your watch progress and AniList list status."""
    from ...libs.media_api.types import UserMediaListStatus

    if not episode and not status and not score:
        click.echo("Specify at least one of: --episode, --status, --score")
        return

    ctx = _get_ctx(config)

    try:
        # Get the media item for registry saving
        media_item = ctx.media_api.get_media_item(media_id)

        # Update via shared WatchHistoryService (local registry + AniList sync)
        if media_item is None:
            click.secho(f"Media #{media_id} not found.", fg="red")
            return

        status_enum = UserMediaListStatus(status) if status else None
        ctx.watch_history.update(
            media_item=media_item,
            progress=str(episode) if episode else None,
            status=status_enum,
            score=float(score) if score is not None else None,
        )
        ctx.data_version += 1
        click.secho("Progress updated!", fg="green")
    except Exception as e:
        click.secho(f"Update failed: {e}", fg="red")
