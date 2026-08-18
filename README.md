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
- Google OAuth 2.0 connection for authorized YouTube user data.
- YouTube user collector for channel, owned playlists, subscriptions, and liked videos.
- OAuth access-token refresh using the stored refresh token.

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### YouTube public API

Set `YOUTUBE_API_KEY` for public catalog search.

### YouTube user OAuth

In Google Cloud, create an OAuth 2.0 **Web application** client and add this exact local redirect URI:

```text
http://127.0.0.1:8787/auth/youtube/callback
```

Then set:

```env
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REDIRECT_URI=http://127.0.0.1:8787/auth/youtube/callback
```

Start the dashboard:

```bash
python -m uvicorn app.dashboard:app --reload --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787` and click **Connect YouTube with Google**. Google authorization produces an access token and, for offline access, a refresh token. The tokens are stored in the local SQLite database and never printed in the dashboard.

The dashboard can then use **Sync YouTube** to ingest authorized user data.

> Development note: OAuth tokens are stored in the local SQLite database for this single-user development engine. Before production/multi-user deployment, move tokens to encrypted secret storage and add per-user token ownership.

## Run the YouTube collector

```bash
python main.py
```

The CLI explicitly configures UTF-8 output and JSON-escapes metadata so Windows runners using legacy `cp1252` cannot crash when a YouTube title contains Unicode characters.

## Developer dashboard

```bash
python -m uvicorn app.dashboard:app --reload --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787`.

The dashboard refreshes every five seconds and shows:

- track / artist / playlist / listening-event counts
- fingerprint coverage
- top artists
- recent listening events
- user taste profile
- YouTube OAuth connection status
- YouTube sync controls
- engine health

## User REST API

`UserRestCollector` remains separate from YouTube OAuth. It expects these endpoints by default:

- `GET /api/user/profile`
- `GET /api/user/tracks`
- `GET /api/user/artists`
- `GET /api/user/history`
- `GET /api/user/likes`
- `GET /api/user/playlists`
- `GET /api/user/playlists/{id}`

Use `USER_API_TOKEN` only if the existing NOMAD REST API requires bearer authentication. It is **not** the YouTube OAuth token.

## YouTube user data

The authorized collector uses the YouTube Data API with OAuth bearer authentication for:

- the authenticated channel
- playlists owned by the user
- playlist items
- subscriptions
- the user's liked-videos playlist when exposed by the channel's related playlists

YouTube API availability does not imply that every piece of account activity, such as private watch history, is exposed. The engine only ingests resources Google makes available through the authorized API.

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
