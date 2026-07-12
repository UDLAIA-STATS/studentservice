from rest_framework import serializers
from .models import PlayerStatsConsolidated


class PlayerStatsConsolidatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerStatsConsolidated
        fields = "__all__"


class PlayerStatsConsolidatedPatchSerializer(serializers.ModelSerializer):
    """Permite actualizar solo ciertos campos del consolidado."""

    class Meta:
        model = PlayerStatsConsolidated
        fields = (
            "shirt_number",
            "team",
            "team_color",
            "passes",
            "goals",
            "avg_speed_kmh",
            "avg_possession_time_s",
            "avg_acceleration",
            "distance_km",
            "heatmap_image_path",
            "player_crop_path",
            "team_heatmap_path",
            "movement_trajectories_path",
        )

class PlayerStatsInputSerializer(serializers.Serializer):
    """Valida el payload de un jugador."""

    player_id = serializers.IntegerField(
        required=True,
        allow_null=True,
        min_value=1,
        error_messages={
            "required": "El ID del jugador es obligatorio.",
            "invalid": "El ID del jugador debe ser un número válido.",
            "min_value": "El ID del jugador debe ser mayor o igual a 1.",
        },
    )

    match_id = serializers.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            "required": "El ID del partido es obligatorio.",
            "invalid": "El ID del partido debe ser un número válido.",
            "min_value": "El ID del partido debe ser mayor o igual a 1.",
        },
    )

    shirt_number = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        error_messages={
            "invalid": "El número de camiseta debe ser un número válido.",
            "min_value": "El número de camiseta debe ser mayor o igual a 1.",
            "null": "El número de camiseta puede ser nulo si no se especifica.",
        },
    )

    team = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "El nombre del equipo debe ser una cadena de texto válida.",
            "blank": "El nombre del equipo puede estar vacío si no se especifica.",
            "null": "El nombre del equipo puede ser nulo si no se especifica.",
        },
    )

    team_color = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "El color del equipo debe ser una cadena de texto válida.",
            "blank": "El color del equipo puede estar vacío si no se especifica.",
            "null": "El color del equipo puede ser nulo si no se especifica.",
        },
    )

    passes = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=0,
        min_value=0,
        error_messages={
            "invalid": "El número de pases debe ser un número válido.",
            "min_value": "El número de pases no puede ser negativo.",
            "null": "El número de pases puede ser nulo si no se especifica.",
        },
    )

    goals = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=0,
        min_value=0,
        error_messages={
            "invalid": "El número de goles debe ser un número válido.",
            "min_value": "El número de goles no puede ser negativo.",
            "null": "El número de goles puede ser nulo si no se especifica.",
        },
    )

    avg_speed_kmh = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=10,
        decimal_places=6,
        min_value=0,
        error_messages={
            "invalid": "La velocidad promedio debe ser un número decimal válido.",
            "max_digits": "La velocidad promedio no puede tener más de 6 dígitos en total.",
            "decimal_places": "La velocidad promedio no puede tener más de 6 decimales.",
            "min_value": "La velocidad promedio debe ser mayor o igual a 0 km/h.",
            "null": "La velocidad promedio puede ser nula si no se especifica.",
        },
    )

    avg_acceleration = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=12,
        decimal_places=6,
        min_value=0,
        error_messages={
            "invalid": "La aceleración promedio debe ser un número decimal valido.",
            "max_digits": "La aceleración promedio no puede tener más de 8 dígitos en total.",
            "decimal_places": "La aceleración promedio no puede tener más de 6 decimales.",
            "min_value": "La aceleración promedio debe ser mayor o igual a 0 m/s^2.",
            "null": "La aceleración promedio puede ser nula si no se especifica.",
        }
    )

    avg_possession_time_s = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=10,
        decimal_places=6,
        min_value=0,
        error_messages={
            "invalid": "El tiempo promedio de posesión debe ser un número decimal válido.",
            "max_digits": "El tiempo promedio de posesión no puede tener más de 8 dígitos en total.",
            "decimal_places": "El tiempo promedio de posesión no puede tener más de 6 decimales.",
            "min_value": "El tiempo promedio de posesión debe ser mayor o igual a 0 segundos.",
            "null": "El tiempo promedio de posesión puede ser nulo si no se especifica.",
        },
    )

    distance_km = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=12,
        decimal_places=6,
        min_value=0,
        error_messages={
            "invalid": "La distancia recorrida debe ser un número decimal válido.",
            "max_digits": "La distancia recorrida no puede tener más de 10 dígitos en total.",
            "decimal_places": "La distancia recorrida no puede tener más de 6 decimales.",
            "min_value": "La distancia recorrida debe ser mayor o igual a 0 km.",
            "null": "La distancia recorrida puede ser nula si no se especifica.",
        },
    )

    heatmap_image_path = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            "invalid": "La ruta de la imagen del mapa de calor debe ser una URL válida.",
            "blank": "La ruta de la imagen del mapa de calor puede estar vacía si no se especifica.",
            "null": "La ruta de la imagen del mapa de calor puede ser nula si no se especifica.",
        },
    )

    player_crop_path = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            "invalid": "La ruta del recorte del jugador debe ser una URL válida.",
            "blank": "La ruta del recorte del jugador puede estar vacía.",
            "null": "La ruta del recorte del jugador puede ser nula.",
        },
    )

    team_heatmap_path = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            "invalid": "La ruta del mapa de calor del equipo debe ser una URL válida.",
            "blank": "La ruta del mapa de calor del equipo puede estar vacía.",
            "null": "La ruta del mapa de calor del equipo puede ser nula.",
        },
    )

    movement_trajectories_path = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            "invalid": "La ruta de las trayectorias debe ser una URL válida.",
            "blank": "La ruta de las trayectorias puede estar vacía.",
            "null": "La ruta de las trayectorias puede ser nula.",
        },
    )

class PlayerStatsBulkInputSerializer(serializers.Serializer):
    """Envoltorio para recibir un array de jugadores."""

    players = serializers.ListField(
        child=PlayerStatsInputSerializer(), allow_empty=True, required=True
    )
