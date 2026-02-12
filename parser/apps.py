from django.apps import AppConfig


class ParserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parser'

    def ready(self):
        """
        Initialize app when Django starts.
        Import signals or perform other initialization.
        """
        pass
