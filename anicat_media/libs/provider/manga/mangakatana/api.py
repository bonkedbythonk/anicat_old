import logging
import re
from typing import Optional
from urllib.parse import quote_plus

from ..base import BaseMangaProvider
from .constants import HEADERS, SEARCH_URL, BASE_URL
from ..params import MangaParams, MangaSearchParams
from ..types import Manga, MangaChapter, MangaSearchResult, MangaSearchResults

logger = logging.getLogger(__name__)


class MangaKatanaApi(BaseMangaProvider):
    """MangaKatana scraper implementing the manga provider interface."""

    HEADERS = HEADERS

    def search(self, params: MangaSearchParams) -> Optional[MangaSearchResults]:
        try:
            encoded_query = quote_plus(params.query)
            url = f"{SEARCH_URL}?search={encoded_query}&search_by=book_name"
            response = self.client.get(url, follow_redirects=True)
            if not response.is_success:
                logger.error(
                    f"[MANGAKATANA] Search request failed: {response.status_code}"
                )
                return None

            html = response.text

            # If the search redirects directly to a manga page (single result),
            # handle that case
            if "/manga/" in str(response.url) and "search" not in str(response.url):
                results = self._parse_single_result(html, str(response.url))
            else:
                results = self._parse_search_results(html)

            if not results:
                return MangaSearchResults(results=[])

            search_results = []
            for r in results:
                search_results.append(
                    MangaSearchResult(
                        id=r["id"], title=r["title"], cover_image=r["cover_image"]
                    )
                )
            return MangaSearchResults(results=search_results)

        except Exception as e:
            logger.error(f"[MANGAKATANA] Search error: {e}")
            return None

    def get(self, params: MangaParams) -> Optional[Manga]:
        try:
            response = self.client.get(params.id, follow_redirects=True)
            if not response.is_success:
                logger.error(
                    f"[MANGAKATANA] Manga fetch failed: {response.status_code}"
                )
                return None

            html = response.text
            data = self._parse_manga_detail(html, params.id)
            if not data:
                return None

            chapters = []
            for ch in data["availableChapters"]:
                # Extract chapter number from title or URL
                # Title usually looks like "Chapter 1", "Chapter 1.5", etc.
                num_match = re.search(r"Chapter\s+(\d+\.?\d*)", ch["title"])
                num = num_match.group(1) if num_match else "0"

                chapters.append(
                    MangaChapter(number=num, title=ch["title"], url=ch["url"])
                )

            # Reverse chapters to be in ascending order if needed
            # MangaKatana usually lists them newest first
            chapters.reverse()

            return Manga(
                id=data["id"],
                title=data["title"],
                cover_image=data["poster"],
                chapters=chapters,
            )

        except Exception as e:
            logger.error(f"[MANGAKATANA] Get manga error: {e}")
            return None

    def _parse_search_results(self, html: str):
        try:
            from lxml import html as lxml_html
        except ImportError:
            return self._parse_search_results_fallback(html)

        try:
            tree = lxml_html.fromstring(html)
            items = tree.xpath('//*[@id="book_list"]//*[contains(@class, "item")]')

            results = []
            for item in items:
                title_el = item.xpath('.//h3[contains(@class, "title")]//a')
                if not title_el:
                    continue

                manga_url = title_el[0].get("href", "")
                title = title_el[0].text_content().strip()
                if manga_url and not manga_url.startswith("http"):
                    manga_url = f"{BASE_URL}{manga_url}"

                cover_els = item.xpath(".//img")
                cover_image = ""
                if cover_els:
                    cover_image = cover_els[0].get("src", "")

                results.append(
                    {
                        "title": title,
                        "id": manga_url,
                        "cover_image": cover_image,
                    }
                )

            return results if results else None

        except Exception as e:
            logger.error(f"[MANGAKATANA] Parse search results error: {e}")
            return None

    def _parse_search_results_fallback(self, html: str):
        results = []
        pattern = re.compile(
            r'<h3[^>]*class="[^"]*title[^"]*"[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            manga_url = match.group(1)
            title = match.group(2).strip()
            if manga_url and not manga_url.startswith("http"):
                manga_url = f"{BASE_URL}{manga_url}"
            results.append(
                {
                    "title": title,
                    "id": manga_url,
                    "cover_image": "",
                }
            )

        return results if results else None

    def _parse_single_result(self, html: str, url: str):
        try:
            from lxml import html as lxml_html

            tree = lxml_html.fromstring(html)
            title_el = tree.xpath("//h1")
            title = title_el[0].text_content().strip() if title_el else "Unknown"

            cover_els = tree.xpath('//*[contains(@class, "cover")]//img')
            cover_image = cover_els[0].get("src", "") if cover_els else ""

            return [
                {
                    "title": title,
                    "id": url,
                    "cover_image": cover_image,
                }
            ]
        except Exception as e:
            logger.error(f"[MANGAKATANA] Parse single result error: {e}")
            return [{"title": "Unknown", "id": url, "cover_image": ""}]

    def _parse_manga_detail(self, html: str, manga_url: str):
        try:
            from lxml import html as lxml_html
        except ImportError:
            return self._parse_manga_detail_fallback(html, manga_url)

        try:
            tree = lxml_html.fromstring(html)

            # Extract title
            title_el = tree.xpath('//h1[contains(@class, "heading")]') or tree.xpath(
                "//h1"
            )
            title = title_el[0].text_content().strip() if title_el else "Unknown"

            # Extract cover image
            cover_els = tree.xpath('//*[contains(@class, "cover")]//img') or tree.xpath(
                '//*[contains(@class, "media")]//img'
            )
            poster = cover_els[0].get("src", "") if cover_els else ""

            # Extract chapters
            chapter_els = tree.xpath(
                '//*[contains(@class, "chapters")]//*[contains(@class, "chapter")]//a'
            )

            chapters = []
            for ch_el in chapter_els:
                ch_url = ch_el.get("href", "")
                ch_title = ch_el.text_content().strip()
                if ch_url and not ch_url.startswith("http"):
                    ch_url = f"{BASE_URL}{ch_url}"
                if ch_url and ch_title:
                    chapters.append(
                        {
                            "title": ch_title,
                            "url": ch_url,
                        }
                    )

            return {
                "id": manga_url,
                "title": title,
                "poster": poster,
                "availableChapters": chapters,
            }

        except Exception as e:
            logger.error(f"[MANGAKATANA] Parse manga detail error: {e}")
            return None

    def _parse_manga_detail_fallback(self, html: str, manga_url: str):
        # Extract title
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        title = title_match.group(1).strip() if title_match else "Unknown"

        # Extract chapters
        chapter_pattern = re.compile(
            r'<div[^>]*class="[^"]*chapter[^"]*"[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )
        chapters = []

        chapters_block_match = re.search(
            r'<div[^>]*class="[^"]*chapters[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        search_html = chapters_block_match.group(1) if chapters_block_match else html

        for match in chapter_pattern.finditer(search_html):
            ch_url = match.group(1)
            if ch_url and not ch_url.startswith("http"):
                ch_url = f"{BASE_URL}{ch_url}"
            chapters.append(
                {
                    "title": match.group(2).strip(),
                    "url": ch_url,
                }
            )

        return {
            "id": manga_url,
            "title": title,
            "poster": "",
            "availableChapters": chapters,
        }

    def get_chapter_thumbnails(self, manga_id: str, chapter: str):
        try:
            response = self.client.get(chapter, follow_redirects=True)
            if not response.is_success:
                logger.error(
                    f"[MANGAKATANA] Chapter fetch failed: {response.status_code}"
                )
                return None

            html = response.text
            return self._parse_chapter_pages(html, chapter)

        except Exception as e:
            logger.error(f"[MANGAKATANA] Get chapter thumbnails error: {e}")
            return None

    def _parse_chapter_pages(self, html: str, chapter_url: str):
        js_array_pattern = re.compile(r"var\s+\w+\s*=\s*\[([^\]]+)\]\s*;", re.DOTALL)

        image_urls: list[str] = []
        for match in js_array_pattern.finditer(html):
            array_content = match.group(1)
            url_pattern = re.compile(
                r"['\"]([^'\"]+(?:\.jpg|\.png|\.webp|\.jpeg)[^'\"]*)['\"]",
                re.IGNORECASE,
            )
            urls = url_pattern.findall(array_content)
            if urls and len(urls) > 1:
                image_urls = urls
                break

        if not image_urls:
            img_pattern = re.compile(
                r'<img[^>]+src=["\']([^"\']+(?:\.jpg|\.png|\.webp|\.jpeg)[^"\']*)["\'][^>]*>',
                re.IGNORECASE,
            )
            imgs_section = re.search(
                r'id=["\']imgs["\'][^>]*>(.*?)</div>', html, re.DOTALL
            )
            if imgs_section:
                image_urls = img_pattern.findall(imgs_section.group(1))
            else:
                all_imgs = img_pattern.findall(html)
                image_urls = [
                    url for url in all_imgs if "mangakatana" in url and "/manga/" in url
                ]

        if not image_urls:
            logger.warning(f"[MANGAKATANA] No images found for chapter: {chapter_url}")
            return None

        chapter_title = chapter_url.rstrip("/").split("/")[-1]

        return {
            "thumbnails": image_urls,
            "title": chapter_title,
        }
