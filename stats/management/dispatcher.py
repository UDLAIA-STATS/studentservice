import logging
from stats.management import handle_player_stats  

logger = logging.getLogger(__name__)


TOPIC_HANDLERS = {
    "write.stats": handle_player_stats,
}


def dispatch_event(topic: str, event: dict):
    handler = TOPIC_HANDLERS.get(topic)

    if not handler:
        logger.warning(f"Sin handler para tópico {topic}")
        return
    
    logger.info(f"Despachando evento para tópico {topic}: {event}")
    handler(event)
