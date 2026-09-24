import boto3
import redis
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import RedisSettings, StorageSettings
from app.db import engine as db_engine
from app.schemas.health import Health


class RedisConnector:
    def __init__(self, url: str) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def get_health(self) -> Health:
        try:
            self.client.ping()
            return Health(name="redis", status="healthy")
        except redis.RedisError as error:
            return Health(name="redis", status="unhealthy", extras={"error": str(error)})


class DatabaseConnector:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def get_health(self) -> Health:
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return Health(name="postgres", status="healthy")
        except Exception as error:
            return Health(name="postgres", status="unhealthy", extras={"error": str(error)})


class S3Connector:
    """RustFS en local/dev, un bucket S3 réel en prod (voir StorageSettings) -
    même client boto3 dans les deux cas, seul endpoint_url change."""

    def __init__(self, settings: StorageSettings) -> None:
        self.bucket = settings.S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=BotoConfig(connect_timeout=2, read_timeout=2, retries={"max_attempts": 0}),
        )

    def get_health(self) -> Health:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return Health(name="s3", status="healthy")
        except (BotoCoreError, ClientError) as error:
            return Health(name="s3", status="unhealthy", extras={"error": str(error)})

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self.client.create_bucket(Bucket=self.bucket)
        except self.client.exceptions.BucketAlreadyOwnedByYou:
            pass
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def download(self, key: str) -> tuple[bytes, str]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        content_type = response.get("ContentType") or "application/octet-stream"
        return response["Body"].read(), content_type

    def delete(self, key: str) -> None:
        # delete_object est idempotent côté S3 (pas d'erreur si la clé
        # n'existe déjà plus) : rien à faire de spécial pour ce cas. On
        # avale seulement les erreurs de connectivité/permission, pour
        # qu'un objet inaccessible ne bloque jamais la suppression DB qui
        # suit (voir DossierRepository.delete_dossier).
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError):
            pass


redis_settings = RedisSettings()
redis_connector = RedisConnector(redis_settings.REDIS_URL)
db_connector = DatabaseConnector(db_engine)
storage_settings = StorageSettings()
s3_connector = S3Connector(storage_settings)
