import asyncio

async def main():
    from anicat_media.api.main import ctx, create_app
    # Ensure context is initialized
    try:
        _ = ctx.config
    except RuntimeError:
        create_app()
    
    # Let's try calling play_media logic directly
    media_item = ctx.media_api.get_media_item(167143)
    if not media_item:
        print("Media item not found")
        return
    episode = "1"
    
    title = media_item.title.romaji or media_item.title.english
    from anicat_media.libs.provider.anime.params import SearchParams as ProviderSearchParams
    from anicat_media.core.utils.normalizer import normalize_title
    
    search_results = ctx.provider.search(
        ProviderSearchParams(
            query=normalize_title(title, ctx.config.general.provider.value, True),
            translation_type=ctx.config.stream.translation_type
        )
    )
    if not search_results or not search_results.results:
        print("No search results found")
        return
    
    from anicat_media.cli.utils.search import find_best_match_title
    results_map = {r.title: r for r in search_results.results}
    try:
        best_title = find_best_match_title(results_map, ctx.config.general.provider, media_item)
        anime_ref = results_map[best_title]
    except Exception:
        anime_ref = search_results.results[0]
        
    print(f"Anime ref: {anime_ref.title}")
    
    from anicat_media.libs.provider.anime.params import EpisodeStreamsParams
    streams_iter = ctx.provider.episode_streams(
        EpisodeStreamsParams(
            query=title,
            anime_id=anime_ref.id,
            episode=episode,
            translation_type=ctx.config.stream.translation_type
        )
    )
    if not streams_iter:
        print("No streams found")
        return
    server = next(streams_iter)
    stream_link = server.links[0].link
    print(f"Stream link: {stream_link}")
    
    # params = PlayerParams(url=stream_link, query=title, episode=episode, title=title, headers=server.headers)
    # ctx.player.play(params, anime=anime_ref, media_item=media_item)

if __name__ == "__main__":
    asyncio.run(main())
