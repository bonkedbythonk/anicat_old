from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import asyncio
import ipaddress
import time
import json
import urllib.parse
import httpx
import logging
from ...core.constants import LOCAL_API_ORIGIN
from ...libs.player.params import PlayerParams
from ...libs.player.types import PlayerResult
from .status import set_playback

logger = logging.getLogger(__name__)


class PlaybackTrackRequest(BaseModel):
    media_id: int
    episode: str
    current_time: float
    total_time: float


router = APIRouter()
_active_requests: dict[int, float] = {}  # media_id -> timestamp
_active_locks: dict[int, asyncio.Lock] = {}  # media_id -> lock

from ..deps import get_ctx

# ── Shared proxy client (M4: connection pooling across segment requests) ──
_proxy_client: httpx.AsyncClient | None = None


def _get_proxy_client() -> httpx.AsyncClient:
    """Return a persistent httpx.AsyncClient for HLS proxy requests."""
    global _proxy_client
    if _proxy_client is None or _proxy_client.is_closed:
        _proxy_client = httpx.AsyncClient(
            follow_redirects=True,
            verify=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
    return _proxy_client


# ── URL validation for proxy (C1: SSRF prevention) ──
_PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _validate_proxy_url(raw_url: str) -> str:
    """Validate that a proxy target URL is safe (public HTTP/HTTPS only)."""
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail=f"Unsupported URL scheme: {parsed.scheme}"
        )
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL has no hostname")
    try:
        addr = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # Not an IP literal — resolve and validate
        try:
            import socket
            resolved = socket.getaddrinfo(parsed.hostname, None)
            for _, _, _, _, sockaddr in resolved:
                addr = ipaddress.ip_address(sockaddr[0])
                for net in _PRIVATE_IP_RANGES:
                    if addr in net:
                        raise HTTPException(
                            status_code=400,
                            detail=f"URL resolves to private/internal address: {addr}",
                        )
        except HTTPException:
            raise
        except Exception:
            pass  # DNS resolution failure — allow through (will fail downstream)
    else:
        for net in _PRIVATE_IP_RANGES:
            if addr in net:
                raise HTTPException(
                    status_code=400,
                    detail=f"URL targets private/internal address: {addr}",
                )
    return raw_url


def _validate_open_url(raw_url: str) -> str:
    """Validate that an open_link URL is safe (HTTP/HTTPS only)."""
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail=f"Unsupported URL scheme: {parsed.scheme}"
        )
    return raw_url


# ── Shared AniSkip fetch helper (M5: async) ──
def _to_hhmmss(sec) -> str | None:
    if sec is None:
        return None
    try:
        total_sec = int(float(sec))
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except (ValueError, TypeError):
        return None


async def _fetch_aniskip_times(media_id: int, mal_id: int | None, episode: str) -> list[dict]:
    """Fetch AniSkip skip times asynchronously for a given media/episode."""
    try:
        query_id = mal_id if mal_id not in (None, 0) else media_id
        ep_num = int(episode)
        url = f"https://api.aniskip.com/v2/skip-times/{query_id}/{ep_num}?types[]=op&types[]=ed&episodeLength=0"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("found") and data.get("results"):
                return [
                    {
                        "type": res.get("skipType"),
                        "start": res.get("interval", {}).get("startTime", 0),
                        "end": res.get("interval", {}).get("endTime", 0),
                    }
                    for res in data["results"]
                ]
    except Exception as e:
        logger.debug(f"Failed to fetch AniSkip times: {e}")
    return []


def _play_and_track(ctx, params, anime, media_item, local: bool = False):
    """Background task to play media and then track watch history."""
    try:
        from ...libs.provider.anime.types import SearchResult as AnimeSearchResult, Anime as AnimeObj
        from ...libs.provider.anime.params import AnimeParams

        # M3: Only re-fetch if we received a SearchResult (not already a full Anime)
        if anime and isinstance(anime, AnimeSearchResult) and not isinstance(anime, AnimeObj):
            try:
                full_anime = ctx.provider.get(
                    AnimeParams(
                        id=anime.id,
                        query=media_item.title.english or media_item.title.romaji or "",
                    )
                )
                if full_anime:
                    anime = full_anime
            except Exception as e:
                logger.error(
                    f"Failed to resolve full anime details in background playback: {e}"
                )

        player_result = ctx.player.play(
            params, anime=anime, media_item=media_item, local=local
        )
        if player_result:
            ctx.watch_history.track(media_item, player_result)
            ctx.data_version += 1
    except Exception as e:
        logger.error(f"Error in background playback tracking: {e}", exc_info=True)


