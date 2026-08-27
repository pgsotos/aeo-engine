"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration loaded from .env / environment."""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""  # anon key

    # Gemini
    gemini_api_key: str = ""

    # Evaluation
    sampling_n: int = 8  # independent runs per prompt

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
