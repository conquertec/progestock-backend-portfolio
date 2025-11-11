from django.apps import AppConfig

class AuditingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditing'

    # Add this ready method
    def ready(self):
        # This imports the signals file when the app is ready,
        # connecting all the signal receivers within it.
        import auditing.signals