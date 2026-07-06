"""Runtime configuration, loaded from the environment via pydantic-settings.

One typed Settings object instead of scattered ``os.environ`` reads. In the
cloud these come from Lambda env vars; locally from a ``.env`` file.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COPILOT_", env_file=".env", extra="ignore")

    # --- storage / AWS ---
    table_name: str = "career-copilot"
    aws_region: str = "us-east-1"

    # --- identity ---
    owner_user_id: str = ""  # Cognito sub the cron writes the briefing under
    my_email: str = ""

    # --- Secrets Manager ids (resolved at runtime in the cloud) ---
    gmail_secret_id: str = "career-copilot/gmail"
    gemini_secret_id: str = "career-copilot/gemini"

    # --- direct keys (local dev / tests; prefer secrets in the cloud) ---
    gemini_api_key: str = ""

    # --- job engine ---
    ja_db_path: str = ""
    min_job_score: int = Field(default=40, ge=0, le=100)
    max_jobs: int = Field(default=8, ge=1, le=50)


def load_settings() -> Settings:
    """Build Settings from the environment. Kept as a function for easy overriding in tests."""
    return Settings()
