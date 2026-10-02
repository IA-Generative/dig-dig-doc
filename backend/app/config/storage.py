from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    # RustFS en local/dev (docker-compose), un bucket S3 réel en prod : même
    # API S3, seul l'endpoint change.
    AWS_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_ACCESS_KEY_ID: str = "rustfsadmin"
    AWS_SECRET_ACCESS_KEY: str = "rustfsadmin"
    AWS_S3_BUCKET_NAME: str = "dig-dig-doc"
    AWS_DEFAULT_REGION: str = "us-east-1"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
