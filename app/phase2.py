from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from app.fingerprint import normalize_text, track_fingerprint


def match_tracks(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Explainably compare two track records and return a confidence score."""
    artist_a = normalize_text(a.get("artist", ""))
    artist_b = normalize_text(b.get("artist", ""))
    title_a = normalize_text(a.get("title", ""))
    title_b = normalize_text(b.get("title", ""))

    artist_score = SequenceMatcher(None, artist_a, artist_b).ratio()
    title_score = SequenceMatcher(None, title_a, title_b).ratio()

    da = a.get("duration_ms")
    db = b.get("duration_ms")
    if da and db:
        duration_score = max(0.0, 1.0 - abs(da - db) / max(da, db))
    else:
        duration_score = 0.5

    score = (artist_score * 0.45) + (title_score * 0.45) + (duration_score * 0.10)
    return {
        "confidence": round(score, 4),
        "artist_similarity": round(artist_score, 4),
        "title_similarity": round(title_score, 4),
        "duration_similarity": round(duration_score, 4),
        "match": score >= 0.82,
    }


def build_user_profile(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a transparent behavioral profile from listening events."""
    plays = len(events)
    artist_plays: Counter[str] = Counter()
    track_plays: Counter[str] = Counter()
    genre_plays: Counter[str] = Counter()
    completed = skipped = liked = 0

    for event in events:
        track_id = str(event.get("track_id", ""))
        if track_id:
            track_plays[track_id] += 1
        artist = event.get("artist")
        if artist:
            artist_plays[str(artist)] += 1
        for genre in event.get("genres", []) or []:
            genre_plays[str(genre)] += 1
        completed += int(bool(event.get("completed")))
        skipped += int(bool(event.get("skipped")))
        liked += int(bool(event.get("liked")))

    def normalized(counter: Counter[str]) -> dict[str, float]:
        if not counter:
            return {}
        maximum = max(counter.values())
        return {key: round(value / maximum, 4) for key, value in counter.most_common(50)}

    return {
        "plays": plays,
        "completion_rate": round(completed / plays, 4) if plays else 0.0,
        "skip_rate": round(skipped / plays, 4) if plays else 0.0,
        "like_rate": round(liked / plays, 4) if plays else 0.0,
        "artist_affinity": normalized(artist_plays),
        "track_affinity": normalized(track_plays),
        "genre_affinity": normalized(genre_plays),
    }


def rank_candidates(candidates: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Baseline explainable hybrid ranker; intentionally not ML yet."""
    artists = profile.get("artist_affinity", {})
    genres = profile.get("genre_affinity", {})
    tracks = profile.get("track_affinity", {})
    ranked: list[dict[str, Any]] = []

    for candidate in candidates:
        artist_score = float(artists.get(candidate.get("artist", ""), 0.0))
        track_score = float(tracks.get(candidate.get("track_id", ""), 0.0))
        genre_values = [float(genres.get(g, 0.0)) for g in candidate.get("genres", []) or []]
        genre_score = max(genre_values, default=0.0)
        score = (artist_score * 0.45) + (genre_score * 0.30) + (track_score * 0.15) + 0.10
        item = dict(candidate)
        item["recommendation_score"] = round(score, 4)
        item["score_breakdown"] = {
            "artist_affinity": round(artist_score, 4),
            "genre_affinity": round(genre_score, 4),
            "track_affinity": round(track_score, 4),
            "exploration": 0.10,
        }
        ranked.append(item)

    return sorted(ranked, key=lambda item: item["recommendation_score"], reverse=True)


def fingerprint_for_track(track: dict[str, Any]) -> str:
    return track_fingerprint(
        track.get("title", ""),
        track.get("artist", ""),
        track.get("duration_ms"),
    )
