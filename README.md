# Anicat

A minimalist, high-performance Media CLI for macOS.

Anicat is designed for users who want a distraction-free, terminal-native experience for browsing and consuming media. Optimized for macOS and the Kitty terminal, it provides lightning-fast performance and deep integration with native tools.

## Core Features

*   **Native IINA Support:** macOS-optimized playback with a seamless auto-next loop.
*   **High-Speed Manga Prefetching:** 15-page concurrent buffer with proactive background resizing for instant page turns.
*   **Kitty Terminal Integration:** Rich image previews using the high-performance `icat` protocol.
*   **Ultra-Clean Configuration:** A minimalist, documentation-free TOML configuration file.
*   **Interactive TUI:** Fuzzy-search and browse your library with `fzf` integration.
*   **Scriptable CLI:** Powerful commands for non-interactive media management.

## Installation

Anicat is best installed using [**uv**](https://github.com/astral-sh/uv).

```bash
uv tool install git+https://github.com/bonkedbythonk/anicat.git
```

### Prerequisites

For the full experience, the following tools are recommended:

*   [**IINA**](https://iina.io/) or [**mpv**](https://mpv.io/) for media playback.
*   [**Kitty Terminal**](https://sw.kovidgoyal.net/kitty/) for high-performance image previews.
*   [**fzf**](https://github.com/junegunn/fzf) for the interactive selection menu.

## Quick Start

1.  **Launch the Interactive TUI:**
    ```bash
    anicat anilist
    ```

2.  **Browse & Read Manga:**
    ```bash
    anicat manga search "Berserk"
    ```

3.  **Keyboard Shortcuts (Manga Viewer):**
    *   `l` / `Right Arrow`: Next Page
    *   `h` / `Left Arrow`: Previous Page
    *   `s`: Toggle Spread Mode (Double Page View)
    *   `b`: Toggle Information Banner
    *   `q`: Exit Viewer

## Configuration

Anicat generates a clean, minimal `config.toml` on its first run. You can find it at:
`~/Library/Application Support/anicat/config.toml` (macOS)

## Credits & Acknowledgements

Anicat is a specialized and heavily modified fork of the Viu project.
This tool would not have been possible without the innovation and solid foundation laid by the original Viu development team. While Anicat has evolved into a dedicated macOS and Kitty-terminal focused utility with its own distinct identity, the core engine and logic are deeply rooted in the vision and architecture of the original creators.
I want to express my sincere gratitude to the original authors and all contributors of the Viu project for their hard work and dedication to the terminal media community. Their open-source code served as the essential catalyst for the creation of this streamlined, high-performance edition.
https://github.com/viu-media/viu
