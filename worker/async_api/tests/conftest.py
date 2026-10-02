import os

# `src.config.settings` est instancié à l'import : variables minimales pour les tests.
for name, value in {
    "BROKER_URL": "amqp://guest:guest@localhost:5672",
    "AWS_ENDPOINT_URL": "http://localhost:9000",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_S3_BUCKET_NAME": "test",
    "DIGDIGDOC_BASE_URL": "http://localhost:8000",
    "DIGDIGDOC_API_TOKEN": "test",
}.items():
    os.environ.setdefault(name, value)
