from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"

    def ready(self) -> None:
        from apps.dashboard import signals  # noqa: F401  (enregistre les signaux)
