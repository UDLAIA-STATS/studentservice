from kafka import KafkaProducer
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

_producer = None


def get_producer():
    global _producer

    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_CONFIG["BROKER"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def publish_event(topic: str, event: dict):
    if topic not in settings.KAFKA_CONFIG["ALLOWED_TOPICS"]:
        raise ValueError(f"Tópico no permitido: {topic}")

    producer = get_producer()
    producer.send(topic, value=event)
    producer.flush()

    logger.info(f"Evento publicado en tópico {topic}")
