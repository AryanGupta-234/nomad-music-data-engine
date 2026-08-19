from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_redirect_uri: str = "http://127.0.0.1:8787/auth/youtube/callback"
    youtube_sync_max_items: int = 0
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8787/auth/spotify/callback"
    user_api_base_url: str = "http://127.0.0.1:8765"
    user_api_token: str = ""
    database_path: str = "data/nomad_music.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
