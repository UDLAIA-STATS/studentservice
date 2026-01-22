import json
import logging
from django.conf import settings
from kafka import KafkaConsumer
import time

from stats.management.dispatcher import dispatch_event

logger = logging.getLogger(__name__)

def start_kafka_consumer():
    config = settings.KAFKA_CONFIG

    topics = list(config["ALLOWED_TOPICS"])

    while True:
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=config["BROKER"],
                group_id=config["GROUP_ID"],
                auto_offset_reset="earliest",
                max_poll_records=50,
                max_poll_interval_ms=300000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )

            logger.info(f"Kafka consumer escuchando: {topics}")

            for message in consumer:
                dispatch_event(
                    topic=message.topic,
                    event=message.value
                )

        except Exception:
            logger.exception("Error en Kafka consumer")
            time.sleep(5)