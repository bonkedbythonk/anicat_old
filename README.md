# Anicat: The Beginner's Guide to Terminal Anime and Manga

Welcome to **Anicat**! If you’ve never used a "terminal" before, don't worry. This guide is written specifically to help you get up and running in minutes.

Anicat is a minimalist, high-performance tool that lets you search, stream, and track your favorite Anime and Manga directly from your computer's command line or a beautiful web dashboard.

---

## 🚀 One-Minute Setup

If you have a Mac, just copy and paste this into your terminal:

```bash
# 1. Install the engines (Kitty, MPV, UV)
brew install --cask kitty && brew install mpv fzf
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Anicat
uv tool install git+https://github.com/bonkedbythonk/anicat.git
```

---

## 🎮 How to Open

### Method 1: The Modern Dashboard (Recommended)
Just type this in your terminal to launch the beautiful "Netflix-style" interface:
```bash
anicat dashboard
```
*The dashboard will automatically open in your browser. You can even install it as a **PWA (App)** for a native desktop experience.*

### Method 2: The Terminal Pro (Classic)
Open the **Kitty** app from your Applications folder and type:
```bash
anicat
```
*This opens the interactive terminal menu where you can browse and play anime directly in the window.*

---

## 🔑 First Run: Login
To sync your watch progress, you need to link your AniList account:
1. Run `anicat login`.
2. Authorize in your browser.
3. Paste the token into the config file that opens.
4. Save and close. Done!

---

## ✨ Features

- **🔍 Search & Discovery**: Lightning-fast search across Anime and Manga.
- **🎥 Premium Streaming**: Stream in up to 1080p with auto-next and tracking.
- **📥 Offline Downloads**: Queue episodes to watch later without buffering.
- **🔗 AniList Sync**: Automatic progress tracking for everything you watch.
- **📱 PWA Ready**: Install the dashboard as a native app on macOS, Windows, or Linux.

---

## ⌨️ Controls (Terminal Mode)

- **Arrow Keys**: Move up/down.
- **Enter**: Select.
- **Escape**: Go back.
- **Shift + N**: Next episode (in-player).

---

## 🛠️ Credits
Anicat is a specialized macOS fork of the [Viu](https://github.com/viu-media/viu) project. Deeply grateful to the original creators!
