from dataclasses import dataclass


@dataclass(frozen=True)
class Icons:
    # Categories / Status
    TRENDING: str = " "
    RECENT: str = " "
    WATCHING: str = " "
    READING: str = " "
    REWATCHING: str = " "
    PAUSED: str = " "
    PLANNED: str = " "
    COMPLETED: str = " "
    DROPPED: str = " "
    POPULAR: str = " "
    TOP_SCORED: str = " "
    FAVOURITES: str = " "
    RANDOM: str = " "
    UPCOMING: str = " "
    UPDATED: str = " "
    UPDATE: str = "󰚰 "
    LOGIN: str = "󰍂 "
    LOGOUT: str = "󰍃 "

    # Actions
    SEARCH: str = " "
    SEARCH_MANGA: str = " "
    DYNAMIC_SEARCH: str = " "
    DOWNLOADS: str = " "
    PLAY: str = " "
    EPISODES: str = " "
    INFO: str = " "
    BACK: str = " "
    EXIT: str = " "
    EDIT: str = " "
    SETTINGS: str = " "
    MANAGE: str = " "
    TRAILER: str = " "
    RECOMMENDATIONS: str = " "
    RELATIONS: str = " "
    CHARACTERS: str = " "
    SCHEDULE: str = " "
    REVIEWS: str = " "
    ADD: str = " "
    SCORE: str = " "
    BROWSER: str = " "
    PROVIDER: str = " "
    TOGGLE: str = " "
    SAVE: str = " "

    # Player controls
    NEXT: str = "󰒭 "
    PREVIOUS: str = "󰒮 "
    REPLAY: str = " "
    HOME: str = " "

    # Feedback
    SUCCESS: str = " "
    ERROR: str = " "
    WARNING: str = " "
    PAUSE: str = " "

    # UI Elements
    STATS: str = "📊 "
    GENRE: str = "🎭 "
    FORMAT: str = "📺 "
    STAR: str = "⭐ "
    BELL: str = "🔔 "
    SPARKLES: str = "✨ "

    # Visual indicators
    NEW: str = "🔹"  # Keeping this as it's a good indicator, maybe NF equivalent later
    DOT: str = " "
    LIGHTBULB: str = "󰌵 "

    def get(self, icon_name: str, enabled: bool = True) -> str:
        if not enabled:
            return ""
        return getattr(self, icon_name, "")


# Global theme instance
ICONS = Icons()
