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
                track_id TEXT PRIMARY KEY, title TEXT NOT NULL, artist TEXT NOT NULL,
                fingerprint TEXT NOT NULL, duration_ms INTEGER, artwork_url TEXT,
                source_ids TEXT NOT NULL, metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS listening_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, track_id TEXT NOT NULL,
                played_at TEXT NOT NULL, position_ms INTEGER, duration_ms INTEGER,
                completed INTEGER, skipped INTEGER, liked INTEGER, source TEXT, artist TEXT
            );
            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT
            );
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id TEXT NOT NULL, track_id TEXT NOT NULL, position INTEGER,
                PRIMARY KEY (playlist_id, track_id)
            );
            CREATE TABLE IF NOT EXISTS artists (
                artist_id TEXT PRIMARY KEY, name TEXT NOT NULL, genres TEXT NOT NULL, metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS youtube_oauth_tokens (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                token_type TEXT,
                scope TEXT,
                expires_at INTEGER NOT NULL
            );
            """
        )
        self._ensure_column("listening_events", "artist", "TEXT")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def reset_music_data(self) -> None:
        """Delete all collected music data but keep the Google OAuth connection."""
        self.conn.executescript(
            """
            DELETE FROM playlist_tracks;
            DELETE FROM playlists;
            DELETE FROM listening_events;
            DELETE FROM artists;
            DELETE FROM tracks;
            """
        )
        self.conn.commit()

    def save_youtube_oauth_token(self, token: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO youtube_oauth_tokens(id,access_token,refresh_token,token_type,scope,expires_at)
            VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET access_token=excluded.access_token,
            refresh_token=COALESCE(excluded.refresh_token,youtube_oauth_tokens.refresh_token),
            token_type=excluded.token_type, scope=excluded.scope, expires_at=excluded.expires_at""",
            (token["access_token"], token.get("refresh_token"), token.get("token_type"),
             token.get("scope"), int(token["expires_at"])),
        )
        self.conn.commit()

    def get_youtube_oauth_token(self) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM youtube_oauth_tokens WHERE id=1").fetchone()
        return dict(row) if row else None

    def disconnect_youtube(self) -> None:
        self.conn.execute("DELETE FROM youtube_oauth_tokens WHERE id=1")
        self.conn.commit()

    def upsert_track(self, track: dict[str, Any], fingerprint: str) -> None:
        self.conn.execute(
            """INSERT INTO tracks(track_id,title,artist,fingerprint,duration_ms,artwork_url,source_ids,metadata)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(track_id) DO UPDATE SET title=excluded.title,
            artist=excluded.artist, fingerprint=excluded.fingerprint, duration_ms=excluded.duration_ms,
            artwork_url=excluded.artwork_url, source_ids=excluded.source_ids, metadata=excluded.metadata""",
            (track["track_id"], track["title"], track["artist"], fingerprint, track.get("duration_ms"),
             track.get("artwork_url"), json.dumps(track.get("source_ids", {}), ensure_ascii=False),
             json.dumps(track.get("metadata", {}), ensure_ascii=False)),
        )
        self.conn.commit()

    def tracks(self, limit: int = 100, search: str = "") -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        search = search.strip()
        if search:
            like = f"%{search}%"
            rows = self.conn.execute(
                "SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ? ORDER BY rowid DESC LIMIT ?",
                (like, like, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM tracks ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["source_ids"] = json.loads(item["source_ids"] or "{}")
                item["metadata"] = json.loads(item["metadata"] or "{}")
            except json.JSONDecodeError:
                pass
            result.append(item)
        return result

    def insert_listening_event(self, event: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO listening_events(user_id,track_id,played_at,position_ms,duration_ms,
            completed,skipped,liked,source,artist) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (str(event.get("user_id", "default")), str(event.get("track_id", "")),
             str(event.get("played_at", "unknown")), event.get("position_ms", event.get("positionMs")),
             event.get("duration_ms", event.get("durationMs")), int(bool(event.get("completed"))),
             int(bool(event.get("skipped"))), int(bool(event.get("liked"))), event.get("source"), event.get("artist")),
        )
        self.conn.commit()

    def upsert_playlist(self, playlist_id: str, name: str, description: str | None = None) -> None:
        self.conn.execute(
            """INSERT INTO playlists(playlist_id,name,description) VALUES(?,?,?)
            ON CONFLICT(playlist_id) DO UPDATE SET name=excluded.name, description=excluded.description""",
            (playlist_id, name, description),
        )
        self.conn.commit()

    def link_playlist_track(self, playlist_id: str, track_id: str, position: int) -> None:
        self.conn.execute(
            """INSERT INTO playlist_tracks(playlist_id,track_id,position) VALUES(?,?,?)
            ON CONFLICT(playlist_id,track_id) DO UPDATE SET position=excluded.position""",
            (playlist_id, track_id, position),
        )
        self.conn.commit()

    def stats(self) -> dict[str, int]:
        queries = {
            "tracks": "SELECT COUNT(*) FROM tracks",
            "artists": "SELECT COUNT(DISTINCT artist) FROM tracks WHERE TRIM(artist) <> ''",
            "playlists": "SELECT COUNT(*) FROM playlists",
            "listening_events": "SELECT COUNT(*) FROM listening_events",
            "fingerprinted_tracks": "SELECT COUNT(DISTINCT fingerprint) FROM tracks WHERE fingerprint <> ''",
            "youtube_tracks": "SELECT COUNT(*) FROM tracks WHERE track_id LIKE 'youtube:%'",
            "tracks_with_duration": "SELECT COUNT(*) FROM tracks WHERE duration_ms IS NOT NULL",
        }
        return {name: int(self.conn.execute(sql).fetchone()[0]) for name, sql in queries.items()}

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM listening_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
        return [dict(row) for row in rows]

    def top_artists(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT artist, COUNT(*) AS tracks FROM tracks WHERE TRIM(artist) <> '' GROUP BY artist ORDER BY tracks DESC LIMIT ?", (max(1, min(limit, 50)),)).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.conn.close()
