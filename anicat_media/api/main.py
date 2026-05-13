import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from ..cli.config import ConfigLoader
from ..cli.interactive.session import Context

logger = logging.getLogger(__name__)

# Initialize Anicat Context
loader = ConfigLoader()
config = loader.load()
ctx = Context(config)

app = FastAPI(title="Anicat API", version="1.0.0")

# Setup CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .routers import media, user, actions, queue, config as config_router
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
app.include_router(config_router.router, prefix="/api/config", tags=["config"])

# Serve Static Frontend Files
# Path to the 'web/out' directory relative to the package
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_OUT_DIR = os.path.join(BASE_DIR, "web", "out")

if os.path.exists(WEB_OUT_DIR):
    app.mount("/", StaticFiles(directory=WEB_OUT_DIR, html=True), name="static")
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return FileResponse(os.path.join(WEB_OUT_DIR, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"status": "ok", "message": "API is running, but frontend is not built. Run 'npm run build' in 'web' folder."}
