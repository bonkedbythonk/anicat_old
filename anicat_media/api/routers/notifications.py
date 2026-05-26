from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ...libs.media_api.types import Notification
from ..deps import get_media_api

router = APIRouter()


@router.get("/", response_model=List[Notification])
def get_notifications(api=Depends(get_media_api)):
    """Get the authenticated user's unread notifications."""
    try:
        if not api.is_authenticated():
            return []
        notifications = api.get_notifications()
        return notifications or []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read")
def mark_notifications_as_read(api=Depends(get_media_api)):
    """Mark all notifications as read."""
    try:
        if not api.is_authenticated():
            return {"status": "success"}
        success = api.mark_notifications_as_read()
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
