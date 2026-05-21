import logging
import os
from ..core.constants import LOG_FILE
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sys

# Ensure common paths are present for macOS GUI launches and Windows bundled apps
if sys.platform == "darwin":
    path = os.environ.get("PATH", "")
    extra_paths = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        os.path.expanduser("~/.local/bin")
    ]
    current_paths = path.split(os.pathsep)
    for p in extra_paths:
        if p not in current_paths:
            current_paths.append(p)
    os.environ["PATH"] = os.pathsep.join(current_paths)
elif sys.platform == "win32":
    path = os.environ.get("PATH", "")
    extra_paths = [
        os.path.expanduser("~\\scoop\\shims"),
        os.path.expanduser("~\\AppData\\Local\\Microsoft\\WindowsApps"),
    ]
    current_paths = path.split(os.pathsep)
    for p in extra_paths:
        if p not in current_paths:
            current_paths.append(p)
    os.environ["PATH"] = os.pathsep.join(current_paths)
from typing import Any
from ..core.config import AppConfig
from ..core.constants import VERSION
from ..cli.config import ConfigLoader
from ..cli.interactive.session import Context

logger = logging.getLogger(__name__)


class _ContextProxy:
    @property
    def _ctx(self) -> Context | None:
        import sys
        return getattr(sys, "_anicat_ctx", None)

    @_ctx.setter
    def _ctx(self, val: Any) -> None:
        import sys
        setattr(sys, "_anicat_ctx", val)

    def set(self, ctx: Context) -> None:
        self._ctx = ctx

    def is_initialized(self) -> bool:
        return self._ctx is not None

    def get_config(self) -> AppConfig:
        # If the runtime context isn't available, load the on-disk config
        # so callers can still read configuration safely during early startup.
        ctx_val = self._ctx
        if ctx_val is None:
            loader = ConfigLoader()
            return loader.load(allow_setup=False)
        return ctx_val.config

    def __getattr__(self, name) -> Any:
        # Allow safe access to `config` even before the interactive Context
        # has been created. This prevents endpoints and utilities that only
        # need read access from raising during early initialization.
        if name == "config":
            return self.get_config()
        ctx_val = self._ctx
        if ctx_val is None:
            raise RuntimeError("Anicat API context has not been initialized.")
        return getattr(ctx_val, name)

    def __setattr__(self, name, value):
        if name == "_ctx":
            import sys
            setattr(sys, "_anicat_ctx", value)
            return
        ctx_val = self._ctx
        if ctx_val is None:
            raise RuntimeError("Anicat API context has not been initialized.")
        setattr(ctx_val, name, value)


ctx = _ContextProxy()


def setup_logging():
    """Setup file logging for the sidecar."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s][sidecar][%(levelname)s] %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Stream handler (console)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    
    logger.info(f"Logging initialized at {LOG_FILE}")

def _cleanup_stale_resources():
    """Remove stale resources left by force-closed previous runs.

    - Orphaned MPV IPC sockets in /tmp
    - Stale playback status from the status router module
    """
    import glob

    # Clean up stale MPV IPC sockets
    for sock in glob.glob("/tmp/anicat-mpv-*.sock"):
        try:
            os.unlink(sock)
            logger.info(f"Cleaned up stale MPV socket: {sock}")
        except OSError:
            pass

    # Reset stale playback status so the NowPlaying bar doesn't show
    # a phantom episode from a previous session.
    try:
        from .routers.status import _clear_playback
        _clear_playback()
    except Exception:
        pass

    # Clear the "update in progress" flag. The new process has started.
    try:
        from anicat_media.core.constants import UPDATE_IN_PROGRESS_FILE
        if UPDATE_IN_PROGRESS_FILE.exists():
            UPDATE_IN_PROGRESS_FILE.unlink()
    except Exception:
        pass


def create_app(config: AppConfig | None = None) -> FastAPI:
    setup_logging()
    if config is None:
        loader = ConfigLoader()
        config = loader.load()

    ctx.set(Context(config))

    # --- Startup cleanup: remove stale resources from previous runs ---
    _cleanup_stale_resources()

    app = FastAPI(title="Anicat API", version=VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routers import (
        actions,
        config as config_router,
        media,
        notifications,
        queue,
        registry as registry_router,
        status,
        user,
    )

    app.include_router(media.router, prefix="/api/media", tags=["media"])
    app.include_router(user.router, prefix="/api/user", tags=["user"])
    app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
    app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
    app.include_router(config_router.router, prefix="/api/config", tags=["config"])
    app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(status.router, prefix="/api/status", tags=["status"])
    app.include_router(registry_router.router, prefix="/api/registry", tags=["registry"])

    api_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(api_dir))
    web_static_dir = os.path.join(api_dir, "static")
    web_out_dir = os.path.join(project_root, "web", "out")

    # Priority 1: Built static files in the api/static directory (Production/Installed)
    if os.path.exists(web_static_dir) and os.listdir(web_static_dir):
        app.mount("/", StaticFiles(directory=web_static_dir, html=True), name="static")

        @app.exception_handler(404)
        async def not_found_handler(request, exc):
            return FileResponse(os.path.join(web_static_dir, "index.html"))
            
    # Priority 2: Built files in the web/out directory (Development build)
    elif os.path.exists(web_out_dir) and os.listdir(web_out_dir):
        app.mount("/", StaticFiles(directory=web_out_dir, html=True), name="static")

        @app.exception_handler(404)
        async def dev_not_found_handler(request, exc):
            return FileResponse(os.path.join(web_out_dir, "index.html"))
            
    # Priority 3: No built files found
    else:
        @app.get("/")
        async def root():
            return {
                "status": "error", 
                "message": "Frontend not found. Please run './scripts/install.sh' or 'npm run build' in the 'web' folder.",
                "paths_checked": [web_static_dir, web_out_dir]
            }

    return app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=13370)