async def _resolve_episode_stream(media_id: int, episode: Optional[str] = None):
    """
    Shared helper to resolve media search results, select the best anime match,
    retrieve streaming servers, select the preferred quality link, and determine resume time.
    """
    ctx = get_ctx()
    media_item = ctx.media_api.get_media_item(media_id)
    if not media_item:
        raise HTTPException(status_code=404, detail="Media not found")

    # 1. Determine next episode and start time
    start_time = None
    if not episode:
        episode, start_time = ctx.watch_history.get_episode(media_item)
        episode = str(episode) if episode else "1"
    else:
        # If episode is provided, check if we have a resume position for it
        _, resume_time = ctx.watch_history.get_episode(media_item)
        current_progress = (
            str(media_item.user_status.progress) if media_item.user_status else "0"
        )
        if episode == str(int(current_progress) + 1) or episode == current_progress:
            start_time = resume_time

    title = media_item.title.romaji or media_item.title.english
    from .media import get_anime_ref

    anime_id, record = await get_anime_ref(ctx, media_item, media_id)
    if not anime_id:
        raise HTTPException(status_code=404, detail=f"No results found for {title}")

    from ...libs.provider.anime.params import AnimeParams

    full_anime = ctx.provider.get(AnimeParams(id=anime_id, query=title))
    if not full_anime:
        raise HTTPException(status_code=404, detail="Anime details not found")

    # 3. Get streams
    from ...libs.provider.anime.params import EpisodeStreamsParams

    streams_iter = ctx.provider.episode_streams(
        EpisodeStreamsParams(
            query=title,
            anime_id=anime_id,
            episode=episode,
            translation_type=ctx.config.stream.translation_type,
        )
    )

    # UX-17: Graceful degradation — return structured error for scraping failures
    if not streams_iter:
        raise HTTPException(
            status_code=502,
            detail="The streaming provider could not find any servers for this episode. "
                   "The site may be restructuring or the episode may have been removed.",
        )

    # Get first server
    try:
        server = next(streams_iter)
    except StopIteration:
        raise HTTPException(status_code=404, detail="No stream servers available")

    if not server.links:
        raise HTTPException(status_code=404, detail="No links found on server")

    preferred_quality = ctx.config.stream.quality
    selected_link = next(
        (link for link in server.links if link.quality == preferred_quality), None
    )

    # UX-18: Quality fallback — try lower qualities if preferred unavailable
    if not selected_link:
        quality_order = ["1080", "720", "480", "360"]
        try:
            pref_idx = quality_order.index(preferred_quality)
            for fallback_q in quality_order[pref_idx + 1:]:
                fallback = next((link for link in server.links if link.quality == fallback_q), None)
                if fallback:
                    logger.info(f"Quality fallback: {preferred_quality}p not available, using {fallback_q}p")
                    selected_link = fallback
                    break
        except (ValueError, IndexError):
            pass

    if not selected_link:
        try:
            selected_link = sorted(
                server.links, key=lambda x: int(x.quality), reverse=True
            )[0]
        except Exception:
            selected_link = server.links[-1]

    stream_link = selected_link.link

    return {
        "url": stream_link,
        "title": title,
        "episode": episode,
        "headers": server.headers or {},
        "start_time": start_time,
        "anime_ref": full_anime,
        "media_item": media_item,
        "subtitles": [s.url for s in server.subtitles] if server.subtitles else None,
    }


# ── Shared playback preparation (L3: deduplicates play_media / resolve_media_stream) ──

