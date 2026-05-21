"""View your AniList — watching, planning, completed."""

import click
from rich.console import Console
from rich.table import Table
from ...core.config import AppConfig
from ...core.constants import LOCAL_API_ORIGIN
import httpx

console = Console()


@click.group(short_help="View your AniList (watching, planning, completed)")
def list():
    """View your AniList by status."""
    pass


def _fetch_list(status: str, type: str = "ANIME"):
    """Fetch a user list from the API."""
    url = f"{LOCAL_API_ORIGIN}/api/user/list?status={status}&type={type}"
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code != 200:
            click.secho("Cannot connect to dashboard. Start it with: anicat dashboard", fg="red")
            return None
        return resp.json()
    except Exception:
        click.secho("Cannot connect to dashboard.", fg="red")
        return None


def _display_list(data, label):
    if not data or not data.get("media"):
        click.echo(f"Nothing in {label}.")
        return
    table = Table(title=label, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Progress", justify="right")
    table.add_column("Score", justify="right")
    for i, item in enumerate(data["media"][:20], 1):
        title = (item.get("title", {}).get("romaji") or item.get("title", {}).get("english") or "?")
        prog = item.get("user_status", {}).get("progress", "-")
        total = item.get("episodes") or "?"
        score = item.get("user_status", {}).get("score", "-")
        table.add_row(str(i), title, f"{prog}/{total}", str(score) if score != "-" else "-")
    console.print(table)


@list.command(short_help="Currently watching")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
def watching(type):
    """Show your currently watching anime."""
    data = _fetch_list("watching", type)
    _display_list(data, "Watching")


@list.command(short_help="Plan to watch")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
def planning(type):
    """Show your plan-to-watch list."""
    data = _fetch_list("planning", type)
    _display_list(data, "Planning")


@list.command(short_help="Completed")
@click.option("--type", "-t", default="ANIME", help="ANIME or MANGA")
def completed(type):
    """Show your completed anime."""
    data = _fetch_list("completed", type)
    _display_list(data, "Completed")
