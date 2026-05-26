import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

from anicat_media.cli.utils.search import find_best_match_title

from anicat_media.core.config.model import AppConfig
from anicat_media.core.constants import APP_CACHE_DIR
from anicat_media.core.downloader import DownloadParams, create_downloader
from anicat_media.core.utils.concurrency import ManagedBackgroundWorker, thread_manager
from anicat_media.core.utils.normalizer import normalize_title
from ....libs.media_api.types import MediaItem
from ....libs.provider.anime.params import (
    AnimeParams,
    EpisodeStreamsParams,
    SearchParams,
)
from ..registry.models import DownloadStatus

if TYPE_CHECKING:
    from ....libs.media_api.api import BaseApiClient
    from ....libs.provider.anime.provider import BaseAnimeProvider
    from ..registry.service import MediaRegistryService


logger = logging.getLogger(__name__)
NOTIFICATION_ICONS_CACHE_DIR = APP_CACHE_DIR / "notification_icons"


class DownloadService:
    def __init__(
        self,
        config: AppConfig,
        registry_service: "MediaRegistryService",
        media_api_service: "BaseApiClient",
        provider_service: "BaseAnimeProvider",
    ):
        self.app_config = config
        self.registry = registry_service
        self.media_api = media_api_service
        self.provider = provider_service
        self.downloader = create_downloader(config)
        # Track in-flight downloads to avoid duplicate queueing
        self._inflight: set[tuple[int, str]] = set()
        # Cooldown to prevent resume_unfinished_downloads from thrashing
        # when start() is called multiple times in quick succession.
        self._last_resume_time: float = 0.0

        self._worker = ManagedBackgroundWorker(
            max_workers=config.downloads.max_concurrent_downloads,
            name="DownloadWorker",
        )
        thread_manager.register_worker("download_worker", self._worker)

    def start(self):
        """Starts the download worker for background tasks."""
        if not self._worker.is_running():
            self._worker.start()
        # Resume unfinished downloads (with cooldown to avoid thrashing)
        self.resume_unfinished_downloads()

    def stop(self):
        """Stops the download worker."""
        self._worker.shutdown(wait=False)

    def add_to_queue(self, media_item: MediaItem, episode_number: str) -> bool:
        """Mark an episode as queued in the registry (no immediate download).

        Refuses to re-queue episodes that have already exceeded the
        maximum retry limit, preventing infinite retry loops when a
        provider consistently returns unplayable streams.
        """
        # Check whether this episode has already been retried too many times
        record = self.registry.get_media_record(media_item.id)
        if record:
            for ep in record.media_episodes:
                if ep.episode_number == episode_number:
                    if (
                        ep.download_status == DownloadStatus.FAILED
                        and ep.download_attempts > self.app_config.downloads.max_retry_attempts
                    ):
                        logger.warning(
                            f"Episode '{episode_number}' of '{media_item.title.english}' "
                            f"has exceeded max retry attempts ({self.app_config.downloads.max_retry_attempts}). "
                            f"Not re-queueing."
                        )
                        return False
                    break

        logger.info(
            f"Queueing episode '{episode_number}' for '{media_item.title.english}' (registry only)"
        )
        self.registry.get_or_create_record(media_item)
        return self.registry.update_episode_download_status(
            media_id=media_item.id,
            episode_number=episode_number,
            status=DownloadStatus.QUEUED,
        )

    def _submit_download(self, media_item: MediaItem, episode_number: str) -> bool:
        """Submit a download task to the worker if not already in-flight."""
        key = (media_item.id, str(episode_number))
        if key in self._inflight:
            return False
        if not self._worker.is_running():
            self._worker.start()
        self._inflight.add(key)
        self._worker.submit_function(
            self._execute_download_job, media_item, episode_number
        )
        return True

    def download_episodes_sync(self, media_item: MediaItem, episodes: List[str]):
        """
        Performs downloads SYNCHRONOUSLY and blocks until complete.
        This is for the direct `download` command.
        """
        success_count = 0
        failed_episodes = []

        for episode_number in episodes:
            title = (
                media_item.title.english
                or media_item.title.romaji
                or f"ID: {media_item.id}"
            )
            logger.info(
                f"Starting synchronous download for '{title}' Episode {episode_number}"
            )
            if self._execute_download_job(media_item, episode_number):
                success_count += 1
            else:
                failed_episodes.append(episode_number)

        return success_count, failed_episodes

    def resume_unfinished_downloads(self):
        """Finds and re-queues any downloads that were left in an unfinished state.

        Includes a short cooldown to prevent redundant re-scans when start()
        is called multiple times in quick succession (e.g. user clicks download
        on several episodes rapidly).
        """
        import time

        now = time.time()
        if now - self._last_resume_time < 3.0:
            logger.debug("Skipping resume scan — within cooldown window")
            return
        self._last_resume_time = now

        logger.info("Checking for unfinished downloads to resume...")
        # TODO: make the checking of unfinished downloads more efficient probably by modifying the registry to be aware of what actually changed and load that instead
        queued_jobs = self.registry.get_episodes_by_download_status(
            DownloadStatus.QUEUED
        )
        downloading_jobs = self.registry.get_episodes_by_download_status(
            DownloadStatus.DOWNLOADING
        )

        unfinished_jobs = queued_jobs + downloading_jobs
        if not unfinished_jobs:
            logger.info("No unfinished downloads found.")
            return

        logger.info(
            f"Found {len(unfinished_jobs)} unfinished downloads. Re-queueing..."
        )
        for media_id, episode_number in unfinished_jobs:
            if (media_id, str(episode_number)) in self._inflight:
                continue
            record = self.registry.get_media_record(media_id)
            if record and record.media_item:
                self._submit_download(record.media_item, episode_number)
            else:
                logger.error(
                    f"Could not find metadata for media ID {media_id}. Cannot resume. Please run 'anicat registry sync'."
                )

    def retry_failed_downloads(self):
        """Finds and re-queues any downloads that were left in an unfinished state."""
        logger.info("Checking for unfinished downloads to resume...")
        # TODO: may need to improve this
        queued_jobs = self.registry.get_episodes_by_download_status(
            DownloadStatus.FAILED
        )

        unfinished_jobs = queued_jobs
        if not unfinished_jobs:
            logger.info("No unfinished downloads found.")
            return

        logger.info(
            f"Found {len(unfinished_jobs)} unfinished downloads. Re-queueing..."
        )
        for media_id, episode_number in unfinished_jobs:
            if (media_id, str(episode_number)) in self._inflight:
                continue

            record = self.registry.get_media_record(media_id)
            if record and record.media_item:
                for episode in record.media_episodes:
                    if episode_number != episode.episode_number:
                        continue
                    if (
                        episode.download_attempts
                        <= self.app_config.downloads.max_retry_attempts
                    ):
                        logger.info(
                            f"Retrying {episode_number} of {record.media_item.title.english}"
                        )
                        self._submit_download(record.media_item, episode_number)
                    else:
                        logger.info(
                            f"Max attempts reached for {episode_number} of {record.media_item.title.english}"
                        )

            else:
                logger.error(
                    f"Could not find metadata for media ID {media_id}. Cannot resume. Please run 'anicat registry sync'."
                )

    def _execute_download_job(self, media_item: MediaItem, episode_number: str):
        """The core download logic, can be called by worker or synchronously.

        Tries the primary provider first. If the yt-dlp download fails
        (stream links are returned but won't play), automatically retries
        with each fallback provider in sequence.
        """
        self.registry.get_or_create_record(media_item)

        # Collect providers to try: primary first, then fallbacks
        from ....libs.provider.anime.fallback import FallbackAnimeProvider

        if isinstance(self.provider, FallbackAnimeProvider):
            providers_to_try = list(self.provider.providers)
        else:
            providers_to_try = [self.provider]

        media_title = media_item.title.romaji or media_item.title.english
        last_error: str | None = None

        try:
            for idx, provider in enumerate(providers_to_try):
                provider_name = getattr(provider, "NAME", provider.__class__.__name__)
                if idx > 0:
                    logger.info(
                        f"Fallback: retrying download of Ep {episode_number} "
                        f"of '{media_title}' with provider '{provider_name}' "
                        f"(previous error: {last_error})"
                    )

                try:
                    self.registry.update_episode_download_status(
                        media_id=media_item.id,
                        episode_number=episode_number,
                        status=DownloadStatus.DOWNLOADING,
                    )

                    # 1. Search the provider
                    provider_search_results = provider.search(
                        SearchParams(
                            query=normalize_title(
                                media_title, self.app_config.general.provider.value, True
                            ),
                            translation_type=self.app_config.stream.translation_type,
                        )
                    )
                    if not provider_search_results or not provider_search_results.results:
                        last_error = (
                            f"Could not find '{media_title}' on provider '{provider_name}'"
                        )
                        continue

                    # 2. Find best match
                    provider_results_map = {
                        result.title: result for result in provider_search_results.results
                    }
                    best_match_title = find_best_match_title(
                        provider_results_map, self.app_config.general.provider, media_item
                    )
                    provider_anime_ref = provider_results_map[best_match_title]

                    # 3. Get full provider anime details
                    provider_anime = provider.get(
                        AnimeParams(id=provider_anime_ref.id, query=media_title)
                    )
                    if not provider_anime:
                        last_error = (
                            f"Failed to get full details for '{best_match_title}' "
                            f"from provider '{provider_name}'."
                        )
                        continue

                    # 4. Get stream links
                    streams_iterator = provider.episode_streams(
                        EpisodeStreamsParams(
                            anime_id=provider_anime.id,
                            query=media_title,
                            episode=episode_number,
                            translation_type=self.app_config.stream.translation_type,
                        )
                    )
                    if not streams_iterator:
                        last_error = f"Provider '{provider_name}' returned no stream iterator."
                        continue

                    server = next(streams_iterator, None)
                    if not server or not server.links:
                        last_error = (
                            f"No stream links found for Episode {episode_number} "
                            f"on provider '{provider_name}'"
                        )
                        continue

                    if server.name != self.app_config.downloads.server.value:
                        while True:
                            try:
                                _server = next(streams_iterator)
                                if _server.name == self.app_config.downloads.server.value:
                                    server = _server
                                    break
                            except StopIteration:
                                break

                    preferred_quality = self.app_config.stream.quality
                    stream_link = next(
                        (link for link in server.links if link.quality == preferred_quality),
                        None,
                    )
                    if not stream_link:
                        try:
                            stream_link = sorted(
                                server.links, key=lambda x: int(x.quality), reverse=True
                            )[0]
                        except Exception:
                            stream_link = server.links[-1]

                    episode_title = f"{media_item.title.english}; Episode {episode_number}"
                    if media_item.streaming_episodes and media_item.streaming_episodes.get(
                        episode_number
                    ):
                        episode_title = media_item.streaming_episodes[episode_number].title

                    # 5. Perform the download
                    download_params = DownloadParams(
                        url=stream_link.link,
                        anime_title=media_item.title.english,
                        episode_title=episode_title,
                        silent=False,
                        headers=server.headers,
                        subtitles=[sub.url for sub in server.subtitles],
                        merge=self.app_config.downloads.merge_subtitles,
                        clean=self.app_config.downloads.cleanup_after_merge,
                        no_check_certificate=self.app_config.downloads.no_check_certificate,
                    )

                    result = self.downloader.download(download_params)

                    # 6. Update registry on success
                    if result.success and result.video_path:
                        file_size = (
                            result.video_path.stat().st_size
                            if result.video_path.exists()
                            else None
                        )
                        self.registry.update_episode_download_status(
                            media_id=media_item.id,
                            episode_number=episode_number,
                            status=DownloadStatus.COMPLETED,
                            file_path=result.merged_path or result.video_path,
                            file_size=file_size,
                            quality=stream_link.quality,
                            provider_name=provider_name,
                            server_name=server.name,
                            subtitle_paths=result.subtitle_paths,
                        )
                        message = (
                            f"Successfully downloaded Episode {episode_number} of '{media_title}'"
                            + (f" via {provider_name}" if idx > 0 else "")
                        )
                        try:
                            from plyer import notification

                            icon_path = self._get_or_fetch_icon(media_item)
                            app_icon = str(icon_path) if icon_path else None

                            notification.notify(  # type: ignore
                                title="Anicat: New Episode",
                                message=message,
                                app_name="Anicat",
                                app_icon=app_icon,
                                timeout=self.app_config.general.desktop_notification_duration,
                            )
                        except:  # noqa: E722
                            pass
                        logger.info(message)
                        return True
                    else:
                        last_error = result.error_message or "Unknown download error"
                        # Don't raise — try the next fallback provider
                        continue

                except Exception as e:
                    last_error = str(e)
                    # Non-download errors (network, provider down, etc.) —
                    # also try the next fallback provider
                    continue

            # All providers exhausted — mark as failed
            final_message = (
                f"Download failed for '{media_title}' Ep {episode_number}: {last_error}"
            )
            try:
                from plyer import notification

                icon_path = self._get_or_fetch_icon(media_item)
                app_icon = str(icon_path) if icon_path else None

                notification.notify(  # type: ignore
                    title="Anicat: Download Failed",
                    message=final_message,
                    app_name="Anicat",
                    app_icon=app_icon,
                    timeout=self.app_config.general.desktop_notification_duration,
                )
            except:  # noqa: E722
                pass
            logger.error(final_message)
            self.registry.update_episode_download_status(
                media_id=media_item.id,
                episode_number=episode_number,
                status=DownloadStatus.FAILED,
                error_message=last_error or "All providers failed",
            )
            return False
        finally:
            # Remove from in-flight tracking regardless of outcome
            try:
                self._inflight.discard((media_item.id, str(episode_number)))
            except Exception:
                pass

    def _get_or_fetch_icon(self, media_item: MediaItem) -> Path | None:
        """Fetch and cache a small cover image for system notifications."""
        import httpx

        try:
            cover = media_item.cover_image
            url = None
            if cover:
                url = cover.extra_large or cover.large or cover.medium
            if not url:
                return None

            cache_dir = NOTIFICATION_ICONS_CACHE_DIR
            cache_dir.mkdir(parents=True, exist_ok=True)
            icon_path = cache_dir / f"{media_item.id}.png"
            if icon_path.exists() and icon_path.stat().st_size > 0:
                return icon_path

            # Directly download the image bytes without resizing
            with httpx.Client(follow_redirects=True, timeout=20) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.content
                if data:
                    icon_path.write_bytes(data)
                    return icon_path
        except Exception as e:
            logger.debug(f"Could not fetch icon for media {media_item.id}: {e}")
        return None