async def _prepare_playback(
    ctx,
    media_id: int,
    episode: str | None = None,
) -> dict:
    """
    Shared orchestration for play_media and resolve_media_stream.
    Returns a dict with keys: media_item, resolved_episode, start_time, is_local, file_path.
    """
    media_item = ctx.media_api.get_media_item(media_id)
    if not media_item:
        raise HTTPException(status_code=404, detail="Media not found")

    # Auto-add to user's watching list if not already tracked, or transition to watching if planning/paused/dropped
    should_update_status = False
    if not media_item.user_status:
        should_update_status = True
    else:
        from ...libs.media_api.types import UserMediaListStatus

        if media_item.user_status.status in (
            UserMediaListStatus.PLANNING,
            UserMediaListStatus.PAUSED,
            UserMediaListStatus.DROPPED,
        ):
            should_update_status = True

    if should_update_status:
        try:
            from ...libs.media_api.params import UpdateUserMediaListEntryParams
            from ...libs.media_api.types import UserMediaListStatus

            ctx.media_api.update_list_entry(
                UpdateUserMediaListEntryParams(
                    media_id=media_id,
                    status=UserMediaListStatus.WATCHING,
                )
            )
            media_item = ctx.media_api.get_media_item(media_id) or media_item
        except Exception as e:
            logger.warning(f"Failed to auto-add media {media_id} to watching list: {e}")

    resolved_episode = episode
    start_time = None
    if not resolved_episode:
        resolved_episode, start_time = ctx.watch_history.get_episode(media_item)
        resolved_episode = str(resolved_episode) if resolved_episode else "1"
    else:
        _, resume_time = ctx.watch_history.get_episode(media_item)
        current_progress = (
            str(media_item.user_status.progress) if media_item.user_status else "0"
        )
        if resolved_episode == str(int(current_progress) + 1) or resolved_episode == current_progress:
            start_time = resume_time

    # Check local downloads
    from ...cli.service.registry.models import DownloadStatus

    record = ctx.media_registry.get_media_record(media_id)
    ep_record = (
        next(
            (e for e in record.media_episodes if e.episode_number == resolved_episode),
            None,
        )
        if record and record.media_episodes
        else None
    )

    is_local = False
    file_path = None
    if ep_record and ep_record.download_status == DownloadStatus.COMPLETED and ep_record.file_path:
        from pathlib import Path
        path_obj = Path(ep_record.file_path)
        if path_obj.exists():
            is_local = True
            file_path = path_obj

    return {
        "media_item": media_item,
        "resolved_episode": resolved_episode,
        "start_time": start_time,
        "is_local": is_local,
        "file_path": file_path,
    }


