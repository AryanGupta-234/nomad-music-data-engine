from __future__ import annotations

from typing import Any

from app.fingerprint import track_fingerprint
from app.storage import Database


def _first(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if data.get(key) is not None:
            return data[key]
    return default


def normalize_track(raw: dict[str, Any], source: str = "user") -> dict[str, Any]:
    artist = _first(raw, "artist", "artist_name", "author", "channelTitle", default="Unknown Artist")
    title = _first(raw, "title", "name", default="Unknown Track")
    duration = _first(raw, "duration_ms", "durationMs", default=None)
    if duration is None and raw.get("duration") is not None:
        duration = int(float(raw["duration"])) if str(raw["duration"]).replace('.', '', 1).isdigit() else None
    provider_id = _first(raw, "track_id", "id", "video_id", "videoId", default=f"{artist}:{title}")
    source_ids = dict(raw.get("source_ids") or {})
    source_ids[source] = str(provider_id)
    return {
        "track_id": str(_first(raw, "canonical_id", "track_id", default=f"{source}:{provider_id}")),
        "title": str(title),
        "artist": str(artist),
        "duration_ms": duration,
        "artwork_url": _first(raw, "artwork_url", "thumbnail", "thumbnail_url"),
        "source_ids": source_ids,
        "metadata": raw,
    }


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "tracks", "artists", "history", "likes", "playlists"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return [payload]
    return []


def ingest_tracks(db: Database, payload: Any, source: str = "user") -> int:
    count = 0
    for raw in extract_items(payload):
        track = normalize_track(raw, source)
        fingerprint = track_fingerprint(track["title"], track["artist"], track.get("duration_ms"))
        db.upsert_track(track, fingerprint)
        count += 1
    return count


def ingest_history(db: Database, payload: Any, source: str = "user") -> int:
    count = 0
    for raw in extract_items(payload):
        track = normalize_track(raw, source)
        fingerprint = track_fingerprint(track["title"], track["artist"], track.get("duration_ms"))
        db.upsert_track(track, fingerprint)
        event = dict(raw)
        event.setdefault("source", source)
        event.setdefault("track_id", track["track_id"])
        event.setdefault("artist", track["artist"])
        event.setdefault("played_at", event.get("timestamp") or event.get("playedAt") or "unknown")
        db.insert_listening_event(event)
        count += 1
    return count


def ingest_playlists(db: Database, payload: Any, source: str = "user") -> int:
    count = 0
    for raw in extract_items(payload):
        playlist_id = str(_first(raw, "playlist_id", "id", default=f"{source}:playlist:{count}"))
        db.upsert_playlist(playlist_id, str(_first(raw, "name", "title", default="Untitled Playlist")), raw.get("description"))
        tracks = raw.get("tracks") or raw.get("items") or []
        if isinstance(tracks, dict):
            tracks = tracks.get("items", [])
        for position, item in enumerate(tracks if isinstance(tracks, list) else []):
            if isinstance(item, dict):
                track = normalize_track(item.get("track", item), source)
                fingerprint = track_fingerprint(track["title"], track["artist"], track.get("duration_ms"))
                db.upsert_track(track, fingerprint)
                db.link_playlist_track(playlist_id, track["track_id"], position)
        count += 1
    return count
