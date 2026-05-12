from typing import Callable, Literal, Union
from ...state import InternalDirective, State
from ...session import Context

MenuAction = Callable[[], Union[State, InternalDirective]]

def toggle_config_state(
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
