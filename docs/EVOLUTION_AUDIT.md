# Anicat Project Evolution & Rationalization Audit

**Date:** 2026-05-21
**Scope:** Full-stack audit (Python backend + Next.js/React frontend + Tauri shell)
**Versions analyzed:** Up to 4.8.4

---

## 1. CHANGE (Logic & Architecture)

### 1.1 Service Locator Anti-Pattern (HIGH priority)

The `Context` class in `anicat_media/cli/interactive/session.py` uses a **Service Locator** pattern — every service is a lazily-loaded private field:

```python
@property
def provider(self) -> Any:
    config_key = f"{self.config.general.provider.value}"
    if not self._provider or self._provider_config_key != config_key:
        from ...libs.provider.anime.provider import create_anime_provider
        self._provider = create_anime_provider(...)
    return self._provider
```

This is repeated verbatim for `_media_api`, `_selector`, `_download`, `_feedback`, `_media_registry`, `_watch_history`, `_session`, `_auth`, `_player`, `_updater`, `_manga_provider` — **11 services** all using the same pattern.

**Problems:**
- No explicit dependency graph — circular dependencies are resolved by lazy imports scattered through property methods
- The `_ContextProxy` in `api/main.py` wraps this with `sys._anicat_ctx` (a global mutable variable on the `sys` module)
- Testing requires mocking `sys._anicat_ctx` or setting up the entire Context
- Each service's lifecycle is tied to first property access, not explicit initialization

