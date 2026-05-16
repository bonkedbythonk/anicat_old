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

## Professional MPV Setup

Anicat uses mpv for high-quality playback. Here is how to unlock its full potential:

### Keyboard Shortcuts
| Command | Action |
| :--- | :--- |
| Shift + N | **Play Next Episode** (Automated sync with Anicat) |
| Shift + P | Play Previous Episode |
| Shift + R | Reload Current Episode |
| Shift + A | Toggle Auto-play |
| Shift + T | Toggle Dub / Sub |
| Space | Play / Pause |
| f | Toggle Fullscreen |

### Improving the Visuals (Anime4K)
Anime4K is a set of state-of-the-art open-source real-time anime upscaling algorithms.

1.  Download the shaders from [Anime4K GitHub](https://github.com/bloc97/Anime4K).
2.  Place them in ~/.config/mpv/shaders/.
3.  Configure your mpv.conf based on your hardware:

#### Tier 1: Low-End / Base Apple Silicon (M1/M2/M3 Base, Intel iGPU)
*Focus on speed and stability.*
```conf
# Add to mpv.conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_M_x2_Fast.glsl"
```

#### Tier 2: Mid-Range (M1/M2/M3 Pro, RTX 3060/4060)
*The "Sweet Spot" for quality.*
```conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_L_x2_HQ.glsl;~/.config/mpv/shaders/Anime4K_Auto_Restore_VL.glsl"
```

#### Tier 3: High-End (M1/M2/M3 Max/Ultra, RTX 3080/4090)
*Ultimate quality with no compromises.*
```conf
glsl-shaders="~/.config/mpv/shaders/Anime4K_Upscale_CNN_UL_x2_Thin.glsl;~/.config/mpv/shaders/Anime4K_Restore_CNN_UL.glsl"
```

### Modern UI Skin
We recommend installing **[uosc](https://github.com/tomasklaen/uosc)** or **[modern-uifk](https://github.com/maoiscat/mpv-modern-uifk)** for a sleek, macOS-native look that replaces the default mpv bar.

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

## License & Credits
Anicat is a fork of [Viu](https://github.com/viu-media/viu). Distributed under the MIT License.
