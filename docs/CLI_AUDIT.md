# Anicat CLI Audit

**Date:** 2026-05-21
**Scope:** `anicat_media/cli/` — commands, interactive menus, services, selectors, utilities

---

## Architecture Overview

The CLI layer has three tiers:

```
cli/cli.py (Click entrypoint + LazyGroup)
  ├── cli/commands/     (12 CLI commands: search, download, dashboard, status, ...)
  ├── cli/interactive/   (TUI: session, context, state, menu/media/)
  └── cli/service/       (8 service classes: player, download, feedback, ...)
libs/selectors/          (FZF, Rofi, default selector abstraction)
libs/player/             (MPV integration)
cli/utils/               (13 utility modules)
```

---

## 1. CHANGE (Logic & Architecture)

### 1.1 Context Object Grows Unbounded (HIGH)

The `Context` dataclass in `cli/interactive/session.py` has **12 lazy-loaded services** plus config, data version, offline state, and a `Switch` toggle system. Every service is a private atttribute with a `@property` that returns `Any`:

```python
_provider: Optional[Any] = None
_selector: Optional["BaseSelector"] = None
_media_api: Optional["BaseApiClient"] = None
_download: Optional["DownloadService"] = None
...
```

**Problems:**
- No type safety — every property returns `Any`
- Service lifecycle is implicit — created on first access, cached forever
- The same pattern is repeated 12 times with subtle differences (provider re-creates on config change; others don't)
- Tests must mock `sys._anicat_ctx` globally

**Recommendation:** Extract a `ServiceContainer` class with explicit `register()` / `resolve()` methods. Each service gets a typed factory.

### 1.2 Duplicated `from .deps import get_ctx` Pattern (MEDIUM)

Every CLI command file does:
```python
from ..deps import get_ctx
ctx = get_ctx()
```

This is the same pattern used in the API layer. But the CLI doesn't use FastAPI's `Depends()` — it uses Click's `@click.pass_obj` for `AppConfig` and then manually calls `get_ctx()`.

**Recommendation:** Add a `click.make_pass_decorator`-style decorator that injects the Context so every command doesn't repeat the import:

```python
pass_context = click.make_pass_decorator(Context)

@click.command()
@pass_context
def search(ctx: Context, **options):
    provider = ctx.provider
```

### 1.3 Hardcoded Ports in CLI (MEDIUM)

`cli/commands/status.py` hardcodes `port = 13370`. `cli/commands/dashboard.py` has `default=13370`. These should use `LOCAL_API_PORT` from constants.

### 1.4 Duplicated Updater Logic (MEDIUM)

There are **three** separate update-check implementations:
- `api/routers/status.py` — `_check_github_update()` (the new, improved one)
- `cli/service/updater/service.py` — `UpdaterService.check_version()` (old, uses `LAST_COMMIT_FILE`)
- The CLI `status` command doesn't even use the updater service

**Recommendation:** Delete `cli/service/updater/service.py` and have the CLI use the same API endpoint (`/api/status/check-update`) or the same helper function.

### 1.5 `LazyGroup` — Clever but Fragile (LOW)

The `cli/utils/lazyloader.py` uses `importlib.import_module()` to lazy-load subcommands. This:
- Bypasses static analysis
- Uses string-based import paths (`"search.search"`)
- The `commands` dict in `cli.py` maps names to module paths — if a module moves, the CLI breaks silently

**Recommendation:** Replace with explicit imports or at minimum validate at import time.

---

## 2. IMPROVE (UX & Performance)

### 2.1 `status` Command Doesn't Use Rate-Limited Client (HIGH)

```python
response = httpx.get(url, timeout=2.0)
```

Uses raw `httpx.get()` without the rate limiter or the shared HTTP client. A standalone request that avoids all the GraphQL safeguards.

**Recommendation:** Use the same `execute_graphql` pipeline or at minimum the shared `httpx.Client`.

### 2.2 `dashboard` Command Starts uvicorn in Foreground (MEDIUM)

```python
uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)
```

This blocks the terminal — the user can't run other CLI commands while the dashboard is running. The Tauri app already handles this; the `dashboard` command is solely for development/debugging.

**Recommendation:** Add a `--daemon` flag that launches uvicorn in the background (using `subprocess.Popen`), printing the PID.

### 2.3 Image Preview Workers Are Complexity Without Payoff (MEDIUM)

`cli/utils/preview_workers.py` and `cli/utils/preview.py` together are ~500 lines implementing FZF preview rendering (images in terminal via `icat`/`feh`/`kitty`). This is solely for the `fzf` selector path.

**Recommendation:** Keep them (they work), but add a feature flag — they shouldn't load for the `default` selector.

### 2.4 Shell Completion Is Static (LOW)

`cli/utils/completion.py` uses `anime_titles_shell_complete()` which fetches from AniList on each tab press. No caching.

**Recommendation:** Add a 5-minute file-based cache for the title list.

### 2.5 `config` Command Could Be More Useful (LOW)

Currently `anicat config` opens the config file in a text editor. This is fine but could be much richer:
- `anicat config get stream.quality` — read a single value
- `anicat config set stream.quality 1080` — set a value
- `anicat config reset` — reset to defaults

---

## 3. ADD (Missing Features)

### 3.1 Subcommand Parity with API (HIGH)

The CLI has 12 commands but the API has 8 routers with ~30 endpoints. CLI subcommands that would be valuable:

| API Endpoint | Suggested CLI Command |
|--------------|----------------------|
| `GET /api/media/{id}` | `anicat details <id>` |
| `GET /api/media/{id}/episodes` | `anicat episodes <id>` |
| `POST /api/user/update` | `anicat track --episode 5 --status watching` |
| `GET /api/status/logs` | `anicat logs` |
| `GET /api/media/smart-playlist` | `anicat discover` |
| `POST /api/actions/play/{id}` | `anicat play <id> --episode 3` (already exists as `search` with `-r`) |

### 3.2 `anicat discover` / TUI Browse Mode (MEDIUM)

The interactive menu system (`cli/interactive/menu/media/`) already has ~15 menu states including `PROVIDER_SEARCH`, `EPISODES`, `SERVERS`, `MEDIA_ACTIONS`. This is a full TUI browser built on `InquirerPy`. It works but is hidden behind a development path.

**Recommendation:** Expose it as `anicat browse` or `anicat tui` — a discoverable entry point for the TUI mode.

### 3.3 Offline Mode Awareness (LOW)

The CLI has no offline detection. If the user is offline, every command that touches the network fails with an opaque error. Adding `--offline` flag support and a `anicat offline` command would help.

### 3.4 JSON Output for Scripting (LOW)

Most CLI commands output Rich-formatted text. Adding `--json` flag to key commands (status, search, config) would make the CLI scriptable.

---

## 4. REMOVE (Safe to Delete)

### 4.1 `cli/service/updater/service.py` — Entire File

This is a duplicate update checker that:
- Uses `LAST_COMMIT_FILE` (deprecated in favor of `COMMIT` in `_version.py`)
- Duplicates logic from `api/routers/status.py`
- Is not called from anywhere except possibly the TUI menu

**Delete it.** The API endpoint is the canonical source now.

### 4.2 `cli/utils/feh.py`

`feh` is a Linux image viewer. This module provides terminal image rendering for Linux. Not used on macOS at all.

### 4.3 `cli/utils/icat.py` — `PrefetchManager` Class

Image prefetching for FZF previews. Only used in the `fzf` selector path. If FZF selector is preserved, keep this. But the `PrefetchManager` is complex (threaded) for marginal gain.

### 4.4 `cli/commands/examples.py` — epilog Helpers

A 120-line file defining `epilog` strings for `--help` output. These are verbose Markdown-like ASCII art examples. Most users never see them.

**Recommendation:** Trim to 1-2 examples per command.

### 4.5 `cli/utils/ansi.py`

Contains ANSI escape codes for terminal colors. Most of this is already handled by `rich` (which is a dependency). This file duplicates `rich`'s functionality.

### 4.6 Redundant `TYPE_CHECKING` Import Blocks

Nearly every CLI command file has a massive `TYPE_CHECKING` block (20-40 lines) for type hints. This is technically correct but adds noise. Since the types are already inferred from Click decorators, many of these can be simplified.

---

## 5. Priority Matrix

### Fix Now

| # | Item | Effort |
|---|------|--------|
| 1 | Centralize port 13370 in CLI commands | 10 min |
| 2 | Delete `cli/service/updater/service.py` | 5 min |
| 3 | Add rate-limited client to `status` command | 15 min |
| 4 | Remove `cli/utils/feh.py` (Linux-only) | 1 min |
| 5 | Remove `cli/utils/ansi.py` (rich duplicates) | 1 min |

### Next Sprint

| # | Item | Effort |
|---|------|--------|
| 6 | Refactor Context to ServiceContainer | 2-3 hours |
| 7 | Add `anicat browse` / TUI entry point | 1 hour |
| 8 | Add JSON output flag to key commands | 1 hour |
| 9 | Trim `examples.py` epilogs | 30 min |
| 10 | Replace LazyGroup with explicit imports | 1 hour |

### Long Term

| # | Item | Effort |
|---|------|--------|
| 11 | CLI subcommand parity with API | 3-4 hours |
| 12 | Offline mode awareness | 1 hour |
| 13 | Shell completion caching | 30 min |
| 14 | `click.make_pass_decorator` for Context | 30 min |

---

## 6. File Manifest

### Keep (actively used)
```
cli/cli.py              — Entrypoint, LazyGroup setup
cli/options.py          — Pydantic → Click option generator (keeps CLI and config in sync)
cli/commands/dashboard.py — Dev dashboard launcher
cli/commands/search.py   — Quick search/play
cli/commands/download.py — Batch download
cli/commands/config.py   — Config editor
cli/commands/status.py   — Health check
cli/commands/stop.py     — Stop background service
cli/commands/worker.py   — Background worker control
cli/commands/login.py    — AniList auth
cli/commands/registry.py — Media registry management
cli/commands/queue/      — Download queue management
cli/interactive/         — TUI framework (keep for future `anicat browse`)
cli/service/             — Service layer (shared with API)
cli/config/              — Config loading (shared)
cli/utils/lazyloader.py  — Click lazy loading
cli/utils/completion.py  — Shell tab completion
cli/utils/preview.py     — FZF image previews
cli/utils/icat.py        — Terminal image rendering (keep PrefetchManager, it works)
cli/utils/image.py       — Image processing utilities
cli/utils/exception.py   — Exception handler setup
cli/utils/logging.py     — Logging setup
cli/utils/search.py      — Search helpers
cli/utils/parser.py      — Input parsing
```

### Delete (safe to remove)
```
cli/service/updater/service.py   — Duplicate update checker
cli/utils/feh.py                 — Linux-only image viewer
cli/utils/ansi.py                — Rich already provides this
```

### Trim
```
cli/commands/examples.py         — Reduce epilog strings to 1-2 per command
TYPE_CHECKING blocks             — Simplify in each command file
```