@router.post("/play/{media_id}")
async def play_media(
    media_id: int,
    background_tasks: BackgroundTasks,
    episode: str | None = None,
    fullscreen: bool = False,
):
    """
    Smart Play: Finds the next episode and triggers playback in MPV.
    """
    # M2: Thread-safe dedup via per-media lock
    lock = _active_locks.setdefault(media_id, asyncio.Lock())
    async with lock:
        now = time.time()
        if media_id in _active_requests:
            last_request_time = _active_requests[media_id]
            if now - last_request_time < 2.0:
                raise HTTPException(status_code=429, detail="Playback request already in progress")

        _active_requests[media_id] = now
        try:
            ctx = get_ctx()

            # L3: Shared preparation
            prep = await _prepare_playback(ctx, media_id, episode)
            media_item = prep["media_item"]
            resolved_episode = prep["resolved_episode"]
            start_time = prep["start_time"]
            is_local = prep["is_local"]
            file_path = prep["file_path"]

            # Check if Manga
            from ...libs.media_api.types import MediaType, MediaFormat

            is_manga = media_item.type == MediaType.MANGA or media_item.format in (
                MediaFormat.MANGA,
                MediaFormat.NOVEL,
                MediaFormat.ONE_SHOT,
            )

            title = media_item.title.romaji or media_item.title.english

            if is_manga:
                from ...libs.provider.manga.params import MangaParams
                from .media import get_manga_ref

                manga_id, record = await get_manga_ref(ctx, media_item, media_id)
                if not manga_id:
                    raise HTTPException(status_code=404, detail=f"No manga results found for {title}")

                full_manga = ctx.manga_provider.get(MangaParams(id=manga_id, query=title))
                if not full_manga or not full_manga.chapters:
                    raise HTTPException(status_code=404, detail="No chapters found")

                chapter = next(
                    (ch for ch in full_manga.chapters if ch.number == episode), None
                )
                if not chapter:
                    chapter = full_manga.chapters[0]
                    episode = chapter.number

                chapter_data = ctx.manga_provider.get_chapter_thumbnails(
                    full_manga.id, chapter.url or chapter.number
                )
                if not chapter_data or not chapter_data.get("thumbnails"):
                    raise HTTPException(status_code=404, detail="Failed to load chapter pages")

                ctx.watch_history.track(
                    media_item,
                    PlayerResult(episode=str(episode), stop_time=None, total_time=None),
                )
                ctx.data_version += 1

                set_playback(media_id=media_id, media_title=title, episode=str(episode))
                return {
                    "status": "reading",
                    "media": title,
                    "episode": episode,
                    "chapter_data": chapter_data,
                }

            # Local file playback
            if is_local and file_path is not None:
                local_title = f"{media_item.title.english or media_item.title.romaji}; Episode {resolved_episode}"
                if media_item.streaming_episodes and media_item.streaming_episodes.get(resolved_episode):
                    local_title = media_item.streaming_episodes[resolved_episode].title

                params = PlayerParams(
                    url=str(file_path),
                    query=media_item.title.english or media_item.title.romaji or "",
                    episode=resolved_episode,
                    title=local_title,
                    headers={},
                    start_time=start_time,
                    fullscreen=fullscreen,
                )

                # M5: Async AniSkip fetch
                skip_times = await _fetch_aniskip_times(media_id, media_item.id_mal, resolved_episode)
                if skip_times:
                    params = params.__class__(**{**params.__dict__, "skip_times": skip_times})

                background_tasks.add_task(
                    _play_and_track, ctx, params, anime=None, media_item=media_item, local=True
                )

                set_playback(
                    media_id=media_id,
                    media_title=media_item.title.english or media_item.title.romaji,
                    episode=resolved_episode,
                )
                return {
                    "status": "playing",
                    "media": media_item.title.english or media_item.title.romaji,
                    "episode": resolved_episode,
                    "local": True,
                }

            # Streaming playback — resolve stream
            resolved = await _resolve_episode_stream(media_id, episode)

            params = PlayerParams(
                url=resolved["url"],
                query=resolved["title"],
                episode=resolved["episode"],
                title=resolved["title"],
                headers=resolved["headers"],
                start_time=resolved["start_time"],
                fullscreen=fullscreen,
                subtitles=resolved.get("subtitles"),
            )

            # M5: Async AniSkip fetch
            skip_times = await _fetch_aniskip_times(media_id, media_item.id_mal, resolved["episode"])
            if skip_times:
                params = params.__class__(**{**params.__dict__, "skip_times": skip_times})

            background_tasks.add_task(
                _play_and_track, ctx, params, anime=resolved["anime_ref"], media_item=resolved["media_item"]
            )

            set_playback(
                media_id=media_id, media_title=resolved["title"], episode=resolved["episode"]
            )
            return {
                "status": "playing",
                "media": resolved["title"],
                "episode": resolved["episode"],
            }

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            _active_requests.pop(media_id, None)


