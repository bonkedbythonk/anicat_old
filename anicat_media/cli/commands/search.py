from typing import TYPE_CHECKING

import click

from anicat_media.core.config import AppConfig
from anicat_media.core.exceptions import AnicatError
from ..utils.completion import anime_titles_shell_complete
from . import examples

if TYPE_CHECKING:
    from typing import TypedDict

    from typing_extensions import Unpack

    from ...libs.provider.anime.types import Anime
    from ...libs.media_api.types import MediaItem
    from ..interactive.session import Context

    class Options(TypedDict):
        anime_title: list[str]
        episode_range: str | None


@click.command(
    help="This subcommand directly interacts with the provider to enable basic streaming. Useful for binging anime.",
    short_help="Binge anime",
    epilog=examples.search,
)
@click.option(
    "--anime-title",
    "-t",
    shell_complete=anime_titles_shell_complete,
    multiple=True,
    help="Specify which anime to stream or binge",
)
@click.option(
    "--episode-range",
    "-r",
    help="A range of episodes to binge (start-end)",
)
@click.pass_obj
def search(config: AppConfig, **options: "Unpack[Options]"):
    from anicat_media.core.utils.normalizer import normalize_title
    from ...libs.provider.anime.params import AnimeParams, SearchParams
    from ..interactive.session import Context

    ctx = Context(config)

    if not options["anime_title"]:
        raw = ""
        while not raw.strip():
            raw = click.prompt(
                "What are you in the mood for? (comma-separated)",
                default="",
                show_default=False,
            )
            if not raw.strip():
                click.echo(
                    click.style("Input cannot be empty. Please try again.", fg="red")
                )

        options["anime_title"] = [a.strip() for a in raw.split(",") if a.strip()]

    anime_titles = options["anime_title"]
    ctx.feedback.info(f"[green bold]Streaming:[/] {anime_titles}")
    for anime_title in anime_titles:
        # ---- search for anime ----
        ctx.feedback.info(f"[green bold]Searching for:[/] {anime_title}")
        with ctx.feedback.progress(
            f"Fetching anime search results for {anime_title}"
        ):
            search_results = ctx.provider.search(
                SearchParams(
                    query=normalize_title(
                        anime_title, config.general.provider.value, True
                    ).lower(),
                    translation_type=config.stream.translation_type,
                )
            )
        if not search_results:
            raise AnicatError("No results were found matching your query")

        _search_results = {
            search_result.title: search_result
            for search_result in search_results.results
        }

        selected_anime_title = ctx.selector.choose(
            "Select Anime", list(_search_results.keys())
        )
        if not selected_anime_title:
            raise AnicatError("No title selected")
        anime_result = _search_results[selected_anime_title]

        # ---- fetch selected anime ----
        with ctx.feedback.progress(f"Fetching {anime_result.title}"):
            anime = ctx.provider.get(
                AnimeParams(id=anime_result.id, query=anime_title)
            )

        if not anime:
            raise AnicatError(f"Failed to fetch anime {anime_result.title}")

        available_episodes: list[str] = sorted(
            getattr(anime.episodes, config.stream.translation_type), key=float
        )

        if options["episode_range"]:
            from ..utils.parser import parse_episode_range

            try:
                episodes_range = parse_episode_range(
                    options["episode_range"], available_episodes
                )

                for episode in episodes_range:
                    stream_anime(ctx, anime, episode, anime_title)
            except (ValueError, IndexError) as e:
                raise AnicatError(f"Invalid episode range: {e}") from e
        else:
            episode = ctx.selector.choose(
                "Select Episode",
                getattr(anime.episodes, config.stream.translation_type),
            )
            if not episode:
                raise AnicatError("No episode selected")
            stream_anime(ctx, anime, episode, anime_title)


def stream_anime(
    ctx: "Context",
    anime: "Anime",
    episode: str,
    anime_title: str,
):
    from ...libs.player.params import PlayerParams
    from ...libs.provider.anime.params import EpisodeStreamsParams

    with ctx.feedback.progress("Fetching episode streams"):
        streams = ctx.provider.episode_streams(
            EpisodeStreamsParams(
                anime_id=anime.id,
                query=anime_title,
                episode=episode,
                translation_type=ctx.config.stream.translation_type,
            )
        )
        if not streams:
            raise AnicatError(
                f"Failed to get streams for anime: {anime.title}, episode: {episode}"
            )

    if ctx.config.stream.server.value == "TOP":
        with ctx.feedback.progress("Fetching top server"):
            server = next(streams, None)
            if not server:
                raise AnicatError(
                    f"Failed to get server for anime: {anime.title}, episode: {episode}"
                )
    else:
        with ctx.feedback.progress("Fetching servers"):
            servers = {server.name: server for server in streams}
        servers_names = list(servers.keys())
        if ctx.config.stream.server.value in servers_names:
            server = servers[ctx.config.stream.server.value]
        else:
            server_name = ctx.selector.choose("Select Server", servers_names)
            if not server_name:
                raise AnicatError("Server not selected")
            server = servers[server_name]
    quality = [
        ep_stream.link
        for ep_stream in server.links
        if ep_stream.quality == ctx.config.stream.quality
    ]
    if quality:
        stream_link = quality[0]
    else:
        ctx.feedback.warning("Preferred quality not found, selecting quality...")
        chosen_quality = ctx.selector.choose(
            "Select Quality", [link.quality for link in server.links]
        )
        if not chosen_quality:
            raise AnicatError("Quality not selected")
        stream_link = next(
            (link.link for link in server.links if link.quality == chosen_quality),
            None,
        )
    if not stream_link:
        raise AnicatError(
            f"Failed to get stream link for anime: {anime.title}, episode: {episode}"
        )

    # Look up the media item via AniList for watch history tracking
    media_item = _resolve_media_item(ctx, anime_title, anime)

    ctx.feedback.info(
        f"[green bold]Now Streaming:[/] {anime.title} Episode: {episode}"
    )

    player_result = ctx.player.play(
        PlayerParams(
            url=stream_link,
            title=f"{anime.title}; Episode {episode}",
            query=anime_title,
            episode=episode,
            subtitles=[sub.url for sub in server.subtitles],
            headers=server.headers,
        ),
        anime,
        media_item=media_item,
    )

    # Track watch history via shared service layer
    if player_result and media_item:
        try:
            ctx.watch_history.track(media_item, player_result)
            ctx.data_version += 1
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to save watch history: {e}"
            )


def _resolve_media_item(
    ctx: "Context", anime_title: str, anime: "Anime"
) -> "MediaItem | None":
    """Resolve the AniList media item for watch history tracking."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        if not ctx.media_api.is_authenticated():
            return None

        from ...libs.media_api.params import MediaSearchParams

        search_result = ctx.media_api.search_media(
            MediaSearchParams(query=anime_title)
        )
        if search_result and search_result.media:
            # Pick the best match: prefer exact title match, then first result
            best = search_result.media[0]
            for m in search_result.media:
                if (
                    m.title.english
                    and anime.title
                    and m.title.english.lower() == anime.title.lower()
                ):
                    best = m
                    break
                if (
                    m.title.romaji
                    and anime.title
                    and m.title.romaji.lower() == anime.title.lower()
                ):
                    best = m
                    break
            logger.info(
                f"Resolved AniList media item #{best.id} for watch history"
            )
            return best
    except Exception as e:
        logger.warning(f"Could not resolve media item for watch history: {e}")
    return None
