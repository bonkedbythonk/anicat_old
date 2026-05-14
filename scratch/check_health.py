from anicat_media.api.main import create_app
from anicat_media.api.routers.status import get_health
import asyncio

async def check():
    app = create_app()
    health = await get_health()
    print(health)

if __name__ == "__main__":
    asyncio.run(check())