@router.post("/play/{media_id}/resolve")
async def resolve_media_stream(media_id: int, episode: str | None = None):
    """
    Resolves the stream details for embedded in-app playback without launching MPV.

    Uses shared _prepare_playback for deduplicated logic (L3).
    """
    try:
        ctx = get_ctx()

        # L3: Shared preparation
        prep = await _prepare_playback(ctx, media_id, episode)
        media_item = prep["media_item"]
        resolved_episode = prep["resolved_episode"]
        start_time = prep["start_time"]
        is_local = prep["is_local"]

        if is_local:
            title = media_item.title.english or media_item.title.romaji
            set_playback(media_id=media_id, media_title=title, episode=resolved_episode)

            local_stream_url = f"{LOCAL_API_ORIGIN}/api/actions/local-file/{media_id}/{resolved_episode}"

            start_time_seconds = 0
            if start_time:
                from ...core.utils.converter import time_to_seconds

                if ":" in str(start_time):
                    start_time_seconds = time_to_seconds(start_time)
                else:
                    try:
                        start_time_seconds = float(start_time)
                    except (ValueError, TypeError):
                        start_time_seconds = 0

            return {
                "stream_url": local_stream_url,
                "raw_stream_url": local_stream_url,
                "title": title,
                "episode": resolved_episode,
                "start_time": start_time_seconds,
                "media_id": media_id,
                "headers": {},
                "local": True,
            }

        resolved = await _resolve_episode_stream(media_id, episode)

        set_playback(
            media_id=media_id,
            media_title=resolved["title"],
            episode=resolved["episode"],
        )

        raw_stream_url = resolved["url"]
        stream_headers = resolved["headers"]

        proxy_prefix = "/api/actions/proxy"
        headers_str = json.dumps(stream_headers)

        proxied_stream_url = f"{LOCAL_API_ORIGIN}{proxy_prefix}?url={urllib.parse.quote(raw_stream_url)}&headers={urllib.parse.quote(headers_str)}"

        start_time_seconds = 0
        if resolved["start_time"]:
            from ...core.utils.converter import time_to_seconds

            if ":" in str(resolved["start_time"]):
                start_time_seconds = time_to_seconds(resolved["start_time"])
            else:
                try:
                    start_time_seconds = float(resolved["start_time"])
                except (ValueError, TypeError):
                    start_time_seconds = 0

        return {
            "stream_url": proxied_stream_url,
            "raw_stream_url": raw_stream_url,
            "title": resolved["title"],
            "episode": resolved["episode"],
            "start_time": start_time_seconds,
            "media_id": media_id,
            "headers": stream_headers,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _proxy_m3u8_content(m3u8_content: str, base_url: str, headers_json: str) -> str:
    """
    Rewrites the HLS manifest so that all segment files (.ts) and sub-playlists
    point back to our local proxy as absolute URLs, injecting the required referer/user-agent headers.
    """
    lines = m3u8_content.splitlines()
    rewritten_lines = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("#"):
            # If the line contains URI= (like in EXT-X-KEY or EXT-X-MAP), rewrite the URI
            if 'URI="' in line_stripped:
                try:
                    parts = line_stripped.split('URI="')
                    prefix = parts[0]
                    suffix_parts = parts[1].split('"', 1)
                    uri = suffix_parts[0]
                    remaining = suffix_parts[1] if len(suffix_parts) > 1 else ""

                    absolute_uri = urllib.parse.urljoin(base_url, uri)
                    proxied_uri = f"{LOCAL_API_ORIGIN}/api/actions/proxy?url={urllib.parse.quote(absolute_uri)}&headers={urllib.parse.quote(headers_json)}"
                    rewritten_lines.append(f'{prefix}URI="{proxied_uri}"{remaining}')
                    continue
                except Exception:
                    pass
            rewritten_lines.append(line)
        else:
            # Segment or sub-playlist URL - converted to absolute proxy URLs
            absolute_url = urllib.parse.urljoin(base_url, line_stripped)
            proxied_url = f"{LOCAL_API_ORIGIN}/api/actions/proxy?url={urllib.parse.quote(absolute_url)}&headers={urllib.parse.quote(headers_json)}"
            rewritten_lines.append(proxied_url)
    return "\n".join(rewritten_lines)


@router.get("/proxy")
async def hls_stream_proxy(url: str, headers: str):
    """
    A local loopback HTTP proxy for HLS .m3u8 files and .ts media segments.
    Injects custom Referer and User-Agent headers, and rewrites playlists
    to ensure full cross-origin compatibility and cookie preservation inside WebViews.

    C1: Validates target URLs to prevent SSRF (scheme whitelist, IP allowlist).
    M4: Uses a persistent connection-pooled httpx.AsyncClient.
    """
    # C1: SSRF prevention
    _validate_proxy_url(url)

    try:
        req_headers = json.loads(headers)
    except Exception:
        req_headers = {}

    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
        )

    # M4: Use persistent pooled client
    client = _get_proxy_client()
    parsed = urllib.parse.urlparse(url)
    is_m3u8 = parsed.path.endswith(".m3u8") or "m3u8" in parsed.query
    is_key = "key" in parsed.path.lower() or parsed.path.endswith(".key")

    response = await client.get(url, headers=req_headers)

    if is_m3u8:
        # Rewrite playlist content
        rewritten_playlist = _proxy_m3u8_content(response.text, url, headers)
        return Response(
            content=rewritten_playlist,
            media_type="application/x-mpegURL",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "no-cache",
            },
        )
    elif is_key:
        # Return standard application/octet-stream for HLS decryption key files
        logger.info(
            f"[Proxy Key Debug] Fetching key {url} | Status: {response.status_code} | Length: {len(response.content)} | First 16 bytes: {response.content.hex()[:32]}"
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type="application/octet-stream",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=86400",
            },
        )
    else:
        # Detect fragmented MP4 segments vs MPEG-TS segments, even if disguised as images (e.g. .jpg)
        media_type = "video/mp2t"
        if len(response.content) >= 12:
            magic_slice = response.content[:12]
            if (
                b"ftyp" in magic_slice
                or b"moof" in magic_slice
                or b"styp" in magic_slice
                or b"mdat" in magic_slice
            ):
                media_type = "video/mp4"

        if len(response.content) < 5000:
            logger.warning(
                f"[Proxy Segment Debug] Warning: abnormally small segment {url} | Length: {len(response.content)} | Content preview: {response.content[:100]}"
            )
        else:
            logger.info(
                f"[Proxy Segment Debug] Fetched segment {url} | Status: {response.status_code} | Length: {len(response.content)} | Media Type: {media_type}"
            )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=media_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=86400",
            },
        )


