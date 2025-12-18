from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-flash-latest"
    
    dd_service: str = "bearstack"
    dd_env: str = "development"
    dd_version: str = "1.0.0"
    dd_api_key: Optional[str] = None
    dd_app_key: Optional[str] = None
    
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl_seconds: int = 3600
    
    jailbreak_keywords: list[str] = ["ignore"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

