from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    CHANNEL_ID: int
    
    DATABASE_URL: str
    DB_ECHO: bool = False
    
    REDIS_URL: str
    REDIS_DB: int = 0
    
    RATE_LIMIT_MESSAGES: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    ENABLE_NSFW_CHECK: bool = True
    ENFORCED_NSFW_CHECK: bool = False
    NSFW_DETECTION_THRESHOLD: float = 0.6

    ENABLE_EDIT: bool = True
    ENABLE_DELETE: bool = True
    
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file='../.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )

settings = Settings()
