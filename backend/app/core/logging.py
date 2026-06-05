"""JSON structured logging.

LOG_FORMAT=text (default in dev) or json (set in prod). JSON includes
timestamp, level, logger, message, and any extra fields passed via
`logger.info("...", extra={...})`.
"""
import json
import logging
import os
import sys
import time

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()

# Fields auto-added by stdlib; everything else is treated as user-extras.
_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k in _RESERVED or k.startswith("_"):
                continue
            payload[k] = v
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    # Clean default handlers so uvicorn's reloader can re-init.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-7s %(name)s %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    root.addHandler(handler)
    root.setLevel(LOG_LEVEL)

    # Tame chatty loggers.
    for noisy in ("uvicorn.access", "httpx", "httpcore", "apscheduler"):
        logging.getLogger(noisy).setLevel(
            max(logging.INFO, logging.getLogger(noisy).level)
        )
