# <p align="center">🐈‍⬛ Anicat</p>

<p align="center">
  <strong>The specialized media companion for macOS.</strong><br>
  <em>Stream anime, read manga, and track progress with zero friction.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-macOS-silver?style=for-the-badge&logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/Interface-Web_%2F_TUI-amber?style=for-the-badge" alt="Interface">
  <img src="https://img.shields.io/badge/Sync-AniList-blue?style=for-the-badge" alt="AniList">
</p>

---

Anicat is a production-ready media dashboard designed for the modern macOS experience. It bridges the gap between your local files, streaming sources, and AniList, all within a beautiful, minimalist PWA that lives silently in your background.

![Anicat Dashboard Preview](https://raw.githubusercontent.com/bonkedbythonk/anicat/main/dashboard_preview.png)

## 🚀 One-Command Install

Get up and running in seconds. This script handles dependencies (mpv, ffmpeg, chafa), sets up the background service, and creates a native macOS App bundle.

```bash
curl -sSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install.sh | bash
```

---

## ✨ Key Features

### 🖥️ macOS Native Experience
- **Silent Persistence**: Runs as a macOS `LaunchAgent`—starts on login and stays in the background with near-zero CPU usage.
- **App Bundle**: Installs as `Anicat Dashboard.app` in your Applications folder for a native Dock presence.
- **Stealth Mode**: Locked to `127.0.0.1` (Localhost) for total privacy and isolation from your network.

### 📚 High-Performance Manga Reader
- **Turbo-Proxy**: Bypasses provider throttling and hotlink blocks for instant page loads.
- **Persistent Disk Cache**: Automatically pre-fetches and saves chapters to your local cache for instantaneous forwards/backwards navigation.
- **Reading Modes**: Support for Single Page, Double Page, and Vertical Long-strip modes.

### 🎬 Seamless Anime Streaming
- **1080p Playback**: Integrated MPV support with high-quality streaming buffers.
- **AniList Sync**: Bi-directional real-time sync. Watch an episode, and your AniList is updated before you even close the player.
- **Offline-First**: Uses a local registry to track progress even when you're disconnected.

---

## 🛠️ Usage

Once installed, you can control Anicat via the web dashboard or the `anicat` CLI.

- **Open Dashboard**: Click the **Anicat Dashboard** icon in your Applications folder.
- **Check Updates**: A pulsating amber dot appears in the sidebar when a new fix is ready. Update with one click from **Settings > Maintenance**.
- **CLI Control**: 
  - `anicat dashboard` — Start/Stop the server.
  - `anicat status` — Check server health.
  - `anicat stop` — Kill all background processes.

---

## 🔒 Privacy & Security

Anicat is designed to be a "quiet citizen" on your Mac:
- **Local Only**: No data ever leaves your machine except to talk to AniList.
- **Zero Tracking**: No telemetry, no analytics, no third-party scripts.
- **Invisible**: The background service is optimized to stay out of your way and out of your Activity Monitor.

---

<p align="center">
  Released under the <a href="./LICENSE">UNLICENSE</a>. Built with ❤️ for the macOS community.
</p>
