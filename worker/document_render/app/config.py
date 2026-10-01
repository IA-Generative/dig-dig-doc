from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # RustFS en local/dev, un bucket S3 réel en prod (mêmes noms de variables
    # que les autres workers et que le backend).
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "rustfsadmin"
    S3_SECRET_KEY: str = "rustfsadmin"
    S3_BUCKET: str = "dig-dig-doc"

    # LibreOffice en ligne de commande (conversion en PDF).
    SOFFICE_BINARY: str = "soffice"
    # Délai maximal d'une conversion : au-delà, le processus LibreOffice (et ses
    # enfants) est tué.
    SOFFICE_TIMEOUT_SECONDS: int = 120

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")


settings = WorkerSettings()
