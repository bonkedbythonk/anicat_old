from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import time
import json
import urllib.parse
import httpx
from ...libs.player.params import PlayerParams
from ...libs.player.types import PlayerResult
from .status import set_playback

class PlaybackTrackRequest(BaseModel):
    media_id: int
    episode: str
    current_time: float
    total_time: float

router = APIRouter()
_active_requests = {} # media_id -> timestamp

def get_ctx():
    from ..main import ctx
    return ctx

def _play_and_track(ctx, params, anime, media_item):
    """Background task to play media and then track watch history."""
    try:
        from ...libs.provider.anime.types import SearchResult as AnimeSearchResult
        from ...libs.provider.anime.params import AnimeParams
        if anime and isinstance(anime, AnimeSearchResult):
            try:
                full_anime = ctx.provider.get(
                    AnimeParams(
                        id=anime.id,
                        query=media_item.title.english or media_item.title.romaji or ""
                    )
                )
                if full_anime:
                    anime = full_anime
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to resolve full anime details in background playback: {e}")

        player_result = ctx.player.play(params, anime=anime, media_item=media_item)
        if player_result:
            ctx.watch_history.track(media_item, player_result)
            ctx.data_version += 1
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
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
        current_progress = str(media_item.user_status.progress) if media_item.user_status else "0"
        if episode == str(int(current_progress) + 1) or episode == current_progress:
            start_time = resume_time

    title = media_item.title.romaji or media_item.title.english
    from ...core.utils.normalizer import normalize_title

    # 2. Search anime provider
    from ...libs.provider.anime.params import SearchParams as ProviderSearchParams
    search_results = ctx.provider.search(
        ProviderSearchParams(
            query=normalize_title(title, ctx.config.general.provider.value, True),
            translation_type=ctx.config.stream.translation_type
        )
    )
    
    if not search_results or not search_results.results:
         raise HTTPException(status_code=404, detail=f"No results found for {title}")
         
    # Pick best match
    from ...cli.utils.search import find_best_match_title
    results_map = {r.title: r for r in search_results.results}
    try:
        best_title = find_best_match_title(results_map, ctx.config.general.provider, media_item)
        anime_ref = results_map[best_title]
    except Exception:
        anime_ref = search_results.results[0]
    
    # 3. Get streams
    from ...libs.provider.anime.params import EpisodeStreamsParams
    streams_iter = ctx.provider.episode_streams(
        EpisodeStreamsParams(
            query=title,
            anime_id=anime_ref.id,
            episode=episode,
            translation_type=ctx.config.stream.translation_type
        )
    )
    
    if not streams_iter:
        raise HTTPException(status_code=404, detail="No streams found")
        
    # Get first server
    try:
        server = next(streams_iter)
    except StopIteration:
        raise HTTPException(status_code=404, detail="No stream servers available")
        
    if not server.links:
        raise HTTPException(status_code=404, detail="No links found on server")
        
    preferred_quality = ctx.config.stream.quality
    selected_link = next((link for link in server.links if link.quality == preferred_quality), None)
    
    if not selected_link:
        try:
            selected_link = sorted(server.links, key=lambda x: int(x.quality), reverse=True)[0]
        except Exception:
            selected_link = server.links[-1]
            
    stream_link = selected_link.link
    
    return {
        "url": stream_link,
        "title": title,
        "episode": episode,
        "headers": server.headers or {},
        "start_time": start_time,
        "anime_ref": anime_ref,
        "media_item": media_item
    }

@router.post("/play/{media_id}")
async def play_media(media_id: int, background_tasks: BackgroundTasks, episode: Optional[str] = None):
    """
    Smart Play: Finds the next episode and triggers playback in MPV.
    """
    now = time.time()
    if media_id in _active_requests:
        last_request_time = _active_requests[media_id]
        if now - last_request_time < 2.0: # Only block if within 2 seconds
            raise HTTPException(status_code=429, detail="Playback request already in progress")
    
    _active_requests[media_id] = now
    try:
        ctx = get_ctx()
        media_item = ctx.media_api.get_media_item(media_id)
        if not media_item:
            raise HTTPException(status_code=404, detail="Media not found")

        # 2. Check if Manga
        from ...libs.media_api.types import MediaType, MediaFormat
        is_manga = media_item.type == MediaType.MANGA or media_item.format in (
            MediaFormat.MANGA,
            MediaFormat.NOVEL,
            MediaFormat.ONE_SHOT,
        )
        
        title = media_item.title.romaji or media_item.title.english
        from ...core.utils.normalizer import normalize_title
        
        if is_manga:
            from ...libs.provider.manga.params import MangaSearchParams, MangaParams
            search_results = ctx.manga_provider.search(
                MangaSearchParams(
                    query=normalize_title(title, ctx.config.general.manga_provider.value, True)
                )
            )
            
            if not search_results or not search_results.results:
                 raise HTTPException(status_code=404, detail=f"No manga results found for {title}")
            
            from ...cli.utils.search import find_best_match_title
            results_map = {r.title: r for r in search_results.results}
            try:
                best_title = find_best_match_title(results_map, ctx.config.general.manga_provider, media_item)
                manga_ref = results_map[best_title]
            except Exception:
                manga_ref = search_results.results[0]
                
            full_manga = ctx.manga_provider.get(MangaParams(id=manga_ref.id, query=title))
            if not full_manga or not full_manga.chapters:
                 raise HTTPException(status_code=404, detail="No chapters found")
            
            # Find the requested chapter
            chapter = next((ch for ch in full_manga.chapters if ch.number == episode), None)
            if not chapter:
                chapter = full_manga.chapters[0]
                episode = chapter.number
                
            chapter_data = ctx.manga_provider.get_chapter_thumbnails(full_manga.id, chapter.url or chapter.number)
            if not chapter_data or not chapter_data.get("thumbnails"):
                 raise HTTPException(status_code=404, detail="Failed to load chapter pages")
            
            ctx.watch_history.track(media_item, PlayerResult(episode=str(episode), stop_time=None, total_time=None))
            ctx.data_version += 1
            
            set_playback(media_id=media_id, media_title=title, episode=str(episode))
            _active_requests.pop(media_id, None)
            return {"status": "reading", "media": title, "episode": episode, "chapter_data": chapter_data}

        # 3. Resolve stream
        resolved = await _resolve_episode_stream(media_id, episode)
        
        params = PlayerParams(
            url=resolved["url"],
            query=resolved["title"],
            episode=resolved["episode"],
            title=resolved["title"],
            headers=resolved["headers"],
            start_time=resolved["start_time"]
        )
        background_tasks.add_task(_play_and_track, ctx, params, anime=resolved["anime_ref"], media_item=resolved["media_item"])
        
        set_playback(media_id=media_id, media_title=resolved["title"], episode=resolved["episode"])
        _active_requests.pop(media_id, None)
        return {"status": "playing", "media": resolved["title"], "episode": resolved["episode"]}
        
    except HTTPException:
        _active_requests.pop(media_id, None)
        raise
    except Exception as e:
        _active_requests.pop(media_id, None)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/play/{media_id}/resolve")
