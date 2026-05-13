import asyncio
from anicat_media.libs.provider.anime.animepahe.provider import AnimePahe
from anicat_media.libs.provider.anime.params import EpisodeStreamsParams, SearchParams
from httpx import Client

async def main():
    with Client(follow_redirects=True) as client:
        provider = AnimePahe(client)
        # Search for "Solo Leveling" (session_id is probably required)
        results = provider.search(SearchParams(query="Solo Leveling"))
        if not results or not results.results:
            print("No results")
            return
        
        anime = results.results[0]
        print(f"Found anime: {anime.title} (ID: {anime.id})")
        
        streams_iter = provider.episode_streams(EpisodeStreamsParams(
            anime_id=anime.id,
            query=anime.title,
            episode="1",
            translation_type="sub"
        ))
        
        if streams_iter:
            for server in streams_iter:
                print(f"Server: {server.name}")
                for link in server.links:
                    print(f"  - Quality: {link.quality} | Link: {link.link[:50]}...")
        else:
            print("No streams found")

if __name__ == "__main__":
    asyncio.run(main())
