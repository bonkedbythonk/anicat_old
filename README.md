# anicat

Anicat is a high-performance media management suite designed for macOS. It provides both a sophisticated web-based dashboard and a robust command-line interface (CLI) for searching, streaming, downloading, and tracking anime and manga.

The project bridges the gap between terminal efficiency and modern streaming experiences, featuring deep AniList integration and a local-first architecture.

---

## Installation

Anicat is optimized for macOS and can be installed with a single command using the [uv](https://astral.sh/uv/) package manager.

### Prerequisites
Ensure you have the core media engines and a compatible terminal installed on your system:
```bash
# Kitty is required for terminal image support (covers/thumbnails)
brew install --cask kitty
brew install mpv fzf
```

### One-Line Install
```bash
uv tool install git+https://github.com/bonkedbythonk/anicat.git
```

---

## Core Interfaces

Anicat offers two primary ways to interact with your media library, both sharing a unified backend.

### 1. Unified Web Dashboard
The dashboard provides a modern, "Netflix-style" Progressive Web App (PWA) experience for local streaming and management.
- **Launch Command:** `anicat dashboard`
- **Features:**
    - **Intelligent Search:** Global media discovery with paginated results for deep browsing.
    - **Enriched Metadata:** Access to episode lists, character profiles, user reviews, and media recommendations.
    - **AniList Synchronization:** Real-time 10-star rating system and list management (Watching, Planning, Completed, etc.).
    - **Responsive Design:** Optimized for both standard browser use and installation as a standalone desktop PWA with custom theme-aware icons.

### 2. Interactive CLI (TUI)
For terminal-focused workflows, Anicat features a fast, keyboard-driven interface.
- **Launch Command:** `anicat`
- **Features:**
    - **Rapid Navigation:** Browse lists and trigger playback using optimized terminal bindings.
    - **Offline Registry:** Track your local media library and watch history without requiring a persistent internet connection.
    - **Background Sync:** Watch history recorded while offline is automatically synchronized to your AniList profile upon reconnection.

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
