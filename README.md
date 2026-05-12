# Anicat: The Beginner's Guide to Terminal Anime

Welcome to **Anicat**! If you’ve never used a "terminal" before, don't worry. This guide is written specifically to help you get up and running in minutes.

Anicat is a minimalist, high-performance tool that lets you search, stream, and track your favorite Anime and Manga directly from your computer's command line. No browser ads, no distractions—just pure content.

---

## What are you installing?

Before we run any commands, it helps to understand the three core tools that make Anicat work:

-   **Homebrew**: Think of this as the "App Store" for developers. It handles the downloading and updating of all the background tools we need.
-   **Kitty Terminal**: This is the "window" where you will run Anicat. We use Kitty because it is one of the few terminals that can display high-quality images and anime covers directly in your workspace.
-   **MPV Media Player**: This is the "engine" that actually plays the video. It's lightweight, fast, and stays out of your way.

---

## Installation Guide

### Step 1: The Tools (Engines)
First, we need to install the foundation. Copy and paste these commands into your current terminal:

1.  **Install Homebrew** (if you don't have it):  
    `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

2.  **Install the Engines** (Kitty, MPV, and FZF):  
    `brew install kitty mpv fzf`

> [!TIP]
> After running `brew install kitty`, you will find **Kitty** in your **Applications** folder just like any other app (Spotify, Chrome, etc.). **From now on, you should always use Kitty to run Anicat!**

---

### Step 2: The App (Anicat)
Now that we have the engines, let's install the actual app.

1.  **Install UV** (The installer):  
    `curl -LsSf https://astral.sh/uv/install.sh | sh`

2.  **Install Anicat**:  
    `uv tool install git+https://github.com/bonkedbythonk/anicat.git`

---

## Getting Started

### 1. Launch Kitty
Open your **Applications** folder and launch **Kitty**. 

> [!IMPORTANT]
> **Stop using the default Apple Terminal!** It cannot show images. Always open the **Kitty** app to enjoy the full Anicat experience.

### 2. Login
Run the login command to link your AniList account:
```bash
anicat login
```
Anicat will open your browser and your config file automatically. Just paste the token into the file, save, and you're ready to go!

### 3. Browse!
Just type `anicat` and press **Enter** to start browsing!

-   **Arrow Keys**: Move up/down in menus.
-   **Enter**: Select an item.
-   **Escape / Backspace**: Go back.

---

## Features

Anicat is packed with features designed for the ultimate terminal-based anime experience:

-   **🔍 Advanced Search**: Find any Anime or Manga with lightning-fast dynamic search and real-time results.
-   **🎥 Premium Streaming**: Stream in high quality (up to 1080p) with support for multiple providers (AnimePahe, HiAnime, AllAnime) and servers.
-   **📖 Manga Support**: Read your favorite Manga chapters directly in the terminal using Kitty's high-resolution image protocol.
-   **🔗 AniList Sync**: Automatically synchronize your watch and read progress with your AniList profile.
-   **📥 Offline Downloads**: Download episodes for viewing anytime using `yt-dlp` or torrents.
-   **📅 Airing Schedule**: Stay up to date with a built-in release calendar for upcoming episodes.
-   **🔄 Auto-Next & Auto-Update**: Seamlessly transition between episodes and keep your app current with manual or automatic updates.

---

## MPV IPC Integration

When `use_ipc = true` is set in your config, Anicat provides powerful in-player controls without needing to close MPV. This allows you to navigate episodes, change settings, and sync progress seamlessly.

### Key Bindings (while MPV is open):

| Key | Action |
| :--- | :--- |
| **Shift + N** | Play the next episode |
| **Shift + P** | Play the previous episode |
| **Shift + R** | Reload the current episode |
| **Shift + A** | Toggle auto-play for the next episode |
| **Shift + T** | Toggle between Dub and Sub |

---

## Credits
Anicat is a specialized macOS fork of the [Viu](https://github.com/viu-media/viu) project. I am deeply grateful to the original creators for their incredible architecture!
