import boto3

from app.config import settings


class RustFsStorage:
    """RustFS est compatible S3 - un client boto3 classique lui parle
    directement, pas besoin d'un SDK dédié à RustFS."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        self._bucket = settings.S3_BUCKET

    def get_object(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        # Le bucket existe déjà : un document ne peut être traité que s'il a
        # d'abord été uploadé par le backend (voir S3Connector.upload côté
        # backend, qui le crée si besoin).
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)


storage = RustFsStorage()
