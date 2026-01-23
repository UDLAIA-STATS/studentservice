from django.db import transaction
from django.db.models import Sum, Avg, Count, Case, When, IntegerField
from jugadores.models import Jugadores
from .models import PlayerStatsConsolidated, PlayerStatsHist


def get_jugador_activo_por_camiseta(shirt_number: int):
    """Obtiene jugador activo por número de camiseta"""
    return Jugadores.objects.filter(
        numerocamisetajugador=shirt_number,
        jugadoractivo=True
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

    # ✅ Filtrar por player_id (más eficiente y exacto)
    # Usamos player_id en lugar de shirt_number porque:
    # - Un jugador puede cambiar de número
    # - Evita ambigüedad si dos equipos usan el mismo número
    qs = PlayerStatsConsolidated.objects.filter(
        player_id=jugador.idjugador
    )

    if not qs.exists():
        return

    agg = qs.aggregate(
        partidos=Count("match_id", distinct=True),
        passes=Sum("passes"),
        shots=Sum("shots_on_target"),
        goals=Sum(
            Case(
                When(has_goal=True, then=1),
                When(has_goal=False, then=0),
                default=0,
                output_field=IntegerField()
            )
        ),
        distance=Sum("distance_km"),
        possession=Sum("avg_possession_time_s"),
        avg_speed=Avg("avg_speed_kmh"),
    )

    PlayerStatsHist.objects.update_or_create(
        jugador=jugador,
        defaults={
            "partidos_jugados": agg["partidos"] or 0,
            "total_passes": agg["passes"] or 0,
            "total_shots_on_target": agg["shots"] or 0,
            "total_goals": agg["goals"] or 0,
            "total_distance_km": agg["distance"] or 0,
            "total_possession_time_s": agg["possession"] or 0,
            "avg_speed_global_kmh": agg["avg_speed"] or 0,
        }
    )
