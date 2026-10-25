"""
config.py — Single source of truth for all configuration.
Only this file reads from os.environ / .env.
All other modules import `settings` from here — never os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Ports ---
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    LANDING_PORT: int = 4321

    # --- Database ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str

    # --- RustFS (S3-compatible) ---
    RUSTFS_ENDPOINT: str
    RUSTFS_ACCESS_KEY: str
    RUSTFS_SECRET_KEY: str
    RUSTFS_BUCKET: str

    # --- LLM — change LLM_MODEL here to switch models, no other code changes required ---
    OPENROUTER_API_KEY: str
    LLM_MODEL: str = "openai/gpt-4o"
    LLM_MAX_INPUT_TOKENS: int = 8000
    LLM_MAX_OUTPUT_TOKENS: int = 2000

    # --- Auth / Sessions ---
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # --- Seed user (inserted on first startup) ---
    SEED_USER_EMAIL: str
    SEED_USER_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
