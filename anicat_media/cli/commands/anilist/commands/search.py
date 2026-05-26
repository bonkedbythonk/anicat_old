from typing import TYPE_CHECKING

import click

from .....core.config import AppConfig
from .....core.exceptions import AnicatError
from .....libs.media_api.types import (
    MediaFormat,
    MediaGenre,
    MediaSeason,
    MediaSort,
    MediaStatus,
    MediaTag,
    MediaType,
    MediaYear,
)
from ....utils.completion import anime_titles_shell_complete
from .. import examples

if TYPE_CHECKING:
    from typing import TypedDict

    from typing_extensions import Unpack

    class SearchOptions(TypedDict, total=False):
        title: str | None
        dump_json: bool
        page: int
        per_page: int | None
        season: str | None
        status: tuple[str, ...]
        status_not: tuple[str, ...]
        sort: str | None
        genres: tuple[str, ...]
        genres_not: tuple[str, ...]
        tags: tuple[str, ...]
        tags_not: tuple[str, ...]
        media_format: tuple[str, ...]
        media_type: str | None
        year: str | None
        popularity_greater: int | None
        popularity_lesser: int | None
        score_greater: int | None
        score_lesser: int | None
        start_date_greater: int | None
        start_date_lesser: int | None
        end_date_greater: int | None
        end_date_lesser: int | None
        on_list: bool | None


