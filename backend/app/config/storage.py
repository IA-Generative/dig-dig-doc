from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    # RustFS en local/dev (docker-compose), un bucket S3 réel en prod : même
    # API S3, seul l'endpoint change.
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "rustfsadmin"
    S3_SECRET_KEY: str = "rustfsadmin"
    S3_BUCKET: str = "dig-dig-doc"
    S3_REGION: str = "us-east-1"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
