import logging
import httpx

logger = logging.getLogger(__name__)

ANILIST_ENDPOINT = "https://graphql.anilist.co"

SEARCH_MANGA_QUERY = """
query ($query: String) {
  Page(page: 1, perPage: 10) {
    media(search: $query, type: MANGA) {
      id
      title {
        romaji
        english
      }
      coverImage {
        large
      }
    }
  }
}
"""


def search_for_manga_with_anilist(query: str):
    """Simple search for manga on AniList."""
    try:
        with httpx.Client() as client:
            response = client.post(
                ANILIST_ENDPOINT,
                json={"query": SEARCH_MANGA_QUERY, "variables": {"query": query}},
            )
            if response.is_success:
                data = response.json()
                results = []
                for media in data.get("data", {}).get("Page", {}).get("media", []):
                    results.append(
                        {
                            "title": media["title"]["english"]
                            or media["title"]["romaji"],
                            "url": str(media["id"]),
                            "cover_image": media["coverImage"]["large"],
                        }
                    )
                return results
            return []
    except Exception as e:
        logger.error(f"[MINI-ANILIST-ERROR]: {e}")
        return []
