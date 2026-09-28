"""Central settings. All secrets come from env vars / .env — never hardcoded."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- AI (Groq, OpenAI-compatible endpoint) ---
    groq_api_key: Optional[str] = None
    groq_model_vision: str = "qwen/qwen3.8-27b"
    groq_model_supporting: str = "openai/gpt-oss-120b"
    groq_model_adversarial: str = "openai/gpt-oss-20b"  # llama-3.3-70b-versatile retired from Groq (404, verified Sep 2026)
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # --- Cloudinary ---
    cloudinary_cloud_name: Optional[str] = None
    cloudinary_api_key: Optional[str] = None
    cloudinary_api_secret: Optional[str] = None

    # --- Firebase ---
    firebase_credentials_json: Optional[str] = None  # full service-account JSON on one line
    firebase_credentials_path: Optional[str] = None  # or a path to the JSON file

    # --- App ---
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 50
    max_frames_per_video: int = 3

    # --- Demo mode (no credentials needed) ---
    demo_mode: bool = False  # DEMO_MODE=1 -> in-memory Firestore + local media storage
    public_base_url: str = "http://localhost:8000"  # base URL for demo media links

    @property
    def cloudinary_configured(self) -> bool:
        return all([self.cloudinary_cloud_name, self.cloudinary_api_key, self.cloudinary_api_secret])

    @property
    def firebase_configured(self) -> bool:
        return bool(self.firebase_credentials_json or self.firebase_credentials_path)

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
