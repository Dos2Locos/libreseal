from django.apps import AppConfig


class APIConfig(AppConfig):
    name = "api"

    def ready(self):
        import api.signals  # noqa: F401

        # LibreSeal does not ship the upstream license checker or the log
        # stream sweeper (both live in Phase's Enterprise-licensed ee/ code),
        # so no post_migrate hooks are registered here.
