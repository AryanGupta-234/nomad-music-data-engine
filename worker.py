from __future__ import annotations

import asyncio
import os

from app.collectors.youtube_user import YouTubeUserCollector
from app.config import settings
from app.fingerprint import track_fingerprint
from app.storage import Database
from app.youtube_oauth import get_valid_access_token


def _duration_ms(value: str | None) -> int | None:
    if not value or not value.startswith("PT"):
        return None
    import re
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not m:
        return None
    h, mnt, s = (int(x or 0) for x in m.groups())
    return ((h * 60 + mnt) * 60 + s) * 1000


async def sync_once(db: Database) -> dict:
    token = await get_valid_access_token(db)
    collector = YouTubeUserCollector(token)
    details, counts = await collector.music_video_details_from_user_sources()
    imported = 0
    for item in details:
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        stats = item.get("statistics", {})
        video_id = item.get("id")
        if not video_id:
            continue
        title = snippet.get("title") or "Unknown"
        artist = snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle") or "Unknown"
        duration = _duration_ms(content.get("duration"))
        track = {
            "track_id": f"youtube:{video_id}",
            "title": title,
            "artist": artist,
            "duration_ms": duration,
            "artwork_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "source_ids": {"youtube": video_id},
            "metadata": {"youtube": {
                "video_id": video_id,
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "description": snippet.get("description"),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId"),
                "duration": content.get("duration"),
                "view_count": stats.get("viewCount"),
                "like_count": stats.get("likeCount"),
                "comment_count": stats.get("commentCount"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }},
        }
        db.upsert_track(track, track_fingerprint(title, artist, duration))
        imported += 1
    return {**counts, "imported": imported, "stats": db.stats()}


async def main() -> None:
    db = Database(settings.database_path)
    minutes = max(1, int(os.getenv("YOUTUBE_BACKGROUND_SYNC_MINUTES", "15")))
    print(f"[NOMAD] background worker started; interval={minutes}m")
    try:
        while True:
            try:
                if db.get_youtube_oauth_token():
                    print("[NOMAD] syncing YouTube song sources...")
                    print(await sync_once(db))
                else:
                    print("[NOMAD] YouTube not connected; waiting...")
            except Exception as exc:
                print(f"[NOMAD] sync failed: {exc}")
            await asyncio.sleep(minutes * 60)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