**Recommendation:** Replace with a proper dependency injection container (e.g., FastAPI's built-in `Depends()` for API routes, or a lightweight container like `dependency-injector`). The `deps.py` already has `get_config()`, `get_media_api()`, `get_provider()` stubs — these are unused by the actual route handlers which still call `get_ctx()` directly.

### 1.2 Hardcoded Host:Port (HIGH priority)

`127.0.0.1:13370` is hardcoded in **6 locations**:

| File | Line | Usage |
|------|------|-------|
| `web/src/lib/api.ts` | 2 | `DEFAULT_API_BASE_ORIGIN` |
| `web/src/lib/useRemoteLogging.ts` | 41 | Log endpoint |
| `anicat_media/api/routers/actions.py` | 517 | Local file stream URL |
| `anicat_media/api/routers/actions.py` | 558, 612, 621 | HLS proxy URLs |

The frontend `DEFAULT_API_BASE_ORIGIN` is the only centralized one — the backend constructs these URLs manually without using a constant. If the port ever changes, it must be updated in 5 backend locations plus the frontend.

**Recommendation:** Move the port to `constants.py` (already exists) and use `LOCAL_API_PORT` or similar everywhere. The backend proxy URLs should reference this constant.

### 1.3 Hardcoded GitHub Username/Repo (MEDIUM priority)

`bonkedbythonk/anicat` is hardcoded in at least **9 locations**:

- 3 in `routers/status.py` (update check + trigger)
- 2 in `constants.py` (`AUTHOR`, `SUPPORT_PROJECT_URL`)
- 2 in `cli/service/updater/service.py`
- 2 in `cli/interactive/menu/media/main.py`

`AUTHOR` is already in `constants.py` but isn't used consistently. `GIT_REPO` is also defined but unused in the hardcoded URLs.

**Recommendation:** Build URLs from constants: `f"https://api.github.com/repos/{AUTHOR}/anicat/releases"`.

### 1.4 Frontend-Backend State Sync Conflicts (MEDIUM priority)

The `AppStateContext.tsx` holds `selectedItem`, `playingItem`, `readingItem` in React state, while the backend has its own `MediaRegistry` and `WatchHistory`. These can desync:

**Case 1: Download status.** The frontend shows `ep.is_downloaded = true` from a cached API response, but the backend's `MediaRegistry` has since deleted the file. No invalidation event is sent.

**Case 2: Progress after close.** When the user closes the AnimePlayer, `trackPlayback` is called but the response is not awaited for the `completed` flag. If the backend marks the episode as completed AFTER the frontend unmounts the player, the detail page won't reflect the update until the next health poll cycle.

**Case 3: AniList sync failure.** If `update_list_entry` fails on the backend (rate limit, token expiry), the backend silently catches the error and returns `synced: false`. The frontend ignores this field entirely — it assumes the update succeeded.

**Recommendation:**
- Add an optimistic update + rollback pattern for AniList mutations
- Surface `synced: false` in the UI ("Sync Pending" indicator)
- Add a download status invalidation event

### 1.5 Dynamic Import Anti-Pattern (LOW priority)

The provider factory (`anicat_media/libs/provider/anime/provider.py`) uses `importlib.import_module()` to dynamically load provider classes. This:
- Bypasses static analysis (pyright can't verify the import)
- Breaks PyInstaller's module detection
- Makes it impossible to tree-shake unused providers

The `PROVIDERS_AVAILABLE` dict maps string names to import paths, duplicating the already-existing directory structure.

**Recommendation:** Replace with explicit imports. There are only 6 providers — a `match/case` or `if/elif` chain is simpler and more robust.

---

## 2. IMPROVE (Performance & UX)

### 2.1 Missing Async Provider Scraping (HIGH priority)

The entire provider layer uses **synchronous `httpx.Client`** for HTTP requests. The `BaseAnimeProvider` class takes a `client: "Client"` (synchronous). Despite the backend being FastAPI (async-native), all network I/O in providers blocks the event loop:

```
FastAPI route → get_ctx() → ctx.provider.get() → httpx.Client.get()  [BLOCKING]
```

**Impact:** A single anime episode resolution makes 3-5 sequential HTTP calls (search → get → episode_streams). Each blocks the FastAPI worker for the entire chain. With `uvicorn` running a single worker, all other requests wait.

**Recommendation:** Convert providers to `httpx.AsyncClient` and make all provider methods `async`. FastAPI auto-detects `async def` route handlers and uses the event loop.

### 2.2 Frontend Re-render Optimization (MEDIUM priority)

Every view component in `web/src/components/views/` re-renders on parent state changes even when their own props haven't changed. None of them use `React.memo`.

**Specific hot spots:**
- `MediaRow` renders 6-10 `MediaCard` items per row — each card re-renders on parent scroll
- `SettingsView` has 5 tabs, each containing form controls — all tabs re-render when any field changes (auto-save debounce fires every 800ms)
- `Hero` component re-evaluates `ambientColor` on every banner hover despite `useAmbientColor` caching

**Recommendation:**
- Wrap pure display components in `React.memo`: `Hero`, `MediaCard`, `MediaRow`, `MediaTypeToggle`, `InfiniteScroll`
- Move tab state in `SettingsView` to separate tab components so auto-save doesn't trigger full re-render of other tabs
- Use `useDeferredValue` for search input in `SearchView`

### 2.3 macOS Native Feel (MEDIUM priority)

The current UI is a dark-themed web app. To feel native on macOS:

**Current gaps:**
- No `.DS_Store` native window chrome integration (Tauri's `titleBarStyle: 'overlay'` is not configured)
- Scrollbars use `scrollbar-hide` (custom CSS) instead of macOS overlay scrollbars
- No `backdrop-filter` blur for sidebar/content areas (macOS vibrancy)
- `framer-motion` animations are web-like (ease-based), not macOS-like (spring physics with high damping)
- No `cmd+,` shortcut for Settings, no `cmd+f` for search, no `cmd+w` to close detail panels

**Recommendation:**
- Set `"titleBarStyle": "overlay"` in `tauri.conf.json` for traffic-light button alignment
- Add `backdrop-filter: blur(40px) saturate(180%)` to `.sidebar` and `.now-playing`
- Change framer-motion transitions to spring physics: `type: "spring", stiffness: 400, damping: 40`
- Add keyboard shortcuts: `cmd+,` → Settings, `cmd+f` → Search, `esc` already handled

### 2.4 ThreadPoolExecutor Underutilized (LOW priority)

`core/utils/concurrency.py` provides a full `ThreadManager` class with cancellation, task queueing, and lifecycle control — but it's only used for downloads. Provider scraping is synchronous (blocking the event loop).

**Recommendation:** Either convert providers to async (preferred) or use the existing `ThreadManager` to offload blocking HTTP calls to a thread pool, preventing event loop blockage.

---

## 3. ADD (The 'Premium' Gap)

### 3.1 Continue Watching Tray / Mini-player (HIGH impact)

The current "Now Playing" bar at the bottom shows playback state but doesn't allow **quick resume** from the sidebar or a tray icon. Users must navigate to the detail page → click Play.

**Recommendation based on data structures:**
- `watch_history` already stores `(media_id, episode, stop_time)` per entry
- Add a "Continue Watching" sidebar section with poster + progress bar
- Add a macOS menu bar item showing currently playing media
- Single-click resume from anywhere in the app

### 3.2 Offline-First Mode (MEDIUM impact)

Downloads work but there's no **offline-aware UI** — no indication which content is available offline, no automatic fallback to local files when the network drops.

**Recommendation:**
- Add an offline badge to downloaded episodes in the episode list
- Show "Watch Offline" vs "Stream" based on download status
- Auto-detect network state (Tauri provides `navigator.onLine` + system events)

### 3.3 Keyboard-Native TUI Navigation (LOW impact, high passion)

The app was originally a CLI (Click + InquirerPy + Rich). The TUI code still exists in `cli/interactive/` but isn't integrated with the macOS GUI. For TUI lovers:

**Recommendation:**
- Add a `cmd+k` command palette (like VS Code / Spotlight) for quick actions
- Make the search bar auto-focus on `cmd+f`
- Add `j/k` (vim-style) navigation in lists

### 3.4 Killer Feature: Smart Playlists (Auto-DJ)

Based on the existing data structures (`MediaRegistry` with genres, scores, watch history), a "Smart Playlist" feature could:
- Generate a queue of unwatched episodes from your watching list
- Mix in recommendations from AniList based on your high-rated shows
- Auto-download the next episode while you're watching the current one
- "Shuffle" mode: play a random episode from your plan-to-watch list

This leverages the existing `media_registry`, `watch_history`, `media_api.getRecommendations()`, and download queue infrastructure.

---

## 4. REMOVE (Dead Wood)

### 4.1 Ghost Code — Viu Fork Remnants

These features exist in the codebase but serve no purpose for a macOS desktop media hub:

| Item | Location | Why Remove |
|------|----------|------------|
| **Syncplay** | `player/mpv/player.py:202-203`, `_stream_on_desktop_with_syncplay()` | Synchronized watching with friends — requires external syncplay server, never used in macOS app |
| **Webtorrent** | `player/mpv/player.py:200-201`, `_stream_on_desktop_with_webtorrent_cli()` | Torrent streaming — requires `webtorrent` CLI, irrelevant for hosted anime streaming |
| **Termux / Mobile** | `player/mpv/player.py:134-139`, `_play_on_mobile()` | Android Termux detection — macOS-only app |
| **TORRENT_REGEX / YOUTUBE_REGEX** | `core/patterns.py` (entire file) | Only used by the syncplay/webtorrent/mobile paths above |
| **`torrents` optional dep** | `pyproject.toml` line 63: `torrent = ["libtorrent>=2.0.11"]` | No user of a macOS anime app uses torrents for streaming |
| **FzfConfig / RofiConfig** | `core/config/infrastructure.py:19-62` | TUI selectors — the macOS app uses the React frontend, not fzf/rofi |
| **Rofi themes** | `assets/defaults/rofi_*` files | TUI-only assets |
| **`inquirerpy`** | `pyproject.toml` dep | TUI input library — only used by CLI, not the macOS app |
| **`rich`** | `pyproject.toml` dep | Terminal output formatting — useful for CLI but pulled in as a heavy dependency for the full app |

### 4.2 Redundant Dependencies

| Dependency | Why Remove | Size Impact |
|------------|------------|-------------|
| `requests>=2.33.1` | `httpx>=0.28.1` is already used everywhere. `requests` adds no capability that `httpx` doesn't provide | ~500KB |
| `pyinstaller>=6.17.0` | Should be a dev dependency, not a runtime dependency. It's only used during CI build | ~30MB (runtime bloat) |
| `pillow>=12.2.0` | Check usage — if only for icon processing during build, move to dev deps | ~4MB |
| `pypresence>=4.3.0` | Discord RPC — optional, should be in `optional-dependencies` only (it already is under `discord`) but check if imported unconditionally | ~200KB |
| `http-server` (npm) | Only used for e2e tests — should be a devDependency (it already IS a devDependency, keep) | N/A |

### 4.3 Dead Provider Directories

| Directory | Status |
|-----------|--------|
| `libs/provider/anime/allanime/` | Listed in `PROVIDERS_AVAILABLE` but domain likely dead or unreliable |
| `libs/provider/anime/allmanga/` | Listed but not functional — commented out in types.py |
| `libs/provider/anime/hianime/` | Listed as fallback, verify if still functional |
| `libs/provider/manga/mangadex/` | Listed but `mangakatana` is the only enabled provider |

**Recommendation:** Test each provider, remove broken ones, remove commented-out code in `types.py`.

### 4.4 Files Safe to Delete Right Now

```
anicat_media/core/patterns.py                          # TORRENT_REGEX, YOUTUBE_REGEX — only used by dead paths
anicat_media/core/downloader/torrents.py                # Torrent download support (never used)
anicat_media/core/config/infrastructure.py              # Lines 19-62: FzfConfig + RofiConfig classes
anicat_media/core/config/infrastructure.py              # Lines 77-82: MpvConfig pre_args default
assets/defaults/rofi_*                                  # Rofi TUI theme files
assets/defaults/fzf_opts                                # FZF TUI options (if not used by GUI)
```

After removing the syncplay/webtorrent/mobile player code from `player/mpv/player.py`, also delete the corresponding test files:
```
tests/play/test_syncplay.py (if exists)
tests/play/test_torrents.py (if exists)
```

---

## 5. Priority Matrix

### Fix Now (High Impact / Low Effort)

| # | Item | Effort |
|---|------|--------|
| 1 | **Centralize port 13370** into `constants.py` constant + use everywhere | 30 min |
| 2 | **Move `pyinstaller` to dev deps** in `pyproject.toml` | 5 min |
| 3 | **Remove dead files** (patterns.py, torrents.py, rofi defaults) | 10 min |
| 4 | **Replace dynamic imports** in provider factory with explicit `if/elif` | 30 min |
| 5 | **Wrap Hero, MediaCard, MediaRow in `React.memo`** | 20 min |
| 6 | **Add `titleBarStyle: overlay`** to `tauri.conf.json` | 5 min |

### Next Sprint (Medium Effort / Medium Impact)

| # | Item | Effort |
|---|------|--------|
| 7 | **Convert providers to async** (`httpx.AsyncClient` + `async def`) | 3-4 hours |
| 8 | **Refactor Context to DI container** (use FastAPI `Depends()` properly) | 2-3 hours |
| 9 | **Add offline-aware UI** (download badge, network detection) | 2 hours |
| 10 | **Add `React.memo` + tab isolation** for SettingsView | 1 hour |
| 11 | **Remove syncplay/webtorrent/mobile from player.py** | 30 min |
| 12 | **Add `cmd+k` command palette** | 2 hours |

### Long Term (Strategic Improvements)

| # | Item | Effort |
|---|------|--------|
| 13 | **Smart Playlists / Auto-DJ** feature | 1-2 weeks |
| 14 | **Offline-first mode** with service worker | 1 week |
| 15 | **macOS menu bar app** with Now Playing controls | 3-4 days |
| 16 | **Build URLs from constants** (AUTHOR, GIT_REPO) across the codebase | 1 hour |
| 17 | **Add AniList sync failure indicator** in the UI | 1-2 hours |

---

## 6. Summary Stats

| Metric | Count |
|--------|-------|
| Hardcoded URLs/ports | **15 instances** across 6 files |
| Service Locator lazy properties | **11 services** in Context |
| Dead viu features (syncplay, webtorrent, mobile, torrent) | **4 code paths** + 1 entire module |
| Redundant/unnecessary deps | **4 packages** (requests, pyinstaller, inquirerpy, rich) |
| Providers with questionable status | **3** (allanime, allmanga, hianime) |
| Missing `React.memo` on pure components | **5+ components** |
| Sync conflict points | **3 identified** |
| Config models for unused features | **2** (FzfConfig, RofiConfig) |
