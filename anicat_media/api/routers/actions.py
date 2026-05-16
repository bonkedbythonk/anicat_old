from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
import webbrowser
from ...libs.player.params import PlayerParams
from ...libs.player.types import PlayerResult
from .status import set_playback

router = APIRouter()
_active_requests = set()

def get_ctx():
    from ..main import ctx
    return ctx

def _play_and_track(ctx, params, anime, media_item):
    """Background task to play media and then track watch history."""
    try:
        player_result = ctx.player.play(params, anime=anime, media_item=media_item)
        if player_result:
            ctx.watch_history.track(media_item, player_result)
            ctx.data_version += 1
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in background playback tracking: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _active_requests.discard(media_item.id)

@router.post("/play/{media_id}")
async def play_media(media_id: int, background_tasks: BackgroundTasks, episode: Optional[str] = None):
    """
    Smart Play: Finds the next episode and triggers playback in MPV.
    """
    if media_id in _active_requests:
        raise HTTPException(status_code=429, detail="Playback request already in progress for this media")
    
    _active_requests.add(media_id)
    try:
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
            # Only use resume time if the episode matches the one being requested
            # get_episode returns the "smart" next episode, so we check if the requested one is the same
            current_progress = str(media_item.user_status.progress) if media_item.user_status else "0"
            if episode == str(int(current_progress) + 1) or episode == current_progress:
                start_time = resume_time

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
            # episode is the chapter number as a string
            chapter = next((ch for ch in full_manga.chapters if ch.number == episode), None)
            if not chapter:
                # Fallback to the first chapter if not found
                chapter = full_manga.chapters[0]
                episode = chapter.number
                
            chapter_data = ctx.manga_provider.get_chapter_thumbnails(full_manga.id, chapter.url or chapter.number)
            if not chapter_data or not chapter_data.get("thumbnails"):
                 raise HTTPException(status_code=404, detail="Failed to load chapter pages")
            
            # For now, we just open the first page in the browser as a "playback" action
            first_page = chapter_data["thumbnails"][0]
            webbrowser.open(first_page)
            
            # Track progress
            ctx.watch_history.track(media_item, PlayerResult(episode=str(episode), stop_time=None, total_time=None))
            ctx.data_version += 1
            
            # Track for Now Playing
            set_playback(media_id=media_id, media_title=title, episode=str(episode))
            
            _active_requests.discard(media_id)
            return {"status": "reading", "media": title, "episode": episode}

        # 3. Search anime provider
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
            
        # 4. Trigger Player
        # We use the first link from the server
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
        
        params = PlayerParams(
            url=stream_link,
            query=title,
            episode=episode,
            title=title,
            headers=server.headers,
            start_time=start_time
        )
        background_tasks.add_task(_play_and_track, ctx, params, anime=anime_ref, media_item=media_item)
        
        # Track playback for Now Playing bar
        set_playback(media_id=media_id, media_title=title, episode=episode)
        
        return {"status": "playing", "media": title, "episode": episode}
        
    except HTTPException:
        _active_requests.discard(media_id)
        raise
    except Exception as e:
        _active_requests.discard(media_id)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
