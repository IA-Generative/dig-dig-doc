from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseSettings):
    OPENAI_API_KEY: str = ""
    # No default: an empty value makes /api/models fail loudly instead of
    # silently talking to a public hub that isn't ours.
    OPENAI_API_BASE_URL: str = ""
    CHAT_MODELS_CACHE_TTL_SECONDS: int = 3600

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")

    @property
    def is_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_BASE_URL)
