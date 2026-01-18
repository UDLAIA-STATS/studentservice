from rest_framework import serializers
from .models import (
    PlayerStatsConsolidated, PlayerEvents,
    PlayerDistanceHistory, PlayerHeatmaps, EventType,
)

# ---------- 1.  Consolidated ---------------------------------
class PlayerStatsConsolidatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerStatsConsolidated
        fields = '__all__'


class PlayerStatsConsolidatedPatchSerializer(serializers.ModelSerializer):
    """Permite actualizar solo ciertos campos del consolidado."""
    class Meta:
        model = PlayerStatsConsolidated
        fields = (
            'shirt_number', 'team', 'team_color',
            'passes', 'shots_on_target', 'has_goal',
            'avg_speed_kmh', 'avg_possession_time_s',
            'distance_km', 'heatmap_image_path',
        )


# ---------- 2.  Entrada de estadísticas (bulk / single) ------
class PlayerStatsInputSerializer(serializers.Serializer):
    """Valida el payload de un jugador."""
    player_id = serializers.IntegerField(required=True, min_value=1)
    match_id  = serializers.IntegerField(required=True, min_value=1)
    shirt_number = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    team         = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    team_color   = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    passes       = serializers.IntegerField(required=False, default=0, min_value=0)
    shots_on_target = serializers.IntegerField(required=False, default=0, min_value=0)
    has_goal     = serializers.BooleanField(required=False, default=False)
    avg_speed_kmh = serializers.DecimalField(required=False, allow_null=True,
                                             max_digits=6, decimal_places=2, min_value=0)
    avg_possession_time_s = serializers.DecimalField(required=False, allow_null=True,
                                                     max_digits=8, decimal_places=2, min_value=0)
    distance_km  = serializers.DecimalField(required=False, allow_null=True,
                                            max_digits=10, decimal_places=3, min_value=0)
    heatmap_image_path = serializers.URLField(required=False, allow_blank=True)


class PlayerStatsBulkInputSerializer(serializers.Serializer):
    """Envoltorio para recibir un array de jugadores."""
    players = serializers.ListField(
        child=PlayerStatsInputSerializer(),
        allow_empty=False,
        required=True
    )