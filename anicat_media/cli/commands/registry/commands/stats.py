"""
Registry stats command - show detailed statistics about the local registry
"""

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict

import click
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .....core.config import AppConfig
from ....service.feedback import FeedbackService
from ....service.registry.service import MediaRegistryService
from .....core.theme import ICONS

if TYPE_CHECKING:
    from ....service.registry.service import StatBreakdown

# --- Constants for better maintainability ---
TOP_N_STATS = 10


@click.command(help="Show detailed statistics about the local media registry")
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed breakdown by genre, format, and year",
)
@click.option(
    "--json", "output_json", is_flag=True, help="Output statistics in JSON format"
)
@click.option(
    "--api",
    default="anilist",
    type=click.Choice(["anilist"], case_sensitive=False),
    help="Media API to show stats for",
)
@click.pass_obj
def stats(config: AppConfig, detailed: bool, output_json: bool, api: str):
    """
    Display comprehensive statistics about your local media registry.

    Shows total counts, status breakdown, and optionally detailed
    analysis by genre, format, and release year.
    """
    feedback = FeedbackService(config)
    console = Console()

    try:
        registry_service = MediaRegistryService(api, config.media_registry)
        stats_data = registry_service.get_registry_stats()

        if output_json:
            print(json.dumps(stats_data, indent=2, default=str))
            return

        _display_stats_overview(console, stats_data, api, config.general.icons)

        if detailed:
            _display_detailed_stats(console, stats_data, config.general.icons)

    except Exception as e:
        feedback.error("Stats Error", f"Failed to generate statistics: {e}")
        raise click.Abort()


def _display_stats_overview(
    console: Console, stats: "StatBreakdown", api: str, icons: bool
):
    """
    Display the main overview and status breakdown tables.
    """
    # --- Main Overview Table ---
    overview_table = Table.grid(expand=True, padding=(0, 1))
    overview_table.add_column("Metric", style="bold cyan", no_wrap=True)
    overview_table.add_column("Value", style="white")

    overview_table.add_row("Media API:", api.title())
    overview_table.add_row("Total Media:", str(stats.get("total_media", 0)))
    overview_table.add_row("Registry Version:", str(stats.get("version", "Unknown")))

    # Format "Last Updated" timestamp to be more human-readable
    last_updated_str = stats.get("last_updated", "Never")
    if last_updated_str != "Never":
        try:
            last_updated_dt = datetime.fromisoformat(last_updated_str)
            last_updated_str = _format_timedelta(datetime.now() - last_updated_dt)
        except (ValueError, TypeError):
            pass  # Keep original string if parsing fails
    overview_table.add_row("Last Updated:", last_updated_str)

    # Format storage size
    storage_size_str = _format_storage_size(float(stats.get("storage_size_bytes", 0)))
    overview_table.add_row("Storage Size:", storage_size_str)

    console.print(
        Panel(
            overview_table,
            title=f"{ICONS.get('STATS', icons)}Registry Overview",
            border_style="cyan",
        )
    )
    console.print()

    # --- Status Breakdown Table ---
    status_breakdown = stats.get("status_breakdown", {})
    if status_breakdown:
        status_table = _create_breakdown_table(
            title=f"{ICONS.get('LIST', icons)}Status Breakdown",
            data=status_breakdown,
            key_header="Status",
            value_header="Count",
            show_percentage=True,
        )
        console.print(status_table)
        console.print()

    # --- Download Status Table ---
    download_stats = stats.get("download_stats", {})
    if download_stats:
        download_table = _create_breakdown_table(
            title=f"{ICONS.get('SAVE', icons)}Download Status",
            data=download_stats,
            key_header="Status",
            value_header="Count",
            show_percentage=False,
        )
        console.print(download_table)
        console.print()


def _display_detailed_stats(console: Console, stats: "StatBreakdown", icons: bool):
    """
    Display detailed breakdowns by various categories using a column layout.
    """
    genre_table = _create_breakdown_table(
        title=f"{ICONS.get('GENRE', icons)}Top {TOP_N_STATS} Genres",
        data=stats.get("genre_breakdown", {}),
        key_header="Genre",
        value_header="Count",
        limit=TOP_N_STATS,
    )

    format_table = _create_breakdown_table(
        title=f"{ICONS.get('FORMAT', icons)}Format Breakdown",
        data=stats.get("format_breakdown", {}),
        key_header="Format",
        value_header="Count",
        show_percentage=True,
    )

    year_table = _create_breakdown_table(
        title=f"{ICONS.get('CALENDAR', icons)}Top {TOP_N_STATS} Release Years",
        data=stats.get("year_breakdown", {}),
        key_header="Year",
        value_header="Count",
        sort_by_key=True,
        limit=TOP_N_STATS,
    )

    rating_table = _create_breakdown_table(
        title=f"{ICONS.get('STAR', icons)}Score Distribution",
        data=stats.get("rating_breakdown", {}),
        key_header="Score Range",
        value_header="Count",
        sort_by_key=True,
        reverse_sort=False,
    )

    # Render tables in columns for a compact view
    console.print(Columns([genre_table, format_table], equal=True, expand=True))
    console.print()
    console.print(Columns([year_table, rating_table], equal=True, expand=True))


def _create_breakdown_table(
    title: str,
    data: Dict,
    key_header: str,
    value_header: str,
    show_percentage: bool = False,
    sort_by_key: bool = False,
    reverse_sort: bool = True,
    limit: int = 0,
) -> Table:
    """
    Generic helper to create a rich Table for breakdown statistics.
    """
    table = Table(title=title)
    table.add_column(key_header, style="cyan")
    table.add_column(value_header, style="magenta", justify="right")
    if show_percentage:
        table.add_column("Percentage", style="green", justify="right")

    if not data:
        row = (
            ["No data available", "-", "-"]
            if show_percentage
            else ["No data available", "-"]
        )
        table.add_row(*row)
        return table

    total = sum(data.values())

    # Determine sorting method
    def sort_key(item):
        return item[0] if sort_by_key else item[1]

    sorted_data = sorted(data.items(), key=sort_key, reverse=reverse_sort)

    # Apply limit if specified
    if limit > 0:
        sorted_data = sorted_data[:limit]

    for key, count in sorted_data:
        row = [str(key).title(), str(count)]
        if show_percentage:
            percentage = (count / total * 100) if total > 0 else 0
            row.append(f"{percentage:.1f}%")
        table.add_row(*row)

    return table


def _format_storage_size(size_bytes: float) -> str:
    """Formats bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024.0 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"


def _format_timedelta(delta: timedelta) -> str:
    """Formats a timedelta into a human-readable relative time string."""
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "Just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days > 1 else ''} ago"
