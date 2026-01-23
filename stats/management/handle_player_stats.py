import logging

from jugadores.models import Jugadores
from stats.models import PlayerStatsConsolidated
from stats.services import actualizar_estadisticas_generales

logger = logging.getLogger(__name__)

def handle_stats(message: dict) -> bool:
    """
    Procesa mensaje de Kafka con estadísticas del modelo IA
    
    Esperado:
    {
        "shirt_number": 10,
        "team_color": "BLUE",
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
        team_color = message.get('team_color')
        match_id = message.get('match_id')
        
        if not all([shirt_number, team_color, match_id]):
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
                f"team_color={team_color}"
            )
            return False
        
        # Crear o actualizar estadísticas consolidadas
        stats, created = PlayerStatsConsolidated.objects.update_or_create(
            player_id=jugador.idjugador,
            match_id=match_id,
            defaults={
                'shirt_number': shirt_number,
                'team_color': team_color,
                "team": message.get('team', ''),
                'passes': message.get('passes', 0),
                'shots_on_target': message.get('shots_on_target', 0),
                'has_goal': message.get('has_goal', 0),
                'goals': message.get('goals', 0),
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
