from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str
    jean_api_base_url: str = "http://localhost:8000" # Default for local dev
    # google_client_id: Optional[str] = None
    # google_client_secret: Optional[str] = None

    # Load from .env file
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

# Create a single instance to be imported
settings = Settings() 