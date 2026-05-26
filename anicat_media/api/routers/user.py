from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from ...libs.media_api.types import (
    MediaSearchResult,
    MediaType,
    UserMediaListStatus,
    UserMediaListSort,
    UserProfile,
)
from ...libs.media_api.params import UserMediaListSearchParams
from pydantic import BaseModel

router = APIRouter()

from ..deps import get_ctx, get_media_api

# Track media IDs that were deleted locally but whose AniList sync hasn't
# completed yet. These are filtered from list responses so the UI doesn't
# show items that the user just deleted (before AniList confirms).
_pending_deletions: set[int] = set()


class ListUpdateRequest(BaseModel):
    media_id: int
    status: Optional[UserMediaListStatus] = None
    progress: Optional[int] = None
    score: Optional[float] = None


def _sync_update(media_id: int, status, progress_str, score) -> None:
    """Background task: sync a list update with AniList."""
    try:
        from ...libs.media_api.params import UpdateUserMediaListEntryParams  # noqa: PLC0415

        ctx = get_ctx()
        params = UpdateUserMediaListEntryParams(
            media_id=media_id,
            status=status,
            progress=progress_str,
            score=score,
        )
        ctx.media_api.update_list_entry(params)
    except Exception:
        pass  # Best-effort; local registry already updated


def _sync_delete(media_id: int) -> None:
    """Background task: sync a list deletion with AniList."""
    try:
        ctx = get_ctx()
        if ctx.media_api.delete_list_entry(media_id):
            # Success: AniList confirmed deletion, safe to clear from pending set.
            _pending_deletions.discard(media_id)
        # If AniList returns False (entry not found / timed out), keep the
        # ID in _pending_deletions so list queries continue filtering it.
    except Exception:
        # Network error: keep filtering until the next successful sync.
        pass


@router.get("/profile", response_model=Optional[UserProfile])
def get_profile(api=Depends(get_media_api)):
    """Get the authenticated user's profile."""
    try:
        if not api.is_authenticated():
            return None
        return api.get_viewer_profile()
    except Exception:
        return None


@router.get("/list", response_model=MediaSearchResult)
def get_user_list(
    api=Depends(get_media_api),
    status: Optional[UserMediaListStatus] = None,
    type: Optional[MediaType] = None,
    page: int = 1,
):
    """Get the authenticated user's media list."""
    try:
        if not api.is_authenticated():
            from ...libs.media_api.types import PageInfo

            return MediaSearchResult(
                page_info=PageInfo(
                    total=0, current_page=1, has_next_page=False, per_page=15
                ),
                media=[],
            )

        params = UserMediaListSearchParams(
            status=status or UserMediaListStatus.WATCHING,
            type=type,
            page=page,
            sort=UserMediaListSort.UPDATED_TIME_DESC,
        )
        result = api.search_media_list(params)
        if not result:
            from ...libs.media_api.types import PageInfo

            return MediaSearchResult(
                page_info=PageInfo(
                    total=0, current_page=1, has_next_page=False, per_page=15
                ),
                media=[],
            )

        # Filter out items that were deleted locally but whose AniList sync
        # hasn't completed yet (prevents deleted items from reappearing).
        if _pending_deletions and result.media:
            result.media = [m for m in result.media if m.id not in _pending_deletions]
            if result.page_info:
                result.page_info.total = len(result.media)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_list_entry(req: ListUpdateRequest, background_tasks: BackgroundTasks):
    """Update a user's list entry for a media item."""
    try:
        ctx = get_ctx()
        progress_str = str(req.progress) if req.progress is not None else None

        # 1. Update local registry immediately (instant, no network)
        ctx.media_registry.update_media_index_entry(
            media_id=req.media_id,
            status=req.status,
            progress=progress_str,
            score=req.score,
        )

        # 2. Bump data version so UI refetches
        ctx.data_version += 1

        # 3. Fire AniList sync in the background (does not block response)
        background_tasks.add_task(
            _sync_update, req.media_id, req.status, progress_str, req.score
        )

        # 4. Clear playback state
        from .status import clear_playback  # noqa: PLC0415

        clear_playback(background_tasks)

        return {"status": "success", "synced": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{media_id}")
async def delete_list_entry(media_id: int, background_tasks: BackgroundTasks):
    """Delete a user's list entry for a media item."""
    try:
        ctx = get_ctx()

        # 1. Remove from local registry immediately (instant, no network)
        ctx.media_registry.remove_media_record(media_id)

        # 2. Track pending deletion so list queries filter it out until AniList syncs
        _pending_deletions.add(media_id)

        # 3. Bump data version so UI refetches
        ctx.data_version += 1

        # 4. Fire AniList deletion in the background (does not block response)
        background_tasks.add_task(_sync_delete, media_id)

        # 5. Clear playback state
        from .status import clear_playback  # noqa: PLC0415

        clear_playback(background_tasks)

        return {"status": "success", "deleted": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
