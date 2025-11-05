"""Application configuration using Pydantic settings"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    APP_NAME: str = "Mindful AI Counselor"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")
    SQL_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(..., description="Redis connection URL")
    CACHE_TTL_SECONDS: int = Field(default=3600)
    SIMILARITY_THRESHOLD: float = Field(default=0.85)

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = Field(default=1000)
    OPENAI_TEMPERATURE: float = Field(default=0.7)

    # Context Management
    MAX_CONTEXT_MESSAGES: int = Field(default=20)
    VECTOR_SEARCH_TOP_K: int = Field(default=5)

    # Crisis Detection
    CRISIS_KEYWORDS_THRESHOLD: int = Field(default=3)
    CRISIS_ALERT_EMAIL: str = Field(default="")
    CRISIS_KEYWORDS: str = Field(
        default="suicide,kill myself,end my life,self-harm,hurt myself,don't want to live"
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=500)

    # Compliance
    ENABLE_ENCRYPTION: bool = Field(default=True)
    DATA_RETENTION_DAYS: int = Field(default=90)
    ENABLE_AUDIT_LOG: bool = Field(default=True)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    SENTRY_DSN: str = Field(default="")

    @validator("ALLOWED_ORIGINS")
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins"""
        return [origin.strip() for origin in v.split(",")]

    @validator("CRISIS_KEYWORDS")
    def parse_crisis_keywords(cls, v: str) -> List[str]:
        """Parse comma-separated crisis keywords"""
        return [keyword.strip().lower() for keyword in v.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
