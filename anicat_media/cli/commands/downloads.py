"""Downloads management — add, list, clear.

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


@click.group(short_help="Manage your downloads queue")
def downloads():
    """Manage your downloads queue."""
    pass


@downloads.command(short_help="Add episodes to the download queue")
@click.argument("media_id", type=int)
@click.option("--episodes", "-e", required=True, help="Episode range (e.g., 1-12 or 5)")
@click.pass_obj
def add(config: AppConfig, media_id: int, episodes: str):
    """Add episodes from a show to the download queue."""
    ctx = _get_ctx(config)

    try:
        # Parse episode range (simple comma/single format for downloads)
        episode_list = _parse_simple_range(episodes)
        if not episode_list:
            click.secho("Invalid episode range.", fg="red")
            return

        # Resolve media item
        media_item = ctx.media_api.get_media_item(media_id)
        if not media_item:
            click.secho(f"Media #{media_id} not found.", fg="red")
            return

        # Queue each episode via the download service
        queued = 0
        for ep in episode_list:
            if ctx.download.add_to_queue(media_item, str(ep)):
                queued += 1

        click.secho(f"Added {queued} episode(s) to download queue.", fg="green")
    except Exception as e:
        click.secho(f"Failed: {e}", fg="red")


@downloads.command(name="list", short_help="View download queue")
@click.pass_obj
def list_queue(config: AppConfig):
    """View your download queue."""
    from ..service.registry.models import DownloadStatus

    ctx = _get_ctx(config)

    try:
        records = list(ctx.media_registry.get_all_media_records())
        queued_items = []
        for record in records:
            if hasattr(record, "media_episodes") and record.media_episodes:
                for ep in record.media_episodes:
                    if getattr(ep, "download_status", None) in (
                        DownloadStatus.QUEUED,
                        DownloadStatus.DOWNLOADING,
                    ):
                        queued_items.append(
                            {
                                "title": (
                                    record.media_item.title.english
                                    or record.media_item.title.romaji
                                    or "?"
                                ),
                                "episode": ep.episode_number,
                                "status": (
                                    ep.download_status.value
                                    if hasattr(ep.download_status, "value")
                                    else str(ep.download_status)
                                ),
                            }
                        )

        if not queued_items:
            click.echo("Download queue is empty.")
            return
    except Exception as e:
        click.secho(f"Failed to fetch queue: {e}", fg="red")
        return

    table = Table(title="Download Queue", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold white")
    table.add_column("Episode", justify="right")
    table.add_column("Status")

    for i, item in enumerate(queued_items[:20], 1):
        table.add_row(str(i), item["title"], str(item["episode"]), item["status"])
    console.print(table)


@downloads.command(short_help="Clear the download queue")
@click.pass_obj
def clear(config: AppConfig):
    """Clear all queued items from the download registry."""
    from ..service.registry.models import DownloadStatus

    ctx = _get_ctx(config)

    try:
        records = list(ctx.media_registry.get_all_media_records())
        cleared = 0
        for record in records:
            if hasattr(record, "media_episodes") and record.media_episodes:
                for ep in record.media_episodes:
                    if getattr(ep, "download_status", None) in (
                        DownloadStatus.QUEUED,
                        DownloadStatus.FAILED,
                    ):
                        ctx.media_registry.update_episode_download_status(
                            media_id=record.media_item.id,
                            episode_number=ep.episode_number,
                            status=DownloadStatus.COMPLETED,
                        )
                        cleared += 1

        click.secho(f"Cleared {cleared} item(s) from queue.", fg="green")
    except Exception as e:
        click.secho(f"Failed: {e}", fg="red")


def _parse_simple_range(episodes: str) -> list[str]:
    """Parse a simple episode string like '1-5' or '1,3,5' or '7' into a list."""
    result = []
    for part in episodes.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start_s, end_s = part.split("-", 1)
                start, end = int(start_s), int(end_s)
                result.extend(str(i) for i in range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                int(part)
                result.append(part)
            except ValueError:
                continue
    return result
