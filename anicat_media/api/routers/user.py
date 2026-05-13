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
        return ctx.media_api.get_viewer_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        params = UserMediaListSearchParams(status=status, type=type, page=page)
        result = ctx.media_api.search_media_list(params)
        if not result:
             raise HTTPException(status_code=404, detail="List not found or empty")
        return result
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
        success = ctx.media_api.update_list_entry(params)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update list entry")
        
        # Also update local registry to stay in sync
        ctx.media_registry.update_media_index_entry(
            media_id=req.media_id,
            status=req.status,
            progress=str(req.progress) if req.progress is not None else None,
            score=req.score
        )
        
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
