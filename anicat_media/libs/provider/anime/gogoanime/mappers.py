"""Mappers for converting AniNeko HTML to generic provider models."""

import re
from typing import Optional

from ....provider.anime.types import (
    Anime,
    AnimeEpisodes,
    PageInfo,
    SearchResult,
    SearchResults,
)
from ....provider.scraping.html_parser import (
    get_elements_by_class,
)


def _parse_episode_counts(element_html: str) -> tuple[int, int]:
    """Extract sub (CC) and dub counts from a search result card."""
    sub_count = 0
    dub_count = 0

    # CC badge indicates sub count
    cc_match = re.search(r"CC\s*(\d+)", element_html)
    if cc_match:
        sub_count = int(cc_match.group(1))

    # Look for dub indicator
    if "DUB" in element_html.upper():
        # Try to find dub count near DUB indicator
        dub_match = re.search(r"DUB\s*(\d+)", element_html, re.IGNORECASE)
        if dub_match:
            dub_count = int(dub_match.group(1))
        else:
            dub_count = sub_count  # many shows have matching sub/dub counts

    return sub_count, dub_count


def map_to_search_results(
    raw_html: str,
) -> Optional[SearchResults]:
    """
    Map AniNeko browse/search page HTML to generic SearchResults.

    Each result is an <article> element containing a link to /watch/{slug},
    an image, type badge, CC count, title, and genres.
    """
    # Find article elements that contain watch links (search result cards)
    articles = get_elements_by_class("", raw_html)
    if not articles:
        return None

    # More targeted: find all <article> elements by tag
    from ....provider.scraping.html_parser import _default_parser as parser

    parsed = parser.parse(raw_html)
    article_elements = parsed.find_by_tag("article")

    results: list[SearchResult] = []
    for article in article_elements:
        raw_article = _element_to_string(article, raw_html)
        if not raw_article:
            continue

        # Extract the link to get slug
        link_match = re.search(r'href="(/watch/[^"]+)"', raw_article)
        if not link_match:
            continue
        slug = link_match.group(1).replace("/watch/", "")

        # Extract title from heading
        title_match = re.search(
            r"<h[23][^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)?[^<]*)</h[23]>", raw_article
        )
        if not title_match:
            continue
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        # Extract poster image
        poster = None
        img_match = re.search(r'<img[^>]+src="([^"]+)"', raw_article)
        if img_match:
            poster = img_match.group(1)

        # Extract type badge
        media_type = None
        type_match = re.search(
            r'<[^>]+class="[^"]*\bbadge\b[^"]*"[^>]*>([^<]+)<', raw_article
        )
        if not type_match:
            type_match = re.search(r'alt="(TV|Movie|OVA|Special|ONA)"', raw_article)
        if type_match:
            media_type = type_match.group(1).strip()

        # Extract episode counts
        sub_count, dub_count = _parse_episode_counts(raw_article)

        # Extract year
        year = None
        year_match = re.search(
            r"(?:Release|Year).*?(\d{4})", raw_article, re.IGNORECASE
        )
        if not year_match:
            year_match = re.search(r">\s*(\d{4})\s*<", raw_article)
        if year_match:
            year = year_match.group(1)

        sub_list = [str(i) for i in range(1, sub_count + 1)]
        dub_list = [str(i) for i in range(1, dub_count + 1)]

        results.append(
            SearchResult(
                id=slug,
                title=title,
                poster=poster,
                episodes=AnimeEpisodes(sub=sub_list, dub=dub_list),
                media_type=media_type,
                year=year,
            )
        )

    if not results:
        return None

    # Parse pagination
    total_pages = 1
    pagination_links = re.findall(r"\?page=(\d+)", raw_html)
    if pagination_links:
        try:
            total_pages = max(int(p) for p in pagination_links)
        except ValueError:
            pass

    return SearchResults(
        page_info=PageInfo(total=total_pages),
        results=results,
    )


