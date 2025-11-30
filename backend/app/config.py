from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings using Pydantic."""

    # App
    app_name: str = "KEGG Explore API"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kgene"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # KEGG API
    kegg_api_base_url: str = "https://rest.kegg.jp"
    kegg_api_rate_limit: float = 0.35  # seconds between requests (3 req/sec)

    # Background Jobs
    arq_queue_name: str = "kgene:queue"
    max_concurrent_orthologs: int = 10  # parallel ortholog fetching

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
