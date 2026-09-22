from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://digdigdoc:digdigdoc@localhost:5432/digdigdoc"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