@click.command(
    help="Search for anime using anilists api and get top ~50 results",
    short_help="Search for anime",
    epilog=examples.search,
)
@click.option("--title", "-t", shell_complete=anime_titles_shell_complete)
@click.option(
    "--dump-json",
    "-d",
    is_flag=True,
    help="Only print out the results dont open anilist menu",
)
@click.option(
    "--page",
    "-p",
    type=click.IntRange(min=1),
    default=1,
    help="Page number for pagination",
)
@click.option(
    "--per-page",
    type=click.IntRange(min=1, max=50),
    help="Number of results per page (max 50)",
)
@click.option(
    "--season",
    help="The season the media was released",
    type=click.Choice([season.value for season in MediaSeason]),
)
@click.option(
    "--status",
    "-S",
    help="The media status of the anime",
    multiple=True,
    type=click.Choice([status.value for status in MediaStatus]),
)
@click.option(
    "--status-not",
    help="Exclude media with these statuses",
    multiple=True,
    type=click.Choice([status.value for status in MediaStatus]),
)
@click.option(
    "--sort",
    "-s",
    help="What to sort the search results on",
    type=click.Choice([sort.value for sort in MediaSort]),
)
@click.option(
    "--genres",
    "-g",
    multiple=True,
    help="the genres to filter by",
    type=click.Choice([genre.value for genre in MediaGenre]),
)
@click.option(
    "--genres-not",
    multiple=True,
    help="Exclude these genres",
    type=click.Choice([genre.value for genre in MediaGenre]),
)
@click.option(
    "--tags",
    "-T",
    multiple=True,
    help="the tags to filter by",
    type=click.Choice([tag.value for tag in MediaTag]),
)
@click.option(
    "--tags-not",
    multiple=True,
    help="Exclude these tags",
    type=click.Choice([tag.value for tag in MediaTag]),
)
@click.option(
    "--media-format",
    "-f",
    multiple=True,
    help="Media format",
    type=click.Choice([format.value for format in MediaFormat]),
)
@click.option(
    "--media-type",
    help="Media type (ANIME or MANGA)",
    type=click.Choice([media_type.value for media_type in MediaType]),
)
@click.option(
    "--year",
    "-y",
    type=click.Choice([year.value for year in MediaYear]),
    help="the year the media was released",
)
@click.option(
    "--popularity-greater",
    type=click.IntRange(min=0),
    help="Minimum popularity score",
)
@click.option(
    "--popularity-lesser",
    type=click.IntRange(min=0),
    help="Maximum popularity score",
)
@click.option(
    "--score-greater",
    type=click.IntRange(min=0, max=100),
    help="Minimum average score (0-100)",
)
@click.option(
    "--score-lesser",
    type=click.IntRange(min=0, max=100),
    help="Maximum average score (0-100)",
)
@click.option(
    "--start-date-greater",
    type=click.IntRange(min=10000101, max=99991231),
    help="Minimum start date (YYYYMMDD format, e.g., 20240101)",
)
@click.option(
    "--start-date-lesser",
    type=click.IntRange(min=10000101, max=99991231),
    help="Maximum start date (YYYYMMDD format, e.g., 20241231)",
)
@click.option(
    "--end-date-greater",
    type=click.IntRange(min=10000101, max=99991231),
    help="Minimum end date (YYYYMMDD format, e.g., 20240101)",
)
@click.option(
    "--end-date-lesser",
    type=click.IntRange(min=10000101, max=99991231),
    help="Maximum end date (YYYYMMDD format, e.g., 20241231)",
)
@click.option(
    "--on-list/--not-on-list",
    "-L/-no-L",
    help="Whether the anime should be in your list or not",
    type=bool,
)
@click.pass_obj
def search(config: AppConfig, **options: "Unpack[SearchOptions]"):
    import json

    from rich.progress import Progress

    from .....libs.media_api.api import create_api_client
    from .....libs.media_api.params import MediaSearchParams
    from ....service.feedback import FeedbackService

    feedback = FeedbackService(config)

    try:
        # Create API client
        api_client = create_api_client(config.general.media_api, config)

        # Extract options
        title = options.get("title")
        dump_json = options.get("dump_json", False)
        page = options.get("page", 1)
        per_page = options.get("per_page") or config.anilist.per_page or 50
        season = options.get("season")
        status = options.get("status", ())
        status_not = options.get("status_not", ())
        sort = options.get("sort")
        genres = options.get("genres", ())
        genres_not = options.get("genres_not", ())
        tags = options.get("tags", ())
        tags_not = options.get("tags_not", ())
        media_format = options.get("media_format", ())
        media_type = options.get("media_type")
        year = options.get("year")
        popularity_greater = options.get("popularity_greater")
        popularity_lesser = options.get("popularity_lesser")
        score_greater = options.get("score_greater")
        score_lesser = options.get("score_lesser")
        start_date_greater = options.get("start_date_greater")
        start_date_lesser = options.get("start_date_lesser")
        end_date_greater = options.get("end_date_greater")
        end_date_lesser = options.get("end_date_lesser")
        on_list = options.get("on_list")

        # Validate logical relationships
        if (
            score_greater is not None
            and score_lesser is not None
            and score_greater > score_lesser
        ):
            raise AnicatError("Minimum score cannot be higher than maximum score")

        if (
            popularity_greater is not None
            and popularity_lesser is not None
            and popularity_greater > popularity_lesser
        ):
            raise AnicatError(
                "Minimum popularity cannot be higher than maximum popularity"
            )

        if (
            start_date_greater is not None
            and start_date_lesser is not None
            and start_date_greater > start_date_lesser
        ):
            raise AnicatError(
                "Start date greater cannot be later than start date lesser"
            )

        if (
            end_date_greater is not None
            and end_date_lesser is not None
            and end_date_greater > end_date_lesser
        ):
            raise AnicatError("End date greater cannot be later than end date lesser")

        # Build search parameters
        search_params = MediaSearchParams(
            query=title,
            page=page,
            per_page=per_page,
            sort=MediaSort(sort) if sort else None,
            status_in=[MediaStatus(s) for s in status] if status else None,
            status_not_in=[MediaStatus(s) for s in status_not] if status_not else None,
            genre_in=[MediaGenre(g) for g in genres] if genres else None,
            genre_not_in=[MediaGenre(g) for g in genres_not] if genres_not else None,
            tag_in=[MediaTag(t) for t in tags] if tags else None,
            tag_not_in=[MediaTag(t) for t in tags_not] if tags_not else None,
            format_in=[MediaFormat(f) for f in media_format] if media_format else None,
            type=MediaType(media_type) if media_type else None,
            season=MediaSeason(season) if season else None,
            seasonYear=int(year) if year else None,
            popularity_greater=popularity_greater,
            popularity_lesser=popularity_lesser,
            averageScore_greater=score_greater,
            averageScore_lesser=score_lesser,
            startDate_greater=start_date_greater,
            startDate_lesser=start_date_lesser,
            endDate_greater=end_date_greater,
            endDate_lesser=end_date_lesser,
            on_list=on_list,
        )

        # Search for anime
        with Progress() as progress:
            progress.add_task("Searching anime...", total=None)
            search_result = api_client.search_media(search_params)

        if not search_result or not search_result.media:
            raise AnicatError("No anime found matching your search criteria")

        if dump_json:
            # Use Pydantic's built-in serialization
            print(json.dumps(search_result.model_dump(mode="json")))
        else:
            # Launch interactive session for browsing results
            from ....interactive.session import session
            from ....interactive.state import MediaApiState, MenuName, State

            feedback.info(
                f"Found {len(search_result.media)} anime matching your search. Launching interactive mode..."
            )

            # Create initial state with search results
            initial_state = State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in search_result.media
                    },
                    search_params=search_params,
                    page_info=search_result.page_info,
                ),
            )

            session.load_menus_from_folder("media")
            session.run(config, history=[initial_state])

    except AnicatError as e:
        feedback.error("Search failed", str(e))
        raise click.Abort()
    except Exception as e:
        feedback.error("Unexpected error occurred", str(e))
        raise click.Abort()
