import logging
from jugadores.models import Jugadores
from stats.models import PlayerStatsConsolidated
from stats.services import actualizar_estadisticas_generales

logger = logging.getLogger(__name__)

def handle_stats(message: dict) -> bool:
    try:
        shirt_number = message.get("shirt_number")
        team_color = message.get("team_color")
        match_id = message.get("match_id")

        if not all([shirt_number, team_color, match_id]):
            logger.error(f"Datos incompletos en mensaje: {message}")
            return False

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

        stats = PlayerStatsConsolidated.objects.create(
            player_id=jugador.idjugador,
            match_id=match_id,
            shirt_number=shirt_number,
            team_color=team_color,
            team=message.get("team", team_color),
            passes=message.get("passes", 0),
            goals=message.get("goals", 0),
            distance_km=message.get("distance_km", 0.0),
            avg_possession_time_s=message.get("avg_possession_time_s", 0.0),
            avg_speed_kmh=message.get("avg_speed_kmh", 0.0),
            avg_acceleration=message.get("avg_acceleration", 0.0),
            heatmap_image_path=message.get("player_heatmap_path", ""),
            player_crop_path=message.get("player_crop_path", ""),
            team_heatmap_path=message.get("team_heatmap_path", ""),
            movement_trajectories_path=message.get("movement_trajectories_path", ""),
        )

        logger.info(
            f"Creada estadística para jugador {jugador.idjugador} "
            f"en partido {match_id}"
        )

        actualizar_estadisticas_generales(shirt_number)

        return True

    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}", exc_info=True)
        return False