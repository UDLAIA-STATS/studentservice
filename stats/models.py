import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import JSONField
from jugadores.models import Jugadores

class EventType(models.TextChoices):
    PASS = "pass", "Pass"
    SHOT_ON_TARGET = "shot_on_target", "Shot on target"
    GOAL = "goal", "Goal"
    FOUL = "foul", "Foul"
    ASSIST = "assist", "Assist"
    INTERCEPTION = "interception", "Interception"


class PlayerStatsConsolidated(models.Model):
    id = models.BigAutoField(primary_key=True)
    
    player_id = models.BigIntegerField(db_index=True)  # ✅ NUEVO - ID del jugador
    match_id = models.IntegerField(db_index=True)

    shirt_number = models.PositiveSmallIntegerField(null=True, blank=True)
    team = models.TextField(blank=True)
    team_color = models.TextField(blank=True)

    passes = models.PositiveIntegerField(default=0)
    shots_on_target = models.PositiveIntegerField(default=0)
    has_goal = models.BooleanField(default=False)

    avg_speed_kmh = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    avg_possession_time_s = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    distance_km = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    heatmap_image_path = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'football"."player_stats_consolidated'
        unique_together = ("player_id", "match_id")  # ✅ CAMBIAR a player_id
        indexes = [
            models.Index(fields=["player_id", "match_id"]),  # ✅ CAMBIAR a player_id
            models.Index(fields=["match_id"]),
        ]
        


# Modelo que se utiliza para almacenar las estadísticas históricas acumuladas de los jugadores
class PlayerStatsHist(models.Model):
    id = models.BigAutoField(primary_key=True)

    jugador = models.OneToOneField(
        Jugadores,
        on_delete=models.CASCADE,
        related_name="estadisticas_generales"
    )

    partidos_jugados = models.PositiveIntegerField(default=0)

    total_passes = models.PositiveIntegerField(default=0)
    total_shots_on_target = models.PositiveIntegerField(default=0)
    total_goals = models.PositiveIntegerField(default=0)

    total_distance_km = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    total_possession_time_s = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    avg_speed_global_kmh = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'football"."player_stats_hist'
