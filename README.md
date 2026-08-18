# NOMAD Music Data Engine

Phase 2 data-intelligence foundation for building NOMAD's own music recommendation system.

## Phase 1

- YouTube Data API v3 song/video metadata and engagement statistics.
- Generic user REST API for tracks, artists, listening history, likes, and playlists.
- Canonical normalization and deterministic track fingerprints.
- SQLite storage for tracks, listening events, playlists, and artists.
- Credentials loaded from `.env` and excluded from Git.

## Phase 2

- Explainable cross-source entity matching with title, artist, and duration similarity.
- User taste profiling from plays, completion, skips, likes, artists, genres, and tracks.
- Baseline hybrid candidate ranker with score breakdowns.
- Live developer dashboard for ingestion/database visibility.
- Dashboard APIs for health, dataset statistics, top artists, and recent listening events.

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set `YOUTUBE_API_KEY` in `.env` before using the YouTube collector.

## Run the YouTube collector

```bash
python main.py
```

The CLI explicitly configures UTF-8 output and JSON-escapes metadata so Windows runners using legacy `cp1252` cannot crash when a YouTube title contains Unicode characters.

## Run the developer dashboard

```bash
python -m uvicorn app.dashboard:app --reload --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787`.

The dashboard refreshes every five seconds and shows:

- track / artist / playlist / listening-event counts
- fingerprint coverage
- top artists
- recent listening events
- engine health

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

## Phase 2 engine

`app/phase2.py` contains the first explainable intelligence layer:

- `match_tracks()` — cross-source match confidence.
- `build_user_profile()` — behavioral taste profile.
- `rank_candidates()` — baseline hybrid recommendation ranking.
- `fingerprint_for_track()` — canonical fingerprint helper.

This is deliberately a transparent baseline. ML, embeddings, collaborative filtering, and sequence models are reserved for Phase 3 after enough clean behavioral data exists.

## Roadmap

1. Connect the collector to NOMAD's real user REST endpoints.
2. Add batch YouTube detail hydration with quota-aware retries.
3. Persist canonical source mappings and match decisions.
4. Add richer behavioral feature aggregation and time decay.
5. Expand the dashboard with ingestion jobs, matching review, user taste, and recommendation explanations.
6. Train the NOMAD recommendation engine in Phase 3.
