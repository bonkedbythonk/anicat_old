from ...session import Context, session
from ...state import InternalDirective, MenuName, ProviderState, State
from anicat_media.core.theme import ICONS


@session.menu
def episodes(ctx: Context, state: State) -> State | InternalDirective:
    """
    Displays available episodes for a selected provider anime and handles
    the logic for continuing from watch history or manual selection.
    """
    config = ctx.config
    feedback = ctx.feedback
    feedback.clear_console()

    provider_anime = state.provider.anime
    media_item = state.media_api.media_item

    if not provider_anime or not media_item:
        feedback.error("Error: Anime details are missing.")
        return InternalDirective.BACK

    available_episodes = getattr(
        provider_anime.episodes, config.stream.translation_type, []
    )
    if not available_episodes:
        feedback.warning(
            f"No '{config.stream.translation_type}' episodes found for this anime."
        )
        return InternalDirective.BACKX2

    chosen_episode: str | None = None
    start_time: str | None = None

    if config.stream.continue_from_watch_history:
        chosen_episode, start_time = ctx.watch_history.get_episode(media_item)

    if not chosen_episode or ctx.switch.show_episodes_menu:
        back_text = f"{ICONS.get('BACK', ctx.config.general.icons)}Back"
        choices = [*available_episodes, back_text]

        preview_command = None
        if ctx.config.general.preview != "none":
            from ....utils.preview import create_preview_context

            with create_preview_context() as preview_ctx:
                preview_command = preview_ctx.get_episode_preview(
                    available_episodes, media_item, ctx.config
                )

                chosen_episode_str = ctx.selector.choose(
                    prompt="Select Episode", choices=choices, preview=preview_command
                )

                if not chosen_episode_str or "Back" in chosen_episode_str:
                    # TODO: should improve the back logic for menus that can be pass through
                    return InternalDirective.BACKX2

                chosen_episode = chosen_episode_str
                # Workers are automatically cleaned up when exiting the context
        else:
            # No preview mode
            chosen_episode_str = ctx.selector.choose(
                prompt="Select Episode", choices=choices, preview=None
            )

            if not chosen_episode_str or "Back" in chosen_episode_str:
                # TODO: should improve the back logic for menus that can be pass through
                return InternalDirective.BACKX2

            chosen_episode = chosen_episode_str

    return State(
        menu_name=MenuName.SERVERS,
        media_api=state.media_api,
        provider=state.provider.model_copy(
            update={"episode_": chosen_episode, "start_time_": start_time}
        ),
    )
