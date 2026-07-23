from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List

from django.db import transaction
from django.db.models import Sum, Avg, Count
from jugadores.models import Jugadores
from .models import PlayerStatsConsolidated, PlayerStatsHist


@dataclass
class PlayerMatchStats:
    stat_id: int
    player_id: int
    player_name: str
    match_id: int
    shirt_number: int
    team: str
    team_color: str
    analisys_date: str

    goals: int
    team_goals: int
    avg_speed_kmh: float
    distance_km: float
    heatmap_image_path: str
    team_heatmap_image_path: str


def get_general_stats():
    stats_dict = {
        "partidos_analizados": 0,
        "distancia_promedio": 0,
        "velocidad_promedio": 0,
        "jugadores_analizados": 0,
    }

    stats_dict["partidos_analizados"] = (
        PlayerStatsConsolidated.objects.values("match_id").distinct().count()
    )
    stats_dict["distancia_promedio"] = (
        PlayerStatsHist.objects.aggregate(distancia=Avg("total_distance_km"))[
            "distancia"
        ]
        or 0
    )
    stats_dict["velocidad_promedio"] = (
        PlayerStatsHist.objects.aggregate(velocidad=Avg("avg_speed_global_kmh"))[
            "velocidad"
        ]
        or 0
    )
    stats_dict["jugadores_analizados"] = Jugadores.objects.count()

    return stats_dict


def get_analyzed_matches():
    final_reponse = []

    matches = PlayerStatsConsolidated.objects.values("match_id", "created_at").distinct(
        "match_id"
    )
    matches_avgs = PlayerStatsConsolidated.objects.values(
        "match_id", "avg_speed_kmh", "distance_km"
    )

    for stat in matches:
        matches_values = matches_avgs.filter(match_id=stat["match_id"])

        avg_dist = (
            matches_values.aggregate(total_distance=Avg("distance_km"))[
                "total_distance"
            ]
            or 0
        )
        avg_speed = (
            matches_values.aggregate(avg_speed=Avg("avg_speed_kmh"))["avg_speed"] or 0
        )

        final_reponse.append(
            {
                "match_id": stat["match_id"],
                "created_at": datetime.strftime(
                    stat["created_at"], "%d-%m-%Y %H:%M:%S"
                ),
                "avg_distance": avg_dist,
                "avg_speed": avg_speed,
            }
        )

    return final_reponse


def player_stats_by_match(match_id: int):
    stats = PlayerStatsConsolidated.objects.filter(match_id=match_id)
    response: List[Dict] = []

    for stat in stats:
        player = Jugadores.objects.filter(idjugador=stat.player_id).first()

        if player is None:
            continue

        item = PlayerMatchStats(
            stat_id=stat.id,
            player_id=stat.player_id,
            player_name=f"{player.nombrejugador} {player.apellidojugador}",
            match_id=stat.match_id,
            shirt_number=player.numerocamisetajugador,
            team=stat.team or "",
            team_color=stat.team_color or "",
            analisys_date=stat.created_at.strftime("%d-%m-%Y %H:%M:%S"),
            goals=stat.goals,
            team_goals=stat.team_goals,
            avg_speed_kmh=float(stat.avg_speed_kmh or 0),
            distance_km=float(stat.distance_km or 0),
            heatmap_image_path=stat.heatmap_image_path,
            team_heatmap_image_path=stat.team_heatmap_path,
        )

        response.append(asdict(item))

    return response
