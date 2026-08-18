from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    youtube_api_key: str = ""
    user_api_base_url: str = "http://127.0.0.1:8765"
    user_api_token: str = ""
    database_path: str = "data/nomad_music.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
