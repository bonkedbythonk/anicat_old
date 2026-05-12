from typing import Callable, Dict, Literal, Union

from .....libs.player.params import PlayerParams
from ...session import Context, session
from ...state import InternalDirective, MenuName, State
from .....core.theme import ICONS

MenuAction = Callable[[], Union[State, InternalDirective]]


@session.menu
def play_downloads(ctx: Context, state: State) -> State | InternalDirective:
    """Menu to select and play locally downloaded episodes."""
    from ....service.registry.models import DownloadStatus

    feedback = ctx.feedback
    media_item = state.media_api.media_item
    current_episode_num = state.provider.episode

    record = ctx.media_registry.get_media_record(media_item.id)
    if not record or not record.media_episodes:
        feedback.warning("No downloaded episodes found for this anime.")
        return InternalDirective.BACK

    downloaded_episodes = {
        ep.episode_number: ep.file_path
        for ep in record.media_episodes
        if ep.download_status == DownloadStatus.COMPLETED
        and ep.file_path
        and ep.file_path.exists()
    }

    if not downloaded_episodes:
        feedback.warning("No complete downloaded episodes found.")
        return InternalDirective.BACK

    chosen_episode: str | None = current_episode_num
    start_time: str | None = None

    if not chosen_episode and ctx.config.stream.continue_from_watch_history:
        _chosen_episode, _start_time = ctx.watch_history.get_episode(media_item)
        if _chosen_episode in downloaded_episodes:
            chosen_episode = _chosen_episode
            start_time = _start_time

    if not chosen_episode or ctx.switch.show_episodes_menu:
        choices = [*list(sorted(downloaded_episodes.keys(), key=float)), "Back"]

        preview_command = None
        if ctx.config.general.preview != "none":
            from ....utils.preview import create_preview_context

            with create_preview_context() as preview_ctx:
                preview_command = preview_ctx.get_episode_preview(
                    list(downloaded_episodes.keys()), media_item, ctx.config
                )

                chosen_episode_str = ctx.selector.choose(
                    prompt="Select Episode", choices=choices, preview=preview_command
                )

                if not chosen_episode_str or chosen_episode_str == "Back":
                    return InternalDirective.BACK

                chosen_episode = chosen_episode_str
        else:
            chosen_episode_str = ctx.selector.choose(
                prompt="Select Episode", choices=choices, preview=None
            )

            if not chosen_episode_str or chosen_episode_str == "Back":
                return InternalDirective.BACK

            chosen_episode = chosen_episode_str

    if not chosen_episode or chosen_episode == "Back":
        return InternalDirective.BACK

    return State(
        menu_name=MenuName.DOWNLOADS_PLAYER_CONTROLS,
        media_api=state.media_api,
        provider=state.provider.model_copy(
            update={"episode_": chosen_episode, "start_time_": start_time}
        ),
    )


# TODO: figure out the best way to implement this logic for next episode ...
@session.menu
def downloads_player_controls(
    ctx: Context, state: State
) -> Union[State, InternalDirective]:
    from ....service.registry.models import DownloadStatus

    feedback = ctx.feedback
    feedback.clear_console()

    config = ctx.config
    selector = ctx.selector

    media_item = state.media_api.media_item
    current_episode_num = state.provider.episode
    current_start_time = state.provider.start_time

    if not media_item or not current_episode_num:
        feedback.error("Player state is incomplete. Returning.")
        return InternalDirective.BACK
    record = ctx.media_registry.get_media_record(media_item.id)
    if not record or not record.media_episodes:
        feedback.warning("No downloaded episodes found for this anime.")
        return InternalDirective.BACK

    downloaded_episodes = {
        ep.episode_number: ep.file_path
        for ep in record.media_episodes
        if ep.download_status == DownloadStatus.COMPLETED
        and ep.file_path
        and ep.file_path.exists()
    }
    available_episodes = list(sorted(downloaded_episodes.keys(), key=float))
    current_index = available_episodes.index(current_episode_num)

    if not ctx.switch.dont_play:
        file_path = downloaded_episodes[current_episode_num]

        # Use the player service to play the local file
        title = f"{media_item.title.english or media_item.title.romaji}; Episode {current_episode_num}"
        if media_item.streaming_episodes:
            streaming_episode = media_item.streaming_episodes.get(current_episode_num)
            title = streaming_episode.title if streaming_episode else title
        player_result = ctx.player.play(
            PlayerParams(
                url=str(file_path),
                title=title,
                query=media_item.title.english or media_item.title.romaji or "",
                episode=current_episode_num,
                start_time=current_start_time,
            ),
            media_item=media_item,
            local=True,
        )

        # Track watch history after playing
        ctx.watch_history.track(media_item, player_result)

    if config.stream.auto_next and current_index < len(available_episodes) - 1:
        feedback.info("Auto-playing next episode...")
        next_episode_num = available_episodes[current_index + 1]

        return State(
            menu_name=MenuName.DOWNLOADS_PLAYER_CONTROLS,
            media_api=state.media_api,
            provider=state.provider.model_copy(
                update={"episode_": next_episode_num, "start_time_": None}
            ),
        )

    # --- Menu Options ---
    icons = config.general.icons
    options: Dict[str, Callable[[], Union[State, InternalDirective]]] = {}

    if current_index < len(available_episodes) - 1:
        options[f"{ICONS.get('NEXT', icons)}Next Episode"] = _next_episode(ctx, state)
    if current_index:
        options[f"{ICONS.get('PREVIOUS', icons)}Previous Episode"] = _previous_episode(
            ctx, state
        )

    options.update(
        {
            f"{ICONS.get('REPLAY', icons)}Replay": _replay(ctx, state),
            f"{ICONS.get('EPISODES', icons)}Episode List": _episodes_list(ctx, state),
            f"{ICONS.get('TOGGLE', icons)}Toggle Auto Next Episode (Current: {ctx.config.stream.auto_next})": _toggle_config_state(
                ctx, state, "AUTO_EPISODE"
            ),
            f"{ICONS.get('TRAILER', icons)}Media Actions Menu": lambda: InternalDirective.BACKX2,
            f"{ICONS.get('HOME', icons)}Main Menu": lambda: InternalDirective.MAIN,
            f"{ICONS.get('EXIT', icons)}Exit": lambda: InternalDirective.EXIT,
        }
    )

    choice = selector.choose(prompt="What's next?", choices=list(options.keys()))

    if choice and choice in options:
        return options[choice]()
    else:
        return InternalDirective.RELOAD


