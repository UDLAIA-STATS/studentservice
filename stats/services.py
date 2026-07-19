from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Avg, Count
from jugadores.models import Jugadores
from .models import PlayerStatsConsolidated, PlayerStatsHist


def get_jugador_activo_por_camiseta(shirt_number: int):
    """Obtiene jugador activo por número de camiseta"""
    return Jugadores.objects.filter(
        numerocamisetajugador=shirt_number, jugadoractivo=True
    ).first()


@transaction.atomic
def actualizar_estadisticas_generales(shirt_number: int) -> None:
    """
    Actualiza estadísticas históricas basadas en stats consolidadas.

    Recibe el número de camiseta del jugador y busca sus estadísticas
    consolidadas por ese número.
    """
    jugador = get_jugador_activo_por_camiseta(shirt_number)
    if not jugador:
        return

    qs = PlayerStatsConsolidated.objects.filter(player_id=jugador.idjugador)

    if not qs.exists():
        return

    agg = qs.aggregate(
        partidos=Count("match_id", distinct=True),
        passes=Sum("passes"),
        goals=Sum("goals"),
        distance=Sum("distance_km"),
        possession=Sum("avg_possession_time_s"),
        avg_speed=Avg("avg_speed_kmh"),
    )

    PlayerStatsHist.objects.update_or_create(
        jugador=jugador,
        defaults={
            "partidos_jugados": agg["partidos"] or 0,
            "total_passes": agg["passes"] or 0,
            "total_shots_on_target": 0,
            "total_goals": agg["goals"] or 0,
            "total_distance_km": agg["distance"] or 0,
            "total_possession_time_s": agg["possession"] or 0,
            "avg_speed_global_kmh": agg["avg_speed"] or 0,
        },
    )


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _merge_sum(current, incoming) -> Decimal:
    return _to_decimal(current) + _to_decimal(incoming)


def _merge_average(current, incoming):
    current = _to_decimal(current)
    incoming = _to_decimal(incoming)

    if current == 0 or incoming == 0:
        return max(current, incoming)

    incoming *= Decimal("0.8")

    return (current + incoming) / Decimal("2")


def _merge_path(current, incoming):
    if current in (None, "") and incoming not in (None, ""):
        return incoming
    return current


def _copy_player_information(
    stat: PlayerStatsConsolidated,
    player,
):
    stat.player_id = player.idjugador
    stat.shirt_number = player.numerocamisetajugador


def merge_player_stats(
    source_stat: PlayerStatsConsolidated,
    target_stat: PlayerStatsConsolidated,
    player,
):
    """
    Fusiona dos estadísticas pertenecientes al mismo partido.

    source_stat:
        Estadística incorrecta (la enviada en el endpoint).

    target_stat:
        Estadística ya existente del jugador correcto.
        Esta será la que se conservará.

    Al finalizar:
        - target_stat contendrá la información consolidada.
        - source_stat será eliminado.
    """

    _copy_player_information(target_stat, player)

    setattr(
        target_stat,
        "passes",
        _merge_sum(
            target_stat.passes,
            source_stat.passes,
        ),
    )

    target_stat.passes = int(
        _merge_sum(
            target_stat.passes,
            source_stat.passes,
        )
    )

    target_stat.goals = int(
        _merge_sum(
            target_stat.goals,
            source_stat.goals,
        )
    )

    target_stat.team_goals = int(
        _merge_sum(
            target_stat.team_goals,
            source_stat.team_goals,
        )
    )

    target_stat.distance_km = _merge_sum(
        target_stat.distance_km,
        source_stat.distance_km,
    )

    target_stat.avg_speed_kmh = _merge_average(
        target_stat.avg_speed_kmh,
        source_stat.avg_speed_kmh,
    )

    target_stat.avg_acceleration = _merge_average(
        target_stat.avg_acceleration,
        source_stat.avg_acceleration,
    )

    target_stat.avg_possession_time_s = _merge_average(
        target_stat.avg_possession_time_s,
        source_stat.avg_possession_time_s,
    )

    target_stat.heatmap_image_path = _merge_path(
        target_stat.heatmap_image_path,
        source_stat.heatmap_image_path,
    )

    target_stat.player_crop_path = _merge_path(
        target_stat.player_crop_path,
        source_stat.player_crop_path,
    )

    target_stat.team_heatmap_path = _merge_path(
        target_stat.team_heatmap_path,
        source_stat.team_heatmap_path,
    )

    target_stat.movement_trajectories_path = _merge_path(
        target_stat.movement_trajectories_path,
        source_stat.movement_trajectories_path,
    )

    target_stat.save()
    source_stat.delete()
    return target_stat
