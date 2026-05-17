from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
import logging

from ...libs.media_api.types import MediaType, MediaSearchResult, MediaItem, CharacterSearchResult, MediaReview, MediaSort, MediaSeason, MediaGenre, MediaStatus, MediaFormat, PageInfo
from ...libs.media_api.params import MediaSearchParams, MediaCharactersParams, MediaReviewsParams, MediaRecommendationParams

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/schedule", response_model=MediaSearchResult)
async def get_schedule(
    days_before: int = 1,
    days_after: int = 1,
    page: int = 1,
    per_page: int = 50,
    media_ids: Optional[List[int]] = Query(None)
):
    """Get the global airing schedule for a time range around now."""
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        start = int((now - timedelta(days=days_before)).timestamp())
        end = int((now + timedelta(days=days_after)).timestamp())
        
        ctx = get_ctx()
        return ctx.media_api.get_global_airing_schedule(
            airingAt_greater=start,
            airingAt_lesser=end,
            page=page,
            per_page=per_page,
            media_ids=media_ids
        )
    except Exception as e:
        logger.error(f"Failed to fetch schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Use lazy import for ctx to avoid circular dependency
def get_ctx():
    from ..main import ctx
    return ctx

def _get_current_anime_season() -> tuple[MediaSeason, int]:
    """Determine the current anime season and year."""
    from datetime import datetime
    now = datetime.now()
    month = now.month
    year = now.year
    if month in (1, 2, 3):
        return MediaSeason.WINTER, year
    elif month in (4, 5, 6):
        return MediaSeason.SPRING, year
    elif month in (7, 8, 9):
        return MediaSeason.SUMMER, year
    else:
        return MediaSeason.FALL, year

@router.get("/recent", response_model=MediaSearchResult)
async def get_recent(
    limit: Optional[int] = 10,
    type: Optional[MediaType] = None
):
    """Get recently watched/read media."""
    try:
        ctx = get_ctx()
        return ctx.media_registry.get_recently_watched(limit=limit, type=type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending", response_model=MediaSearchResult)
async def get_trending(
    type: MediaType = MediaType.ANIME,
    page: int = 1,
    per_page: int = 15
):
    """Get trending media sorted by current trending rank."""
    try:
        ctx = get_ctx()
        params = MediaSearchParams(
            type=type,
            page=page,
            per_page=per_page,
            sort=MediaSort.TRENDING_DESC,
        )
        result = ctx.media_api.search_media(params)
        return result or MediaSearchResult(page_info=PageInfo(total=0, current_page=1, has_next_page=False, per_page=per_page), media=[])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/seasonal", response_model=MediaSearchResult)
async def get_seasonal(
    type: MediaType = MediaType.ANIME,
    page: int = 1,
    per_page: int = 15
):
    """Get media from the current anime season, sorted by popularity."""
    try:
        ctx = get_ctx()
        season, year = _get_current_anime_season()
        params = MediaSearchParams(
            type=type,
            page=page,
            per_page=per_page,
            sort=MediaSort.POPULARITY_DESC,
            season=season,
            seasonYear=year,
        )
        result = ctx.media_api.search_media(params)
        return result or MediaSearchResult(page_info=PageInfo(total=0, current_page=1, has_next_page=False, per_page=per_page), media=[])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=MediaSearchResult)
async def search_media(
    query: str,
    type: MediaType = MediaType.ANIME,
    page: int = 1,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    min_score: Optional[int] = None,
    status: Optional[MediaStatus] = None,
    format: Optional[MediaFormat] = None,
):
    """Search for media with optional filters."""
    try:
        ctx = get_ctx()
        genre_list = None
        if genre:
            try:
                genre_list = [MediaGenre(g.strip()) for g in genre.split(",")]
            except ValueError:
                pass

        format_list = [format] if format else None

        params = MediaSearchParams(
            query=query,
            type=type,
            page=page,
            genre_in=genre_list,
            seasonYear=year,
            averageScore_greater=min_score,
            status=status,
            format_in=format_list,
        )
        return ctx.media_api.search_media(params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id:int}", response_model=MediaItem)
async def get_media_details(media_id: int):
    """Get detailed information for a specific media, merged with local registry status."""
    try:
        ctx = get_ctx()
        media = ctx.media_api.get_media_item(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
            
        # Merge with local registry for "Live" feel and offline support
        local_entry = ctx.media_registry.get_media_index_entry(media_id)
        if local_entry:
            logger.debug(f"Merging local registry for media {media_id}. Local progress: {local_entry.progress}")
            if not media.user_status:
                from ...libs.media_api.types import UserListItem
                media.user_status = UserListItem(
                    status=local_entry.status,
                    progress=int(local_entry.progress) if local_entry.progress.isdigit() else 0,
                    score=local_entry.score
                )
            else:
                if local_entry.progress.isdigit():
                    local_progress = int(local_entry.progress)
                    if local_progress != media.user_status.progress:
                        logger.info(f"Overriding AniList progress ({media.user_status.progress}) with local progress ({local_progress}) for media {media_id}")
                        media.user_status.progress = local_progress
                
                if local_entry.status != media.user_status.status:
                    media.user_status.status = local_entry.status
                
                if local_entry.score != media.user_status.score:
                    media.user_status.score = local_entry.score
                    
        return media
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_manga_ref(ctx, media, media_id: int):
    """Get the manga reference from registry or search."""
    record = ctx.media_registry.get_media_record(media_id)
    provider_name = ctx.config.general.manga_provider.value
    
    if record and record.provider_mapping and provider_name in record.provider_mapping:
        provider_id = record.provider_mapping[provider_name]
        return provider_id, record

    # Search for the manga
    title = media.title.romaji or media.title.english
    from ...core.utils.normalizer import normalize_title
    from ...libs.provider.manga.params import MangaSearchParams
    
    search_results = ctx.manga_provider.search(
        MangaSearchParams(
            query=normalize_title(title, provider_name, True)
        )
    )
    
    if not search_results or not search_results.results:
        return None, record
        
    from ...cli.utils.search import find_best_match_title
    results_map = {r.title: r for r in search_results.results}
    try:
        best_title = find_best_match_title(results_map, ctx.config.general.manga_provider, media)
        manga_ref = results_map[best_title]
    except Exception:
        manga_ref = search_results.results[0]
        
    # Cache the result
    if not record:
        record = ctx.media_registry.get_or_create_record(media)
    
    if not record.provider_mapping:
        record.provider_mapping = {}
        
    record.provider_mapping[provider_name] = manga_ref.id
    ctx.media_registry.save_media_record(record)
    
    return manga_ref.id, record

@router.get("/{media_id:int}/episodes")
async def get_media_episodes(media_id: int):
    """Get episodes/chapters for a given media from the configured provider."""
    try:
        ctx = get_ctx()
        media = ctx.media_api.get_media_item(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        
        from ...libs.media_api.types import MediaType
        is_manga = media.type == MediaType.MANGA
        
        if is_manga:
            from ...libs.provider.manga.params import MangaParams
            
            manga_id, record = await get_manga_ref(ctx, media, media_id)
            if not manga_id:
                return []
                
            full_manga = ctx.manga_provider.get(MangaParams(id=manga_id, query=media.title.romaji))
            if not full_manga:
                return []
                
            local_chapters = {e.episode_number: e for e in record.media_episodes} if record else {}
            
            result = []
            for ch in full_manga.chapters:
                local = local_chapters.get(ch.number)
                result.append({
                    "number": ch.number,
                    "title": ch.title or f"Chapter {ch.number}",
                    "download_status": local.download_status.value if local else "not_downloaded",
                    "is_downloaded": local.download_status.name == "COMPLETED" if local else False
                })
            return result
        else:
            # --- Anime Logic ---
            from ...libs.provider.anime.params import AnimeParams, SearchParams as AnimeSearchParams
            # Ensure we have a normalized title for searching
            title = media.title.romaji or media.title.english
            from ...core.utils.normalizer import normalize_title
            from ...cli.utils.search import find_best_match_title

            search_results = ctx.provider.search(
                AnimeSearchParams(
                    query=normalize_title(title, ctx.config.general.provider.value, True),
                    translation_type=ctx.config.stream.translation_type
                )
            )
            
            if not search_results or not search_results.results:
                 return []
                 
            results_map = {r.title: r for r in search_results.results}
            try:
                best_title = find_best_match_title(results_map, ctx.config.general.provider, media)
                anime_ref = results_map[best_title]
            except Exception:
                anime_ref = search_results.results[0]
            
            full_anime = ctx.provider.get(AnimeParams(id=anime_ref.id, query=title))
            if not full_anime:
                return []
                
            record = ctx.media_registry.get_media_record(media_id)
            local_episodes = {e.episode_number: e for e in record.media_episodes} if record else {}
            
            trans_type = ctx.config.stream.translation_type
            available_eps = getattr(full_anime.episodes, trans_type)
            if not available_eps:
                available_eps = full_anime.episodes.sub or []
    
            ep_info_map = {info.episode: info for info in (full_anime.episodes_info or [])}
            
            result = []
            for ep_str in available_eps:
                local = local_episodes.get(ep_str)
                info = ep_info_map.get(ep_str)
                title = info.title if info and info.title else f"Episode {ep_str}"
                result.append({
                    "number": ep_str,
                    "title": title,
                    "download_status": local.download_status.value if local else "not_downloaded",
                    "is_downloaded": local.download_status.name == "COMPLETED" if local else False
                })
            return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id:int}/characters", response_model=CharacterSearchResult)
async def get_media_characters(media_id: int):
    """Get characters for a specific media."""
    try:
        ctx = get_ctx()
        params = MediaCharactersParams(id=media_id)
        return ctx.media_api.get_characters_of(params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id:int}/reviews", response_model=List[MediaReview])
async def get_media_reviews(media_id: int, page: int = 1):
    """Get reviews for a specific media."""
    try:
        ctx = get_ctx()
        params = MediaReviewsParams(id=media_id, page=page)
        return ctx.media_api.get_reviews_for(params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id:int}/recommendations", response_model=List[MediaItem])
async def get_media_recommendations(media_id: int, page: int = 1):
    """Get recommendations for a specific media."""
    try:
        ctx = get_ctx()
        params = MediaRecommendationParams(id=media_id, page=page)
        return ctx.media_api.get_recommendation_for(params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id:int}/chapter/{chapter_number}/pages")
async def get_chapter_pages(media_id: int, chapter_number: str):
    """Get pages for a specific manga chapter."""
    try:
        ctx = get_ctx()
        media = ctx.media_api.get_media_item(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        
        from ...libs.provider.manga.params import MangaParams
        
        manga_id, _ = await get_manga_ref(ctx, media, media_id)
        if not manga_id:
             raise HTTPException(status_code=404, detail="Manga not found")
            
        full_manga = ctx.manga_provider.get(MangaParams(id=manga_id, query=media.title.romaji))
        if not full_manga or not full_manga.chapters:
             raise HTTPException(status_code=404, detail="No chapters found")
        
        # Find the requested chapter
        chapter = next((ch for ch in full_manga.chapters if ch.number == chapter_number), None)
        if not chapter:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_number} not found")
            
        chapter_data = ctx.manga_provider.get_chapter_thumbnails(full_manga.id, chapter.url or chapter.number)
        if not chapter_data or not chapter_data.get("thumbnails"):
             raise HTTPException(status_code=404, detail="Failed to load chapter pages")
        
        return chapter_data
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/manga/proxy")
async def proxy_manga_image(url: str):
    """Proxy and cache manga images to provide instantaneous navigation."""
    import httpx
    import hashlib
    from fastapi import Response
    from ...core.constants import APP_CACHE_DIR
    
    # Setup cache directory
    manga_cache = APP_CACHE_DIR / "manga"
    manga_cache.mkdir(parents=True, exist_ok=True)
    
    # Create a unique filename from the URL
    url_hash = hashlib.md5(url.encode()).hexdigest()
    # Try to guess extension from URL or use .jpg as fallback
    ext = ".jpg"
    if ".webp" in url.lower():
        ext = ".webp"
    elif ".png" in url.lower():
        ext = ".png"
    elif ".avif" in url.lower():
        ext = ".avif"
    
    cache_path = manga_cache / f"{url_hash}{ext}"

    # 1. Check if we already have it in the local cache
    if cache_path.exists():
        try:
            from fastapi.responses import FileResponse

            return FileResponse(
                path=str(cache_path),
                media_type=f"image/{ext.replace('.', '')}",
                headers={"Cache-Control": "public, max-age=31536000", "X-Cache-Status": "HIT"},
            )
        except Exception:
            pass  # Fallback to fetching if read fails

    # 2. Not in cache, fetch it
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mangakatana.com/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15.0, follow_redirects=True)
            if response.status_code == 200:
                # Save to cache for next time
                cache_path.write_bytes(response.content)

                from fastapi.responses import FileResponse

                return FileResponse(
                    path=str(cache_path),
                    media_type=response.headers.get("Content-Type", "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=31536000", "X-Cache-Status": "MISS"},
                )
            else:
                logger.error(f"[MANGA PROXY] Source failed: {url} ({response.status_code})")
                raise HTTPException(status_code=response.status_code, detail="Source refused request")
    except Exception as e:
        logger.error(f"[MANGA PROXY] Cache error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
