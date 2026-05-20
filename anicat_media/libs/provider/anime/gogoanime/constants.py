# AniNeko (formerly GogoAnime) — constants

ANINEKO_DOMAIN = "anineko.to"
ANINEKO_BASE_URL = f"https://{ANINEKO_DOMAIN}"

# Primary endpoints
SEARCH_URL = f"{ANINEKO_BASE_URL}/browser"
WATCH_URL = f"{ANINEKO_BASE_URL}/watch"

# The Referer header is required for successful requests.
AJAX_REFERER_HEADER = f"{ANINEKO_BASE_URL}/"