def _next_episode(ctx: Context, state: State) -> MenuAction:
    def action():
        from ....service.registry.models import DownloadStatus

        feedback = ctx.feedback

        media_item = state.media_api.media_item
        current_episode_num = state.provider.episode

        if not media_item or not current_episode_num:
            feedback.error(
                "Player state is incomplete. not going to next episode. Returning."
            )
            ctx.switch.force_dont_play()
            return InternalDirective.RELOAD

        record = ctx.media_registry.get_media_record(media_item.id)
        if not record or not record.media_episodes:
            feedback.warning("No downloaded episodes found for this anime.")
            ctx.switch.force_dont_play()
            return InternalDirective.RELOAD

        downloaded_episodes = {
            ep.episode_number: ep.file_path
            for ep in record.media_episodes
            if ep.download_status == DownloadStatus.COMPLETED
            and ep.file_path
            and ep.file_path.exists()
        }
        available_episodes = list(sorted(downloaded_episodes.keys(), key=float))
        current_index = available_episodes.index(current_episode_num)

        if current_index < len(available_episodes) - 1:
            next_episode_num = available_episodes[current_index + 1]

            return State(
                menu_name=MenuName.DOWNLOADS_PLAYER_CONTROLS,
                media_api=state.media_api,
                provider=state.provider.model_copy(
                    update={"episode_": next_episode_num, "start_time_": None}
                ),
            )
        feedback.warning("This is the last available episode.")
        ctx.switch.force_dont_play()
        return InternalDirective.RELOAD

    return action


def _previous_episode(ctx: Context, state: State) -> MenuAction:
    def action():
        from ....service.registry.models import DownloadStatus

        feedback = ctx.feedback

        media_item = state.media_api.media_item
        current_episode_num = state.provider.episode

        if not media_item or not current_episode_num:
            feedback.error(
                "Player state is incomplete not going to previous episode. Returning."
            )
            ctx.switch.force_dont_play()
            return InternalDirective.RELOAD

        record = ctx.media_registry.get_media_record(media_item.id)
        if not record or not record.media_episodes:
            feedback.warning("No downloaded episodes found for this anime.")
            ctx.switch.force_dont_play()
            return InternalDirective.RELOAD

        downloaded_episodes = {
            ep.episode_number: ep.file_path
            for ep in record.media_episodes
            if ep.download_status == DownloadStatus.COMPLETED
            and ep.file_path
            and ep.file_path.exists()
        }
        available_episodes = list(sorted(downloaded_episodes.keys(), key=float))
        current_index = available_episodes.index(current_episode_num)

        if current_index:
            prev_episode_num = available_episodes[current_index - 1]

            return State(
                menu_name=MenuName.DOWNLOADS_PLAYER_CONTROLS,
                media_api=state.media_api,
                provider=state.provider.model_copy(
                    update={"episode_": prev_episode_num, "start_time_": None}
                ),
            )
        feedback.warning("This is the last available episode.")
        ctx.switch.force_dont_play()
        return InternalDirective.RELOAD

    return action


def _replay(ctx: Context, state: State) -> MenuAction:
    def action():
        return InternalDirective.RELOAD

    return action


def _toggle_config_state(
    ctx: Context,
    state: State,
    config_state: Literal[
        "AUTO_ANIME", "AUTO_EPISODE", "CONTINUE_FROM_HISTORY", "TRANSLATION_TYPE"
    ],
) -> MenuAction:
    def action():
        match config_state:
            case "AUTO_ANIME":
                ctx.config.general.auto_select_anime_result = (
                    not ctx.config.general.auto_select_anime_result
                )
            case "AUTO_EPISODE":
                ctx.config.stream.auto_next = not ctx.config.stream.auto_next
            case "CONTINUE_FROM_HISTORY":
                ctx.config.stream.continue_from_watch_history = (
                    not ctx.config.stream.continue_from_watch_history
                )
            case "TRANSLATION_TYPE":
                ctx.config.stream.translation_type = (
                    "sub" if ctx.config.stream.translation_type == "dub" else "dub"
                )
        return InternalDirective.RELOAD

    return action


def _episodes_list(ctx: Context, state: State) -> MenuAction:
    def action():
        ctx.switch.force_episodes_menu()
        return InternalDirective.BACK

    return action
