# Anicat

![Anicat Desktop](assets/branding/dashboard.png)

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

### 2. Setting Up Playback (Built-in vs. Advanced MPV)
Anicat features two premium ways to watch anime, fitting both casual viewers and quality purists:

#### A. The Built-in Player (Zero Setup)
* Works 100% out-of-the-box on your first launch!
* Plays streams directly inside the Anicat window without installing any extra software.

#### B. The Companion MPV Player (Zero Setup + Advanced ModernZ Skin & Upscaling)
On macOS, Anicat **automatically bundles** a standalone, high-performance isolated **MPV** player package pre-configured with:
*   The premium **Samillion/ModernZ** skin.
*   Curated Outfit typography and responsive controls.
*   Automatic **Skip Intro / Skip Outro** glassmorphic overlay badges.
*   Support for high-end **Anime4K** real-time upscaling.

No manual Homebrew or external MPV installation is required! The desktop installer handles everything automatically.

*Note: If you prefer to use your own system-wide, custom-configured MPV player instead, simply install it via Homebrew (`brew install mpv`), select "External" in settings, and Anicat will seamlessly route streams to it.*

---

### 3. The Terminal TUI & Developer CLI
For developers and keyboard-driven power users. Fast, fully customizable, and lightweight.

#### A. Run the CLI / TUI Instantly
If you are inside the cloned repository root, you can run the interactive CLI interface instantly using `uv`:
```bash
uv run anicat
```
*(Requires [uv](https://github.com/astral-sh/uv) to be installed on your system.)*

#### B. Local Developer / Advanced Installation
To compile the Python backend server sidecar, build the native Tauri macOS bundle, and install the **global `anicat` command** globally under your terminal PATH:

1. Open your terminal.
2. Navigate into your cloned repository root folder:
   ```bash
   cd /path/to/your/cloned/anicat
   ```
3. Run the advanced installation script:
   ```bash
   ./scripts/install.sh
   ```
This script automatically:
* Installs system tools (like `mpv`, `ffmpeg`, and `chafa` for TUI image rendering).
* Configures the local Python environment.
* Installs the global `anicat` wrapper command at `~/.local/bin/anicat`.
* Compiles the native desktop application and puts it in `~/Applications/Anicat.app`.

*Once installed, you can launch the TUI by typing `anicat` anywhere in your terminal!*

---

---

## Power User Guide
Anicat uses **mpv** for high-quality playback. To unlock features like Anime4K upscaling, custom skins (ModernZ), and advanced keyboard shortcuts, see our:
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
- **Interface Flexibility**: Switch seamlessly between the premium native macOS App or the keyboard-driven terminal TUI/CLI.

---

## Legal
Anicat is for educational and personal use only. The developer is not responsible for how the user utilizes the software. 
- [Disclaimer](DISCLAIMER.md)
- [Security Policy](SECURITY.md)

---

## License & Credits
Anicat is a fork of [Viu](https://github.com/viu-media/viu). Distributed under the MIT License.
