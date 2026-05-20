"""General application behavior and integration settings."""

from typing import List, Literal

from pydantic import Field

from ...libs.provider.anime.types import ProviderName
from ...libs.provider.manga.types import MangaProviderName
from .base import BaseConfig
from . import defaults
from . import descriptions as desc


class GeneralConfig(BaseConfig):
    """Configuration for general application behavior and integrations."""

    desktop_notification_duration: int = Field(
        default=defaults.GENERAL_DESKTOP_NOTIFICATION_DURATION,
        description=desc.GENERAL_DESKTOP_NOTIFICATION_DURATION,
    )
    preferred_tracker: Literal["local", "remote", "anilist"] = Field(
        default=defaults.GENERAL_PREFERRED_TRACKER,
        description=desc.GENERAL_PREFERRED_TRACKER,
    )
    pygment_style: Literal[
        "abap", "algol", "algol_nu", "arduino", "autumn", "bw", "borland",
        "coffee", "colorful", "default", "dracula", "emacs", "friendly_grayscale",
        "friendly", "fruity", "github-dark", "gruvbox-dark", "gruvbox-light",
        "igor", "inkpot", "lightbulb", "lilypond", "lovelace", "manni",
        "material", "monokai", "murphy", "native", "nord-darker", "nord",
        "one-dark", "paraiso-dark", "paraiso-light", "pastie", "perldoc",
        "rainbow_dash", "rrt", "sas", "solarized-dark", "solarized-light",
        "staroffice", "stata-dark", "stata-light", "tango", "trac", "vim",
        "vs", "xcode", "zenburn",
    ] = Field(
        default=defaults.GENERAL_PYGMENT_STYLE, description=desc.GENERAL_PYGMENT_STYLE  # type: ignore
    )
    preferred_spinner: Literal[
        "dots", "dots2", "dots3", "dots4", "dots5", "dots6", "dots7", "dots8",
        "dots9", "dots10", "dots11", "dots12", "dots8Bit", "line", "line2",
        "pipe", "simpleDots", "simpleDotsScrolling", "star", "star2", "flip",
        "hamburger", "growVertical", "growHorizontal", "balloon", "balloon2",
        "noise", "bounce", "boxBounce", "boxBounce2", "triangle", "arc",
        "circle", "squareCorners", "circleQuarters", "circleHalves", "squish",
        "toggle", "toggle2", "toggle3", "toggle4", "toggle5", "toggle6",
        "toggle7", "toggle8", "toggle9", "toggle10", "toggle11", "toggle12",
        "toggle13", "arrow", "arrow2", "arrow3", "bouncingBar", "bouncingBall",
        "smiley", "monkey", "hearts", "clock", "earth", "material", "moon",
        "runner", "pong", "shark", "dqpb", "weather", "christmas", "grenade",
        "point", "layer", "betaWave", "aesthetic",
    ] = Field(
        default=defaults.GENERAL_PREFERRED_SPINNER,  # type: ignore
        description=desc.GENERAL_PREFERRED_SPINNER,
    )
    media_api: Literal["anilist", "jikan"] = Field(
        default=defaults.GENERAL_API_CLIENT,
        description=desc.GENERAL_API_CLIENT,
    )
    welcome_screen: bool = Field(
        default=defaults.GENERAL_WELCOME_SCREEN, description=desc.GENERAL_WELCOME_SCREEN
    )
    provider: ProviderName = Field(
        default=ProviderName.ANIMEPAHE,
        description=desc.GENERAL_PROVIDER,
    )
    manga_provider: MangaProviderName = Field(
        default=MangaProviderName.MANGAKATANA,
        description="The provider to use for manga content.",
    )
    selector: Literal["default", "fzf", "rofi"] = Field(
        default_factory=defaults.GENERAL_SELECTOR,
        description=desc.GENERAL_SELECTOR,
    )
    auto_select_anime_result: bool = Field(
        default=defaults.GENERAL_AUTO_SELECT_ANIME_RESULT,
        description=desc.GENERAL_AUTO_SELECT_ANIME_RESULT,
    )
    icons: bool = Field(default=defaults.GENERAL_ICONS, description=desc.GENERAL_ICONS)
    preview: Literal["full", "text", "image", "none"] = Field(
        default_factory=defaults.GENERAL_PREVIEW,
        description=desc.GENERAL_PREVIEW,
    )
    preview_scale_up: bool = Field(
        default=defaults.GENERAL_SCALE_PREVIEW,
        description=desc.GENERAL_SCALE_PREVIEW,
    )
    image_renderer: Literal[
        "icat", "chafa", "imgcat", "system-sixels", "system-kitty", "system-default"
    ] = Field(
        default_factory=defaults.GENERAL_IMAGE_RENDERER,  # type: ignore
        description=desc.GENERAL_IMAGE_RENDERER,
    )
    manga_viewer: Literal["feh", "icat"] = Field(
        default=defaults.GENERAL_MANGA_VIEWER,
        description=desc.GENERAL_MANGA_VIEWER,
    )
    cache_requests: bool = Field(
        default=defaults.GENERAL_CACHE_REQUESTS,
        description=desc.GENERAL_CACHE_REQUESTS,
    )
    max_cache_lifetime: str = Field(
        default=defaults.GENERAL_MAX_CACHE_LIFETIME,
        description=desc.GENERAL_MAX_CACHE_LIFETIME,
    )
    normalize_titles: bool = Field(
        default=defaults.GENERAL_NORMALIZE_TITLES,
        description=desc.GENERAL_NORMALIZE_TITLES,
    )
    discord: bool = Field(
        default=defaults.GENERAL_DISCORD,
        description=desc.GENERAL_DISCORD,
    )
    recent: int = Field(
        default=defaults.GENERAL_RECENT, ge=0, description=desc.GENERAL_RECENT,
    )
    hidden_categories: List[str] = Field(
        default_factory=list, description=desc.GENERAL_HIDDEN_CATEGORIES,
    )
    check_for_updates: bool = Field(
        default=defaults.GENERAL_CHECK_FOR_UPDATES,
        description=desc.GENERAL_CHECK_FOR_UPDATES,
    )
    update_branch: Literal["stable", "nightly"] = Field(
        default=defaults.GENERAL_UPDATE_BRANCH,
        description=desc.GENERAL_UPDATE_BRANCH,
    )
    time_format: Literal["12h", "24h"] = Field(
        default=defaults.GENERAL_TIME_FORMAT,
        description=desc.GENERAL_TIME_FORMAT,
    )
