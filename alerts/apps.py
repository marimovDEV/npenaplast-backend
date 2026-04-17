from django.apps import AppConfig

class AlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alerts'
    verbose_name = 'Bildirishnomalar va Alertlar'

    def ready(self):
        import alerts.signals  # noqa: F401
