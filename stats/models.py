import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import JSONField

class EventType(models.TextChoices):
    PASS = "pass", "Pass"
    SHOT_ON_TARGET = "shot_on_target", "Shot on target"
    GOAL = "goal", "Goal"
    FOUL = "foul", "Foul"
    ASSIST = "assist", "Assist"
    INTERCEPTION = "interception", "Interception"



class PlayerEvents(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player_id = models.BigIntegerField(db_index=True)
    match_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    timestamp_ms = models.BigIntegerField(null=True, blank=True)
    metadata = JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'football"."player_events'
        indexes = [
            models.Index(fields=["player_id", "match_id"]),
            models.Index(fields=["match_id", "event_type"]),
            models.Index(fields=["metadata"], name="idx_events_metadata_gin"),
        ]


class PlayerDistanceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player_id = models.BigIntegerField(db_index=True)
    match_id = models.IntegerField(db_index=True)
    total_distance_km = models.DecimalField(
        max_digits=10, decimal_places=3, validators=[MinValueValidator(0)]
    )
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'football"."player_distance_history'
        indexes = [models.Index(fields=["player_id", "match_id"])]


class PlayerHeatmaps(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player_id = models.BigIntegerField(db_index=True, blank=False)
    match_id = models.IntegerField(db_index=True, blank=False)
    heatmap_url = models.URLField(blank=True)
    resolution_w = models.PositiveIntegerField(null=True, blank=True)
    resolution_h = models.PositiveIntegerField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    mime_type = models.TextField(default="image/png")
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'football"."player_heatmaps'
        indexes = [models.Index(fields=["player_id", "match_id"])]


class PlayerStatsConsolidated(models.Model):
    id = models.BigAutoField(primary_key=True)
    player_id = models.BigIntegerField(db_index=True)
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
        unique_together = ("player_id", "match_id")
        indexes = [
            models.Index(fields=["match_id"]),
            models.Index(fields=["player_id", "match_id"]),
        ]