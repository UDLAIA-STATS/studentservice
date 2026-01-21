from django.apps import AppConfig
import threading
import os
import logging

logger = logging.getLogger(__name__)

class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "events"

    def ready(self):
        # Evita ejecutar dos veces con runserver
        if os.environ.get("RUN_MAIN") != "true":
            return

        from ..consumer import start_kafka_consumer

        thread = threading.Thread(
            target=start_kafka_consumer,
            daemon=True
        )
        thread.start()

def handle_event(event: dict):
    """
    Lógica de negocio real
    """
    logger.info(f"Procesando evento: {event}")
