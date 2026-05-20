---
name: backend-patterns
description: 'Work on the Anicat Python backend (FastAPI + Click CLI). Covers context injection, lazy imports, platform guards, config models, provider adapters. Use when: adding/modifying API routes, CLI commands, core logic, providers, downloaders, or config models.'
user-invocable: false
---

# Anicat Backend Patterns

## When to Use
- Adding or modifying FastAPI routes
- Creating or modifying Click CLI commands
- Working with core business logic (config, downloader, storage)
- Modifying or adding streaming/media API providers
- Changing Pydantic config models
- Working with the Context service container

## Critical Rules

### 1. Context Access: Always use `get_ctx()`

Never instantiate `Context()` directly. The app stores a single `Context` in `sys._anicat_ctx` via the `_ContextProxy` in [api/main.py](../../anicat_media/api/main.py). Access it through the centralized dependency:

```python
from anicat_media.api.deps import get_ctx

ctx = get_ctx()
ctx.media_api.get_media_item(42)       # lazy-loaded AniList API
ctx.provider.get_anime_episode(42, 1)  # streaming provider
ctx.player.play(...)                    # MPV / built-in player
```

The `Context` class lives in [cli/interactive/session.py](../../anicat_media/cli/interactive/session.py) and provides 12+ lazy-loaded services: `media_api`, `provider`, `manga_provider`, `selector`, `download`, `feedback`, `media_registry`, `watch_history`, `session`, `auth`, `player`, `updater`.

### 2. Lazy Imports for Circular Dependencies

The `anicat_media` package uses **lazy imports inside function bodies** to break circular dependency chains. Do NOT promote these to module-level imports:

```python
# OK — lazy import inside function body
def get_ctx():
    from ..main import ctx  # noqa: PLC0415
    return ctx

# OK — lazy import in data migration
def _migrate_config(path: Path):
    from ..core.config.model import AppConfig  # noqa: PLC0415
    ...
```

The `# noqa: PLC0415` suppression is intentional — it silences Pyright's "import outside module level" warning.

### 3. Platform Guards for Optional Dependencies

Optional platform-specific deps (pyobjc, dbus-python, pypiwin32) may not be installed. Always guard:

```python
if sys.platform == "darwin":
    import pyobjc  # noqa: PLC0415

if sys.platform.startswith("win"):
    import pypiwin32  # noqa: PLC0415
```

On macOS the server also patches `PATH` at startup to ensure Homebrew tools are found. See [api/main.py](../../anicat_media/api/main.py#L11-L24).

### 4. API Router: Internal Functions Stay Private

Each router file in [api/routers/](../../anicat_media/api/routers/) exports a `router = APIRouter()` and keeps helper functions as module-level privates (prefixed with `_`):

```python
router = APIRouter()

def _resolve_episode_stream(media_id: int, episode: Optional[str] = None):
    """Shared helper — not exposed as a route."""
    ctx = get_ctx()
    ...
```

### 5. Pydantic Config Model Structure

The config lives in [core/config/model.py](../../anicat_media/core/config/model.py) (~500 lines, 12+ nested classes, 200+ fields). Key patterns:

```python
class BaseConfig(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def expand_path(cls, v, info):
        """Auto-expand ~ in any string config field."""
        if isinstance(v, str) and "~" in v:
            return Path(v).expanduser()
        return v

class StreamConfig(BaseConfig):
    preferred_server: Optional[ProviderServer] = Field(default=None)
    ...

class AppConfig(BaseConfig):
    general: GeneralConfig
    stream: StreamConfig
    ...
```

Config loading is handled by `ConfigLoader` in [cli/config/](../../anicat_media/cli/config/). Use `ctx.config` to access the loaded config at runtime.

### 6. FastAPI Routers: Thin HTTP Layer

Routers should be thin — delegate complex orchestration to service classes in [cli/service/](../../anicat_media/cli/service/):

```python
@router.get("/")
async def get_config():
    ctx = get_ctx()
    return ctx.config.model_dump(mode="json")
```

For endpoints that need streaming responses, use `StreamingResponse` from FastAPI:

```python
from fastapi.responses import StreamingResponse
return StreamingResponse(stream_generator(), media_type="video/mp4")
```

### 7. CLI Commands: Lazy-Loaded Click Groups

CLI subcommands are lazily loaded in [cli/cli.py](../../anicat_media/cli/cli.py):

```python
commands = {
    "config": "config.config",
    "search": "search.search",
    ...
}
```

Each command module is a Click group with Click options. Use `click.option` decorators for CLI arguments.

### 8. Provider Adapter Pattern

Streaming providers follow the adapter pattern in [libs/provider/](../../anicat_media/libs/provider/). Each provider implements a `BaseAnimeProvider` interface:

```python
class BaseAnimeProvider(ABC):
    @abstractmethod
    def search(self, query: str) -> SearchResult: ...
    @abstractmethod
    def get_episodes(self, url: str) -> list[EpisodeInfo]: ...
```

There's a provider factory that selects the right provider based on config. New providers should extend `BaseAnimeProvider`.

### 9. Downloader: Factory + Strategy

Downloads use a factory pattern in [core/downloader/](../../anicat_media/core/downloader/):

```python
class DownloadFactory:
    @staticmethod
    def create(config: AppConfig) -> BaseDownloader:
        if downloader_name == "yt-dlp":
            return YtDLPDownloader(config)
        return DefaultDownloader(config)
```

### 10. Testing

- Tests live in `tests/` mirroring source structure
- Use `pytest` with `pytest-httpx` for HTTP mocking
- Mark network-dependent tests with `@pytest.mark.integration`
- Run: `uv run pytest -m "not integration"` to skip network tests
- Run: `uv run pytest -m integration` for integration-only
