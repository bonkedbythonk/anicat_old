# Anicat

![Anicat Dashboard](assets/branding/dashboard.png)

**Premium Anime & Manga Experience for macOS.**

Anicat is a high-performance, native media hub designed for those who want a seamless, unified interface for searching, streaming, and tracking their favorite content. It is a powerful fork of the viu engine, evolved into a full-featured macOS application.

---

## Getting Started

Anicat offers three ways to experience your library, depending on your workflow:

### 1. The Native App (Recommended)
The premium way to use Anicat. It sits in your Dock and Menu Bar, manages a background server automatically, and looks stunning.

**Install via Terminal:**
```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install_macos.sh | bash
```
*   **Updates:** Simply click "Install Update" in the Settings > Maintenance tab within the app. No more terminal commands needed after the first install.

### 2. The TUI / CLI
For those who live in the terminal. Fast, keyboard-driven, and lightweight.

**Run instantly:**
```bash
uv run anicat
```
*   Requires [uv](https://github.com/astral-sh/uv) to be installed.

### 3. Web Dashboard
Access the Anicat interface from any browser on your local network.

*   Launch the app/server and visit http://localhost:13370 in your browser.

---

---

## Power User Guide
Anicat uses **mpv** for high-quality playback. To unlock features like Anime4K upscaling, custom skins (ModernX), and advanced keyboard shortcuts, see our:
- [MPV Customization Guide](MPV_GUIDE.md)

---

## Features
- **AniList Native Sync**: Automated real-time progress tracking for both anime and manga.
- **Zero-Terminal Updates**: One-click in-app update mechanism for a seamless end-user experience.
- **Persistent Background Engine**: Dedicated system tray integration keeps the server alive and ready.
- **Smart Scrapers**: High-speed native integration with AnimePahe and MangaKatana.
- **Real-Time Data Sync**: Instant UI updates across all views powered by TanStack Query.
- **Airing Schedules**: Live relative countdowns for currently releasing series.
- **Premium Design**: Fluid Framer Motion transitions, glassmorphism, and a sleek media drawer layout.
- **Cross-Platform Access**: Switch between the Native macOS App, TUI/CLI, or Web Dashboard.

---

## Legal
Anicat is for educational and personal use only. The developer is not responsible for how the user utilizes the software. 
- [Disclaimer](DISCLAIMER.md)
- [Security Policy](SECURITY.md)

---

## License & Credits
Anicat is a fork of [Viu](https://github.com/viu-media/viu). Distributed under the MIT License.
