from __future__ import annotations

from typing import Any

import httpx


class UserRestCollector:
    def __init__(self, base_url: str, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=15, headers=self.headers) as client:
            response = await client.get(f"{self.base_url}/{path.lstrip('/')}", params=params)
            response.raise_for_status()
            return response.json()

    async def profile(self) -> Any:
        return await self.get("api/user/profile")

    async def tracks(self, limit: int = 100) -> Any:
        return await self.get("api/user/tracks", {"limit": limit})

    async def artists(self, limit: int = 100) -> Any:
        return await self.get("api/user/artists", {"limit": limit})

    async def history(self, limit: int = 500) -> Any:
        return await self.get("api/user/history", {"limit": limit})

    async def likes(self, limit: int = 500) -> Any:
        return await self.get("api/user/likes", {"limit": limit})

    async def playlists(self) -> Any:
        return await self.get("api/user/playlists")

    async def playlist(self, playlist_id: str) -> Any:
        return await self.get(f"api/user/playlists/{playlist_id}")
