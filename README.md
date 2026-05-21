# Anicat

![Anicat Desktop](assets/branding/dashboard.png)

**Premium Anime & Manga Experience for macOS.**

Anicat is a high-performance, native media hub for searching, streaming, and tracking anime and manga. Features a full macOS desktop app (Tauri) and a blazing-fast terminal CLI.

---

## Getting Started

### 1. The Native macOS App (Recommended)
Sits in your Dock, manages the background server, looks native.

#### Easy Installation
```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/master/scripts/install_macos.sh | bash
```

#### Nightly Build
```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/master/scripts/install_macos.sh | sed 's/releases\/latest/releases\/tags\/nightly/g' | bash
```

#### Manual Installation
Download the `.dmg` from [Releases](https://github.com/bonkedbythonk/anicat/releases), mount it, drag to `/Applications`.

---

### 2. The CLI / Terminal (One Command)
Install the `anicat` CLI command globally — works on macOS, Linux, Windows:
```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/master/scripts/install_cli.sh | bash
```
After installation, `anicat` is available everywhere. Runs all 16 commands for streaming, tracking, downloading, and discovery. The installer automatically installs `uv` if needed.

---

### 3. Playback Options

**Built-in Player:** Works out of the box in the GUI app.

**MPV Companion (Bundled):** The macOS installer bundles MPV with the ModernZ skin, Anime4K upscaling shaders, and Outfit typography — zero configuration. The in-app player includes skip-intro/outro overlay with auto-skip support from AniSkip crowdsourced timings.


---

## Features
- **AniList Sync** — Real-time progress tracking for anime and manga
- **Smart Playlist** — Personalized recommendations from your watching list
- **Smart Scrapers** — AnimePahe, AniZone, GogoAnime, HiAnime providers with automatic fallback
- **One-Click Updates** — In-app update mechanism, no terminal needed
- **Persistent Background Engine** — Dedicated sidecar keeps the server alive
- **Real-Time Data Sync** — Instant UI updates via TanStack Query + data_version polling
- **Airing Schedules** — Live countdowns for currently releasing series
- **Rate-Limited API Client** — Automatic 700ms throttling and 429 backoff for AniList GraphQL
- **Terminal TUI** — Full interactive browser (`anicat anilist`) with FZF, image previews
- **macOS Native** — Tauri v2, title bar overlay, traffic-light buttons

---

## Legal
Anicat is for educational and personal use only. See [DISCLAIMER.md](DISCLAIMER.md) and [SECURITY.md](SECURITY.md).

## License
MIT
