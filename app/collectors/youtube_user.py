from __future__ import annotations

from typing import Any

import httpx


class YouTubeUserCollector:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30, headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def _paginate(self, endpoint: str, params: dict[str, Any], max_items: int = 5000) -> list[dict[str, Any]]:
        """Collect all pages up to max_items instead of silently stopping at 50."""
        items: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(items) < max_items:
            page_params = dict(params)
            page_params["maxResults"] = min(50, max_items - len(items))
            if page_token:
                page_params["pageToken"] = page_token

            data = await self._get(endpoint, page_params)
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return items[:max_items]

    async def channel(self) -> dict[str, Any]:
        return await self._get(
            "channels",
            {"part": "snippet,contentDetails,statistics", "mine": "true"},
        )

    async def playlists(self, max_items: int = 5000) -> list[dict[str, Any]]:
        return await self._paginate(
            "playlists",
            {"part": "snippet,contentDetails", "mine": "true"},
            max_items,
        )

    async def playlist_items(self, playlist_id: str, max_items: int = 5000) -> list[dict[str, Any]]:
        return await self._paginate(
            "playlistItems",
            {"part": "snippet,contentDetails", "playlistId": playlist_id},
            max_items,
        )

    async def subscriptions(self, max_items: int = 5000) -> list[dict[str, Any]]:
        return await self._paginate(
            "subscriptions",
            {"part": "snippet,contentDetails", "mine": "true"},
            max_items,
        )

    async def liked_video_items(self, max_items: int = 5000) -> list[dict[str, Any]]:
        """Return all available liked-video playlist items, not just the first 50."""
        channel = await self.channel()
        items = channel.get("items", [])
        if not items:
            return []
        playlist_id = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("likes")
        )
        if not playlist_id:
            return []
        return await self.playlist_items(playlist_id, max_items)

    async def video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Hydrate videos in batches of 50 with duration, category and engagement metadata."""
        results: list[dict[str, Any]] = []
        ids = [x for x in dict.fromkeys(video_ids) if x]
        for start in range(0, len(ids), 50):
            batch = ids[start : start + 50]
            data = await self._get(
                "videos",
                {
                    "part": "snippet,contentDetails,statistics",
                    "id": ",".join(batch),
                },
            )
            results.extend(data.get("items", []))
        return results

    async def liked_music_videos(self, max_items: int = 5000) -> list[dict[str, Any]]:
        """Return enriched liked videos that YouTube categorizes as Music (category 10)."""
        items = await self.liked_video_items(max_items)
        ids = []
        for item in items:
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                ids.append(video_id)

        details = await self.video_details(ids)
        return [item for item in details if item.get("snippet", {}).get("categoryId") == "10"]
