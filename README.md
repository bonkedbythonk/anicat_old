# Anicat

**A simple way to watch and track anime on your Mac.**

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

Then use commands like `anicat search -t "Attack on Titan"` to stream from the terminal.

---

## Features
- **AniList Sync** — Your watch progress syncs automatically
- **Built-in Player** — Watch right inside the app, nothing else to install
- **Skip Intro** — Automatically skip openings and endings
- **One-Click Updates** — Update the app from Settings > Maintenance
- **Terminal Version** — Also works as a command-line app for power users

---

## Legal
Anicat is for educational and personal use only. See [DISCLAIMER.md](DISCLAIMER.md) and [SECURITY.md](SECURITY.md).

## License
MIT