@router.get("/local-file/{media_id}/{episode}")
async def serve_local_file(media_id: int, episode: str):
    """
    Serves a completed local download file for in-app browser playback.
    """
    ctx = get_ctx()
    record = ctx.media_registry.get_media_record(media_id)
    if not record or not record.media_episodes:
        raise HTTPException(status_code=404, detail="Media record not found")

    ep_record = next(
        (e for e in record.media_episodes if e.episode_number == episode), None
    )
    if not ep_record or not ep_record.file_path:
        raise HTTPException(status_code=404, detail="Downloaded episode not found")

    from pathlib import Path

    file_path = Path(ep_record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Local video file does not exist")

    if file_path.suffix == ".m3u8":
        import json

        headers = {}
        provider = (ep_record.provider_name or "").lower()
        if "animepahe" in provider:
            headers["Referer"] = "https://animepahe.pw"
        elif "hianime" in provider:
            headers["Referer"] = "https://hianime.to"
        elif "allanime" in provider:
            headers["Referer"] = "https://allanime.to"
        else:
            headers["Referer"] = "https://animepahe.pw"

        headers_json = json.dumps(headers)
        m3u8_content = file_path.read_text(encoding="utf-8")
        rewritten = _proxy_m3u8_content(
            m3u8_content, base_url="", headers_json=headers_json
        )
        return Response(
            content=rewritten,
            media_type="application/x-mpegURL",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "no-cache",
            },
        )

    import mimetypes

    media_type, _ = mimetypes.guess_type(str(file_path))
    if not media_type:
        media_type = "video/mp4"

    return FileResponse(path=str(file_path), media_type=media_type)


