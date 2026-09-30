from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # RabbitMQ (AsyncTaskAPI)
    BROKER_URL: str
    IN_QUEUE_NAME: str = "dig_dig_doc_queue_in"
    OUT_QUEUE_NAME: str = "dig_dig_doc_queue_out"
    WORKER_CONCURRENCY: int = 2
    HEALTH_CHECK_HOST: str = "0.0.0.0"  # noqa: S104
    HEALTH_CHECK_PORT: int = 8084
    LOG_LEVEL: str = "INFO"
    # Classe de service déclarée dans `config/services.yaml` d'async-api : elle décide si les appels
    # `progress()` sont émis. Absente, la bibliothèque applique son défaut.
    SERVICE_CLASS: str | None = None

    # Stockage objet d'AsyncTaskAPI, où les fichiers sont déposés avant la tâche.
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_REGION_NAME: str = "fr-par"
    S3_BUCKET_NAME: str
    S3_VERIFY_SSL: bool = True

    # API dig-dig-doc (l'API éphémère est appelée avec un token API : X-App-Token).
    DIGDIGDOC_BASE_URL: str
    DIGDIGDOC_API_TOKEN: str
    DIGDIGDOC_REQUEST_TIMEOUT: float = 30.0

    # Garde-fous : le worker charge les fichiers en mémoire avant de les envoyer au backend
    # (contrat de service d'async-api, §5 : borner ses consommations).
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024
    MAX_TOTAL_SIZE_BYTES: int = 100 * 1024 * 1024
    MAX_FILES: int = 20

    # Durée maximale d'attente de la fin d'un run, et fréquence d'interrogation.
    RUN_TIMEOUT_SECONDS: float = 900.0
    POLL_INTERVAL_SECONDS: float = 3.0
    # Supprime le résultat conservé côté dig-dig-doc une fois renvoyé dans le message `success`.
    DELETE_RUN_AFTER_RESULT: bool = True


settings = Settings()
