# Anicat — AI Agent Quickstart

> **Anicat** is a full-stack anime/manga media hub: Python FastAPI backend + Next.js/React PWA frontend, bundled as a Tauri macOS desktop app.

---

## Global Behavior

- **No emojis.** The agent does not generate standard emojis (like :smile:, :rocket:, :fire:, etc.) in chat responses, code comments, commit messages, or any output. Use plain text labels instead.

---

## Quick Commands

| Task | Command |
|------|---------|
| Install Python deps | `uv sync --dev --all-extras` |
| Python type-check | `uv run pyright` |
| Python format/lint | `uv run ruff format . && uv run ruff check .` |
| Python tests | `uv run pytest` (add `-m "not integration"` to skip network tests) |
| Frontend dev server | `cd web && npm run dev` (→ localhost:3000) |
| Bump version | Auto-bumps on `git commit` via `.githooks/pre-commit` (see below) |
| Frontend build | `cd web && npm run build` |
| Frontend lint | `cd web && npm run lint` |

---

## Architecture

```
anicat/                        # Python backend (FastAPI + Click CLI)
├── anicat_media/
│   ├── api/                   # HTTP layer — routers, static files
│   │   ├── main.py            # FastAPI app, global `ctx` singleton
│   │   ├── deps.py            # Centralized `get_ctx()` dependency
│   │   └── routers/           # 8 routers (actions, config, media, …)
│   ├── cli/                   # CLI layer — Click commands, interactive TUI
│   │   ├── cli.py             # Click entrypoint
│   │   ├── interactive/       # Context service container, menu system
│   │   ├── service/           # 8 service classes (Download, Player, …)
│   │   └── config/            # Config loading
│   ├── core/                  # Business logic
│   │   ├── config/model.py    # Pydantic config models (~500 lines)
│   │   ├── downloader/        # Download abstraction (factory + strategy)
│   │   └── storage/           # Media registry, watch history
│   ├── libs/                  # Adapter layer
│   │   ├── media_api/         # AniList / media API abstraction
│   │   ├── provider/          # Streaming provider abstraction
│   │   └── player/            # MPV / built-in player abstraction
│   └── utils/                 # Shared utilities

web/                           # Next.js 16 + React 19 frontend (Tauri PWA)
├── src/
│   ├── app/page.tsx           # Root component — view routing, health polling
│   ├── components/
│   │   ├── views/             # 10 view components (Home, Search, Lists, …)
│   │   ├── media/             # Media detail, player, reader
│   │   ├── layout/            # Sidebar, NowPlaying, Onboarding
│   │   └── shared/            # Shared UI (InfiniteScroll, MediaTypeToggle, …)
│   └── lib/                   # Hooks, API client, events, date utils
│       └── api.ts             # Centralized API client (50+ endpoints → backend)
└── src-tauri/                 # Tauri native shell
```

See [README.md](README.md) for user-facing docs.

---

---

## Versioning (Auto-Bump via Git Hook)