@router.post("/stream/renew")
async def renew_stream(media_id: int, episode: str):
    """
    C4: Re-resolve an expired or failed stream URL without re-initializing the
    entire playback flow. Called by the frontend when HLS.js encounters a
    network error during streaming (expired tokens, server-side kill).
    """
    try:
        resolved = await _resolve_episode_stream(media_id, episode)

        raw_stream_url = resolved["url"]
        stream_headers = resolved["headers"]

        proxy_prefix = "/api/actions/proxy"
        headers_str = json.dumps(stream_headers)

        proxied_stream_url = (
            f"{LOCAL_API_ORIGIN}{proxy_prefix}"
            f"?url={urllib.parse.quote(raw_stream_url)}"
            f"&headers={urllib.parse.quote(headers_str)}"
        )

        start_time_seconds = 0
        if resolved["start_time"]:
            from ...core.utils.converter import time_to_seconds
            if ":" in str(resolved["start_time"]):
                start_time_seconds = time_to_seconds(resolved["start_time"])
            else:
                try:
                    start_time_seconds = float(resolved["start_time"])
                except (ValueError, TypeError):
                    start_time_seconds = 0

        return {
            "stream_url": proxied_stream_url,
            "raw_stream_url": raw_stream_url,
            "title": resolved["title"],
            "episode": resolved["episode"],
            "start_time": start_time_seconds,
            "media_id": media_id,
            "headers": stream_headers,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_actions():
    return {"status": "ok", "message": "Actions router is active"}




class FrontendLogRequest(BaseModel):
    level: str
    message: str
    data: Optional[dict] = None


@router.post("/log")
async def log_frontend_message(req: FrontendLogRequest):
    import logging

    logger = logging.getLogger("frontend")
    formatted_msg = f"[Frontend {req.level.upper()}] {req.message}"
    if req.data:
        formatted_msg += f" | Data: {json.dumps(req.data)}"

    if req.level == "error":
        logger.error(formatted_msg)
    elif req.level == "warn":
        logger.warning(formatted_msg)
    else:
        logger.info(formatted_msg)
    return {"status": "success"}


@router.get("/open")
async def open_link(url: str):
    """Opens a URL in the user's default browser.

    M6: Validates URL scheme to prevent open redirects to dangerous protocols.
    """
    try:
        import webbrowser

        _validate_open_url(url)
        webbrowser.open(url)
        return {"status": "success", "url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/playback/track")
async def track_playback(req: PlaybackTrackRequest):
    """
    Saves current watch progress, stops, and handles auto-increment of AniList progress.
    """
    try:
        ctx = get_ctx()
        media_item = ctx.media_api.get_media_item(req.media_id)
        if not media_item:
            raise HTTPException(status_code=404, detail="Media not found")

        # 1. Save local watch history
        from ...libs.player.types import PlayerResult

        def _to_hhmmss(sec) -> str | None:
            if sec is None:
                return None
            try:
                total_sec = int(float(sec))
                h = total_sec // 3600
                m = (total_sec % 3600) // 60
                s = total_sec % 60
                return f"{h:02d}:{m:02d}:{s:02d}"
            except (ValueError, TypeError):
                return None

        result = PlayerResult(
            episode=req.episode,
            stop_time=_to_hhmmss(req.current_time),
            total_time=_to_hhmmss(req.total_time),
        )
        ctx.watch_history.track(media_item, result)

        # 2. Check for completion (default 80%)
        complete_percent = ctx.config.stream.episode_complete_at
        is_completed = (
            (req.current_time / req.total_time * 100) >= complete_percent
            if req.total_time > 0
            else False
        )

        synced = False
        if is_completed:
            # Check if this episode is greater than the current progress
            current_progress = (
                media_item.user_status.progress if media_item.user_status else 0
            )
            try:
                ep_num = int(float(req.episode))
            except ValueError:
                ep_num = 0

            if ep_num > current_progress:
                # Update progress in local registry
                ctx.media_registry.update_media_index_entry(
                    media_id=req.media_id, progress=str(ep_num)
                )
                # Sync with AniList
                from ...libs.media_api.params import UpdateUserMediaListEntryParams

                params = UpdateUserMediaListEntryParams(
                    media_id=req.media_id, progress=str(ep_num)
                )
                synced = ctx.media_api.update_list_entry(params)

        ctx.data_version += 1
        return {"status": "success", "completed": is_completed, "synced": synced}

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
