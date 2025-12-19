from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-flash-latest"
    
    DD_SERVICE: str = "bearstack"
    DD_ENV: str = "development"
    DD_VERSION: str = "1.0.0"
    DD_API_KEY: Optional[str] = None
    DD_APP_KEY: Optional[str] = None
    
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL_SECONDS: int = 3600
    
    JAILBREAK_KEYWORDS: list[str] = ["ignore"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

