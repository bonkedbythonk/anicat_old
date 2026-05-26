"""Shared regex patterns used across the downloader modules."""

import re

# Matches magnet: links and .torrent URLs
TORRENT_REGEX = re.compile(
    r"^(magnet:\?|https?://.*\.torrent)",
    re.IGNORECASE,
)
