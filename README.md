# Anicat: The Beginner's Guide to Terminal Anime

Welcome to **Anicat**! If you’ve never used a "terminal" before, don't worry. This guide is written specifically for you. 

Anicat is a minimalist, high-performance tool that lets you search, stream, and track your favorite Anime and Manga directly from your computer's command line. No browser ads, no distractions—just pure content.

---

## 🚀 Quick Start in 2 Steps

### 1. Install
Copy and paste these commands in order:

1.  **Install Homebrew:**  
    `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2.  **Install Engines:**  
    `brew install mpv fzf kitty`
3.  **Install UV:**  
    `curl -LsSf https://astral.sh/uv/install.sh | sh`
4.  **Install Anicat:**  
    `uv tool install git+https://github.com/bonkedbythonk/anicat.git`

> [!IMPORTANT]
> **You MUST use the Kitty Terminal!** Standard Apple Terminal cannot show images. Always open the **Kitty** app to run Anicat.

### 2. Setup
Run the login command to link your AniList account (this is how your progress is saved):
```bash
anicat login
```
Follow the link provided, paste your token, and you're ready to go!

---

## 🎮 Basic Usage

Just type `anicat` and press **Enter** to start browsing!

- **Arrow Keys**: Move up/down in menus.
- **Enter**: Select an item.
- **Escape / Backspace**: Go back.
- **Right Arrow**: Quick select (in some menus).

---

## ✨ Features
- **Auto-Next**: Automatically plays the next episode when you finish one.
- **Sync**: Your progress is automatically saved to your AniList profile.
- **High Quality**: Supports up to 1080p streaming.
- **Minimalist**: Beautiful ASCII interface with zero distractions.

---

## 🛠️ Self-Update
Anicat is updated frequently. To get the latest features, just run:
```bash
anicat update
```

## Credits
Anicat is a specialized macOS fork of the [Viu](https://github.com/viu-media/viu) project. I am deeply grateful to the original creators for their incredible architecture!
