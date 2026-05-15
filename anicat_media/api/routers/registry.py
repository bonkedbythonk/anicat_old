from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

def get_ctx():
    from ..main import ctx
    return ctx

@router.get("/stats")
async def get_registry_stats():
    """Get comprehensive registry and download statistics."""
    try:
        ctx = get_ctx()
        registry_stats = ctx.media_registry.get_registry_stats()
        download_stats = ctx.media_registry.get_download_statistics()
        return {
            "registry": registry_stats,
            "downloads": download_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backup")
async def create_backup():
    """Create a registry backup archive."""
    try:
        import shutil
        import tempfile
        from pathlib import Path
        from datetime import datetime

        ctx = get_ctx()
        registry_dir = ctx.media_registry.media_registry_dir
        index_dir = ctx.media_registry.config.index_dir

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = registry_dir.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"anicat_backup_{timestamp}"

        # Create zip archive
        archive_path = shutil.make_archive(
            str(backup_path),
            'zip',
            root_dir=str(registry_dir.parent),
            base_dir=registry_dir.name,
        )

        return {
            "status": "created",
            "path": archive_path,
            "filename": f"anicat_backup_{timestamp}.zip",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backup/download")
async def download_latest_backup():
    """Download the most recent backup archive."""
    try:
        from pathlib import Path

        ctx = get_ctx()
        backup_dir = ctx.media_registry.media_registry_dir.parent / "backups"

        if not backup_dir.exists():
            raise HTTPException(status_code=404, detail="No backups found")

        # Find the latest .zip
        backups = sorted(backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            raise HTTPException(status_code=404, detail="No backups found")

        latest = backups[0]
        return FileResponse(
            path=str(latest),
            filename=latest.name,
            media_type="application/zip",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wipe")
async def wipe_registry():
    """Wipe the entire local registry and index."""
    try:
        import shutil
        ctx = get_ctx()
        registry_dir = ctx.media_registry.media_registry_dir
        if registry_dir.exists():
            shutil.rmtree(registry_dir)
        registry_dir.mkdir(parents=True, exist_ok=True)
        return {"status": "wiped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
