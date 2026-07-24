import logging
from jugadores.models import Jugadores
from stats.models import PlayerStatsConsolidated
from stats.services import actualizar_estadisticas_generales

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

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
        "heatmap_image_path": "/path/to/heatmap.png"
    }
    """
    try:
        shirt_number = message.get("shirt_number")
        team_color = message.get("team_color")
        match_id = message.get("match_id")

        if not all([shirt_number, team_color, match_id]):
            logger.error("Datos incompletos en mensaje: %s", message)
            return False

        jugador = Jugadores.objects.filter(
            numerocamisetajugador=shirt_number,
            jugadoractivo=True
        ).first()

        if not jugador:
            logger.warning(
                "Jugador no encontrado: shirt_number=%s, team_color=%s",
                shirt_number,
                team_color
            )
            return False

        stats = PlayerStatsConsolidated.objects.create(
            player_id=jugador.idjugador,
            match_id=match_id,
            shirt_number=shirt_number,
            team_color=team_color,
            team=message.get("team", 1),
            passes=message.get("passes", 0),
            shots_on_target=message.get("shots_on_target", 0),
            has_goal=message.get("has_goal", 0),
            goals=message.get("goals", 0),
            distance_km=message.get("distance_km", 0.0),
            avg_possession_time_s=message.get("avg_possession_time_s", 0.0),
            avg_speed_kmh=message.get("avg_speed_kmh", 0.0),
            avg_acceleration=message.get("avg_acceleration", 0.0),
            heatmap_image_path=message.get("heatmap_image_path", ""),
            player_crop_path=message.get("player_crop_path", ""),
            team_heatmap_path=message.get("team_heatmap_path", ""),
            movement_trajectories_path=message.get("movement_trajectories_path", ""),
            team_goals=message.get("team_goals", 0),
        )

        logger.info(
            "Creada estadística para jugador %s en partido %s",
            jugador.idjugador,
            match_id
        )

        actualizar_estadisticas_generales(shirt_number)

        return True

    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}", exc_info=True)
        return False