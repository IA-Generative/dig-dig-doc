import os

# `src.config.settings` est instancié à l'import : variables minimales pour les tests.
for name, value in {
    "BROKER_URL": "amqp://guest:guest@localhost:5672",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY": "test",
    "S3_SECRET_KEY": "test",
    "S3_BUCKET_NAME": "test",
    "DIGDIGDOC_BASE_URL": "http://localhost:8000",
    "DIGDIGDOC_API_TOKEN": "test",
}.items():
    os.environ.setdefault(name, value)
