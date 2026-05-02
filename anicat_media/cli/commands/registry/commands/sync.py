"""
Registry sync command - synchronize local registry with remote media API
"""

import click
from anicat_media.cli.service.feedback.service import FeedbackService
from anicat_media.cli.service.registry.service import MediaRegistryService

from .....core.config import AppConfig


@click.command(help="Synchronize local registry with remote media API")
@click.option(
    "--download", "-d", is_flag=True, help="Download remote user list to local registry"
)
@click.option(
    "--upload", "-u", is_flag=True, help="Upload local registry changes to remote API"
)
@click.option(
    "--force", "-f", is_flag=True, help="Force sync even if there are conflicts"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be synced without making changes"
)
@click.option(
    "--status",
    multiple=True,
    type=click.Choice(
        ["watching", "completed", "planning", "dropped", "paused", "repeating"],
        case_sensitive=False,
    ),
    help="Only sync specific status lists (can be used multiple times)",
)
@click.option(
    "--api",
    default="anilist",
    type=click.Choice(["anilist"], case_sensitive=False),
    help="Media API to sync with",
)
@click.pass_obj
def sync(
    config: AppConfig,
    download: bool,
    upload: bool,
    force: bool,
    dry_run: bool,
    status: tuple[str, ...],
    api: str,
):
    """
    Synchronize local registry with remote media API.

    This command can download your remote media list to the local registry,
    upload local changes to the remote API, or both.
    """

    from .....libs.media_api.api import create_api_client
    from .....libs.media_api.types import UserMediaListStatus
    from ....service.auth import AuthService
    from ....service.feedback import FeedbackService
    from ....service.registry import MediaRegistryService

    feedback = FeedbackService(config)
    auth = AuthService(config.general.media_api)
    registry_service = MediaRegistryService(api, config.media_registry)

    media_api_client = create_api_client(api, config)

    # Default to both download and upload if neither specified
    if not download and not upload:
        download = upload = True

    # Check authentication
    token = auth.resolve_token(config)
    if token:
        if not media_api_client.authenticate(token):
        feedback.error(
            "Authentication Required",
            "You are not logged in. Please run 'anicat login' to continue.",
        )
        raise click.Abort()

    # Determine which statuses to sync
    status_list = (
        list(status)
        if status
        else ["watching", "completed", "planning", "dropped", "paused", "repeating"]
    )

    # Convert to enum values
    status_map = {
        "watching": UserMediaListStatus.WATCHING,
        "completed": UserMediaListStatus.COMPLETED,
        "planning": UserMediaListStatus.PLANNING,
        "dropped": UserMediaListStatus.DROPPED,
        "paused": UserMediaListStatus.PAUSED,
        "repeating": UserMediaListStatus.REPEATING,
    }

    statuses_to_sync = [status_map[s] for s in status_list]

    if download:
        _sync_download(
            media_api_client,
            registry_service,
            statuses_to_sync,
            feedback,
            dry_run,
            force,
        )

    if upload:
        _sync_upload(
            media_api_client,
            registry_service,
            statuses_to_sync,
            feedback,
            dry_run,
            force,
        )

    feedback.success("Sync Complete", "Registry synchronization finished successfully")


def _sync_download(
    api_client, registry_service, statuses, feedback: "FeedbackService", dry_run, force
):
    """Download remote media list to local registry."""
    from .....libs.media_api.params import UserMediaListSearchParams

    feedback.info("Starting Download", "Fetching remote media lists...")

    total_downloaded = 0
    total_updated = 0
    with feedback.progress("Downloading media lists...", total=len(statuses)) as (
        task_id,
        progress,
    ):
        for status in statuses:
            try:
                # Fetch all pages for this status
                page = 1
                while True:
                    params = UserMediaListSearchParams(
                        status=status, page=page, per_page=50
                    )

                    result = api_client.search_media_list(params)
                    if not result or not result.media:
                        break

                    for media_item in result.media:
                        if dry_run:
                            feedback.info(
                                "Would download",
                                f"{media_item.title.english or media_item.title.romaji} ({status.value})",
                            )
                        else:
                            # Get or create record and update with user status
                            record = registry_service.get_or_create_record(media_item)

                            # Update index entry with latest status
                            if media_item.user_status:
                                registry_service.update_media_index_entry(
                                    media_item.id,
                                    media_item=media_item,
                                    status=media_item.user_status.status,
                                    progress=str(media_item.user_status.progress or 0),
                                    score=media_item.user_status.score,
                                    repeat=media_item.user_status.repeat,
                                    notes=media_item.user_status.notes,
                                )
                                total_updated += 1

                            registry_service.save_media_record(record)
                            total_downloaded += 1

                    if not result.page_info.has_next_page:
                        break
                    page += 1

            except Exception as e:
                feedback.error(f"Download Error ({status.value})", str(e))
                continue

            progress.advance(task_id)  # type:ignore

    if not dry_run:
        feedback.success(
            "Download Complete",
            f"Downloaded {total_downloaded} media entries, updated {total_updated} existing entries",
        )


def _sync_upload(
    api_client,
    registry_service: MediaRegistryService,
    statuses,
    feedback,
    dry_run,
    force,
):
    """Upload local registry changes to remote API."""
    feedback.info("Starting Upload", "Syncing local changes to remote...")

    total_uploaded = 0
    total_errors = 0

    with feedback.progress("Uploading changes..."):
        try:
            # Get all media records from registry
            all_records = registry_service.get_all_media_records()

            for record in all_records:
                try:
                    # Get the index entry for this media
                    index_entry = registry_service.get_media_index_entry(
                        record.media_item.id
                    )
                    if not index_entry or not index_entry.status:
                        continue

                    # Only sync if status is in our target list
                    if index_entry.status.value not in statuses:
                        continue

                    if dry_run:
                        feedback.info(
                            "Would upload",
                            f"{record.media_item.title.english or record.media_item.title.romaji} "
                            f"({index_entry.status.value}, progress: {index_entry.progress or 0})",
                        )
                    else:
                        # Update remote list entry
                        from .....libs.media_api.params import (
                            UpdateUserMediaListEntryParams,
                        )

                        update_params = UpdateUserMediaListEntryParams(
                            media_id=record.media_item.id,
                            status=index_entry.status,
                            progress=index_entry.progress,
                            score=index_entry.score,
                        )

                        if api_client.update_list_entry(update_params):
                            total_uploaded += 1
                        else:
                            total_errors += 1
                            feedback.warning(
                                "Upload Failed",
                                f"Failed to upload {record.media_item.title.english or record.media_item.title.romaji}",
                            )

                except Exception as e:
                    total_errors += 1
                    feedback.error(
                        "Upload Error",
                        f"Failed to upload media {record.media_item.id}: {e}",
                    )
                    continue

        except Exception as e:
            feedback.error("Upload Error", f"Failed to get local records: {e}")
            return

    if not dry_run:
        feedback.success(
            "Upload Complete",
            f"Uploaded {total_uploaded} entries, {total_errors} errors",
        )
