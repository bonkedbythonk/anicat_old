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

### Setup Anicat

**Step 1:** Install with [uv](https://astral.sh/uv/) package manager:
```bash
uv tool install git+https://github.com/bonkedbythonk/anicat.git
```

**Step 2:** Start the backend service:
```bash
anicat dashboard --no-browser
```

This starts the API backend on `localhost:8000`. Keep this running in the background.

---

## Getting Started

### Option 1: Web Dashboard (Recommended for Most Users)

The easiest way to use Anicat is through the **Progressive Web App (PWA)** in your browser. No additional setup needed.

1. **Open your browser** and navigate to `http://localhost:3000`
2. **Bookmark or Install as PWA**: 
   - **macOS Safari**: Press `Cmd+Shift+B` to bookmark, or use "Add to Dock" from the Share menu
   - **Any browser**: Look for the "Install" or "+" icon in the address bar to install as a standalone app
3. **Enjoy**: Full Netflix-style dashboard with all features in your browser

---

### Option 2: macOS Desktop App (Optional)

If you prefer a native-looking macOS application in your Launchpad:

```bash
bash ~/path/to/anicat/scripts/install.sh
```

Then:
1. **Open Launchpad**: Press `F4` or search for **Anicat** in Spotlight (`Cmd+Space`)
2. **Add to Dock**: Drag the **Anicat** icon into your Dock
3. **Click to Launch**: Opens the dashboard automatically

**Note:** This is a convenience wrapper around the web dashboard—the PWA option in your browser provides the same experience without the extra setup.

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
