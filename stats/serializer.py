from rest_framework import serializers
from .models import (
    PlayerStatsConsolidated, PlayerEvents,
    PlayerDistanceHistory, PlayerHeatmaps, EventType,
)

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


class PlayerStatsInputSerializer(serializers.Serializer):
    """Valida el payload de un jugador."""
    
    player_id = serializers.IntegerField(
        required=True, 
        min_value=1,
        error_messages={
            'required': 'El ID del jugador es obligatorio.',
            'invalid': 'El ID del jugador debe ser un número válido.',
            'min_value': 'El ID del jugador debe ser mayor o igual a 1.',
            'null': 'El ID del jugador no puede ser nulo.'
        }
    )
    
    match_id = serializers.IntegerField(
        required=True, 
        min_value=1,
        error_messages={
            'required': 'El ID del partido es obligatorio.',
            'invalid': 'El ID del partido debe ser un número válido.',
            'min_value': 'El ID del partido debe ser mayor o igual a 1.',
            'null': 'El ID del partido no puede ser nulo.'
        }
    )
    
    shirt_number = serializers.IntegerField(
        required=False, 
        allow_null=True, 
        min_value=1,
        error_messages={
            'invalid': 'El número de camiseta debe ser un número válido.',
            'min_value': 'El número de camiseta debe ser mayor o igual a 1.',
            'null': 'El número de camiseta puede ser nulo si no se especifica.'
        }
    )
    
    team = serializers.CharField(
        required=False, 
        allow_blank=True, 
        trim_whitespace=True,
        error_messages={
            'invalid': 'El nombre del equipo debe ser una cadena de texto válida.',
            'blank': 'El nombre del equipo puede estar vacío si no se especifica.'
        }
    )
    
    team_color = serializers.CharField(
        required=False, 
        allow_blank=True, 
        trim_whitespace=True,
        error_messages={
            'invalid': 'El color del equipo debe ser una cadena de texto válida.',
            'blank': 'El color del equipo puede estar vacío si no se especifica.'
        }
    )
    
    passes = serializers.IntegerField(
        required=False, 
        default=0, 
        min_value=0,
        error_messages={
            'invalid': 'El número de pases debe ser un número válido.',
            'min_value': 'El número de pases no puede ser negativo.'
        }
    )
    
    shots_on_target = serializers.IntegerField(
        required=False, 
        default=0, 
        min_value=0,
        error_messages={
            'invalid': 'El número de tiros al arco debe ser un número válido.',
            'min_value': 'El número de tiros al arco no puede ser negativo.'
        }
    )
    
    has_goal = serializers.BooleanField(
        required=False, 
        default=False,
        error_messages={
            'invalid': 'El campo "tiene gol" debe ser un valor booleano (true/false).'
        }
    )
    
    avg_speed_kmh = serializers.DecimalField(
        required=False, 
        allow_null=True,
        max_digits=6, 
        decimal_places=2, 
        min_value=0,
        error_messages={
            'invalid': 'La velocidad promedio debe ser un número decimal válido.',
            'max_digits': 'La velocidad promedio no puede tener más de 6 dígitos en total.',
            'decimal_places': 'La velocidad promedio no puede tener más de 2 decimales.',
            'min_value': 'La velocidad promedio debe ser mayor o igual a 0 km/h.',
            'null': 'La velocidad promedio puede ser nula si no se especifica.'
        }
    )
    
    avg_possession_time_s = serializers.DecimalField(
        required=False, 
        allow_null=True,
        max_digits=8, 
        decimal_places=2, 
        min_value=0,
        error_messages={
            'invalid': 'El tiempo promedio de posesión debe ser un número decimal válido.',
            'max_digits': 'El tiempo promedio de posesión no puede tener más de 8 dígitos en total.',
            'decimal_places': 'El tiempo promedio de posesión no puede tener más de 2 decimales.',
            'min_value': 'El tiempo promedio de posesión debe ser mayor o igual a 0 segundos.',
            'null': 'El tiempo promedio de posesión puede ser nulo si no se especifica.'
        }
    )
    
    distance_km = serializers.DecimalField(
        required=False, 
        allow_null=True,
        max_digits=10, 
        decimal_places=3, 
        min_value=0,
        error_messages={
            'invalid': 'La distancia recorrida debe ser un número decimal válido.',
            'max_digits': 'La distancia recorrida no puede tener más de 10 dígitos en total.',
            'decimal_places': 'La distancia recorrida no puede tener más de 3 decimales.',
            'min_value': 'La distancia recorrida debe ser mayor o igual a 0 km.',
            'null': 'La distancia recorrida puede ser nula si no se especifica.'
        }
    )
    
    heatmap_image_path = serializers.URLField(
        required=False, 
        allow_blank=True,
        error_messages={
            'invalid': 'La ruta de la imagen del mapa de calor debe ser una URL válida.',
            'blank': 'La ruta de la imagen del mapa de calor puede estar vacía si no se especifica.'
        }
    )
class PlayerStatsBulkInputSerializer(serializers.Serializer):
    """Envoltorio para recibir un array de jugadores."""
    players = serializers.ListField(
        child=PlayerStatsInputSerializer(),
        allow_empty=False,
        required=True
    )