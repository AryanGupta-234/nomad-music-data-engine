from __future__ import annotations

from typing import Any

import httpx


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


async def search_songs(query: str, api_key: str, limit: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is required")
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "10",
        "maxResults": max(1, min(limit, 50)),
        "key": api_key,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{YOUTUBE_API}/search", params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        results.append({
            "youtube_video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_name": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "description": snippet.get("description", ""),
            "published_at": snippet.get("publishedAt"),
            "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "source": "youtube",
        })
    return results


async def get_video_details(video_id: str, api_key: str) -> dict[str, Any] | None:
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is required")
    params = {"part": "snippet,contentDetails,statistics", "id": video_id, "key": api_key}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{YOUTUBE_API}/videos", params=params)
        if response.status_code != 200:
            return None
        data = response.json()

    item = next(iter(data.get("items") or []), None)
    if not item:
        return None
    snippet = item.get("snippet") or {}
    return {
        "youtube_video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_name": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "description": snippet.get("description", ""),
        "published_at": snippet.get("publishedAt"),
        "tags": snippet.get("tags", []),
        "category_id": snippet.get("categoryId"),
        "duration": (item.get("contentDetails") or {}).get("duration"),
        "view_count": int((item.get("statistics") or {}).get("viewCount", 0) or 0),
        "like_count": int((item.get("statistics") or {}).get("likeCount", 0) or 0),
        "comment_count": int((item.get("statistics") or {}).get("commentCount", 0) or 0),
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "source": "youtube",
    }
