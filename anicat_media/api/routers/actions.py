from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ...libs.player.params import PlayerParams

router = APIRouter()

def get_ctx():
    from ..main import ctx
    return ctx

@router.post("/play/{media_id}")
async def play_media(media_id: int, background_tasks: BackgroundTasks, episode: Optional[str] = None):
    """
    Smart Play: Finds the next episode and triggers playback in MPV.
    """
    try:
        ctx = get_ctx()
        media_item = ctx.media_api.get_media_item(media_id)
        if not media_item:
            raise HTTPException(status_code=404, detail="Media not found")

        # 1. Determine next episode
        if not episode:
            next_ep_info = ctx.watch_history.get_episode(media_item)
            episode = str(next_ep_info.episode) if next_ep_info else "1"

        # 2. Search provider
        title = media_item.title.romaji or media_item.title.english
        from ...libs.provider.anime.params import SearchParams as ProviderSearchParams
        from ...core.utils.normalizer import normalize_title
        
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
            headers=server.headers
        )
        background_tasks.add_task(ctx.player.play, params, anime=anime_ref, media_item=media_item)
        
        return {"status": "playing", "media": title, "episode": episode}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
