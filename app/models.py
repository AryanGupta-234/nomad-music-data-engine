from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Track:
    track_id: str
    title: str
    artist: str
    artist_id: str | None = None
    album: str | None = None
    album_id: str | None = None
    duration_ms: int | None = None
    artwork_url: str | None = None
    source_ids: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ListeningEvent:
    user_id: str
    track_id: str
    played_at: str
    position_ms: int | None = None
    duration_ms: int | None = None
    completed: bool | None = None
    skipped: bool | None = None
    liked: bool | None = None
    source: str | None = None


@dataclass
class Playlist:
    playlist_id: str
    name: str
    description: str | None = None
    track_ids: list[str] = field(default_factory=list)


@dataclass
class Artist:
    artist_id: str
    name: str
    genres: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
