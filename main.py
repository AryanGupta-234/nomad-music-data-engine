from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.collectors.user_rest import UserRestCollector
from app.collectors.youtube import search_songs
from app.config import settings
from app.storage import Database
from app.sync import sync_user_data


def configure_utf8_output() -> None:
    """Prevent Windows cp1252 terminals from crashing on Unicode metadata."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


async def main() -> None:
    configure_utf8_output()
    parser = argparse.ArgumentParser(description="NOMAD Music Data Engine")
    parser.add_argument("--sync-user", action="store_true", help="sync the configured user REST API")
    parser.add_argument("--query", default="The Weeknd Blinding Lights", help="YouTube song search query")
    args = parser.parse_args()

    if args.sync_user:
        if not settings.user_api_token:
            print("Set USER_API_TOKEN in .env before running --sync-user.")
            return
        db = Database(settings.database_path)
        try:
            collector = UserRestCollector(settings.user_api_base_url, settings.user_api_token)
            counts = await sync_user_data(collector, db)
            print(json.dumps({"status": "ok", "synced": counts, "stats": db.stats()}, ensure_ascii=False, indent=2))
        finally:
            db.close()
        return

    if not settings.youtube_api_key:
        print("Set YOUTUBE_API_KEY in .env before running the YouTube collector.")
        return

    songs = await search_songs(args.query, settings.youtube_api_key, limit=5)
    for song in songs:
        print(json.dumps(song, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
