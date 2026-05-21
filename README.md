# Anicat

![Anicat Desktop](assets/branding/dashboard.png)

**A simple way to watch and track anime on your Mac.** Search, stream, download, and track everything in one place — with a beautiful GUI app and a powerful terminal version.

---

## How to Install

### 1. Open Terminal

Terminal is an app that lets you install things with a text command.

- Press **Command + Space** on your keyboard
- Type **Terminal**
- Press **Enter**

The Terminal app will open — it's a black or white window where you can type commands.

### 2. Copy and paste this one command

Click inside the Terminal window, then paste (Command + V) this line:

```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/master/scripts/install_macos.sh | bash
```

Then press **Enter**. The installer will download and set up everything automatically.

> **What this does:** It downloads the latest version of Anicat from GitHub, moves it to your Applications folder, and sets it up so it works properly on your Mac.

### 3. Open Anicat

After the install finishes:

1. Open your **Applications** folder (Finder > Applications)
2. Double-click **Anicat**
3. If Mac shows a warning, click **Open** (it's safe — the app is just not from the App Store)

That's it! Anicat will start and you can search for anime right away.

---

### For People Who Know Computers (CLI Version)

If you're comfortable with the terminal, you can install just the command-line version:

```bash
curl -fsSL https://raw.githubusercontent.com/bonkedbythonk/anicat/master/scripts/install_cli.sh | bash
```

Then type **`anicat`** to open the home screen and see what to watch next. Use `anicat search -t "Attack on Titan"` to find and stream specific shows.

> **Image previews (TUI mode):** For rich image previews when browsing anime in the terminal, use [Kitty terminal](https://sw.kovidgoyal.net/kitty/). It's the only terminal that supports the image protocol Anicat uses.

---

## What You Can Do

| Feature | What It Does |
|---------|-------------|
| **Search & Stream** | Find any anime and start watching in one command. Multiple providers with automatic fallback. |
| **AniList Sync** | Your progress, scores, and lists sync automatically to your AniList account. |
| **Continue Watching** | Pick up where you left off. The app remembers which episode and timestamp you were on. |
| **Smart Playlist** | Personalized recommendations from your watching list, top-rated shows, and plan-to-watch. |
| **Airing Schedule** | See what's airing today and the next 7 days, with live countdowns. |
| **Skip Intro** | Automatically detect and skip openings and endings using crowdsourced AniSkip timings. |
| **Batch Download** | Download entire seasons for offline watching, with yt-dlp engine and subtitle merging. |
| **Manga Support** | Read manga chapters from MangaKatana, with progress tracking and chapter navigation. |
| **Notifications** | Get notified when a new episode of your watched show airs, directly from AniList. |
| **One-Click Updates** | Update to the latest version from Settings > Maintenance. No terminal needed after install. |
| **Terminal Version** | 15 CLI commands that mirror the app. Search, track, download, and manage everything from the terminal. |
| **Built-in Player** | Watch right inside the app. HLS.js streaming with auto-quality, picture-in-picture, and keyboard shortcuts. |
| **MPV Integration** | For power users — bundled MPV with Anime4K upscaling shaders, ModernZ skin, and subtitle support. |

---

## Screenshots

_TODO: Add screenshots showing the search view, episode list, player, and settings._

---

## Legal
Anicat is for educational and personal use only. See [DISCLAIMER.md](DISCLAIMER.md) and [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
