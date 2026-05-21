"""Downloads management — add, list, clear."""

import click
from rich.console import Console
from rich.table import Table
from ...core.constants import LOCAL_API_ORIGIN
import httpx

console = Console()


@click.group(short_help="Manage your downloads queue")
def downloads():
    """Manage your downloads queue."""
    pass


@downloads.command(short_help="Add episodes to the download queue")
@click.argument("media_id", type=int)
@click.option("--episodes", "-e", required=True, help="Episode range (e.g., 1-12 or 5)")
def add(media_id: int, episodes: str):
    """Add episodes from a show to the download queue."""
    url = f"{LOCAL_API_ORIGIN}/api/queue/add?media_id={media_id}"
    try:
        resp = httpx.post(url, json=[episodes], timeout=5.0)
        if resp.status_code == 200:
            click.secho("Added to download queue.", fg="green")
        else:
            click.secho(f"Failed: {resp.text}", fg="red")
    except Exception:
        click.secho("Cannot connect to dashboard.", fg="red")


@downloads.command(short_help="View download queue")
def list():
    """View your download queue."""
    url = f"{LOCAL_API_ORIGIN}/api/queue/"
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code != 200:
            click.secho("Cannot connect to dashboard.", fg="red")
            return
        items = resp.json()
        if not items:
            click.echo("Download queue is empty.")
            return
    except Exception:
        click.secho("Cannot connect to dashboard.", fg="red")
        return

    table = Table(title="Download Queue", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Episode", justify="right")
    table.add_column("Status")

    for i, item in enumerate(items[:20], 1):
        table.add_row(
            str(i),
            item.get("media_title", "?"),
            item.get("episode_number", "?"),
            item.get("status", "?"),
        )
    console.print(table)


@downloads.command(short_help="Clear the download queue")
def clear():
    """Clear all queued items from the download registry."""
    url = f"{LOCAL_API_ORIGIN}/api/queue/clear"
    try:
        resp = httpx.post(url, timeout=5.0)
        if resp.status_code == 200:
            click.secho("Queue cleared.", fg="green")
        else:
            click.secho(f"Failed: {resp.text}", fg="red")
    except Exception:
        click.secho("Cannot connect to dashboard.", fg="red")
