---
name: frontend-patterns
description: 'Work on the Anicat Next.js/React frontend (Tauri PWA). Covers "use client" rules, static export constraints, React Query conventions, custom hooks, component patterns, Tailwind v4. Use when: adding/modifying views, media components, hooks, API client, or UI state management.'
user-invocable: false
---

# Anicat Frontend Patterns

## When to Use
- Adding or modifying view components (Home, Search, Lists, etc.)
- Creating media components (MediaCard, MediaDetail, AnimePlayer, MangaReader)
- Working with hooks in `web/src/lib/`
- Modifying the API client in `web/src/lib/api.ts`
- Changing UI state management or data fetching
- Working with layout components (Sidebar, NowPlaying, Onboarding)
- Adding Tailwind CSS styling

## Critical Rules

### 1. Every Interactive Component Needs `"use client"`

The project uses Next.js **static export** (`output: 'export'` in [next.config.ts](../../web/next.config.ts)). There is **no SSR**, no `/app/api` routes. Every file with hooks, event handlers, or browser APIs must start with:

```tsx
"use client";
```

This applies to all components in `views/`, `media/`, `layout/`, `shared/`, and all hook files.

### 2. Default Exports for Components, Named Exports for Hooks/Utils

```tsx
// Components — default export
export default function SearchView({ onSelect }: SearchViewProps) { ... }

// Hooks — named export
export function useHealthPolling(): HealthPollingState { ... }

// API client — named export
export const mediaApi = { ... };
```

### 3. State Management: React Query + useState

| State Type | Pattern | Example |
|-----------|---------|---------|
| Server data | React Query (`@tanstack/react-query`) | `useQuery({ queryKey: ["home-trending"], queryFn: () => mediaApi.getTrending("ANIME") })` |
| UI state | `useState` in components | No Redux/Zustand |
| Cross-view refresh | `dispatchRefresh()` from [events.ts](../../web/src/lib/events.ts) | Triggers `CustomEvent` all views listen to |

React Query is configured in [Providers.tsx](../../web/src/components/Providers.tsx) with:
- `staleTime: 60000` (1 minute)
- `refetchOnWindowFocus: false`

### 4. API Client: Centralized in `web/src/lib/api.ts`

All backend requests go through the centralized [api.ts](../../web/src/lib/api.ts) module which exports `mediaApi` with 50+ typed methods. The base URL is always `http://127.0.0.1:13370/api`.

```tsx
import { mediaApi, type MediaItem } from "@/lib/api";

// Fetching
const data = await mediaApi.getTrending("ANIME");
const details = await mediaApi.getDetails(id);

// Mutations
await mediaApi.updateStatus(mediaId, "watching", 8.5, 12);
await mediaApi.playNext(mediaId);
```

### 5. Custom Hooks Live in `web/src/lib/`

All extracted hooks live in `web/src/lib/` and follow `useCamelCase` naming:

| Hook | Purpose |
|------|---------|
| `useHealthPolling` | Backend connection status, offline detection, live sync |
| `useTheme` | System + localStorage theme management |
| `useAmbientColor(bannerUrl)` | Canvas-based color extraction for glow effects |
| `useRemoteLogging` | WebView console → backend logging bridge |
| `useProgressEditor` | Inline progress editing state machine |
| `usePaginatedList<T>({ fetchFn, deps })` | Generic paginated list with load-more |
| `useKeyboardShortcuts` | Keyboard navigation (/, Escape, h, n, l, d, ?) |
| `useRefreshTrigger` | Listen for `dispatchRefresh()` custom events |

### 6. Shared Components Avoid Duplication

Common UI patterns are in `web/src/components/shared/`:

- **`MediaTypeToggle`** — Anime/Manga toggle button group. Used by SearchView, LibraryView, ListsView instead of duplicated JSX.
- **`InfiniteScroll`** — Intersection observer for pagination triggers.
- **`ErrorBanner`** — Reusable success/error messages.

When you notice the same JSX pattern appearing in 3+ views, extract it into a shared component.

### 7. Tailwind CSS v4

The project uses **Tailwind CSS v4** (PostCSS) — no `tailwind.config.js` file. Theme tokens are defined via CSS variables in the global stylesheet. Key utility classes:

```
text-accent          — accent color
bg-background        — page background
bg-foreground/10     — foreground with opacity
text-muted-foreground — secondary text
text-foreground      — primary text
border-border        — borders
```

Dark mode is automatic via `prefers-color-scheme: dark` media query, with a `class`-based override for user setting.

### 8. View Components: PascalCase + View Suffix

View files in `web/src/components/views/` follow a strict naming convention:

```
HomeView.tsx          — Dashboard with 5 parallel queries
SearchView.tsx        — Search with discovery, suggestions, filters
ListsView.tsx         — User lists (watching/completed/paused/dropped/planning)
LibraryView.tsx       — Completed library with pagination
DownloadsView.tsx     — Download queue (polls every 5s)
ProfileView.tsx       — AniList profile with stats
NotificationsView.tsx — Episode notifications
ScheduleView.tsx      — Airing schedule
SettingsView.tsx      — Config, theme, updates, registry
MangaView.tsx         — Manga discovery
```

### 9. AnimatePresence + Framer Motion

View transitions use `framer-motion`:

```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={activeView}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    transition={{ duration: 0.15, ease: "easeOut" }}
  >
    {renderView()}
  </motion.div>
</AnimatePresence>
```

Modals and drawers (MediaDetail, AnimePlayer, MangaReader) also use framer-motion with `animate={{ x: 0 }}` patterns.

### 10. Development Workflow

```bash
cd web
npm run dev          # Dev server → http://localhost:3000
npm run build        # Static export check
npm run lint         # ESLint
npm run test:e2e     # Playwright e2e tests
```
