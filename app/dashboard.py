from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.collectors.user_rest import UserRestCollector
from app.config import settings
from app.phase2 import build_user_profile
from app.storage import Database
from app.sync import sync_user_data

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "dashboard"
db = Database(settings.database_path)
app = FastAPI(title="NOMAD Data Engine Dashboard", version="0.3.0")


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