def map_to_anime_result(slug: str, raw_html: str) -> Optional[Anime]:
    """
    Map AniNeko anime detail page HTML to generic Anime object.

    Extracts title, type, status, year, episode list, poster, and sub/dub flags.
    """
    # Extract title
    title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", raw_html)
    if not title_match:
        # Try og:title or other meta
        title_match = re.search(r"<title>([^-]+)", raw_html)
    if not title_match:
        return None
    title = title_match.group(1).strip()

    # Extract episode numbers from episode list
    ep_matches = re.findall(r"/watch/" + re.escape(slug) + r"/ep-(\d+)", raw_html)
    episode_numbers = sorted(set(ep_matches), key=int) if ep_matches else []

    # Extract sub/dub availability
    has_dub = "DUB" in raw_html

    # Extract type
    media_type = None
    type_match = re.search(r">\s*(TV|Movie|OVA|Special|ONA)\s*<", raw_html)
    if type_match:
        media_type = type_match.group(1)

    # Extract year
    year = None
    year_match = re.search(r">\s*(\d{4})\s*<", raw_html)
    if year_match:
        year = year_match.group(1)

    # Extract poster
    poster = None
    poster_match = re.search(
        r'<img[^>]+src="([^"]+)"[^>]*alt="[^"]*' + re.escape(title[:20]) + r'[^"]*"',
        raw_html,
    )
    if not poster_match:
        poster_match = re.search(
            r'<img[^>]+src="(https://[^"]+/(?:poster|cover|image)[^"]+)"', raw_html
        )
    if not poster_match:
        # Just grab the first image in the hero area
        poster_match = re.search(
            r'<img[^>]+src="(https://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', raw_html
        )
    if poster_match:
        poster = poster_match.group(1)

    sub_list = (
        [str(i) for i in range(1, len(episode_numbers) + 1)]
        if episode_numbers
        else episode_numbers
    )
    dub_list = (
        [str(i) for i in range(1, len(episode_numbers) + 1)]
        if has_dub and episode_numbers
        else []
    )

    return Anime(
        id=slug,
        title=title,
        episodes=AnimeEpisodes(
            sub=sub_list,
            dub=dub_list,
            raw=[],
        ),
        type=media_type,
        poster=poster,
        year=year,
    )


def extract_episode_servers(raw_html: str) -> list[tuple[str, str]]:
    """
    Extract server embed URLs from an episode page.

    Returns a list of (server_name, embed_url) tuples from data-video attributes.

    The episode page has server selection buttons with data-video attributes
    pointing to external embed providers (VibePlayer, OtakuVid, etc.).
    """
    servers: list[tuple[str, str]] = []

    # Extract data-video attributes from server buttons/elements
    data_video_matches = re.findall(r'data-video="([^"]+)"', raw_html)

    # Extract associated server names
    server_name_matches = re.findall(
        r"(?:server-name|data-server)[^>]*>\s*([^<]+)\s*<",
        raw_html,
        re.IGNORECASE,
    )

    # If no specific server names, use generic names
    if not server_name_matches:
        # Look for text in buttons near the data-video attributes
        server_name_matches = re.findall(
            r"<(?:button|span|div)[^>]*>\s*(?:<[^>]+>)?\s*(?:Hard Sub|Sort Sub|Raw|HD|SD|Stream \d+)[^<]*<",
            raw_html,
            re.IGNORECASE,
        )
        # Clean up
        server_name_matches = [
            re.sub(r"<[^>]+>", "", m).strip() for m in server_name_matches
        ]

    for i, embed_url in enumerate(data_video_matches):
        name = (
            server_name_matches[i]
            if i < len(server_name_matches)
            else f"Server {i + 1}"
        )
        servers.append((name.strip(), embed_url))

    return servers


def _element_to_string(element: dict, raw_html: str) -> Optional[str]:
    """Convert a parsed element dict back to its raw HTML string representation."""
    try:
        start_pos = element.get("start_pos", (0, 0))
        if isinstance(start_pos, tuple) and len(start_pos) == 2:
            # start_pos is (line, col) — approximate using character offset
            # For simplicity, use regex to find the element in raw_html
            tag = element.get("tag", "div")
            # Find by tag + some content
            pattern = re.compile(
                rf"<{tag}\b[^>]*>.*?</{tag}>", re.DOTALL | re.IGNORECASE
            )
            matches = list(pattern.finditer(raw_html))
            # Return first match if we can't be more precise
            if matches:
                return matches[0].group(0)
    except Exception:
        pass
    return None
