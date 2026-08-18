from __future__ import annotations

import asyncio
import json
import sys

from app.collectors.youtube import search_songs
from app.config import settings


def configure_utf8_output() -> None:
    """Prevent Windows cp1252 terminals from crashing on Unicode metadata."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


async def main() -> None:
    configure_utf8_output()

    if not settings.youtube_api_key:
        print("Set YOUTUBE_API_KEY in .env before running the collector.")
        return

    songs = await search_songs("The Weeknd Blinding Lights", settings.youtube_api_key, limit=5)
    for song in songs:
        print(json.dumps(song, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
