import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from ...libs.media_api.types import MediaSearchResult, MediaType, UserMediaListStatus, UserMediaListSort, UserProfile
from ...libs.media_api.params import UserMediaListSearchParams
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

from ..deps import get_ctx, get_media_api

class ListUpdateRequest(BaseModel):
    media_id: int
    status: Optional[UserMediaListStatus] = None
    progress: Optional[int] = None
    score: Optional[float] = None

@router.get("/profile", response_model=Optional[UserProfile])
async def get_profile(api = Depends(get_media_api)):
    """Get the authenticated user's profile."""
    try:
        if not api.is_authenticated():
            return None
        return api.get_viewer_profile()
    except Exception:
        return None

@router.get("/list", response_model=MediaSearchResult)
async def get_user_list(
    api = Depends(get_media_api),
    status: Optional[UserMediaListStatus] = None,
    type: Optional[MediaType] = None,
    page: int = 1
):
    """Get the authenticated user's media list."""
    try:
        if not api.is_authenticated():
            from ...libs.media_api.types import PageInfo
            return MediaSearchResult(
                page_info=PageInfo(total=0, current_page=1, has_next_page=False, per_page=15),
                media=[]
            )
            
        params = UserMediaListSearchParams(
            status=status or UserMediaListStatus.WATCHING,
            type=type,
            page=page,
            sort=UserMediaListSort.UPDATED_TIME_DESC
        )
        result = api.search_media_list(params)
        if not result:
            from ...libs.media_api.types import PageInfo
            return MediaSearchResult(
                page_info=PageInfo(total=0, current_page=1, has_next_page=False, per_page=15),
                media=[]
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def sync_update_in_background(media_id: int, status: Optional[UserMediaListStatus], progress: Optional[int], score: Optional[float]):
    """Background task to sync list entry update to AniList."""
    try:
        ctx = get_ctx()
        from ...libs.media_api.params import UpdateUserMediaListEntryParams
        params = UpdateUserMediaListEntryParams(
            media_id=media_id,
            status=status,
            progress=str(progress) if progress is not None else None,
            score=score
        )
        success = ctx.media_api.update_list_entry(params)
        if success and not hasattr(ctx.media_registry, "updated_entries"):
            ctx.media_registry.update_media_index_entry(
                media_id=media_id,
                is_synced=True
            )
            logger.info(f"Successfully synced update for media {media_id} to AniList.")
        else:
            logger.warning(f"Failed to sync update for media {media_id} to AniList.")
    except Exception as e:
        logger.error(f"Error in background sync_update for media {media_id}: {e}")

def sync_delete_in_background(media_id: int):
    """Background task to sync list entry deletion to AniList."""
    try:
        ctx = get_ctx()
        success = ctx.media_api.delete_list_entry(media_id)
        if success:
            logger.info(f"Successfully synced deletion for media {media_id} to AniList.")
        else:
            logger.warning(f"Failed to sync deletion for media {media_id} to AniList.")
    except Exception as e:
        logger.error(f"Error in background sync_delete for media {media_id}: {e}")

@router.post("/update")
async def update_list_entry(req: ListUpdateRequest, background_tasks: BackgroundTasks):
    """Update a user's list entry for a media item."""
    try:
        ctx = get_ctx()
        
        # 1. Update local registry first (Live source of truth)
        ctx.media_registry.update_media_index_entry(
            media_id=req.media_id,
            status=req.status,
            progress=str(req.progress) if req.progress is not None else None,
            score=req.score,
            is_synced=False,
        )
        
        # 2. Queue sync to AniList in background
        background_tasks.add_task(
            sync_update_in_background,
            req.media_id,
            req.status,
            req.progress,
            req.score
        )
        
        # 3. Handle playback clear
        from .status import clear_playback
        await clear_playback()
        ctx.data_version += 1
        return {"status": "success", "synced": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{media_id}")
async def delete_list_entry(media_id: int, background_tasks: BackgroundTasks):
    """Delete a user's list entry for a media item."""
    try:
        ctx = get_ctx()
        # 1. Update local registry
        ctx.media_registry.remove_media_record(media_id)
        
        # 2. Queue sync to AniList in background
        background_tasks.add_task(sync_delete_in_background, media_id)
        
        # 3. Handle playback clear
        from .status import clear_playback
        await clear_playback()
        ctx.data_version += 1
        return {"status": "success", "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

