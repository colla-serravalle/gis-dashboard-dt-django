from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    verbose_name = "Audit"

    def ready(self):
        import apps.audit.signals  # noqa: F401 — connect signal handlers
