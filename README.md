# anicat

Anicat is a high-performance media management suite designed for macOS. It provides both a sophisticated web-based dashboard and a robust command-line interface (CLI) for searching, streaming, downloading, and tracking anime and manga.

The project bridges the gap between terminal efficiency and modern streaming experiences, featuring deep AniList integration and a local-first architecture.

---

## Installation

### Prerequisites
Ensure you have the core media engines installed on your system:
```bash
brew install --cask kitty  # Required for terminal image support (covers/thumbnails)
brew install mpv fzf       # Required for playback and terminal features
```

### Install Anicat

Install the package with [uv](https://astral.sh/uv/) package manager:
```bash
uv tool install git+https://github.com/bonkedbythonk/anicat.git
```

That's it! Now choose how you want to use it below.

---

## Getting Started

Choose the setup that works best for you:

### Option 1: Quick Start - macOS Desktop App (Recommended)

**The absolute easiest way.** One click and everything starts.

```bash
bash ~/path/to/anicat/scripts/install.sh
```

Then:
1. **Open Launchpad**: Press `F4` or search for **Anicat** in Spotlight (`Cmd+Space`)
2. **Add to Dock**: Drag the **Anicat** icon into your Dock
3. **Click Once**: Done! The app:
   - Starts the backend API server in the background
   - Opens your dashboard automatically (`http://localhost:8000`)
   - Everything works with zero terminal commands

**Perfect for:** Users who just want to watch anime, no technical setup needed.

---

### Option 2: Developer Setup - Web Dashboard + Terminal

For developers who want control over what's running and easier code updates.

1. **Start the backend** (in a terminal, keep it running):
   ```bash
   anicat dashboard --no-browser
   ```

2. **Open your browser** and navigate to `http://localhost:3000`

3. **Optional - Install as PWA**: 
   - **macOS Safari**: Press `Cmd+Shift+B` to bookmark, or use "Add to Dock" from the Share menu
   - **Any browser**: Look for the "Install" or "+" icon in the address bar to install as a standalone app

**Advantages:** 
- Works in any browser on any device on your network
- Easy to modify code and see changes live
- More control over when services start/stop

---

## Core Interfaces

Anicat provides a unified web-based dashboard backed by a powerful CLI layer for terminal workflows.

### 1. Web Dashboard (Primary Interface)

The main way to interact with Anicat is through the **Progressive Web App (PWA)** dashboard accessible at `http://localhost:3000`.

**Features:**
- **Intelligent Search:** Global media discovery with paginated results for deep browsing
- **Enriched Metadata:** Episode lists, character profiles, user reviews, and recommendations
- **AniList Sync:** Real-time 10-star rating system and list management (Watching, Planning, Completed, etc.)
- **Playback Management:** Queue episodes directly from the interface with intelligent resume functionality
- **Responsive Design:** Optimized for desktop browsers and installable as a standalone PWA
- **Local Library:** Monitor downloads and manage your media collection visually

### 2. Interactive CLI (Terminal-Focused Workflows)

For power users who prefer the terminal, the CLI provides fast keyboard-driven access to the same media library.

**Launch:** `anicat`

**Features:**
- **Rapid Navigation:** Browse lists and trigger playback using optimized terminal bindings
- **Offline Registry:** Track your local media library and watch history without persistent internet
- **Background Sync:** Watch history recorded offline automatically syncs to AniList upon reconnection

---

## Technical Functionality

### High-Performance Streaming
- **Quality Control:** Support for streaming in up to 1080p with configurable provider preferences.
- **Auto-Tracking:** Playback progress is automatically tracked and updated on your account as you watch.
- **Media Engine:** Uses `mpv` for lightweight, hardware-accelerated playback.

### Download Management
- **Queue System:** Queue individual episodes or entire ranges directly from the dashboard or CLI.
- **Task Resilience:** Automatic support for retrying failed tasks and managing the local download queue.
- **Local Library:** Visual interface for monitoring storage and managing completed downloads.

### Account Management
- **Secure Authentication:** Integrated OAuth2 login flow for AniList.
- **Profile Management:** Instantly update your watch status, episode progress, and personal ratings.

---

## Configuration

Anicat is highly customizable through its `config.toml` file. These settings can be managed visually through the dashboard settings panel.

- **Provider Preferences:** Configure default scrapers, streaming quality, and translation types (Sub/Dub).
- **Library Management:** Define custom directories for downloads and the local media registry.
- **Interface Settings:** Toggle categories and customize the visual experience.

---

## Credits
Anicat is a specialized macOS fork of the [Viu](https://github.com/viu-media/viu) project, refined for a premium dashboard experience and enhanced automation.
