"""
Registry search command - search through the local media registry
"""

import json
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

from .....core.config import AppConfig
from .....libs.media_api.params import MediaSearchParams
from .....libs.media_api.types import (
    MediaFormat,
    MediaGenre,
    MediaSort,
    UserMediaListStatus,
)
from ....service.feedback import FeedbackService
from ....service.registry.service import MediaRegistryService
from .....core.theme import ICONS

if TYPE_CHECKING:
    from .....libs.media_api.types import MediaSearchResult


@click.command(help="Search through the local media registry")
@click.argument("query", required=False)
@click.option(
    "--status",
    type=click.Choice(
        [s.value for s in UserMediaListStatus],
        case_sensitive=False,
    ),
    help="Filter by watch status",
)
@click.option(
    "--genre", multiple=True, help="Filter by genre (can be used multiple times)"
)
@click.option(
    "--format",
    type=click.Choice(
        [
            f.value
            for f in MediaFormat
            if f not in [MediaFormat.MANGA, MediaFormat.NOVEL, MediaFormat.ONE_SHOT]
        ],
        case_sensitive=False,
    ),
    help="Filter by format",
)
@click.option("--year", type=int, help="Filter by release year")
@click.option("--min-score", type=float, help="Minimum average score (0.0 - 10.0)")
@click.option("--max-score", type=float, help="Maximum average score (0.0 - 10.0)")
@click.option(
    "--sort",
    type=click.Choice(
        ["title", "score", "popularity", "year", "episodes", "updated"],
        case_sensitive=False,
    ),
    default="title",
    help="Sort results by field",
)
@click.option("--limit", type=int, default=20, help="Maximum number of results to show")
@click.option(
    "--json", "output_json", is_flag=True, help="Output results in JSON format"
)
@click.option(
    "--api",
    default="anilist",
    type=click.Choice(["anilist"], case_sensitive=False),
    help="Media API registry to search",
)
@click.pass_obj
def search(
    config: AppConfig,
    query: str | None,
    status: str | None,
    genre: tuple[str, ...],
    format: str | None,
    year: int | None,
    min_score: float | None,
    max_score: float | None,
    sort: str,
    limit: int,
    output_json: bool,
    api: str,
):
    """
    Search through your local media registry.

    You can search by title and filter by various criteria like status,
    genre, format, year, and score range.
    """
    feedback = FeedbackService(config)
    console = Console()

    try:
        registry_service = MediaRegistryService(api, config.media_registry)

        search_params = _build_search_params(
            query, status, genre, format, year, min_score, max_score, sort, limit
        )

        with feedback.progress("Searching local registry..."):
            result = registry_service.search_for_media(search_params)

        if not result or not result.media:
            feedback.info("No Results", "No media found matching your criteria")
            return

        if output_json:
            print(json.dumps(result.model_dump(mode="json"), indent=2))
            return

        _display_search_results(console, result, config.general.icons)

    except Exception as e:
        feedback.error("Search Error", f"Failed to search registry: {e}")
        raise click.Abort()


def _build_search_params(
    query: str | None,
    status: str | None,
    genre: tuple[str, ...],
    format_str: str | None,
    year: int | None,
    min_score: float | None,
    max_score: float | None,
    sort: str,
    limit: int,
) -> MediaSearchParams:
    """Build MediaSearchParams from command options for local filtering."""
    sort_map = {
        "title": MediaSort.TITLE_ROMAJI,
        "score": MediaSort.SCORE_DESC,
        "popularity": MediaSort.POPULARITY_DESC,
        "year": MediaSort.START_DATE_DESC,
        "episodes": MediaSort.EPISODES_DESC,
        "updated": MediaSort.UPDATED_AT_DESC,
    }

    # Safely convert strings to enums
    format_enum = next(
        (f for f in MediaFormat if f.value.lower() == (format_str or "").lower()), None
    )
    genre_enums = [
        g for g_str in genre for g in MediaGenre if g.value.lower() == g_str.lower()
    ]

    # Note: Local search handles status separately as it's part of the index, not MediaItem

    return MediaSearchParams(
        query=query,
        per_page=limit,
        sort=[sort_map.get(sort.lower(), MediaSort.TITLE_ROMAJI)],
        averageScore_greater=int(min_score * 10) if min_score is not None else None,
        averageScore_lesser=int(max_score * 10) if max_score is not None else None,
        genre_in=genre_enums or None,
        format_in=[format_enum] if format_enum else None,
        seasonYear=year,
    )


def _display_search_results(console: Console, result: "MediaSearchResult", icons: bool):
    """Display search results in a formatted table."""
    table = Table(
        title=f"{ICONS.get('SEARCH', icons)}Search Results ({len(result.media)} found)"
    )
    table.add_column("Title", style="cyan", min_width=30, overflow="ellipsis")
    table.add_column("Year", style="dim", justify="center")
    table.add_column("Format", style="magenta", justify="center")
    table.add_column("Episodes", style="green", justify="center")
    table.add_column("Score", style="yellow", justify="center")
    table.add_column("Status", style="blue", justify="center")
    table.add_column("Progress", style="white", justify="center")

    for media in result.media:
        title = media.title.english or media.title.romaji or "Unknown"
        year = str(media.start_date.year) if media.start_date else "N/A"
        episodes_total = str(media.episodes) if media.episodes else "?"
        score = (
            f"{media.average_score / 10:.1f}"
            if media.average_score is not None
            else "N/A"
        )

        status = "Not Listed"
        progress = "0"
        if media.user_status:
            status = (
                media.user_status.status.value.title()
                if media.user_status.status
                else "Unknown"
            )
            progress = f"{media.user_status.progress or 0}/{episodes_total}"

        table.add_row(
            title,
            year,
            media.format.value if media.format else "N/A",
            episodes_total,
            score,
            status,
            progress,
        )

    console.print(table)

    if result.page_info and result.page_info.total > len(result.media):
        console.print(
            f"\n[dim]Showing {len(result.media)} of {result.page_info.total} total results[/dim]"
        )
