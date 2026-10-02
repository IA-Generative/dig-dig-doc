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
    # (Mode « legacy » uniquement, voir EXTRACTION_MODE.)
    EXTRACTION_BATCH_SIZE: int = 5

    # Extraction d'entités (issue #126) :
    # - "by_document" : un appel par (lot de pages d'un même document × groupe
    #   de définitions) ; les lots sont définis par un budget de jetons.
    # - "legacy" : l'ancien comportement (lots de EXTRACTION_BATCH_SIZE pages
    #   sur tout le dossier, toutes les définitions dans un seul appel), à
    #   garder le temps de valider le nouveau découpage sur de vrais dossiers.
    EXTRACTION_MODE: str = "by_document"
    # Budget total d'un appel (texte des pages + définitions + prompt + réponse),
    # en jetons estimés (un jeton ~ 4 caractères).
    EXTRACTION_MAX_TOKENS: int = 8000
    # Part du budget réservée à la réponse du LLM.
    EXTRACTION_RESERVED_OUTPUT_TOKENS: int = 1500
    # Pages communes entre deux lots consécutifs d'un document (pour ne pas
    # couper une entité qui s'étend sur deux lots).
    EXTRACTION_OVERLAP_PAGES: int = 1
    # Taille des groupes de définitions d'entités (0 : un seul groupe).
    EXTRACTION_DEFINITIONS_PER_GROUP: int = 8

    # Génération des valeurs de champs d'un document (issue #141) : budget de jetons estimés du contexte
    # (éléments de l'analyse et notes) d'un appel, nombre de champs par appel, et taille maximale d'un
    # élément ou d'une note avant coupe. Des réglages à ajuster sur de vrais dossiers.
    GENERATION_MAX_CONTEXT_TOKENS: int = 12000
    GENERATION_FIELDS_PER_CALL: int = 10
    GENERATION_MAX_ITEM_CHARS: int = 1500

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
