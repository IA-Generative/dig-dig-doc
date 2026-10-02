import json
import logging
import logging.config
from datetime import UTC, datetime

# Attributs standard d'un LogRecord : tout le reste vient de ``extra=`` et part tel quel dans le JSON.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "color_message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        # uvicorn.access : args = (client_addr, method, path, http_version, status_code)
        if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, http_version, status_code = record.args
            payload.update(
                message=f"{method} {path} {status_code}",
                client=client,
                method=method,
                path=path,
                http_version=http_version,
                status_code=status_code,
            )
        else:
            payload["message"] = record.getMessage()
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": f"{__name__}.JsonFormatter"}},
            "handlers": {"stdout": {"class": "logging.StreamHandler", "formatter": "json", "stream": "ext://sys.stdout"}},
            "root": {"level": "INFO", "handlers": ["stdout"]},
            "loggers": {
                name: {"handlers": [], "level": "INFO", "propagate": True}
                for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
            },
        }
    )
