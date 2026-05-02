# Anicat: The Beginner's Guide to Terminal Anime

Welcome to **Anicat**! If you’ve never used a "terminal" before, don't worry. This guide is written specifically for you. 

Anicat is a minimalist, high-performance tool that lets you search, stream, and track your favorite Anime and Manga directly from your computer's command line. No browser ads, no distractions—just pure content.

---

## Quick Start

If you already know what you're doing, here are the magic words:

1.  **Install Homebrew:** `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2.  **Install Tools:** `brew install mpv fzf kitty`
3.  **Install UV:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
4.  **Install Anicat:** `uv tool install git+https://github.com/bonkedbythonk/anicat.git`
5.  **Run:** `anicat`

---

## Detailed Step-by-Step Setup

### Step 0: The "App Store" for your Terminal
To use Anicat, we first need to install **Homebrew**. Think of this as an App Store that works inside your terminal.

1.  Open your "Terminal" app (search for it in Spotlight).
2.  Copy and paste this command and press **Enter**:
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```
3.  Wait for it to finish (it might ask for your Mac password).

### Step 1: Install the Required Tools
Now we need to install the "engines" that Anicat uses to show images and play videos.

> [!IMPORTANT]
> **You MUST use the Kitty Terminal!** Standard Apple Terminal (the white/black box) cannot show the beautiful anime posters and manga pages. **Kitty** is a special terminal that makes images work.

Copy and paste this command to install everything you need:
```bash
brew install mpv fzf kitty
```
*   **mpv**: Plays the videos.
*   **fzf**: Powers the search menus.
*   **kitty**: The "window" you'll use to run Anicat.

### Step 2: Install Anicat
We use a modern tool called `uv` to install Anicat safely.

1.  **Install uv first:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2.  **Install Anicat using uv:**
    ```bash
    uv tool install git+https://github.com/bonkedbythonk/anicat.git
    ```

---

## Connecting your AniList Account
**Why do I need this?** 
AniList is a website that tracks what you watch. By connecting it to Anicat, the app will automatically remember which episode you stopped at and update your "Watching" list for you!

1.  Open the **Kitty Terminal** you just installed.
2.  Run the following command to open the authorization page:
    ```bash
    anicat anilist auth
    ```
3.  Your browser will open to the [AniList Developer Settings](https://anilist.co/settings/developer). Click **"Authorize"** and copy the long code (the "Token") that appears.
4.  **Save the Token (The Easiest Way):** 
    Copy and paste this command into your terminal (replace **YOUR_TOKEN_HERE** with your actual code):
    ```bash
    echo 'export ANILIST_TOKEN="YOUR_TOKEN_HERE"' >> ~/.zshrc
    ```
    *(**What does this do?** It's a shortcut that saves the token to your Mac's hidden settings file so Anicat remembers you **permanently**, even after you restart your computer!)*
5.  **Restart your Terminal** (close Kitty and open it again), and you’re all set! Now when you type `anicat`, your progress will be saved.

*Note: The `export` method is the most reliable for macOS users. You can also try adding it directly to your config file, but we recommend the steps above for a hassle-free setup.*

---

## How to Use Anicat

Once installed, simply type **anicat** in your **Kitty Terminal**.

*   **Search**: Type the name of an anime and press Enter.
*   **Navigate**: Use your **Up/Down Arrows** to browse.
*   **Select**: Press **Right-Arrow** or **Enter** to pick an anime or episode.
*   **Manga Viewer Keys**:
    *   `Right Arrow`: Next Page
    *   `Left Arrow`: Previous Page
    *   `q`: Exit Viewer

> [!CAUTION]
> **Reminder**: If you use the default Apple Terminal, you will see text but **NO IMAGES**. Always open the **Kitty** app to get the full experience!

---

## Credits
Anicat is a specialized macOS fork of the [Viu](https://github.com/viu-media/viu) project. I am deeply grateful to the original creators for their incredible architecture!
