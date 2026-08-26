import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv('APP_NAME', 'ScamShield API')
    environment: str = os.getenv('ENVIRONMENT', 'development')
    cors_origins: tuple[str, ...] = tuple(os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(','))
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./data/scamshield.db')
    rate_limit_per_minute: int = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    ai_analysis_enabled: bool = os.getenv('AI_ANALYSIS_ENABLED', 'false').lower() == 'true'
    ai_model: str = os.getenv('AI_MODEL', 'gpt-4o-mini')
    max_content_length: int = int(os.getenv('MAX_CONTENT_LENGTH', '50000'))

settings = Settings()
