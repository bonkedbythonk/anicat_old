from typing import TYPE_CHECKING

import click

from anicat_media.core.config import AppConfig
from anicat_media.core.exceptions import AnicatError
from ..utils.completion import anime_titles_shell_complete
from . import examples

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TypedDict

    from anicat_media.cli.service.feedback.service import FeedbackService
    from typing_extensions import Unpack

    from ...libs.provider.anime.base import BaseAnimeProvider
    from ...libs.provider.anime.types import Anime
    from ...libs.selectors.base import BaseSelector

    class Options(TypedDict):
        anime_title: tuple
        episode_range: str
        file: Path | None
        force_unknown_ext: bool
        silent: bool
        verbose: bool
        merge: bool
        clean: bool
        wait_time: int
        prompt: bool
        force_ffmpeg: bool
        hls_use_mpegts: bool
        hls_use_h264: bool


@click.command(
    help="Download anime using the anime provider for a specified range",
    short_help="Download anime",
    epilog=examples.download,
)
@click.option(
    "--anime_title",
    "-t",
    required=True,
    shell_complete=anime_titles_shell_complete,
    multiple=True,
    help="Specify which anime to download",
)
@click.option(
    "--episode-range",
    "-r",
    help="A range of episodes to download (start-end)",
)
@click.option(
    "--file",
    "-f",
    type=click.File(),
    help="A file to read from all anime to download",
)
@click.option(
    "--force-unknown-ext",
    "-F",
    help="This option forces yt-dlp to download extensions its not aware of",
    is_flag=True,
)
@click.option(
    "--silent/--no-silent",
    "-q/-V",
    type=bool,
    help="Download silently (during download)",
    default=True,
)
@click.option("--verbose", "-v", is_flag=True, help="Download verbosely (everywhere)")
@click.option(
    "--merge", "-m", is_flag=True, help="Merge the subfile with video using ffmpeg"
)
@click.option(
    "--clean",
    "-c",
    is_flag=True,
    help="After merging delete the original files",
)
@click.option(
    "--prompt/--no-prompt",
    help="Whether to prompt for anything instead just do the best thing",
    default=True,
)
@click.option(
    "--force-ffmpeg",
    is_flag=True,
    help="Force the use of FFmpeg for downloading (supports large variety of streams but slower)",
)
@click.option(
    "--hls-use-mpegts",
    is_flag=True,
    help="Use mpegts for hls streams, resulted in .ts file (useful for some streams: see Docs) (this option forces --force-ffmpeg to be True)",
)
@click.option(
    "--hls-use-h264",
    is_flag=True,
    help="Use H.264 (MP4) for hls streams, resulted in .mp4 file (useful for some streams: see Docs) (this option forces --force-ffmpeg to be True)",
)
@click.pass_obj
def download(config: AppConfig, **options: "Unpack[Options]"):
    from anicat_media.cli.service.feedback.service import FeedbackService

    from anicat_media.core.exceptions import AnicatError
    from ...libs.provider.anime.params import (
        AnimeParams,
        SearchParams,
    )
    from ...libs.provider.anime.provider import create_provider
    from ...libs.selectors.selector import create_selector

    feedback = FeedbackService(config)
    provider = create_provider(config.general.provider)
    selector = create_selector(config)

    anime_titles = options["anime_title"]
    feedback.info(f"[green bold]Streaming:[/] {anime_titles}")
    for anime_title in anime_titles:
        # ---- search for anime ----
        feedback.info(f"[green bold]Searching for:[/] {anime_title}")
        with feedback.progress(f"Fetching anime search results for {anime_title}"):
            search_results = provider.search(
                SearchParams(
                    query=anime_title, translation_type=config.stream.translation_type
                )
            )
        if not search_results:
            raise AnicatError("No results were found matching your query")

        _search_results = {
            search_result.title: search_result
            for search_result in search_results.results
        }

        selected_anime_title = selector.choose(
            "Select Anime", list(_search_results.keys())
        )
        if not selected_anime_title:
            raise AnicatError("No title selected")
        anime_result = _search_results[selected_anime_title]

        # ---- fetch selected anime ----
        with feedback.progress(f"Fetching {anime_result.title}"):
            anime = provider.get(AnimeParams(id=anime_result.id, query=anime_title))

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
                    download_anime(
                        config,
                        options,
                        provider,
                        selector,
                        feedback,
                        anime,
                        anime_title,
                        episode,
                    )
            except (ValueError, IndexError) as e:
                raise AnicatError(f"Invalid episode range: {e}") from e
        else:
            episode = selector.choose(
                "Select Episode",
                getattr(anime.episodes, config.stream.translation_type),
            )
            if not episode:
                raise AnicatError("No episode selected")
            download_anime(
                config,
                options,
                provider,
                selector,
                feedback,
                anime,
                anime_title,
                episode,
            )


def download_anime(
    config: AppConfig,
    download_options: "Options",
    provider: "BaseAnimeProvider",
    selector: "BaseSelector",
    feedback: "FeedbackService",
    anime: "Anime",
    anime_title: str,
    episode: str,
):
    from anicat_media.core.downloader import DownloadParams, create_downloader
    from ...libs.provider.anime.params import EpisodeStreamsParams

    downloader = create_downloader(config.downloads)

    with feedback.progress("Fetching episode streams"):
        streams = provider.episode_streams(
            EpisodeStreamsParams(
                anime_id=anime.id,
                query=anime_title,
                episode=episode,
                translation_type=config.stream.translation_type,
            )
        )
        if not streams:
            raise AnicatError(
                f"Failed to get streams for anime: {anime.title}, episode: {episode}"
            )

    if config.stream.server.value == "TOP":
        with feedback.progress("Fetching top server"):
            server = next(streams, None)
            if not server:
                raise AnicatError(
                    f"Failed to get server for anime: {anime.title}, episode: {episode}"
                )
    else:
        with feedback.progress("Fetching servers"):
            servers = {server.name: server for server in streams}
        servers_names = list(servers.keys())
        if config.stream.server in servers_names:
            server = servers[config.stream.server.value]
        else:
            server_name = selector.choose("Select Server", servers_names)
            if not server_name:
                raise AnicatError("Server not selected")
            server = servers[server_name]
    quality = [
        ep_stream.link
        for ep_stream in server.links
        if ep_stream.quality == config.stream.quality
    ]
    if quality:
        stream_link = quality[0]
    else:
        feedback.warning("Preferred quality not found, selecting quality...")
        chosen_quality = selector.choose(
            "Select Quality", [link.quality for link in server.links]
        )
        if not chosen_quality:
            raise AnicatError("Quality not selected")
        stream_link = next(
            (link.link for link in server.links if link.quality == chosen_quality), None
        )
    if not stream_link:
        raise AnicatError(
            f"Failed to get stream link for anime: {anime.title}, episode: {episode}"
        )
    feedback.info(f"[green bold]Now Downloading:[/] {anime.title} Episode: {episode}")
    downloader.download(
        DownloadParams(
            url=stream_link,
            anime_title=anime.title,
            episode_title=f"{anime.title}; Episode {episode}",
            subtitles=[sub.url for sub in server.subtitles],
            headers=server.headers,
            vid_format=config.downloads.ytdlp_format,
            force_unknown_ext=download_options["force_unknown_ext"],
            verbose=download_options["verbose"],
            hls_use_mpegts=download_options["hls_use_mpegts"],
            hls_use_h264=download_options["hls_use_h264"],
            silent=download_options["silent"],
            no_check_certificate=config.downloads.no_check_certificate,
        )
    )
