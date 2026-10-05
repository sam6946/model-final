"""Configuration Django de KEMTA.

L'application Celery est importée ici pour être chargée dès que Django démarre
(convention Django) : `from config import celery_app` fonctionne partout.
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
