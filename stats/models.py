from django.db import models
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

    player_id = models.BigIntegerField(db_index=True)
    match_id = models.BigIntegerField(db_index=True)

    shirt_number = models.PositiveSmallIntegerField(null=True, blank=True)
    team = models.TextField(blank=True, null=True)
    team_goals = models.PositiveIntegerField(default=0)
    team_color = models.TextField(blank=True, null=True)

    passes = models.PositiveIntegerField(default=0)
    goals = models.PositiveIntegerField(default=0)

    avg_speed_kmh = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    avg_possession_time_s = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    distance_km = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    avg_acceleration = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    heatmap_image_path = models.URLField(blank=True)
    player_crop_path = models.URLField(blank=True)
    team_heatmap_path = models.URLField(blank=True)
    movement_trajectories_path = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'football"."player_stats_consolidated'
        indexes = [
            models.Index(fields=["player_id", "match_id"]),
            models.Index(fields=["match_id"]),
        ]


class PlayerStatsHist(models.Model):
    id = models.BigAutoField(primary_key=True)

    jugador = models.OneToOneField(
        Jugadores, on_delete=models.CASCADE, related_name="estadisticas_generales"
    )

    partidos_jugados = models.PositiveIntegerField(default=0)

    total_passes = models.PositiveIntegerField(default=0)
    total_shots_on_target = models.PositiveIntegerField(default=0)
    total_goals = models.PositiveIntegerField(default=0)

    total_distance_km = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_possession_time_s = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    avg_speed_global_kmh = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'football"."player_stats_hist'
