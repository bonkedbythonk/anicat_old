import logging
from typing import Optional

from ..mini_anilist import search_for_manga_with_anilist
from ..base import BaseMangaProvider
from ..common import fetch_manga_info_from_bal
from ..params import MangaParams, MangaSearchParams
from ..types import Manga, MangaChapter, MangaSearchResult, MangaSearchResults

logger = logging.getLogger(__name__)


class MangaDexApi(BaseMangaProvider):
    HEADERS = {}

    def search(self, params: MangaSearchParams) -> Optional[MangaSearchResults]:
        try:
            results = search_for_manga_with_anilist(params.query)
            if not results:
                return MangaSearchResults(results=[])

            search_results = []
            for r in results:
                search_results.append(
                    MangaSearchResult(
                        id=r["url"],  # This is the AniList ID for MangaDex logic
                        title=r["title"] or "Unknown Manga",
                        cover_image=r["cover_image"],
                    )
                )
            return MangaSearchResults(results=search_results)
        except Exception as e:
            logger.error(f"[MANGADEX-ERROR]: {e}")
            return None

    def get(self, params: MangaParams) -> Optional[Manga]:
        try:
            bal_data = fetch_manga_info_from_bal(params.id)
            if (
                not bal_data
                or "Sites" not in bal_data
                or "Mangadex" not in bal_data["Sites"]
            ):
                return None

            mangadex_sites = bal_data["Sites"].get("Mangadex")
            if not mangadex_sites:
                return None

            manga_id, MangaDexManga = next(iter(mangadex_sites.items()))

            # Fetch actual chapters from MangaDex API
            chapters = []
            offset = 0
            while True:
                chapters_url = f"https://api.mangadex.org/manga/{manga_id}/feed?translatedLanguage[]=en&limit=500&offset={offset}&order[chapter]=asc&contentRating[]=safe&contentRating[]=suggestive&contentRating[]=erotica&contentRating[]=pornographic"
                resp = self.client.get(chapters_url)
                if not resp.is_success:
                    break
                try:
                    data = resp.json()
                except Exception:
                    break
                for item in data.get("data", []):
                    attr = item.get("attributes", {})
                    chapters.append(
                        MangaChapter(
                            number=attr.get("chapter") or "0",
                            title=attr.get("title") or f"Chapter {attr.get('chapter')}",
                            url=item.get("id"),
                        )
                    )

                total = data.get("total", 0)
                offset += 500
                if offset >= total:
                    break

            return Manga(
                id=manga_id,
                title=MangaDexManga.get("title", params.query),
                cover_image=MangaDexManga.get("image"),
                chapters=chapters,
            )
        except Exception as e:
            logger.error(f"[MANGADEX-ERROR]: {e}")
            return None

    def get_chapter_thumbnails(self, manga_id: str, chapter: str):
        # Note: chapter here is the MangaDex chapter ID (UUID)
        try:
            chapters_thumbnails_url = (
                f"https://api.mangadex.org/at-home/server/{chapter}"
            )
            chapter_thumbnails_response = self.client.get(chapters_thumbnails_url)
            if not chapter_thumbnails_response.is_success:
                return None

            chapter_thumbnails_info = chapter_thumbnails_response.json()
            base_url = chapter_thumbnails_info["baseUrl"]
            hash = chapter_thumbnails_info["chapter"]["hash"]
            return {
                "thumbnails": [
                    f"{base_url}/data/{hash}/{chapter_thumbnail}"
                    for chapter_thumbnail in chapter_thumbnails_info["chapter"]["data"]
                ],
                "title": f"Chapter {chapter}",  # We don't have the title here easily
            }
        except Exception as e:
            logger.error(f"[MANGADEX-ERROR]: {e}")
            return None
