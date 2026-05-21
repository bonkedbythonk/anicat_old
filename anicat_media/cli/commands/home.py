"""Home, Schedule, Profile, Notifications — app-aligned CLI views."""

import click
from rich.console import Console
from rich.table import Table
from ...core.config import AppConfig
from ...core.constants import LOCAL_API_ORIGIN
import httpx
from datetime import datetime

console = Console()


# ── Home (default `anicat` with no args) ────────────────────────────────────

@click.command(short_help="Home — what to watch next")
@click.pass_obj
def home(config: AppConfig):
    """Home page — Continue Watching, Trending, and Smart Playlist."""
    console.print("[bold cyan]Home[/bold cyan]\n")
    
    # Continue Watching
    try:
        data = _api_get(f"{LOCAL_API_ORIGIN}/api/media/recent?type=ANIME&limit=5")
        if data and data.get("media"):
            table = Table(title="Continue Watching", show_header=True, header_style="bold")
            table.add_column("#", style="dim", width=2)
            table.add_column("Title")
            table.add_column("Progress", justify="right")
            for i, item in enumerate(data["media"][:5], 1):
                title = (item.get("title", {}).get("romaji") or
                         item.get("title", {}).get("english") or "?")
                prog = item.get("user_status", {}).get("progress", 0)
                total = item.get("episodes", "?")
                table.add_row(str(i), title, f"{prog}/{total}")
            console.print(table)
            console.print()
    except Exception:
        pass

    # Trending
    try:
        data = _api_get(f"{LOCAL_API_ORIGIN}/api/media/trending?type=ANIME&per_page=5")
        if data and data.get("media"):
            table = Table(title="Trending Now", show_header=True, header_style="bold")
            table.add_column("#", style="dim", width=2)
            table.add_column("Title")
            table.add_column("Score", justify="right")
            for i, item in enumerate(data["media"][:5], 1):
                title = (item.get("title", {}).get("romaji") or
                         item.get("title", {}).get("english") or "?")
                score = item.get("average_score", "?")
                table.add_row(str(i), title, f"{score}%")
            console.print(table)
    except Exception:
        pass

    console.print("\n[dim]anicat search <title>  |  anicat watching  |  anicat discover  |  anicat schedule[/dim]")


# ── Schedule ───────────────────────────────────────────────────────────────

