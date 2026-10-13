"""Structured logging: one JSON object per line on stderr.

Records carry an event message plus fields passed through ``extra=`` (cohort, path,
status, duration_ms, request_id...). Configuration never logs settings or environment
values.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(
            {
                k: v
                for k, v in record.__dict__.items()
                if k not in _STANDARD and not k.startswith("_")
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Idempotent: attaches one JSON handler to the ``app`` and ``analytics`` loggers."""
    for name in ("app", "analytics"):
        logger = logging.getLogger(name)
        logger.setLevel(level.upper())
        if not any(getattr(h, "_saarps", False) for h in logger.handlers):
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(JsonFormatter())
            handler._saarps = True  # type: ignore[attr-defined]
            logger.addHandler(handler)
        logger.propagate = False
