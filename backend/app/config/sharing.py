from pydantic_settings import BaseSettings, SettingsConfigDict


class SharingSettings(BaseSettings):
    # Clé secrète du HMAC signant les liens de partage d'analyse par email
    # (magic link) - à changer en prod, comme KEYCLOAK_CLIENT_SECRET.
    SHARE_SECRET_KEY: str = "dev-only-share-secret-not-for-prod"
    SHARE_DEFAULT_TTL_HOURS: int = 7 * 24

    # Jeton partagé par lequel les workers Celery s'authentifient sur les
    # routes de callback (/api/internal/*) : ce ne sont pas des clients
    # Keycloak, donc pas de session/bearer token utilisateur.
    INTERNAL_WORKER_TOKEN: str = "dev-only-worker-token-not-for-prod"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
