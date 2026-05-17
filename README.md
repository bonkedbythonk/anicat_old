# Anicat

![Anicat Dashboard](assets/branding/dashboard.png)

**Premium Anime & Manga Experience for macOS.**

Anicat is a high-performance, native media hub designed for those who want a seamless, unified interface for searching, streaming, and tracking their favorite content. It is a powerful fork of the viu engine, evolved into a full-featured macOS application.

---

## Getting Started

Anicat offers a premium experience tailored for your workflow, whether you want a seamless macOS app or a blazing-fast terminal UI.

### 1. The Native macOS App (Recommended)
The premium way to use Anicat. It sits in your Dock and Menu Bar, manages the background server automatically, and looks stunning.

#### Easy Installation (One-Click Setup)
Run this simple command in your Terminal to download, install, and configure all security permissions for Anicat automatically:
```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install_macos.sh | bash
```
*   **Updates:** Simply click "Install Update" in the `Settings > Maintenance` tab within the app. No more terminal commands needed after the first install!

##### Want the unstable Nightly/Beta release instead?
To download, install, and configure all Gatekeeper permissions for the rolling **Nightly Build** automatically, run this command in your Terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/main/scripts/install_macos.sh | sed 's/releases\/latest/releases\/tags\/nightly/g' | bash
```

#### Manual Installation (Alternative)
If you prefer to download the `.dmg` manually from the GitHub Releases page:
1. Download the latest `.dmg` and double-click to mount it.
2. Drag `Anicat.app` to your `/Applications` folder (never run it directly from the mounted volume).
3. If macOS blocks the background server from launching external programs (like MPV), open Terminal and run this one-time command to remove the quarantine flag:
   ```bash
   xattr -dr com.apple.quarantine /Applications/Anicat.app
   ```

---

### 2. Setting Up Playback (Built-in vs. Native MPV)
Anicat features two ways to watch anime, fitting both casual viewers and quality purists:

#### A. The Built-in Player (Zero Setup)
* Works 100% out-of-the-box on your first launch!
* Plays streams directly inside the Anicat window without installing any extra software.

#### B. The Native MPV Player (Unlock Premium 4K Upscaling & Skins)
To play high-performance upscaled anime via **Anime4K** shaders or use advanced skins (ModernX), you need the native **MPV** player. 

We highly recommend installing it via **Homebrew** (this handles all media decoders and updates automatically):

1. **Install Homebrew** (if you don't have it already):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. **Install MPV**:
   ```bash
   brew install mpv
   ```
Anicat will automatically detect the installation and seamlessly route your upscaled playback!

---

### 3. The Terminal TUI & Developer CLI
For developers and those who live in the terminal. Fast, keyboard-driven, and lightweight.

#### Run instantly (CLI/TUI)
```bash
uv run anicat
```
*Requires [uv](https://github.com/astral-sh/uv) to be installed.*

#### Developer / Advanced Local Installation
If you want to build the entire suite (CLI, TUI, and App) locally from the source:
```bash
./scripts/install.sh
```
*This script automatically checks/installs Homebrew, `mpv`, `ffmpeg`, `chafa`, `uv`, Node.js, builds the static frontends, and registers persistent system LaunchAgents.*

---

### 4. Web Dashboard
Access the Anicat interface from any browser on your local network.
* Launch the app/server and visit http://localhost:13370 in your browser.

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
