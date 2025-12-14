from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-flash-latest"
    
    dd_service: str = "gemini-chat-api"
    dd_env: str = "development"
    dd_version: str = "1.0.0"
    
    jailbreak_keywords: list[str] = ["ignore"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

