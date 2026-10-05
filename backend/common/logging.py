"""Journalisation structurée (JSON) exploitable par un agrégateur de logs."""
from __future__ import annotations

import json
import logging
import traceback

from django.conf import settings


class StructuredFormatter(logging.Formatter):
    """Formate chaque entrée en JSON une-ligne, prêt pour Loki/Datadog."""

    RESERVED = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
        "pathname", "process", "processName", "relativeCreated", "stack_info",
        "thread", "threadName", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
        request = getattr(record, "request", None)
        if request is not None:
            payload.setdefault("path", getattr(request, "path", None))
            payload.setdefault("method", getattr(request, "method", None))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
            payload["traceback_tail"] = traceback.format_tb(record.exc_info[2])[-5:]
        payload["app"] = "kemta"
        payload["env"] = "prod" if not settings.DEBUG else "dev"
        return json.dumps(payload, ensure_ascii=False, default=str)
