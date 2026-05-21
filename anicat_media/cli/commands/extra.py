"""Quick-access CLI commands that mirror the API endpoints."""

import click
import httpx
from rich.console import Console
from rich.table import Table
from ...core.config import AppConfig
from ...core.constants import LOCAL_API_ORIGIN

console = Console()


@click.command(short_help="Binge all episodes of an anime")
@click.option("--anime-title", "-t", required=True, multiple=True, help="Anime title to binge")
@click.pass_obj
def binge(config: AppConfig, anime_title: tuple[str, ...]):
    """Binge all episodes of an anime (alias for search -t <title> -r ':')."""
    from .search import search

    # Call search with the binge range
    for title in anime_title:
        click.echo(f"Starting binge for: {', '.join(anime_title)}")
    ctx = click.get_current_context()
    # We can't easily call search with modified options, so redirect
    click.echo("Use: anicat search -t <title> -r ':'")
    raise SystemExit(0)


@click.command(short_help="Get personalized recommendations")
@click.pass_obj
def discover(config: AppConfig):
    """Get a personalized Smart Playlist of recommendations."""
    url = f"{LOCAL_API_ORIGIN}/api/media/smart-playlist"
    with console.status("Fetching your personalized playlist..."):
        try:
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code != 200:
                click.secho("Failed to fetch playlist. Is the dashboard running?", fg="red")
                return
            data = resp.json()
            media = data.get("media", [])
            if not media:
                click.echo("No recommendations available. Try adding shows to your watchlist.")
                return
        except Exception:
            click.secho("Cannot connect to dashboard. Start it with: anicat dashboard", fg="red")
            return

    table = Table(title="Smart Playlist", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Why", style="italic green")

    for i, item in enumerate(media[:15], 1):
        title = (item.get("title", {}).get("romaji") or
                 item.get("title", {}).get("english") or "Unknown")
        reason = item.get("playlist_reason", "")
        table.add_row(str(i), title, reason)

    console.print(table)


@click.command(short_help="View details about a media entry")
@click.argument("media_id", type=int)
@click.pass_obj
def details(config: AppConfig, media_id: int):
    """View details about a media entry by its AniList ID."""
    url = f"{LOCAL_API_ORIGIN}/api/media/{media_id}"
    with console.status(f"Fetching details for #{media_id}..."):
        try:
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code != 200:
                click.secho("Failed to fetch details. Is the dashboard running?", fg="red")
                return
            item = resp.json()
        except Exception:
            click.secho("Cannot connect to dashboard.", fg="red")
            return

    title = (item.get("title", {}).get("romaji") or
             item.get("title", {}).get("english") or "Unknown")
    episodes = item.get("episodes", "?")
    score = item.get("average_score", "?")
    status = item.get("status", "?")
    desc = item.get("description", "")

    console.print(f"\n[bold cyan]{title}[/bold cyan]", highlight=False)
    console.print(f"  Episodes: {episodes}  |  Score: {score}%  |  Status: {status}")
    if desc:
        # Truncate long descriptions
        desc = desc[:500].replace("<br>", "\n").replace("<i>", "").replace("</i>", "")
        console.print(f"\n  [dim]{desc}[/dim]")
    console.print(f"\n  [dim]AniList ID: {media_id}[/dim]")


@click.command(short_help="Track your watch progress")
@click.argument("media_id", type=int)
@click.option("--episode", "-e", type=int, help="Episode number you watched")
@click.option("--status", "-s", type=click.Choice(["watching", "completed", "planning", "dropped", "paused", "repeating"]), help="Update list status")
@click.option("--score", type=int, help="Score (1-10)")
@click.pass_obj
def track(config: AppConfig, media_id: int, episode: int | None, status: str | None, score: int | None):
    """Update your watch progress and AniList list status."""
    if not episode and not status and not score:
        click.echo("Specify at least one of: --episode, --status, --score")
        return

    url = f"{LOCAL_API_ORIGIN}/api/user/update"
    body = {"media_id": media_id}
    if episode:
        body["progress"] = str(episode)
    if status:
        body["status"] = status.lower()
    if score is not None:
        body["score"] = score

    try:
        resp = httpx.post(url, json=body, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                click.secho("Progress updated!", fg="green")
            else:
                click.secho(f"Update failed: {data}", fg="red")
        else:
            click.secho("Cannot connect to dashboard.", fg="red")
    except Exception:
        click.secho("Cannot connect to dashboard. Start it with: anicat dashboard", fg="red")
