import json
import logging
from django.core.management.base import BaseCommand
from kafka import KafkaConsumer
from django.db import transaction
from .models import PlayerStatsConsolidated
from .services import actualizar_estadisticas_generales
from jugadores.models import Jugadores

logger = logging.getLogger(__name__)


class StatsKafkaConsumer:
    """Consumer de Kafka para estadísticas de jugadores"""
    
    def __init__(self, bootstrap_servers='localhost:9092', topic='player-stats'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.consumer = None
    
    def connect(self):
        """Conecta al broker de Kafka"""
        self.consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=[self.bootstrap_servers],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='stats-service-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            max_poll_records=100,
        )
    
    @transaction.atomic
    def process_message(self, message: dict) -> bool:
        """
        Procesa mensaje de Kafka con estadísticas del modelo IA
        
        Esperado:
        {
            "shirt_number": 10,
            "shirt_color": "BLUE",
            "match_id": 123,
            "passes": 45,
            "shots_on_target": 3,
            "has_goal": 1,
            "distance_km": 9.5,
            "avg_possession_time_s": 120,
            "avg_speed_kmh": 7.2
        }
        """
        try:
            shirt_number = message.get('shirt_number')
            shirt_color = message.get('shirt_color')
            match_id = message.get('match_id')
            
            if not all([shirt_number, shirt_color, match_id]):
                logger.error(f"Datos incompletos en mensaje: {message}")
                return False
            
            # Buscar jugador activo por número y color de camiseta
            jugador = Jugadores.objects.filter(
                numerocamisetajugador=shirt_number,
                jugadoractivo=True
            ).first()
            
            if not jugador:
                logger.warning(
                    f"Jugador no encontrado: shirt_number={shirt_number}, "
                    f"color={shirt_color}"
                )
                return False
            
            # Crear o actualizar estadísticas consolidadas
            stats, created = PlayerStatsConsolidated.objects.update_or_create(
                player_id=jugador.idjugador,
                match_id=match_id,
                defaults={
                    'shirt_number': shirt_number,
                    'shirt_color': shirt_color,
                    'passes': message.get('passes', 0),
                    'shots_on_target': message.get('shots_on_target', 0),
                    'has_goal': message.get('has_goal', 0),
                    'distance_km': message.get('distance_km', 0.0),
                    'avg_possession_time_s': message.get('avg_possession_time_s', 0),
                    'avg_speed_kmh': message.get('avg_speed_kmh', 0.0),
                }
            )
            
            action = "Creada" if created else "Actualizada"
            logger.info(
                f"{action} estadística para jugador {jugador.idjugador} "
                f"en partido {match_id}"
            )
            
            # Actualizar histórico de estadísticas generales
            actualizar_estadisticas_generales(jugador.idjugador)
            
            return True
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}", exc_info=True)
            return False
    
    def start(self):
        """Inicia el consumer y procesa mensajes"""
        try:
            self.connect()
            logger.info(f"Consumer iniciado en topic: {self.topic}")
            
            for message in self.consumer:
                logger.debug(f"Mensaje recibido: {message.value}")
                self.process_message(message.value)
                
        except KeyboardInterrupt:
            logger.info("Consumer detenido por el usuario")
        except Exception as e:
            logger.error(f"Error en consumer: {str(e)}", exc_info=True)
        finally:
            if self.consumer:
                self.consumer.close()