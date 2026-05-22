"""App-style TUI — sidebar navigation matching the Anicat web app.

Provides a persistent Rich layout with a left sidebar (Home, Manga, Search,
Lists, Downloads, Library, Schedule, Notifications, Profile, Settings) and
a right content area that renders the active view.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from anicat_media.core.constants import LOCAL_API_ORIGIN
from ...session import Context, session
from ...state import InternalDirective, MenuName, State

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Navigation items (matching the web app sidebar order)
# ---------------------------------------------------------------------------

NAV_ITEMS: list[dict[str, Any]] = [
    {"id": "home",      "label": "Home",           "icon": "H"},
    {"id": "manga",     "label": "Manga",           "icon": "M"},
    {"id": "search",    "label": "Search",          "icon": "/"},
    {"id": "lists",     "label": "My Lists",        "icon": "L"},
    {"id": "downloads", "label": "Downloads",       "icon": "D"},
    {"id": "library",   "label": "Library",         "icon": "B"},
    {"id": "schedule",  "label": "Schedule",        "icon": "C"},
    # divider
    {"id": "notifications", "label": "Notifications", "icon": "N"},
    {"id": "profile",   "label": "Profile",         "icon": "P"},
    {"id": "settings",  "label": "Settings",        "icon": "S"},
]

SIDEBAR_WIDTH = 22
DIVIDER_INDEX = 7  # index after schedule, before notifications

# ---------------------------------------------------------------------------
# Keyboard helpers (cross-platform arrow-key reading)
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import msvcrt as _msvcrt

    def _get_key() -> str:
        ch = _msvcrt.getch()
        if ch in (b"\xe0", b"\x00"):  # arrow key prefix
            ch2 = _msvcrt.getch()
            mapping = {b"H": "up", b"P": "down", b"K": "left", b"M": "right"}
            return mapping.get(ch2, "")
        try:
            return ch.decode("utf-8")
        except UnicodeDecodeError:
            return ""

else:
    import termios
    import tty

    def _get_key() -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.buffer.read(1)
            if ch == b"\x1b":
                seq = sys.stdin.buffer.read(2)
                if seq == b"[A":
                    return "up"
                elif seq == b"[B":
                    return "down"
                elif seq == b"[C":
                    return "right"
                elif seq == b"[D":
                    return "left"
                return ""
            return ch.decode("utf-8", errors="replace")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api_get(url: str) -> dict | None:
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def _title(item: dict) -> str:
    t = item.get("title", {})
    return t.get("romaji") or t.get("english") or "?"

# ---------------------------------------------------------------------------
# View renderers — each returns a Rich renderable for the content area
# ---------------------------------------------------------------------------

def _render_home() -> Panel:
    tables: list[Any] = []

    # Continue Watching
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/media/recent?type=ANIME&limit=5")
    if data and data.get("media"):
        t = Table(title="Continue Watching", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Title")
        t.add_column("Progress", justify="right")
        for item in data["media"][:5]:
            prog = item.get("user_status", {}).get("progress", 0)
            total = item.get("episodes", "?")
            t.add_row(_title(item), f"{prog}/{total}")
        tables.append(t)

    # Trending
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/media/trending?type=ANIME&per_page=5")
    if data and data.get("media"):
        t = Table(title="Trending Now", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Title")
        t.add_column("Score", justify="right")
        for item in data["media"][:5]:
            score = item.get("average_score", "?")
            t.add_row(_title(item), f"{score}%")
        tables.append(t)

    content = Text()
    for tbl in tables:
        content.append(Text.from_ansi(str(tbl)))
        content.append("\n")

    return Panel(content, title="Home", border_style="cyan")


def _render_manga() -> Panel:
    tables: list[Any] = []
    reading = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=watching&type=MANGA")
    if reading and reading.get("media"):
        t = Table(title="Currently Reading", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Title")
        t.add_column("Progress", justify="right")
        for item in reading["media"][:5]:
            prog = item.get("user_status", {}).get("progress", 0)
            total = item.get("chapters", "?")
            t.add_row(_title(item), f"{prog}/{total}")
        tables.append(t)

    trending = _api_get(f"{LOCAL_API_ORIGIN}/api/media/trending?type=MANGA&per_page=5")
    if trending and trending.get("media"):
        t = Table(title="Trending Manga", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Title")
        t.add_column("Score", justify="right")
        for item in trending["media"][:5]:
            score = item.get("average_score", "?")
            t.add_row(_title(item), f"{score}%")
        tables.append(t)

    content = Text()
    for tbl in tables:
        content.append(Text.from_ansi(str(tbl)))
        content.append("\n")
    return Panel(content, title="Manga", border_style="cyan")


def _render_search() -> Panel:
    return Panel(
        "Type a query to search for anime or manga.\n\n"
        "Use [bold]anicat search <query>[/bold] from the CLI for quick search.",
        title="Search",
        border_style="cyan",
    )


def _render_lists() -> Panel:
    watching = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=watching&type=ANIME")
    planning = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=planning&type=ANIME")
    completed = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=completed&type=ANIME")

    content = Text()
    for label, data in [("Watching", watching), ("Planning", planning), ("Completed", completed)]:
        count = len(data.get("media", [])) if data else 0
        content.append(f"  {label}: {count} titles\n")
    return Panel(content, title="My Lists", border_style="cyan")


def _render_downloads() -> Panel:
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/queue/")
    if data:
        t = Table(title="Download Queue", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Title")
        t.add_column("Episode", justify="right")
        t.add_column("Status")
        for item in data[:15]:
            t.add_row(
                item.get("media_title", "?"),
                item.get("episode_number", "?"),
                item.get("status", "?"),
            )
        return Panel(t, title="Downloads", border_style="cyan")
    return Panel("Queue is empty.", title="Downloads", border_style="cyan")


def _render_library() -> Panel:
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/list?status=completed&type=ANIME")
    if data and data.get("media"):
        t = Table(title="Completed", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Title")
        t.add_column("Score", justify="right")
        for item in data["media"][:15]:
            score = item.get("user_status", {}).get("score", "-")
            t.add_row(_title(item), str(score))
        return Panel(t, title="Library", border_style="cyan")
    return Panel("Nothing completed yet.", title="Library", border_style="cyan")


def _render_schedule() -> Panel:
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/media/schedule?days_before=0&days_after=3")
    if data and data.get("media"):
        t = Table(title="Upcoming Episodes", box=box.SIMPLE, show_header=True,
                  header_style="bold cyan", expand=True)
        t.add_column("Time")
        t.add_column("Title")
        t.add_column("Ep", justify="right")
        for item in data["media"][:10]:
            na = item.get("next_airing") or {}
            ep = na.get("episode", "?")
            at = na.get("airing_at", "?")
            if at != "?":
                try:
                    from datetime import datetime
                    at = datetime.fromtimestamp(int(at)).strftime("%a %H:%M")
                except Exception:
                    pass
            t.add_row(str(at), _title(item), f"Ep {ep}")
        return Panel(t, title="Schedule", border_style="cyan")
    return Panel("No upcoming episodes found.", title="Schedule", border_style="cyan")


def _render_notifications() -> Panel:
    health = _api_get(f"{LOCAL_API_ORIGIN}/api/status/health")
    count = health.get("unread_notifications", 0) if health else 0
    return Panel(
        f"{count} unread notifications." if count else "No unread notifications.",
        title="Notifications",
        border_style="cyan",
    )


def _render_profile() -> Panel:
    data = _api_get(f"{LOCAL_API_ORIGIN}/api/user/profile")
    if data:
        content = Text()
        content.append(f"  {data.get('name', '?')}\n\n", style="bold")
        content.append(f"  Anime: {data.get('anime_count', 0)}  |  Manga: {data.get('manga_count', 0)}\n")
        content.append(f"  Episodes: {data.get('episodes_watched', 0)}  |  Chapters: {data.get('chapters_read', 0)}\n")
        minutes = data.get("minutes_watched", 0)
        if minutes:
            content.append(f"  Watch time: {minutes // 60}h {minutes % 60}m\n")
        return Panel(content, title="Profile", border_style="cyan")
    return Panel("Not connected.", title="Profile", border_style="cyan")


def _render_settings() -> Panel:
    return Panel(
        "Run [bold]anicat settings[/bold] to edit configuration.\n"
        "Subcommands: [bold]path[/bold], [bold]view[/bold], [bold]open[/bold].",
        title="Settings",
        border_style="cyan",
    )


VIEW_RENDERERS: dict[str, Callable[[], Panel]] = {
    "home":          _render_home,
    "manga":         _render_manga,
    "search":        _render_search,
    "lists":         _render_lists,
    "downloads":     _render_downloads,
    "library":       _render_library,
    "schedule":      _render_schedule,
    "notifications": _render_notifications,
    "profile":       _render_profile,
    "settings":      _render_settings,
}

# ---------------------------------------------------------------------------
# Layout builder
# ---------------------------------------------------------------------------

def _build_layout(active_idx: int, content: Any) -> Layout:
    """Build a Rich Layout with sidebar + content."""
    layout = Layout()
    layout.split_row(
        Layout(name="sidebar", size=SIDEBAR_WIDTH),
        Layout(name="content", ratio=1),
    )

    # Sidebar
    sidebar_text = Text()
    sidebar_text.append(" ANICAT\n\n", style="bold magenta")
    for i, item in enumerate(NAV_ITEMS):
        if i == DIVIDER_INDEX:
            sidebar_text.append("─" * (SIDEBAR_WIDTH - 2) + "\n", style="dim")
        label = f" {item['icon']}  {item['label']}"
        if i == active_idx:
            sidebar_text.append(label + "\n", style="bold white on cyan")
        else:
            sidebar_text.append(label + "\n", style="dim")
    sidebar_text.append("\n q  Quit", style="dim")
    layout["sidebar"].update(Panel(sidebar_text, box=box.SIMPLE, border_style="cyan"))

    # Content
    layout["content"].update(Panel(content, padding=(0, 1)))

    return layout

# ---------------------------------------------------------------------------
# Main TUI entry point (registered as a session menu)
# ---------------------------------------------------------------------------

@session.menu
def app_home(ctx: Context, state: State) -> State | InternalDirective:
    """Launch the app-style TUI with sidebar navigation."""
    ctx.feedback.clear_console()

    active_idx = 0
    console = Console()

    def refresh():
        view_id = NAV_ITEMS[active_idx]["id"]
        try:
            content = VIEW_RENDERERS.get(view_id, lambda: Panel("Coming soon..."))()
        except Exception:
            content = Panel("Could not load this view.", title="Error", border_style="red")
        return _build_layout(active_idx, content)

    layout = refresh()

    with Live(layout, console=console, screen=True, refresh_per_second=10) as live:
        while True:
            key = _get_key()
            if key in ("q", "Q", "\x03"):  # q or Ctrl-C
                return InternalDirective.BACK
            if key == "up":
                active_idx = (active_idx - 1) % len(NAV_ITEMS)
            elif key == "down":
                active_idx = (active_idx + 1) % len(NAV_ITEMS)
            elif key in ("\r", "\n", " "):  # Enter or Space
                view_id = NAV_ITEMS[active_idx]["id"]
                if view_id == "settings":
                    return InternalDirective.CONFIG_EDIT
                # For other views, stay in the TUI — just refresh content
                # (content is already shown, Enter highlights the selection)
            else:
                continue
            live.update(refresh())

    return InternalDirective.BACK
