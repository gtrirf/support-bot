from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
from zoneinfo import ZoneInfo

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    admins: List[int] = Field(default_factory=list, alias="ADMINS")

    timezone: str = Field(default="UTC", alias="TIMEZONE")
    database_url: str = Field(default="support_bot.db", alias="DATABASE_URL")
    session_timeout: int = Field(default=300, alias="SESSION_TIMEOUT")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

settings = Settings()
