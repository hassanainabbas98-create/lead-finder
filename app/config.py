"""Application Configuration module using pydantic-settings."""

import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Business Opportunity Finder"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    SECRET_KEY: str = "dev-secret-key-business-opportunity-finder"


    # Database
    DATABASE_URL: str = "sqlite:///./opportunity_finder.db"

    # Discovery / OSM Overpass settings
    OVERPASS_SERVERS: Union[List[str], str] = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    NOMINATIM_USER_AGENT: str = "BusinessOpportunityFinder/1.0 (https://hasin8n.me; contact: admin@hasin8n.me)"
    OVERPASS_TIMEOUT_SECONDS: int = 8
    DEFAULT_SEARCH_MAX_RESULTS: int = 100

    # Website audit / Scraping settings
    HTTP_TIMEOUT_SECONDS: int = 10
    HTTP_MAX_REDIRECTS: int = 5
    MAX_RESPONSE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    @field_validator("OVERPASS_SERVERS", mode="before")
    @classmethod
    def parse_overpass_servers(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [s.strip() for s in v.split(",") if s.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
