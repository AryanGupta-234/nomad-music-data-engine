from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.collectors.user_rest import UserRestCollector
from app.collectors.youtube_user import YouTubeUserCollector
from app.config import settings
from app.fingerprint import track_fingerprint
from app.phase2 import build_user_profile
from app.storage import Database
from app.sync import sync_user_data
from app.youtube_oauth import authorization_url, create_state, exchange_code, get_valid_access_token

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "dashboard"
db = Database(settings.database_path)
app = FastAPI(title="NOMAD Data Engine Dashboard", version="0.4.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "online", "service": "nomad-music-data-engine", "phase": 2}


@app.get("/api/stats")
def stats() -> dict:
    return db.stats()


@app.get("/api/artists")
def artists(limit: int = 10) -> list[dict]:
    return db.top_artists(limit)


@app.get("/api/events")
def events(limit: int = 50) -> list[dict]:
    return db.recent_events(limit)


@app.get("/api/profile")
def profile() -> dict:
    return build_user_profile(db.recent_events(2000))


@app.get("/api/youtube/status")
def youtube_status() -> dict:
    token = db.get_youtube_oauth_token()
    return {"connected": bool(token), "has_refresh_token": bool(token and token.get("refresh_token"))}


@app.get("/auth/youtube")
def youtube_login() -> RedirectResponse:
    state = create_state()
    response = RedirectResponse(authorization_url(state), status_code=302)
    response.set_cookie("nomad_oauth_state", state, httponly=True, samesite="lax", max_age=600)
    return response


@app.get("/auth/youtube/callback")
async def youtube_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth denied: {error}")
    expected = request.cookies.get("nomad_oauth_state")
    if not state or not expected or not secrets.compare_digest(state, expected):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    try:
        token = await exchange_code(code)
        db.save_youtube_oauth_token(token)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google token exchange failed: {exc}") from exc
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("nomad_oauth_state")
    return response


@app.post("/api/youtube/disconnect")
def youtube_disconnect() -> dict:
    db.disconnect_youtube()
    return {"status": "disconnected"}


@app.post("/api/youtube/sync")
async def youtube_sync() -> dict:
    try:
        access_token = await get_valid_access_token(db)
        collector = YouTubeUserCollector(access_token)
        channel = await collector.channel()
        playlists = await collector.playlists()
        subscriptions = await collector.subscriptions()
        likes = await collector.liked_videos()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YouTube sync failed: {exc}") from exc

    for item in likes.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("contentDetails", {}).get("videoId") or item.get("id", {}).get("videoId")
        if not video_id:
            continue
        title = snippet.get("title") or "Unknown"
        artist = snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle") or "Unknown"
        track = {
            "track_id": f"youtube:{video_id}",
            "title": title,
            "artist": artist,
            "duration_ms": None,
            "artwork_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "source_ids": {"youtube": video_id},
            "metadata": {"youtube": item},
        }
        db.upsert_track(track, track_fingerprint(title, artist, None))

    return {
        "status": "ok",
        "channel": channel.get("items", [])[:1],
        "playlists": len(playlists.get("items", [])),
        "subscriptions": len(subscriptions.get("items", [])),
        "liked_videos": len(likes.get("items", [])),
        "stats": db.stats(),
    }


@app.post("/api/sync/user")
async def sync_user() -> dict:
    if not settings.user_api_token:
        raise HTTPException(status_code=400, detail="USER_API_TOKEN is not configured")
    collector = UserRestCollector(settings.user_api_base_url, settings.user_api_token)
    try:
        counts = await sync_user_data(collector, db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"User API sync failed: {exc}") from exc
    return {"status": "ok", "synced": counts, "stats": db.stats()}


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
