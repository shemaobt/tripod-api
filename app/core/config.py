from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = "development"
    port: int = 8000

    database_url: str

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:5173"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    google_api_key: str = ""
    google_maps_api_key: str = ""
    google_embedding_model: str = "gemini-embedding-001"
    google_llm_model: str = "gemini-3.1-pro-preview"
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5

    gcs_bucket_name: str = ""
    bhsa_data_path: str = ""

    cleaning_api_url: str = ""
    cleaning_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def qdrant_collection(self) -> str:
        return "meaning_map_prod" if self.env == "production" else "meaning_map_test"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
