from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                duration_ms INTEGER,
                artwork_url TEXT,
                source_ids TEXT NOT NULL,
                metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS listening_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                played_at TEXT NOT NULL,
                position_ms INTEGER,
                duration_ms INTEGER,
                completed INTEGER,
                skipped INTEGER,
                liked INTEGER,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            );
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                position INTEGER,
                PRIMARY KEY (playlist_id, track_id)
            );
            CREATE TABLE IF NOT EXISTS artists (
                artist_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                genres TEXT NOT NULL,
                metadata TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def upsert_track(self, track: dict[str, Any], fingerprint: str) -> None:
        self.conn.execute(
            """INSERT INTO tracks(track_id,title,artist,fingerprint,duration_ms,artwork_url,source_ids,metadata)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(track_id) DO UPDATE SET title=excluded.title, artist=excluded.artist,
            fingerprint=excluded.fingerprint, duration_ms=excluded.duration_ms,
            artwork_url=excluded.artwork_url, source_ids=excluded.source_ids, metadata=excluded.metadata""",
            (
                track["track_id"], track["title"], track["artist"], fingerprint,
                track.get("duration_ms"), track.get("artwork_url"),
                json.dumps(track.get("source_ids", {})), json.dumps(track.get("metadata", {})),
            ),
        )
        self.conn.commit()

    def stats(self) -> dict[str, int]:
        queries = {
            "tracks": "SELECT COUNT(*) FROM tracks",
            "artists": "SELECT COUNT(*) FROM artists",
            "playlists": "SELECT COUNT(*) FROM playlists",
            "listening_events": "SELECT COUNT(*) FROM listening_events",
            "fingerprinted_tracks": "SELECT COUNT(DISTINCT fingerprint) FROM tracks WHERE fingerprint <> ''",
        }
        return {name: int(self.conn.execute(sql).fetchone()[0]) for name, sql in queries.items()}

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM listening_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)
        ).fetchall()
        return [dict(row) for row in rows]

    def top_artists(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT artist, COUNT(*) AS tracks FROM tracks GROUP BY artist ORDER BY tracks DESC LIMIT ?",
            (max(1, min(limit, 50)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.conn.close()
