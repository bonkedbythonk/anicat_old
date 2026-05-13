from typing import List, Optional
from fastapi import APIRouter, HTTPException
from ...libs.media_api.types import MediaType, MediaSearchResult, MediaItem, CharacterSearchResult, MediaReview, MediaSort, MediaSeason, MediaGenre, MediaStatus, MediaFormat
from ...libs.media_api.params import MediaSearchParams, MediaCharactersParams, MediaReviewsParams, MediaRecommendationParams

router = APIRouter()

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
        return result or MediaSearchResult(page_info={"total": 0, "current_page": 1, "has_next_page": False, "per_page": per_page}, media=[])
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
        return result or MediaSearchResult(page_info={"total": 0, "current_page": 1, "has_next_page": False, "per_page": per_page}, media=[])
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id}", response_model=MediaItem)
async def get_media_details(media_id: int):
    """Get detailed information for a specific media."""
    try:
        ctx = get_ctx()
        media = ctx.media_api.get_media_item(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        return media
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id}/episodes")
async def get_media_episodes(media_id: int):
    """Get episodes/chapters for a given media from the configured provider."""
    try:
        ctx = get_ctx()
        media = ctx.media_api.get_media_item(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        
        from ...libs.media_api.types import MediaType
        is_manga = media.type == MediaType.MANGA
        title = media.title.romaji or media.title.english
        
        from ...core.utils.normalizer import normalize_title
        from ...cli.utils.search import find_best_match_title
        
        if is_manga:
            # --- Manga Logic ---
            from ...libs.provider.manga.base import MangaSearchParams as MangaProviderParams
            from ...libs.provider.manga.base import MangaParams
            
            search_results = ctx.manga_provider.search(
                MangaProviderParams(
                    query=normalize_title(title, ctx.config.general.manga_provider.value, True)
                )
            )
            
            if not search_results or not search_results.results:
                return []
            
            results_map = {r.title: r for r in search_results.results}
            try:
                best_title = find_best_match_title(results_map, ctx.config.general.manga_provider, media)
                manga_ref = results_map[best_title]
            except Exception:
                manga_ref = search_results.results[0]
                
            full_manga = ctx.manga_provider.get(MangaParams(id=manga_ref.id, query=title))
            if not full_manga:
                return []
                
            record = ctx.media_registry.get_media_record(media_id)
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
            from ...libs.provider.anime.params import SearchParams as ProviderSearchParams
            from ...libs.provider.anime.params import AnimeParams
            
            search_results = ctx.provider.search(
                ProviderSearchParams(
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id}/characters", response_model=CharacterSearchResult)
async def get_media_characters(media_id: int):
    """Get characters for a specific media."""
    try:
        ctx = get_ctx()
        params = MediaCharactersParams(id=media_id)
        return ctx.media_api.get_characters_of(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id}/reviews", response_model=List[MediaReview])
async def get_media_reviews(media_id: int, page: int = 1):
    """Get reviews for a specific media."""
    try:
        ctx = get_ctx()
        params = MediaReviewsParams(id=media_id, page=page)
        return ctx.media_api.get_reviews_for(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{media_id}/recommendations", response_model=List[MediaItem])
async def get_media_recommendations(media_id: int, page: int = 1):
    """Get recommendations for a specific media."""
    try:
        ctx = get_ctx()
        params = MediaRecommendationParams(id=media_id, page=page)
        return ctx.media_api.get_recommendation_for(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
