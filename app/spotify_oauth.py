from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "user-read-private user-read-email user-library-read playlist-read-private playlist-read-collaborative user-follow-read user-read-recently-played"


def authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "true",
    })


def new_state() -> str:
    return secrets.token_urlsafe(32)


async def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        return response.json()


async def refresh_token(client_id: str, client_secret: str, refresh: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh},
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        return response.json()
