# Anicat

A specialized media companion for macOS designed for seamless anime and manga management. Anicat provides a centralized dashboard to stream content, track progress via AniList, and manage local downloads with a focus on performance and minimalist design.

![Anicat Dashboard](./dashboard_preview.png)

---

## Installation

Anicat can be installed via a single command. Open your Terminal and execute the following:

```bash
git clone https://github.com/bonkedbythonk/anicat.git && cd anicat && ./scripts/install.sh
```

The installation script automatically manages system dependencies, including Homebrew and MPV, and initializes the web dashboard.

---

## Core Features

- **Centralized Dashboard**: A responsive, dark-themed web interface for media management.
- **Bi-Directional Sync**: Real-time synchronization with AniList using a local-first architecture for zero-latency progress tracking.
- **Integrated Streaming**: Direct streaming support for anime with resolution options up to 1080p.
- **Manga Support**: A high-performance reading environment for manga chapters.
- **Background Operation**: Optimized to run as a lightweight background service.
- **Local Registry**: Persistent offline tracking for progress and library metadata.

---

## Usage and Commands

Anicat is controlled via the `anicat` command-line utility.

### Launching the Dashboard
To start the dashboard and run it as a background service:
```bash
anicat dashboard &
```
Once the command is executed, the terminal window can be closed. The dashboard will remain accessible at `http://localhost:8000`.

### Stopping the Service
To terminate all background Anicat processes:
```bash
anicat stop
```

### Updates
Anicat supports automated updates. Navigate to the **Settings > Maintenance** section within the web dashboard to check for and install the latest version. This process handles code retrieval, dependency synchronization, and service restarts automatically.

---

## Mobile Integration

The dashboard is accessible from any device on the same local network. 
1. Identify your local IP address (displayed in the terminal during startup).
2. Access the dashboard via `http://[YOUR-IP]:8000` on your mobile device.
3. For a native experience on iOS, select "Add to Home Screen" from the sharing menu.

---

## Troubleshooting

### Directory Conflicts
If an existing installation is detected, remove the directory before re-cloning:
```bash
rm -rf anicat && git clone https://github.com/bonkedbythonk/anicat.git && cd anicat && ./scripts/install.sh
```

### Command Resolution
If the `anicat` command is not recognized after installation, ensure your shell environment is refreshed:
```bash
source ~/.zshrc
```

---

## License
Anicat is a macOS-focused implementation based on the Viu project. It is released under the UNLICENSE.
