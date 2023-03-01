from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ryft.core"

    def ready(self) -> None:
        from .backend import SiweBackend  # noqa
