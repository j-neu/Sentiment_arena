from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application configuration from environment variables"""

    # OpenRouter API
    OPENROUTER_API_KEY: str = ""

    # Financial Data APIs
    ALPHAVANTAGE_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./sentiment_arena.db"

    # Trading Configuration
    STARTING_CAPITAL: float = 1000.0
    TRADING_FEE: float = 5.0

    # Market Hours (CET timezone)
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 0
    MARKET_CLOSE_HOUR: int = 17
    MARKET_CLOSE_MINUTE: int = 30
    TIMEZONE: str = "Europe/Berlin"

    # Research Schedule (CET timezone)
    PRE_MARKET_RESEARCH_HOUR: int = 8
    PRE_MARKET_RESEARCH_MINUTE: int = 30
    AFTERNOON_RESEARCH_HOUR: int = 14
    AFTERNOON_RESEARCH_MINUTE: int = 0

    # Active LLM Models
    ACTIVE_MODELS: str = "openai/gpt-4-turbo,anthropic/claude-3-opus-20240229,google/gemini-pro"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"
    DEBUG: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # Research Configuration
    MAX_RESEARCH_SEARCHES: int = 2
    RESEARCH_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def active_models_list(self) -> List[str]:
        """Parse comma-separated models into list"""
        return [m.strip() for m in self.ACTIVE_MODELS.split(",") if m.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
