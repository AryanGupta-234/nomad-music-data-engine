from __future__ import annotations

import hashlib
import re
import unicodedata

from rapidfuzz.fuzz import ratio


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    value = re.sub(r"\([^)]*\)|\[[^]]*\]|\{[^}]*\}", " ", value)
    value = re.sub(r"\b(official|video|audio|lyrics?|visualizer|remastered|hd|hq|4k)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def track_fingerprint(title: str, artist: str, duration_ms: int | None = None) -> str:
    duration_bucket = ""
    if duration_ms is not None:
        duration_bucket = str(round(duration_ms / 5000) * 5)
    payload = f"{normalize_text(artist)}|{normalize_text(title)}|{duration_bucket}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def match_score(title_a: str, artist_a: str, title_b: str, artist_b: str) -> float:
    title_score = ratio(normalize_text(title_a), normalize_text(title_b))
    artist_score = ratio(normalize_text(artist_a), normalize_text(artist_b))
    return round((title_score * 0.65) + (artist_score * 0.35), 2)
