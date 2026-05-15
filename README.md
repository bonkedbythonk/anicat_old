# Anicat

Anicat is a specialized media companion for macOS, designed to streamline anime and manga management. It provides a centralized dashboard to stream content, track progress via AniList, and manage local reading with a minimalist, performance-first architecture.

Anicat is built on the foundations of the [Viu](https://github.com/viu-media/viu) project, refined for a native macOS experience with a focus on background persistence and ease of use.

![Anicat Dashboard](dashboard_preview.png)

## Architecture

Anicat is designed as a **Silent Background Service**. Once installed, the core engine (the "Brain") runs as a macOS LaunchAgent that starts automatically when you log in. The **Anicat Dashboard** app in your Applications folder acts as the interface to control this service.

This architecture allows Anicat to keep your AniList progress synced and your updates checked even when the dashboard window is closed.

## Quick Start

### Installation
Anicat can be installed via a single command. The installer manages all system dependencies (mpv, ffmpeg, chafa), sets up the background service, and creates the native App bundle.

```bash
curl -sSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install.sh | bash
```

### Usage
- **Open Dashboard**: Launch the **Anicat Dashboard** from your `/Applications` folder.
- **Login**: When prompted, connect your AniList account to enable real-time progress syncing.
- **Updates**: A visual indicator appears in the sidebar when an update is ready. Install it with one click from **Settings > Maintenance**.

## Key Features

- **macOS Native Integration**: Operates as a persistent background service with near-zero system impact.
- **High-Speed Manga Reader**: Integrated image proxying and local disk caching for instantaneous chapter navigation.
- **Advanced Playback**: Native MPV integration supporting custom shaders, multi-track audio, and subtitle selection.
- **AniList Sync**: Bi-directional progress tracking—Anicat updates AniList, and AniList updates Anicat.
- **Privacy First**: The service is bound exclusively to `127.0.0.1` (Localhost), ensuring complete isolation from your local network.

## Keyboard Shortcuts

### Video Player (MPV)
- `Space`: Play / Pause
- `F`: Toggle Fullscreen
- `Shift + N`: Skip to Next Episode
- `Shift + P`: Return to Previous Episode
- `Left / Right`: Seek backwards/forwards (5 seconds)
- `Up / Down`: Volume control
- `[` / `]`: Adjust playback speed
- `J`: Cycle through subtitles
- `#`: Cycle through audio tracks
- `Q`: Quit player and save progress

### Manga Reader
- `Left / Right`: Previous / Next page
- `F`: Toggle Fullscreen
- `S`: Single Page mode
- `D`: Double Page mode
- `V`: Vertical (Long-strip) mode
- `Esc`: Close reader

## Advanced Management

For power users, the `anicat` command provides direct control over the service:
- `anicat status`: Report health, version, and connectivity.
- `anicat stop`: Safely terminate all background services.
- `anicat dashboard`: Manually start the dashboard server.

---

Released under the [UNLICENSE](LICENSE). Developed for the macOS community.
