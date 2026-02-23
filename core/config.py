from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "washbot"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Telegram Bots
    BOT_CLIENT_TOKEN: str = Field(..., env="BOT_CLIENT_TOKEN")
    BOT_EMPLOYEE_TOKEN: str = Field(..., env="BOT_EMPLOYEE_TOKEN")
    BOT_OWNER_TOKEN: str = Field(..., env="BOT_OWNER_TOKEN")
    
    # Webhook (опционально)
    USE_WEBHOOK: bool = False
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PORT: int = 8443
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