async def resolve_media_stream(media_id: int, episode: Optional[str] = None):
    """
    Resolves the stream details for embedded in-app playback without launching MPV.
    """
    try:
        resolved = await _resolve_episode_stream(media_id, episode)
        
        # Track playback for Now Playing bar
        set_playback(media_id=media_id, media_title=resolved["title"], episode=resolved["episode"])
        
        raw_stream_url = resolved["url"]
        stream_headers = resolved["headers"]
        
        # Route HLS manifest through local proxy
        proxy_prefix = "/api/actions/proxy"
        headers_str = json.dumps(stream_headers)
        
        proxied_stream_url = f"{proxy_prefix}?url={urllib.parse.quote(raw_stream_url)}&headers={urllib.parse.quote(headers_str)}"
        
        return {
            "stream_url": proxied_stream_url,
            "raw_stream_url": raw_stream_url,
            "title": resolved["title"],
            "episode": resolved["episode"],
            "start_time": resolved["start_time"],
            "media_id": media_id,
            "headers": stream_headers
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
    point back to our local proxy, injecting the required referer/user-agent headers.
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
                    proxied_uri = f"/api/actions/proxy?url={urllib.parse.quote(absolute_uri)}&headers={urllib.parse.quote(headers_json)}"
                    rewritten_lines.append(f'{prefix}URI="{proxied_uri}"{remaining}')
                    continue
                except Exception:
                    pass
            rewritten_lines.append(line)
        else:
            # Segment or sub-playlist URL
            absolute_url = urllib.parse.urljoin(base_url, line_stripped)
            proxied_url = f"/api/actions/proxy?url={urllib.parse.quote(absolute_url)}&headers={urllib.parse.quote(headers_json)}"
            rewritten_lines.append(proxied_url)
    return "\n".join(rewritten_lines)

@router.get("/proxy")
async def hls_stream_proxy(url: str, headers: str):
    """
    A local loopback HTTP proxy for HLS .m3u8 files and .ts media segments.
    Injects custom Referer and User-Agent headers, and rewrites playlists
    to ensure full cross-origin compatibility and cookie preservation inside WebViews.
    """
    try:
        req_headers = json.loads(headers)
    except Exception:
        req_headers = {}

    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"

    # Make the request to the real server
    async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
        parsed = urllib.parse.urlparse(url)
        is_m3u8 = parsed.path.endswith(".m3u8") or "m3u8" in parsed.query

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
                    "Cache-Control": "no-cache"
                }
            )
        else:
            # For HLS video segments (.ts), stream binary data directly to the webview
            def iter_bytes_chunks():
                for chunk in response.iter_bytes(chunk_size=65536):
                    yield chunk

            return StreamingResponse(
                iter_bytes_chunks(),
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "video/mp2t"),
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Cache-Control": "public, max-age=86400"
                }
            )

@router.get("/test")
async def test_actions():
    return {"status": "ok", "message": "Actions router is active"}

@router.get("/open")
async def open_link(url: str):
    """Opens a URL in the user's default browser."""
    try:
        import webbrowser
        webbrowser.open(url)
        return {"status": "success", "url": url}
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
        result = PlayerResult(
            episode=req.episode,
            stop_time=req.current_time,
            total_time=req.total_time
        )
        ctx.watch_history.track(media_item, result)
        
        # 2. Check for completion (default 80%)
        complete_percent = ctx.config.stream.episode_complete_at
        is_completed = (req.current_time / req.total_time * 100) >= complete_percent if req.total_time > 0 else False
        
        synced = False
        if is_completed:
            # Check if this episode is greater than the current progress
            current_progress = media_item.user_status.progress if media_item.user_status else 0
            try:
                ep_num = int(float(req.episode))
            except ValueError:
                ep_num = 0
                
            if ep_num > current_progress:
                # Update progress in local registry
                ctx.media_registry.update_media_index_entry(
                    media_id=req.media_id,
                    progress=str(ep_num)
                )
                # Sync with AniList
                from ...libs.media_api.params import UpdateUserMediaListEntryParams
                params = UpdateUserMediaListEntryParams(
                    media_id=req.media_id,
                    progress=str(ep_num)
                )
                synced = ctx.media_api.update_list_entry(params)

        ctx.data_version += 1
        return {"status": "success", "completed": is_completed, "synced": synced}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
