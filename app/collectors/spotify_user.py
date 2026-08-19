from __future__ import annotations

from typing import Any

import httpx


class SpotifyUserCollector:
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, access_token: str):
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30, headers=self.headers) as client:
            response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params or {})
            response.raise_for_status()
            return response.json()

    async def _paginate(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = dict(params or {})
        params.setdefault("limit", 50)
        offset = 0
        items: list[dict[str, Any]] = []
        while True:
            params["offset"] = offset
            data = await self._get(endpoint, params)
            batch = data.get("items", [])
            items.extend(batch)
            if not data.get("next") or not batch:
                break
            offset += len(batch)
        return items

    async def profile(self) -> dict:
        return await self._get("me")

    async def saved_tracks(self) -> list[dict]:
        return await self._paginate("me/tracks", {"market": "from_token"})

    async def playlists(self) -> list[dict]:
        return await self._paginate("me/playlists")

    async def followed_artists(self) -> list[dict]:
        # Spotify returns this endpoint as pages with artists.items and artists.next.
        result: list[dict] = []
        after: str | None = None
        while True:
            params: dict[str, Any] = {"type": "artist", "limit": 50}
            if after:
                params["after"] = after
            data = await self._get("me/following", params)
            artists = data.get("artists", {})
            result.extend(artists.get("items", []))
            after = artists.get("cursors", {}).get("after")
            if not artists.get("next"):
                break
        return result

    async def recently_played(self, limit: int = 50) -> list[dict]:
        # This endpoint is intentionally limited by Spotify; do not pretend it is full history.
        data = await self._get("me/player/recently-played", {"limit": min(limit, 50)})
        return data.get("items", [])

    async def snapshot(self) -> dict:
        saved = await self.saved_tracks()
        playlists = await self.playlists()
        artists = await self.followed_artists()
        recent = await self.recently_played()
        return {
            "profile": await self.profile(),
            "saved_tracks": saved,
            "playlists": playlists,
            "followed_artists": artists,
            "recently_played": recent,
        }
