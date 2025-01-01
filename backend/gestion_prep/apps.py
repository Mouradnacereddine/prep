from django.apps import AppConfig
from django.db import models
from typing import Any


class GestionPrepConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # type: ignore
    name = 'gestion_prep'
    verbose_name = 'Gestion des préparations'

    def ready(self) -> None:
        import gestion_prep.signals