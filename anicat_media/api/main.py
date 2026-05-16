import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from ..core.config import AppConfig
from ..cli.config import ConfigLoader
from ..cli.interactive.session import Context

logger = logging.getLogger(__name__)


class _ContextProxy:
    def __init__(self):
        self._ctx: Context | None = None

    def set(self, ctx: Context) -> None:
        self._ctx = ctx

    def __getattr__(self, name):
        if self._ctx is None:
            raise RuntimeError("Anicat API context has not been initialized.")
        return getattr(self._ctx, name)

    def __setattr__(self, name, value):
        if name == "_ctx":
            object.__setattr__(self, name, value)
            return
        if self._ctx is None:
            raise RuntimeError("Anicat API context has not been initialized.")
        setattr(self._ctx, name, value)


ctx = _ContextProxy()


def create_app(config: AppConfig | None = None) -> FastAPI:
    if config is None:
        loader = ConfigLoader()
        config = loader.load()

    ctx.set(Context(config))

    app = FastAPI(title="Anicat API", version="1.0.0")

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
