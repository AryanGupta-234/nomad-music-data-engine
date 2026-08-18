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

    async def _paginate(
        self,
        endpoint: str,
        params: dict[str, Any],
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """Follow every YouTube page until exhausted unless an explicit cap is supplied."""
        items: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            page_params = dict(params)
            remaining = None if max_items is None else max_items - len(items)
            if remaining is not None and remaining <= 0:
                break
            page_params["maxResults"] = 50 if remaining is None else min(50, remaining)
            if page_token:
                page_params["pageToken"] = page_token

            data = await self._get(endpoint, page_params)
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return items if max_items is None else items[:max_items]

    async def channel(self) -> dict[str, Any]:
        return await self._get(
            "channels",
            {"part": "snippet,contentDetails,statistics", "mine": "true"},
        )

    async def playlists(self, max_items: int | None = None) -> list[dict[str, Any]]:
        return await self._paginate(
            "playlists",
            {"part": "snippet,contentDetails", "mine": "true"},
            max_items,
        )

    async def playlist_items(self, playlist_id: str, max_items: int | None = None) -> list[dict[str, Any]]:
        return await self._paginate(
            "playlistItems",
            {"part": "snippet,contentDetails", "playlistId": playlist_id},
            max_items,
        )

    async def subscriptions(self, max_items: int | None = None) -> list[dict[str, Any]]:
        return await self._paginate(
            "subscriptions",
            {"part": "snippet,contentDetails", "mine": "true"},
            max_items,
        )

    async def liked_video_items(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """Return every available liked-video item; YouTube pagination is followed to completion."""
        channel = await self.channel()
        items = channel.get("items", [])
        if not items:
            return []
        playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("likes")
        if not playlist_id:
            return []
        return await self.playlist_items(playlist_id, max_items)

    async def owned_playlist_video_items(self, max_playlists: int | None = None) -> list[dict[str, Any]]:
        """Return video items from every playlist owned by the authorized user."""
        result: list[dict[str, Any]] = []
        for playlist in await self.playlists(max_playlists):
            playlist_id = playlist.get("id")
            if not playlist_id:
                continue
            items = await self.playlist_items(playlist_id)
            for item in items:
                item["_nomad_playlist_id"] = playlist_id
                item["_nomad_playlist_title"] = playlist.get("snippet", {}).get("title")
                result.append(item)
        return result

    async def video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Hydrate videos in batches of 50 with duration, category and engagement metadata."""
        results: list[dict[str, Any]] = []
        ids = [x for x in dict.fromkeys(video_ids) if x]
        for start in range(0, len(ids), 50):
            batch = ids[start : start + 50]
            data = await self._get(
                "videos",
                {"part": "snippet,contentDetails,statistics", "id": ",".join(batch)},
            )
            results.extend(data.get("items", []))
        return results

    async def music_video_details_from_user_sources(self) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Collect unique Music-category videos from Likes and all owned playlists."""
        liked = await self.liked_video_items()
        playlist_items = await self.owned_playlist_video_items()
        source_items = liked + playlist_items
        ids = [item.get("contentDetails", {}).get("videoId") for item in source_items]
        details = await self.video_details(ids)
        music = [item for item in details if item.get("snippet", {}).get("categoryId") == "10"]
        return music, {
            "liked_items": len(liked),
            "playlist_items": len(playlist_items),
            "unique_videos": len(set(x for x in ids if x)),
            "videos_hydrated": len(details),
            "music_videos": len(music),
        }

    async def liked_music_videos(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """Compatibility helper for callers that only want liked Music videos."""
        items = await self.liked_video_items(max_items)
        ids = [item.get("contentDetails", {}).get("videoId") for item in items]
        details = await self.video_details(ids)
        return [item for item in details if item.get("snippet", {}).get("categoryId") == "10"]
