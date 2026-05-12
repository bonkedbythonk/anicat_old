from dataclasses import asdict
from typing import Callable, Dict, Union

from .....libs.media_api.params import MediaSearchParams, UserMediaListSearchParams
from .....libs.media_api.types import MediaItem, MediaStatus, UserMediaListStatus
from ...session import Context, session
from ...state import InternalDirective, MediaApiState, MenuName, State
from .....core.theme import ICONS


@session.menu
def results(ctx: Context, state: State) -> State | InternalDirective:
    feedback = ctx.feedback
    feedback.clear_console()

    search_result = state.media_api.search_result
    page_info = state.media_api.page_info

    search_result_dict = {
        _format_title(ctx, media_item): media_item
        for media_item in search_result.values()
    }
    choices: Dict[str, Callable[[], Union[int, State, InternalDirective]]] = {
        title: lambda media_id=item.id: media_id
        for title, item in search_result_dict.items()
    }
    if page_info:
        if page_info.has_next_page:
            choices.update(
                {
                    f"Next Page (Page {page_info.current_page + 1})": lambda: _handle_pagination(
                        ctx, state, 1
                    )
                }
            )
        if page_info.current_page > 1:
            choices.update(
                {
                    f"Previous Page (Page {page_info.current_page - 1})": lambda: _handle_pagination(
                        ctx, state, -1
                    )
                }
            )
    choices.update(
        {
            "Back": lambda: InternalDirective.BACK
            if page_info and page_info.current_page == 1
            else InternalDirective.MAIN,
            "Exit": lambda: InternalDirective.EXIT,
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

            prompt = "Select Anime"
            if state.media_api.search_params:
                from .....libs.media_api.types import MediaType
                if getattr(state.media_api.search_params, "type", None) == MediaType.MANGA:
                    prompt = "Select Manga"

            choice = ctx.selector.choose(
                prompt=prompt,
                choices=list(choices),
                preview=preview_command,
            )

    else:
        # No preview mode

        prompt = "Select Anime"
        if state.media_api.search_params:
            from .....libs.media_api.types import MediaType
            if getattr(state.media_api.search_params, "type", None) == MediaType.MANGA:
                prompt = "Select Manga"

        choice = ctx.selector.choose(
            prompt=prompt,
            choices=list(choices),
            preview=None,
        )

    if not choice:
        return InternalDirective.RELOAD

    next_step = choices[choice]()
    if isinstance(next_step, State) or isinstance(next_step, InternalDirective):
        return next_step
    else:
        return State(
            menu_name=MenuName.MEDIA_ACTIONS,
            media_api=MediaApiState(
                media_id=next_step,
                search_result=state.media_api.search_result,
                page_info=state.media_api.page_info,
            ),
        )


def _format_title(ctx: Context, media_item: MediaItem) -> str:
    config = ctx.config

    title = media_item.title.english or media_item.title.romaji
    progress = "0"

    if media_item.user_status:
        progress = str(media_item.user_status.progress or 0)

    episodes_total = str(media_item.episodes or "??")
    display_title = f"{title} ({progress} of {episodes_total})"

    # Add a visual indicator for new episodes if applicable
    if (
        media_item.status == MediaStatus.RELEASING
        and media_item.next_airing
        and media_item.user_status
        and media_item.user_status.status == UserMediaListStatus.WATCHING
    ):
        last_aired = media_item.next_airing.episode - 1
        unwatched = last_aired - (media_item.user_status.progress or 0)
        if unwatched > 0:
            icon = ICONS.get('NEW', config.general.icons) if config.general.icons else "!"
            display_title += f" {icon}{unwatched} new{icon}"

    return display_title


def _handle_pagination(
    ctx: Context, state: State, page_delta: int
) -> State | InternalDirective:
    feedback = ctx.feedback

    search_params = state.media_api.search_params

    if (
        not state.media_api.search_result
        or not state.media_api.page_info
        or not search_params
    ):
        feedback.error("No search results available for pagination")
        return InternalDirective.RELOAD

    current_page = state.media_api.page_info.current_page
    new_page = current_page + page_delta

    # Validate page bounds
    if new_page < 1:
        feedback.warning("Already at the first page")
        return InternalDirective.RELOAD

    if page_delta == -1:
        return InternalDirective.BACK
    if page_delta > 0 and not state.media_api.page_info.has_next_page:
        feedback.warning("No more pages available")
        return InternalDirective.RELOAD

    # Determine which type of search to perform based on stored parameters
    if isinstance(search_params, UserMediaListSearchParams):
        if not ctx.media_api.is_authenticated():
            feedback.error("You haven't logged in")
            return InternalDirective.RELOAD

        search_params_dict = asdict(search_params)
        search_params_dict.pop("page")

        loading_message = "Fetching media list"
        result = None
        new_search_params = UserMediaListSearchParams(
            **search_params_dict, page=new_page
        )
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media_list(new_search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=new_search_params,
                    page_info=result.page_info,
                ),
            )
    else:
        search_params_dict = asdict(search_params)
        search_params_dict.pop("page")

        loading_message = "Fetching media list"
        result = None
        new_search_params = MediaSearchParams(**search_params_dict, page=new_page)
        with feedback.progress(loading_message):
            result = ctx.media_api.search_media(new_search_params)

        if result:
            return State(
                menu_name=MenuName.RESULTS,
                media_api=MediaApiState(
                    search_result={
                        media_item.id: media_item for media_item in result.media
                    },
                    search_params=new_search_params,
                    page_info=result.page_info,
                ),
            )

    feedback.warning("Failed to load page")
    return InternalDirective.RELOAD
