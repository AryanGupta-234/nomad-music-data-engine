from __future__ import annotations

import asyncio

from app.collectors.youtube import search_songs
from app.config import settings


async def main() -> None:
    if not settings.youtube_api_key:
        print("Set YOUTUBE_API_KEY in .env before running the collector.")
        return

    songs = await search_songs("The Weeknd Blinding Lights", settings.youtube_api_key, limit=5)
    for song in songs:
        print(song)


if __name__ == "__main__":
    asyncio.run(main())