@click.command(short_help="Upcoming anime & manga episodes")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.option("--days", default=3, help="Days ahead to show")
@click.pass_obj
def schedule(config: AppConfig, days: int, type: str):
    """Airing schedule — upcoming episodes."""
    url = f"{LOCAL_API_ORIGIN}/api/media/schedule?days_before=0&days_after={days}"
    if type:
        url += f"&type={type}"
    
    with console.status("Fetching schedule..."):
        data = _api_get(url)

    if not data or not data.get("media"):
        click.echo("No upcoming episodes found.")
        return

    table = Table(title=f"Schedule (next {days} days)", show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim")
    table.add_column("Title", style="bold white")
    table.add_column("Episode", justify="right")

    for item in data["media"][:15]:
        title = (item.get("title", {}).get("romaji") or
                 item.get("title", {}).get("english") or "?")
        next_ep = item.get("next_airing")
        ep_num = next_ep.get("episode", "?") if next_ep else "?"
        air_time = next_ep.get("airing_at", "?") if next_ep else "?"
        # Format time nicely
        if air_time and air_time != "?":
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(int(air_time))
                air_time = dt.strftime("%a %H:%M")
            except (ValueError, TypeError):
                air_time = "?"
        table.add_row(air_time, title, f"Ep {ep_num}")

    console.print(table)


# ── Profile ────────────────────────────────────────────────────────────────

@click.command(short_help="Your AniList profile & stats")
@click.pass_obj
def profile(config: AppConfig):
    """Show your AniList profile and statistics."""
    with console.status("Loading profile..."):
        profile_data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/profile")

    if not profile_data:
        click.secho("Not connected to dashboard.", fg="red")
        return

    name = profile_data.get("name", "?")
    anime = profile_data.get("anime_count", 0)
    manga = profile_data.get("manga_count", 0)
    minutes = profile_data.get("minutes_watched", 0)
    eps = profile_data.get("episodes_watched", 0)
    chaps = profile_data.get("chapters_read", 0)
    about = profile_data.get("about", "")

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
    with console.status("Checking..."):
        health = _api_get(f"{LOCAL_API_ORIGIN}/api/status/health")
    count = health.get("unread_notifications", 0) if health else 0
    if count == 0:
        click.echo("No unread notifications.")
    else:
        click.secho(f"{count} unread notification{'s' if count != 1 else ''}.", fg="amber")
        click.echo("Open the Dashboard to view them: anicat dashboard")


# ── Shortcuts ──────────────────────────────────────────────────────────────

@click.command(short_help="Currently watching")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def watching(config: AppConfig, type: str):
    """View your currently watching/reading list."""
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=watching&type={type}")
    display_list(data, f"{'Watching' if type == 'ANIME' else 'Reading'}")


@click.command(short_help="Plan to watch")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def planning(config: AppConfig, type: str):
    """View your plan-to-watch/read list."""
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=planning&type={type}")
    display_list(data, "Planning")


@click.command(short_help="Finished watching")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.pass_obj
def completed(config: AppConfig, type: str):
    """View your completed anime/manga."""
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=completed&type={type}")
    display_list(data, "Completed")


# ── Manga ──────────────────────────────────────────────────────────────────

@click.command(short_help="Trending & popular manga")
@click.pass_obj
def manga(config: AppConfig):
    """Manga homepage — trending, popular, and currently reading."""
    with console.status("Loading manga data..."):
        trending = _api_get(f"{LOCAL_API_ORIGIN}/api/media/trending?type=MANGA&per_page=5")
        reading = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=watching&type=MANGA")

    console.print("[bold cyan]Manga[/bold cyan]\n")

    if reading and reading.get("media"):
        table = Table(title="Currently Reading", show_header=True, header_style="bold")
        table.add_column("Title")
        table.add_column("Progress", justify="right")
        table.add_column("Score", justify="right")
        for item in reading["media"][:5]:
            title = (item.get("title", {}).get("romaji") or
                     item.get("title", {}).get("english") or "?")
            prog = item.get("user_status", {}).get("progress", 0)
            total = item.get("chapters", "?")
            score = item.get("user_status", {}).get("score", "-")
            table.add_row(title, f"{prog}/{total}", str(score))
        console.print(table)
        console.print()

    if trending and trending.get("media"):
        table = Table(title="Trending Manga", show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=2)
        table.add_column("Title")
        table.add_column("Score", justify="right")
        for i, item in enumerate(trending["media"][:5], 1):
            title = (item.get("title", {}).get("romaji") or
                     item.get("title", {}).get("english") or "?")
            score = item.get("average_score", "?")
            table.add_row(str(i), title, f"{score}%")
        console.print(table)

    console.print("\n[dim]anicat search -t MANGA <title>  |  anicat lists[/dim]")


# ── Library ────────────────────────────────────────────────────────────────

@click.command(short_help="Your completed library")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
@click.option("--page", "-p", default=1, help="Page number")
@click.pass_obj
def library(config: AppConfig, type: str, page: int):
    """Browse your completed anime/manga library."""
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=completed&type={type}&page={page}")
    display_list(data, f"{type} Library")

def _api_get(url: str):
    """Fetch JSON from the local API."""
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def display_list(data, label: str):
    """Render a user list as a rich table."""
    if not data or not data.get("media"):
        click.echo(f"Nothing in {label}.")
        return
    table = Table(title=label, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Progress", justify="right")
    table.add_column("Score", justify="right")
    for i, item in enumerate(data["media"][:20], 1):
        title = (item.get("title", {}).get("romaji") or
                 item.get("title", {}).get("english") or "?")
        prog = item.get("user_status", {}).get("progress", "-")
        total = item.get("episodes") or item.get("chapters") or "?"
        score = item.get("user_status", {}).get("score", "-")
        score_str = str(score) if score is not None and score != "-" else "-"
        table.add_row(str(i), title, f"{prog}/{total}", score_str)
    console.print(table)
