# NOMAD Music Data Engine

Phase 1 ingestion foundation for building NOMAD's own music recommendation dataset.

## Sources

- YouTube Data API v3 for song/video metadata and engagement statistics.
- A generic user REST API for tracks, artists, listening history, likes, and playlists.

## Core capabilities

- Normalize song metadata into a canonical track representation.
- Generate deterministic track fingerprints.
- Fuzzy-match artist/title pairs across providers.
- Store tracks, listening events, playlists, and artists in SQLite.
- Keep API credentials in `.env` only.

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set `YOUTUBE_API_KEY` in `.env` before using the YouTube collector.

## YouTube

```python
from app.collectors.youtube import search_songs, get_video_details
```

`search_songs()` searches YouTube's Music category and returns normalized video/song metadata. `get_video_details()` adds duration, tags, and engagement statistics.

## User REST API

`UserRestCollector` expects these endpoints by default:

- `GET /api/user/profile`
- `GET /api/user/tracks`
- `GET /api/user/artists`
- `GET /api/user/history`
- `GET /api/user/likes`
- `GET /api/user/playlists`
- `GET /api/user/playlists/{id}`

The paths are intentionally easy to adapt to NOMAD's existing API.

## Fingerprinting

`app/fingerprint.py` normalizes titles and artists, removes common YouTube noise such as `official video`, and creates a stable SHA-256 fingerprint. It also exposes a fuzzy matching score for cross-source entity resolution.

## Roadmap

1. Connect the collector to NOMAD's real user REST endpoints.
2. Add batch YouTube detail hydration with quota-aware retries.
3. Persist canonical tracks and source mappings.
4. Add audio fingerprinting/features where legally and technically available.
5. Build behavioral feature aggregation.
6. Train the NOMAD recommendation engine.
