from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_S3_ENDPOINT_URL = "http://localhost:9000"


class WorkerSettings(BaseSettings):
    # Broker et résultats Celery. En Kubernetes, le secret `digdigdoc-redis` fournit `REDIS_URL` (avec le mot de
    # passe) : à défaut de `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (docker-compose), c'est lui qui sert.
    REDIS_URL: str = ""
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # RustFS en local/dev, un bucket S3 réel en prod. En Kubernetes, l'endpoint complet est `AWS_ENDPOINT_URL`
    # (défini par le chart) ; le secret `digdigdoc-s3` peut fournir `S3_ENDPOINT_URL`, parfois sans schéma.
    AWS_ENDPOINT_URL: str = ""
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = "rustfsadmin"
    S3_SECRET_KEY: str = "rustfsadmin"
    S3_BUCKET: str = "dig-dig-doc"

    # LibreOffice en ligne de commande (conversion en PDF).
    SOFFICE_BINARY: str = "soffice"
    # Délai maximal d'une conversion : au-delà, le processus LibreOffice (et ses enfants) est tué.
    SOFFICE_TIMEOUT_SECONDS: int = 120
    # Fontconfig : sert à savoir si une police du modèle est installée dans l'image (issue #148).
    FC_MATCH_BINARY: str = "fc-match"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")

    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL or DEFAULT_REDIS_URL

    @property
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL or DEFAULT_REDIS_URL

    @property
    def s3_endpoint_url(self) -> str:
        """Endpoint S3 avec son schéma : boto3 refuse un hôte nu (`s3.fr-par.scw.cloud`)."""
        url = self.AWS_ENDPOINT_URL or self.S3_ENDPOINT_URL or DEFAULT_S3_ENDPOINT_URL
        return url if "://" in url else f"https://{url}"


settings = WorkerSettings()
