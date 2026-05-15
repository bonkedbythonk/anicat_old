from typing import Optional
from fastapi import APIRouter, HTTPException
from ...libs.media_api.types import MediaSearchResult, MediaType, UserMediaListStatus, UserProfile
from ...libs.media_api.params import UserMediaListSearchParams
from pydantic import BaseModel

router = APIRouter()

def get_ctx():
    from ..main import ctx
    return ctx

class ListUpdateRequest(BaseModel):
    media_id: int
    status: Optional[UserMediaListStatus] = None
    progress: Optional[int] = None
    score: Optional[float] = None

@router.get("/profile", response_model=Optional[UserProfile])
async def get_profile():
    """Get the authenticated user's profile."""
    try:
        ctx = get_ctx()
        if not ctx.media_api.is_authenticated():
            return None
        return ctx.media_api.get_viewer_profile()
    except Exception:
        return None

@router.get("/list", response_model=MediaSearchResult)
async def get_user_list(
    status: Optional[UserMediaListStatus] = None,
    type: Optional[MediaType] = None,
    page: int = 1
):
    """Get the authenticated user's media list."""
    try:
        ctx = get_ctx()
        if not ctx.media_api.is_authenticated():
            from ...libs.media_api.types import PageInfo
            return MediaSearchResult(
                page_info=PageInfo(total=0, current_page=1, has_next_page=False, per_page=15),
                media=[]
            )
            
        params = UserMediaListSearchParams(status=status, type=type, page=page)
        result = ctx.media_api.search_media_list(params)
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

@router.post("/update")
async def update_list_entry(req: ListUpdateRequest):
    """Update a user's list entry for a media item."""
    try:
        ctx = get_ctx()
        from ...libs.media_api.params import UpdateUserMediaListEntryParams
        params = UpdateUserMediaListEntryParams(
            media_id=req.media_id,
            status=req.status,
            progress=req.progress,
            score=req.score
        )
        # 1. Update local registry first (Live source of truth)
        ctx.media_registry.update_media_index_entry(
            media_id=req.media_id,
            status=req.status,
            progress=str(req.progress) if req.progress is not None else None,
            score=req.score
        )
        
        # 2. Attempt to sync with AniList
        success = ctx.media_api.update_list_entry(params)
        
        # 3. Handle playback clear
        from .status import clear_playback
        await clear_playback()
        ctx.data_version += 1
        return {"status": "success", "synced": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
