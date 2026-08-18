from __future__ import annotations

from typing import Any

from app.collectors.user_rest import UserRestCollector
from app.pipeline import ingest_history, ingest_playlists, ingest_tracks, extract_items
from app.storage import Database


async def sync_user_data(collector: UserRestCollector, db: Database, limit: int = 500) -> dict[str, int]:
    """Pull the user's current REST datasets and persist normalized records.

    Endpoint response shapes can be lists or wrapped in items/data/results; the pipeline
    handles both. Playlist details are also fetched when playlist IDs are available.
    """
    tracks = await collector.tracks(limit)
    artists = await collector.artists(limit)
    history = await collector.history(limit)
    likes = await collector.likes(limit)
    playlists = await collector.playlists()

    counts = {
        "tracks": ingest_tracks(db, tracks, "user"),
        "history": ingest_history(db, history, "user"),
        "likes": ingest_history(db, likes, "user_like"),
        "playlists": ingest_playlists(db, playlists, "user"),
        "artists": 0,
    }

    for artist in extract_items(artists):
        artist_id = str(artist.get("artist_id") or artist.get("id") or artist.get("name") or "unknown")
        name = str(artist.get("name") or artist.get("artist") or "Unknown Artist")
        db.conn.execute(
            """INSERT INTO artists(artist_id,name,genres,metadata) VALUES(?,?,?,?)
            ON CONFLICT(artist_id) DO UPDATE SET name=excluded.name, genres=excluded.genres, metadata=excluded.metadata""",
            (artist_id, name, __import__("json").dumps(artist.get("genres", [])), __import__("json").dumps(artist)),
        )
        counts["artists"] += 1
    db.conn.commit()

    playlist_items = extract_items(playlists)
    for playlist in playlist_items:
        playlist_id = playlist.get("playlist_id") or playlist.get("id")
        if playlist_id and not playlist.get("tracks"):
            try:
                detail = await collector.playlist(str(playlist_id))
                ingest_playlists(db, [detail], "user")
            except Exception:
                # A missing/unsupported detail endpoint should not invalidate the full sync.
                pass

    return counts
