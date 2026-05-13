from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ...cli.service.registry.models import DownloadStatus

router = APIRouter()

def get_ctx():
    from ..main import ctx
    return ctx

class QueueItem(BaseModel):
    media_id: int
    media_title: str
    episode_number: str
    status: DownloadStatus
    error_message: Optional[str] = None

@router.get("/", response_model=List[QueueItem])
async def get_queue():
    """Get all items currently in the download queue or failed."""
    ctx = get_ctx()
    items = []
    # Query registry for QUEUED, DOWNLOADING, FAILED
    for status in [DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING, DownloadStatus.FAILED]:
        job_refs = ctx.media_registry.get_episodes_by_download_status(status)
        for media_id, ep_num in job_refs:
            record = ctx.media_registry.get_media_record(media_id)
            if record:
                # Find the specific episode in the record
                ep_record = next((e for e in record.media_episodes if e.episode_number == ep_num), None)
                items.append(QueueItem(
                    media_id=media_id,
                    media_title=record.media_item.title.english or record.media_item.title.romaji,
                    episode_number=ep_num,
                    status=status,
                    error_message=ep_record.last_error if ep_record else None
                ))
    return items

@router.post("/add")
async def add_to_queue(media_id: int, episodes: List[str]):
    """Add episodes to the download queue."""
    try:
        ctx = get_ctx()
        media_item = ctx.media_api.get_media_item(media_id)
        if not media_item:
            raise HTTPException(status_code=404, detail="Media not found")
        
        for ep in episodes:
            ctx.download.add_to_queue(media_item, ep)
        
        # Trigger worker if not running
        ctx.download.start()
        return {"status": "added", "count": len(episodes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry")
async def retry_failed():
    """Retry all failed downloads."""
    try:
        ctx = get_ctx()
        ctx.download.retry_failed_downloads()
        return {"status": "retrying"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{media_id}/{episode}")
async def remove_from_queue(media_id: int, episode: str):
    """Remove an item from the queue."""
    try:
        ctx = get_ctx()
        # Update status to NOT_DOWNLOADED in registry
        success = ctx.media_registry.update_episode_download_status(
            media_id=media_id,
            episode_number=episode,
            status=DownloadStatus.NOT_DOWNLOADED
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update status")
        return {"status": "removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
