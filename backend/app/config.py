from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Make these optional for now to allow startup without a full .env
    database_url: Optional[str] = None
    gemini_api_key: Optional[str] = None

    jean_api_base_url: str = "http://localhost:8000" # Default for local dev
    # google_client_id: Optional[str] = None
    # google_client_secret: Optional[str] = None

    # Load from .env file if it exists
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

# Create a single instance to be imported
settings = Settings() 