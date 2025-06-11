from django.apps import AppConfig


class AgnoConfig(AppConfig):
    """Django app configuration for Agno integration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agno.app.django'
    verbose_name = 'Agno AI Integration'

    def ready(self):
        """App ready signal handler."""
        pass
