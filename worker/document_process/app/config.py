from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class WorkerSettings(BaseSettings):
    # Broker et résultats Celery. En Kubernetes, le secret `millefeuille-redis` fournit `REDIS_URL` (avec le mot de
    # passe) : à défaut de `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (docker-compose), c'est lui qui sert.
    REDIS_URL: str = ""
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    BACKEND_INTERNAL_URL: str = "http://localhost:8000"
    INTERNAL_WORKER_TOKEN: str = ""

    # RustFS en local/dev, un bucket S3 réel en prod (voir backend
    # StorageSettings, mêmes noms de variables des deux côtés).
    AWS_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_ACCESS_KEY_ID: str = "rustfsadmin"
    AWS_SECRET_ACCESS_KEY: str = "rustfsadmin"
    AWS_S3_BUCKET_NAME: str = "mille-feuille"

    # Langue Tesseract (ISO 639-2) pour l'OCR des pages scannées par
    # liteparse. "fra" couvre le français par défaut.
    OCR_LANGUAGE: str = "fra"
    TESSDATA_PATH: str | None = None

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")

    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL or DEFAULT_REDIS_URL

    @property
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL or DEFAULT_REDIS_URL


settings = WorkerSettings()
