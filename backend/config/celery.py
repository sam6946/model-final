"""Application Celery de KEMTA (broker Redis, beat planifié)."""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import setup_logging, task_failure

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("kemta")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@setup_logging.connect
def _configure_logging(**_: object) -> None:
    """Laisse Django (et notre logging structuré) piloter les logs Celery."""
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, **kwargs) -> None:  # noqa: ANN001
    import logging

    logging.getLogger("kemta.celery").error(
        "celery.task_failed",
        extra={"task": getattr(sender, "name", "?"), "task_id": task_id, "error": str(exception)},
    )
