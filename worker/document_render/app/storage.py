import boto3

from app.config import settings


class RustFsStorage:
    """RustFS est compatible S3 : un client boto3 classique lui parle directement
    (même implémentation que les autres workers, mais ce worker écrit aussi : il
    dépose les documents générés)."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        self._bucket = settings.S3_BUCKET

    def get_object(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)


storage = RustFsStorage()
