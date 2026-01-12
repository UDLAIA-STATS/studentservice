from django.db import transaction, IntegrityError
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

from stats.models import (
    PlayerStatsConsolidated, PlayerEvents,
    PlayerDistanceHistory, PlayerHeatmaps, EventType)
from stats.serializer import (
    PlayerStatsConsolidatedSerializer,
    PlayerStatsConsolidatedPatchSerializer,
    PlayerStatsBulkInputSerializer
)
from shared import (
    format_serializer_errors, success_response,
    error_response, paginate_queryset,
)

def upsert_player_consolidated(player_id: int, match_id: int, defaults: dict):
    """Crea o actualiza el registro consolidado de un jugador."""
    return PlayerStatsConsolidated.objects.update_or_create(
        player_id=player_id, match_id=match_id, defaults=defaults
    )[0]


def regenerate_player_child_tables(consolidated: PlayerStatsConsolidated):
    """
    Regenera las tablas hijas (eventos, distancia, heatmap)
    a partir del consolidado.
    """
    # 1. Eventos
    PlayerEvents.objects.filter(
        player_id=consolidated.player_id,
        match_id=consolidated.match_id
    ).delete()

    events = []
    if consolidated.passes:
        events.append(PlayerEvents(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id,
            event_type=EventType.PASS,
            metadata={'count': consolidated.passes}
        ))
    if consolidated.shots_on_target:
        events.append(PlayerEvents(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id,
            event_type=EventType.SHOT_ON_TARGET,
            metadata={'count': consolidated.shots_on_target}
        ))
    if consolidated.has_goal:
        events.append(PlayerEvents(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id,
            event_type=EventType.GOAL
        ))
    if events:
        PlayerEvents.objects.bulk_create(events, batch_size=100)

    # 2. Distancia
    if consolidated.distance_km is not None:
        PlayerDistanceHistory.objects.update_or_create(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id,
            defaults={'total_distance_km': consolidated.distance_km}
        )
    else:
        PlayerDistanceHistory.objects.filter(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id
        ).delete()

    # 3. Heatmap
    if consolidated.heatmap_image_path:
        PlayerHeatmaps.objects.update_or_create(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id,
            defaults={'heatmap_url': consolidated.heatmap_image_path}
        )
    else:
        PlayerHeatmaps.objects.filter(
            player_id=consolidated.player_id,
            match_id=consolidated.match_id
        ).delete()


class PlayerStatsBulkCreateView(APIView):
    """
    POST /api/players/stats/bulk/
    Payload: {"players": [ {player_id, match_id, ...}, ... ] }
    """
    @transaction.atomic
    def post(self, request):
        try:
            serializer = PlayerStatsBulkInputSerializer(data=request.data)
            if not serializer.is_valid():
                raise ValidationError(format_serializer_errors(serializer.errors))

            players_data = serializer.validated_data['players']
            if not players_data:
                raise ValidationError("No se enviaron jugadores.")

            consolidated_list = []
            for player_data in players_data:
                consolidated = upsert_player_consolidated(
                    player_id=player_data['player_id'],
                    match_id=player_data['match_id'],
                    defaults={
                        'shirt_number': player_data.get('shirt_number'),
                        'team': player_data.get('team'),
                        'team_color': player_data.get('team_color'),
                        'passes': player_data.get('passes', 0),
                        'shots_on_target': player_data.get('shots_on_target', 0),
                        'has_goal': player_data.get('has_goal', False),
                        'avg_speed_kmh': player_data.get('avg_speed_kmh'),
                        'avg_possession_time_s': player_data.get('avg_possession_time_s'),
                        'distance_km': player_data.get('distance_km'),
                        'heatmap_image_path': player_data.get('heatmap_image_path', ''),
                    }
                )
                regenerate_player_child_tables(consolidated)
                consolidated_list.append(consolidated)

            return success_response(
                "Estadísticas guardadas",
                PlayerStatsConsolidatedSerializer(consolidated_list, many=True).data,
                status.HTTP_201_CREATED
            )

        except ValidationError as ve:
            return error_response("Error de validación", ve.detail, status.HTTP_400_BAD_REQUEST)
        except IntegrityError as ie:
            return error_response("Error de integridad", str(ie), status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response("Error inesperado", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------------------------------------
# 2.  Partial update
# -----------------------------------------------------------
class PlayerStatsPartialUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/players/stats/<pk>/
    """
    queryset = PlayerStatsConsolidated.objects.all()
    serializer_class = PlayerStatsConsolidatedPatchSerializer
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if not serializer.is_valid():
                raise ValidationError(format_serializer_errors(serializer.errors))

            self.perform_update(serializer)
            regenerate_player_child_tables(serializer.instance)

            return success_response(
                "Estadística actualizada",
                PlayerStatsConsolidatedSerializer(serializer.instance).data,
                status.HTTP_200_OK
            )

        except ValidationError as ve:
            return error_response("Error de validación", ve.detail, status.HTTP_400_BAD_REQUEST)
        except IntegrityError as ie:
            return error_response("Error de integridad", str(ie), status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return error_response("Error inesperado", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlayerStatsListView(generics.ListAPIView):
    """
    GET /api/players/stats/?match_id=<id>&page=<n>&offset=<m>
    """
    serializer_class = PlayerStatsConsolidatedSerializer

    def get_queryset(self):
        qs = PlayerStatsConsolidated.objects.all()
        match_id = self.request.query_params.get('match_id')
        if match_id:
            qs = qs.filter(match_id=match_id)
        return qs.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            return paginate_queryset(
                queryset,
                self.get_serializer_class(),
                request
            )
        except Exception as exc:
            return error_response("Error al listar", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlayerStatsDetailView(generics.RetrieveAPIView):
    """
    GET /api/players/stats/<pk>/
    """
    queryset = PlayerStatsConsolidated.objects.all()
    serializer_class = PlayerStatsConsolidatedSerializer
    lookup_field = 'pk'

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return success_response("Estadística", serializer.data, status.HTTP_200_OK)
        except Exception as exc:
            return error_response("Error al recuperar", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
