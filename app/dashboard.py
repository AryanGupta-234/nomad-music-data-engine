from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import settings
from app.storage import Database

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "dashboard"

db = Database(settings.database_path)
app = FastAPI(title="NOMAD Data Engine Dashboard", version="0.2.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "online", "service": "nomad-music-data-engine"}


@app.get("/api/stats")
def stats() -> dict:
    return db.stats()


@app.get("/api/artists")
def artists(limit: int = 10) -> list[dict]:
    return db.top_artists(limit)


@app.get("/api/events")
def events(limit: int = 50) -> list[dict]:
    return db.recent_events(limit)


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
