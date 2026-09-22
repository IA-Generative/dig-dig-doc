from fastapi import FastAPI

app = FastAPI(title="dig-dig-doc BFF")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict[str, str]:
    return {"status": "ok"}
