# Anicat

Anicat is a specialized media companion for macOS, designed to streamline anime and manga management. It provides a centralized dashboard to stream content, track progress via AniList, and manage local reading with a minimalist, performance-first architecture.

Anicat is built on the foundations of the [Viu](https://github.com/viu-media/viu) project, refined for a native macOS experience with a focus on background persistence and ease of use.

![Anicat Dashboard](assets/branding/dashboard_preview.png)

## Architecture

Anicat is designed as a **Silent Background Service**. Once installed, the core engine (the "Brain") runs as a macOS LaunchAgent that starts automatically when you log in. The **Anicat Dashboard** app in your Applications folder acts as the interface to control this service.

This architecture allows Anicat to keep your AniList progress synced and your updates checked even when the dashboard window is closed.

## Installation

Anicat is installed using a single command that handles everything for you automatically. If you have never used the Terminal before, just follow these simple steps:

1. **Open the Terminal**: Press the **Command** key and the **Spacebar** on your keyboard at the same time. Type "Terminal" into the search box that appears and press **Enter**.
2. **Paste the Command**: Copy the entire line of text below and paste it into the Terminal window:
   ```bash
   curl -sSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install.sh | bash
   ```
3. **Press Enter**: Hit the **Enter** key on your keyboard.
4. **Wait for Completion**: The installer will set up everything for you. This may take a minute. Once it is finished, you can close the Terminal.

You will now find the **Anicat Dashboard** app waiting for you in your **Applications** folder.

### Usage
- **Open Dashboard**: Launch the **Anicat Dashboard** from your `/Applications` folder.
- **Native Experience (PWA)**: For a cleaner interface without browser tabs, you can install Anicat as a standalone app:
  - **Safari**: Go to File > Add to Dock.
  - **Chrome**: Go to the three-dot menu > Save and Share > Install page as app.
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

## Privacy & Security

Anicat is built with a local-first philosophy to ensure total user privacy:
- **Zero Telemetry**: The application does not collect or transmit analytics, usage data, or tracking information.
- **Local-Only Access**: The backend service is bound to `127.0.0.1` (Localhost), making it inaccessible to other devices on your network.
- **On-Device Storage**: All configuration, login tokens, and history are stored locally in `~/Library/Application Support/anicat`.
- **Open Source**: The code is fully transparent and available for audit under the [UNLICENSE](LICENSE).

## Advanced Management

For power users, the `anicat` command provides direct control over the service:
- `anicat status`: Report health, version, and connectivity.
- `anicat stop`: Safely terminate all background services.
- `anicat dashboard`: Manually start the dashboard server.

---

---

## Disclaimer

Anicat is a media API client that does not host any content. All content is accessed via public-facing websites through client-side mechanisms. Use of this software is at the user's own risk. 

For the full legal notice, please refer to the [DISCLAIMER](DISCLAIMER.md).

---

Released under the [UNLICENSE](LICENSE). Developed for the macOS community.
