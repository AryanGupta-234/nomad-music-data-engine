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
app = FastAPI(title="NOMAD Data Engine Dashboard", version="0.5.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "online", "service": "nomad-music-data-engine", "phase": 2}


@app.get("/api/stats")
def stats() -> dict:
    return db.stats()


@app.get("/api/tracks")
def tracks(limit: int = 100, search: str = "") -> list[dict]:
    return db.tracks(limit=limit, search=search)


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
        liked_items = await collector.liked_video_items(max_items=settings.youtube_sync_max_items)
        details = await collector.video_details([
            item.get("contentDetails", {}).get("videoId", "") for item in liked_items
        ])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"YouTube sync failed: {exc}") from exc

    music_count = 0
    skipped_non_music = 0
    for item in details:
        snippet = item.get("snippet", {})
        if snippet.get("categoryId") != "10":
            skipped_non_music += 1
            continue

        video_id = item.get("id")
        if not video_id:
            continue
        music_count += 1
        title = snippet.get("title") or "Unknown"
        artist = (
            snippet.get("videoOwnerChannelTitle")
            or snippet.get("channelTitle")
            or "Unknown"
        )
        content = item.get("contentDetails", {})
        statistics = item.get("statistics", {})
        duration_ms = _iso_duration_ms(content.get("duration"))
        track = {
            "track_id": f"youtube:{video_id}",
            "title": title,
            "artist": artist,
            "duration_ms": duration_ms,
            "artwork_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "source_ids": {"youtube": video_id},
            "metadata": {
                "youtube": {
                    "video_id": video_id,
                    "channel_id": snippet.get("channelId"),
                    "channel_title": snippet.get("channelTitle"),
                    "video_owner_channel_title": snippet.get("videoOwnerChannelTitle"),
                    "published_at": snippet.get("publishedAt"),
                    "description": snippet.get("description"),
                    "tags": snippet.get("tags", []),
                    "category_id": snippet.get("categoryId"),
                    "duration": content.get("duration"),
                    "view_count": statistics.get("viewCount"),
                    "like_count": statistics.get("likeCount"),
                    "comment_count": statistics.get("commentCount"),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            },
        }
        db.upsert_track(track, track_fingerprint(title, artist, duration_ms))

    return {
        "status": "ok",
        "channel": channel.get("items", [])[:1],
        "liked_items_fetched": len(liked_items),
        "videos_hydrated": len(details),
        "music_songs_imported": music_count,
        "non_music_skipped": skipped_non_music,
        "stats": db.stats(),
    }


def _iso_duration_ms(value: str | None) -> int | None:
    if not value or not value.startswith("PT"):
        return None
    import re
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return None
    hours, minutes, seconds = (int(x or 0) for x in match.groups())
    return ((hours * 60 + minutes) * 60 + seconds) * 1000


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
