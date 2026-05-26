import logging
from typing import Optional

from ....core.config.model import AppConfig
from ....libs.media_api.base import BaseApiClient
from ....libs.media_api.params import UpdateUserMediaListEntryParams
from ....libs.media_api.types import MediaItem, UserMediaListStatus
from ....libs.player.types import PlayerResult
from ..registry import MediaRegistryService

logger = logging.getLogger(__name__)


class WatchHistoryService:
    def __init__(
        self,
        config: AppConfig,
        media_registry: MediaRegistryService,
        media_api: Optional[BaseApiClient] = None,
    ):
        self.config = config
        self.media_registry = media_registry
        self.media_api = media_api

    def track(self, media_item: MediaItem, player_result: PlayerResult):
        logger.info(
            f"Updating watch history for {media_item.title.english} ({media_item.id}) with Episode={player_result.episode}; Stop Time={player_result.stop_time}; Total Duration={player_result.total_time}"
        )
        status = None

        if (
            media_item.user_status
            and media_item.user_status.status == UserMediaListStatus.COMPLETED
        ):
            status = UserMediaListStatus.REPEATING

        # Calculate completion percentage if times are present
        is_completed = False
        completion_percentage = 0.0
        if player_result.stop_time and player_result.total_time:
            from ....core.utils.converter import calculate_completion_percentage

            completion_percentage = calculate_completion_percentage(
                player_result.stop_time, player_result.total_time
            )
            is_completed = (
                completion_percentage >= self.config.stream.episode_complete_at
            )

        # Determine what progress to write to local registry
        if is_completed:
            progress_value = player_result.episode
            # Clear watch position/duration since it is completed
            last_watch_pos = None
            total_dur = None
        else:
            # Not completed! Keep previous progress from registry or media_item
            index_entry = self.media_registry.get_media_index_entry(media_item.id)
            if index_entry and index_entry.progress:
                progress_value = index_entry.progress
            elif media_item.user_status and media_item.user_status.progress is not None:
                progress_value = str(media_item.user_status.progress)
            else:
                progress_value = None

            last_watch_pos = player_result.stop_time
            total_dur = player_result.total_time

        self.media_registry.update_media_index_entry(
            media_id=media_item.id,
            watched=True,
            media_item=media_item,
            last_watch_position=last_watch_pos,
            total_duration=total_dur,
            progress=progress_value,
            status=status,
            is_synced=False if is_completed else True,
        )

        if not is_completed:
            logger.info(
                f"Not updating remote watch history since completion percentage ({completion_percentage}) is not greater than episode complete at ({self.config.stream.episode_complete_at})"
            )
            return True

        if self.media_api and self.media_api.is_authenticated():
            # --- Progress Regression Check ---
            if self.config.stream.force_forward_tracking and media_item.user_status:
                try:
                    current_progress = media_item.user_status.progress or 0
                    watched_episode = int(player_result.episode)
                    if watched_episode <= current_progress:
                        logger.info(
                            f"Skipping AniList sync: Episode {watched_episode} is not an advancement over current progress {current_progress}."
                        )
                        return True
                except (ValueError, TypeError):
                    pass

            success = self.media_api.update_list_entry(
                UpdateUserMediaListEntryParams(
                    media_id=media_item.id,
                    status=status,
                    progress=player_result.episode,
                )
            )
            if success:
                logger.info(
                    f"successfully updated remote progress with {player_result.episode}"
                )
                self.media_registry.update_media_index_entry(
                    media_id=media_item.id, is_synced=True
                )
            else:
                logger.warning(
                    f"failed to update remote progress with {player_result.episode}"
                )
            return success
        else:
            logger.warning("Not logged in")
            return False

    def get_episode(self, media_item: MediaItem):
        index_entry = self.media_registry.get_media_index_entry(media_item.id)

        # 1. Get baseline from AniList (Remote)
        remote_progress = 0
        if media_item.user_status:
            remote_progress = media_item.user_status.progress or 0

        # 2. Get baseline from Local Registry
        local_progress = remote_progress
        start_time = None
        total_duration = None

        if index_entry:
            try:
                local_progress = int(index_entry.progress or 0)
                start_time = index_entry.last_watch_position
                total_duration = index_entry.total_duration
            except (ValueError, TypeError):
                local_progress = remote_progress

        # 3. Determine the best known progress (local registry is the live source,
        #    AniList is a fallback that may be up to 5 minutes stale).
        best_progress = max(local_progress, remote_progress)

        # 4. Handle stale resume positions from old registry data (before the
        #    last_watch_position clearing bug was fixed). If AniList progress
        #    has moved past the local value, the partial-watch data belongs to
        #    a previous episode — discard it.
        if start_time and local_progress < best_progress:
            logger.debug(
                f"Discarding stale resume position for media {media_item.id}: "
                f"local progress={local_progress}, best progress={best_progress}"
            )
            start_time = None
            total_duration = None

        # 5. Handle Completion and Increment
        # C3: Only increment when we have actual evidence the current episode was completed.
        # The old code unconditionally incremented in the `else` branch, causing episodes
        # to be skipped every time the media detail page was loaded.
        episode_completed = False
        if start_time and total_duration:
            # Active local session — check if the episode was completed
            from ....core.utils.converter import calculate_completion_percentage

            if (
                calculate_completion_percentage(start_time, total_duration)
                >= self.config.stream.episode_complete_at
            ):
                # Episode is considered finished, move to next
                episode_completed = True
                start_time = None

        # Only advance to the next episode when we have confirmed completion
        # (either via start_time/total_duration calculation above, or when the
        # episode number in the registry already exceeds the best_progress).
        # This prevents the "phantom increment" bug where loading a media page
        # would unconditionally skip to the next episode.
        if episode_completed:
            best_progress += 1

        # Determine the next episode to watch.
        # best_progress represents the highest completed episode number.
        # next_episode is the first unwatched episode.
        total_eps = media_item.episodes or 0
        if total_eps > 0 and best_progress >= total_eps:
            # Series is completed; start over at episode 1
            next_episode = 1
            start_time = None
        else:
            # best_progress was NOT incremented for completion → resume
            # the in-progress episode (best_progress + 1) with its position.
            # best_progress WAS incremented for completion → advance to
            # the next episode (best_progress) from the beginning.
            if episode_completed:
                next_episode = best_progress
            else:
                next_episode = best_progress + 1

        return str(next_episode), start_time

    def update(
        self,
        media_item: MediaItem,
        progress: Optional[str] = None,
        status: Optional[UserMediaListStatus] = None,
        score: Optional[float] = None,
        notes: Optional[str] = None,
    ):
        self.media_registry.update_media_index_entry(
            media_id=media_item.id,
            media_item=media_item,
            progress=progress,
            status=status,
            score=score,
            notes=notes,
        )

        if self.media_api and self.media_api.is_authenticated():
            self.media_api.update_list_entry(
                UpdateUserMediaListEntryParams(
                    media_id=media_item.id,
                    status=status,
                    score=score,
                    progress=progress,
                )
            )
            logger.info("updating remote progressd")
        else:
            logger.warning("Not logged in")

    def add_media_to_list_if_not_present(self, media_item: MediaItem):
        """Adds a media item to the user's PLANNING list if it's not already on any list."""
        if not self.media_api or not self.media_api.is_authenticated():
            return

        # If user_status is None, it means the item is not on the user's list.
        if media_item.user_status is None:
            logger.info(
                f"'{media_item.title.english}' not on list. Adding to 'Planning'."
            )
            self.update(media_item, status=UserMediaListStatus.PLANNING)
