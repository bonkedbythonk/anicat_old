from typing import Callable, Dict, Union

from .....libs.media_api.types import MediaItem, PageInfo
from ...session import Context, session
from ...state import InternalDirective, MediaApiState, MenuName, State


@session.menu
def local_library(ctx: Context, state: State) -> State | InternalDirective:
    """Displays all media that have downloaded episodes, directly linking to playback."""
    from ....service.registry.models import DownloadStatus

    feedback = ctx.feedback
    feedback.clear_console()

    # Fetch all records with at least one completed download
    records = list(ctx.media_registry.get_all_media_records())

    downloaded_media: Dict[int, MediaItem] = {}

    for record in records:
        has_downloads = any(
            ep.download_status == DownloadStatus.COMPLETED
            and ep.file_path
            and ep.file_path.exists()
            for ep in record.media_episodes
        )
        if has_downloads:
            downloaded_media[record.media_item.id] = record.media_item

    if not downloaded_media:
        feedback.warning("No downloaded anime found in your local library.")
        return InternalDirective.MAIN

    # Sort them by recently watched or title
    # Here we'll just sort by title for simplicity
    sorted_items = sorted(
        downloaded_media.values(), key=lambda x: x.title.english or x.title.romaji or ""
    )

    search_result_dict = {
        _format_title(ctx, media_item): media_item for media_item in sorted_items
    }

    choices: Dict[str, Callable[[], Union[int, State, InternalDirective]]] = {
        title: lambda media_id=item.id: media_id
        for title, item in search_result_dict.items()
    }

    choices.update(
        {
            "Back": lambda: InternalDirective.MAIN,
        }
    )

    preview_command = None
    if ctx.config.general.preview != "none":
        from ....utils.preview import create_preview_context

        with create_preview_context() as preview_ctx:
            preview_command = preview_ctx.get_anime_preview(
                list(search_result_dict.values()),
                list(search_result_dict.keys()),
                ctx.config,
            )

            choice = ctx.selector.choose(
                prompt="Select Downloaded Anime to Play",
                choices=list(choices),
                preview=preview_command,
            )
    else:
        choice = ctx.selector.choose(
            prompt="Select Downloaded Anime to Play",
            choices=list(choices),
            preview=None,
        )

    if not choice:
        return InternalDirective.RELOAD

    next_step = choices[choice]()
    if isinstance(next_step, State) or isinstance(next_step, InternalDirective):
        return next_step
    else:
        # Directly go to Play Downloads menu
        return State(
            menu_name=MenuName.PLAY_DOWNLOADS,
            media_api=MediaApiState(
                media_id=next_step,
                search_result={item.id: item for item in sorted_items},
                page_info=PageInfo(
                    total=len(sorted_items),
                    current_page=1,
                    has_next_page=False,
                    per_page=len(sorted_items),
                ),
            ),
        )


def _format_title(ctx: Context, media_item: MediaItem) -> str:
    title = media_item.title.english or media_item.title.romaji
    progress = "0"

    if media_item.user_status:
        progress = str(media_item.user_status.progress or 0)

    episodes_total = str(media_item.episodes or "??")
    display_title = f"{title} ({progress} of {episodes_total})"

    return display_title
