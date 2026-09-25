from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    BACKEND_INTERNAL_URL: str = "http://localhost:8000"
    INTERNAL_WORKER_TOKEN: str = ""

    # RustFS en local/dev, un bucket S3 réel en prod (voir backend
    # StorageSettings, mêmes noms de variables des deux côtés).
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "rustfsadmin"
    S3_SECRET_KEY: str = "rustfsadmin"
    S3_BUCKET: str = "dig-dig-doc"

    # Hub LLM (compatible API OpenAI) - mêmes variables que côté backend
    # (voir app.config.llm.LlmSettings). Le worker en a besoin pour parler
    # au VLM (description d'image) et au LLM (classification/extraction en
    # structured output).
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE_URL: str = ""
    # Modèle vision pour décrire la capture de chaque page (VLM).
    VLM_MODEL: str = "pixtral-12b-2409"
    # Modèle texte pour la classification et l'extraction d'entités.
    LLM_MODEL: str = "llama-3.3-70b-instruct"
    # Taille de batch pour l'extraction d'entités : nombre de pages
    # envoyées en un seul appel LLM (compromis contexte/coût).
    EXTRACTION_BATCH_SIZE: int = 5

    # Nombre maximum d'itérations du graphe LangGraph (pour éviter les
    # boucles infinies).
    AGENT_MAX_ITERATIONS: int = 10
    # Nombre de résultats retournés par la recherche BM25.
    BM25_TOP_K: int = 5

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")

    @property
    def is_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_BASE_URL)


settings = WorkerSettings()
