from __future__ import annotations

from typing import Any

import httpx


class YouTubeUserCollector:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20, headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def channel(self) -> dict[str, Any]:
        return await self._get("channels", {"part": "snippet,contentDetails,statistics", "mine": "true"})

    async def playlists(self, limit: int = 50) -> dict[str, Any]:
        return await self._get("playlists", {"part": "snippet,contentDetails", "mine": "true", "maxResults": min(limit, 50)})

    async def playlist_items(self, playlist_id: str, limit: int = 50) -> dict[str, Any]:
        return await self._get("playlistItems", {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(limit, 50),
        })

    async def subscriptions(self, limit: int = 50) -> dict[str, Any]:
        return await self._get("subscriptions", {
            "part": "snippet,contentDetails",
            "mine": "true",
            "maxResults": min(limit, 50),
        })

    async def liked_videos(self, limit: int = 50) -> dict[str, Any]:
        # YouTube exposes the user's liked videos through the special Likes playlist.
        channel = await self.channel()
        items = channel.get("items", [])
        if not items:
            return {"items": []}
        playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("likes")
        if not playlist_id:
            return {"items": []}
        return await self.playlist_items(playlist_id, limit)