A `pre-commit` hook at `.githooks/pre-commit` auto-bumps the version
when you commit with [conventional commits](https://www.conventionalcommits.org/):

| Commit prefix | Bump | Example |
|---------------|------|---------|
| `fix:` | PATCH (4.0.0 → 4.0.1) | `git commit -m "fix: typo in search"` |
| `feat:` | MINOR (4.0.0 → 4.1.0) | `git commit -m "feat: add mal sync"` |
| `feat!:`, `fix!:`, `BREAKING CHANGE:` | MAJOR (4.0.0 → 5.0.0) | `git commit -m "feat!: rewrite player"` |

Hook updates 5 files: `version.txt`, `pyproject.toml`, `web/package.json`,
`web/src-tauri/tauri.conf.json`, `flake.nix`. The hook is activated by
`git config core.hooksPath .githooks` (already set). If no prefix matches,
no bump occurs.

## Critical Rules

### 0. Always use conventional commits (auto-bump hook)

Every `git commit` message **must** use the conventional commits format.
The `.githooks/pre-commit` hook reads the first line to auto-bump
the version — if you use a generic message like `"updated stuff"`, no bump
happens and the version stays stale.

| Change type | Commit message | Bump |
|---|---|---|
| Bug fix | `git commit -m "fix: correct continue watching filter"` | PATCH (4.0.0 -> 4.0.1) |
| New feature | `git commit -m "feat: add mal sync"` | MINOR (4.0.0 -> 4.1.0) |
| Breaking change | `git commit -m "feat!: rewrite player in rust"` | MAJOR (4.0.0 -> 5.0.0) |
| Refactor/docs/chore | `git commit -m "refactor: clean up imports"` | No bump |

### 1. Backend: Context access via `get_ctx()`

**Never instantiate `Context()` directly.** The app stores a single `Context` in `sys._anicat_ctx`. Always access it through the centralized dependency:

```python
from anicat_media.api.deps import get_ctx

ctx = get_ctx()
```

The `Context` provides lazy-loaded access to 12 services (media_api, provider, download, player, etc.). See [anicat_media/api/deps.py](anicat_media/api/deps.py).

### 2. Frontend: Every interactive component needs `"use client"`

The project uses Next.js **static export** (`output: 'export'` in [web/next.config.ts](web/next.config.ts)). There is **no SSR**, no `/app/api` routes. All data flows client-side via React Query to `http://127.0.0.1:13370/api`. Every file with hooks, event handlers, or browser APIs must start with:

```tsx
"use client";
```

### 3. Backend: Lazy imports prevent circular dependencies

Python relative imports use the package name `anicat_media` as root. When circular imports would occur, use a **lazy import inside a function body**:

```python
def get_ctx():
    from ..main import ctx  # noqa: PLC0415
    return ctx
```

Don't promote these to module-level — they exist deliberately to break import cycles.

### 4. Frontend: Default exports for components, named exports for hooks/utils

```tsx
// Components → default export
export default function SearchView({ onSelect }: SearchViewProps) { … }

// Hooks/utils → named export
export function useHealthPolling(): HealthPollingState { … }
export const mediaApi = { … };
```

### 5. Python: Platform guards for optional deps

Optional dependencies (pyobjc, dbus-python) may not be installed. Always guard:

```python
if sys.platform == "darwin":
    import pyobjc  # noqa: PLC0415
```

### 6. Frontend state management

- **Server data** → React Query (`@tanstack/react-query`) with 60s stale time. See [web/src/app/Providers.tsx](web/src/app/Providers.tsx).
- **UI state** → `useState` in components (no Redux/Zustand).
- **Cross-view refresh** → `dispatchRefresh()` from [web/src/lib/events.ts](web/src/lib/events.ts).
- **Shared hooks** live in `web/src/lib/` (`useHealthPolling`, `useAmbientColor`, `usePaginatedList`, `useProgressEditor`, `useRemoteLogging`, `useTheme`, `useKeyboardShortcuts`).

---

## File Naming

| Layer | Convention | Examples |
|-------|-----------|----------|
| Python modules | `snake_case` | `media_api.py`, `watch_history.py` |
| Python classes | `PascalCase` | `AppConfig`, `BaseAnimeProvider` |
| Python constants | `UPPER_SNAKE` | `VERSION`, `LOG_FILE` |
| React components | `PascalCase` files, default exports | `MediaCard.tsx`, `Sidebar.tsx` |
| React hooks | `useCamelCase` files, named exports | `useHealthPolling.ts` |
| Shared UI | `PascalCase` in `shared/` | `InfiniteScroll.tsx` |
| Views | `PascalCase` + `View` suffix in `views/` | `HomeView.tsx` |

---

## Testing

```bash
# All tests (skip network-dependent ones if offline)
uv run pytest -m "not integration"

# Integration tests only
uv run pytest -m integration

# Frontend e2e
cd web && npm run test:e2e
```

Tests live in `tests/` mirroring the source structure. Use `@pytest.mark.integration` for tests that need live network. See [tox.ini](tox.ini) and [pyproject.toml](pyproject.toml) for config.

---

## Key Documentation

- [README.md](README.md) — Project overview, installation, user guide
- [DISCLAIMER.md](DISCLAIMER.md) — Legal disclaimer
- [MPV_GUIDE.md](MPV_GUIDE.md) — MPV player configuration
- [SECURITY.md](SECURITY.md) — Security policy
- [web/README.md](web/README.md) — Frontend-specific (boilerplate, low value)

## Domain Skills

These skills load automatically when you work in a relevant area:

- [`.github/skills/backend-patterns/`](.github/skills/backend-patterns/SKILL.md) — Python backend: context injection, lazy imports, platform guards, config models, provider adapters. Triggered by changes to `anicat_media/` files.
- [`.github/skills/frontend-patterns/`](.github/skills/frontend-patterns/SKILL.md) — Next.js/React frontend: "use client" rules, React Query, custom hooks, shared components, Tailwind v4. Triggered by changes to `web/src/` files.
