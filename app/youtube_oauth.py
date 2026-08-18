from __future__ import annotations

import secrets
import time
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.storage import Database

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def create_state() -> str:
    return secrets.token_urlsafe(32)


def authorization_url(state: str) -> str:
    if not settings.youtube_client_id:
        raise RuntimeError("YOUTUBE_CLIENT_ID is not configured")
    params = {
        "client_id": settings.youtube_client_id,
        "redirect_uri": settings.youtube_redirect_uri,
        "response_type": "code",
        "scope": YOUTUBE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    data = {
        "code": code,
        "client_id": settings.youtube_client_id,
        "client_secret": settings.youtube_client_secret,
        "redirect_uri": settings.youtube_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        token = response.json()
    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))
    return token


async def refresh_access_token(refresh_token: str) -> dict:
    data = {
        "client_id": settings.youtube_client_id,
        "client_secret": settings.youtube_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        token = response.json()
    token["refresh_token"] = refresh_token
    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))
    return token


async def get_valid_access_token(db: Database) -> str:
    token = db.get_youtube_oauth_token()
    if not token:
        raise RuntimeError("YouTube account is not connected")

    if token["expires_at"] > int(time.time()) + 60:
        return token["access_token"]

    if not token.get("refresh_token"):
        raise RuntimeError("YouTube access token expired and no refresh token is stored")

    refreshed = await refresh_access_token(token["refresh_token"])
    db.save_youtube_oauth_token(refreshed)
    return refreshed["access_token"]
