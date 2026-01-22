import json
from django.db import transaction, IntegrityError
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
import logging
from stats.management import handle_player_stats
from stats.producer import publish_event
from stats.models import (
    PlayerStatsConsolidated, EventType)
from stats.serializer import (
    PlayerStatsConsolidatedSerializer,
    PlayerStatsConsolidatedPatchSerializer,
    PlayerStatsBulkInputSerializer,
    PlayerStatsInputSerializer
)
from shared import (
    format_serializer_errors, success_response,
    error_response, paginate_queryset,
)

logger = logging.getLogger(__name__)

def upsert_player_consolidated(player_id: int, match_id: int, defaults: dict):
    """Crea o actualiza el registro consolidado de un jugador."""
    return PlayerStatsConsolidated.objects.update_or_create(
        player_id=player_id, match_id=match_id, defaults=defaults
    )[0]


class PlayerStatsBulkCreateView(APIView):
#     """
#     POST /api/players/stats/bulk/
#     Payload: {"players": [ {player_id, match_id, ...}, ... ] }
#     Crea NUEVOS registros solamente. Si ya existe un registro para 
#     (player_id, match_id), lo omite y continúa con el siguiente.
#     """
    @transaction.atomic
    def post(self, request):
        try:
            serializer = PlayerStatsInputSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error("serializer.errors: %s", serializer.errors)
                logger.error("serializer.errors como JSON: %s", json.dumps(serializer.errors, indent=2, default=str))
                raise ValidationError(format_serializer_errors(serializer.errors))
            handle_player_stats.handle_stats(serializer.validated_data)
            # publish_event(
            #     topic="write.stats",
            #     event=serializer.validated_data["players"]
            # )
            return success_response(
                "Eventos de estadísticas publicados",
                None,
                status.HTTP_200_OK
            )

        except:
            logger.error("Error inesperado en PlayerStatsBulkCreateView", exc_info=True)
            return error_response("Error inesperado", "Revise los logs para más detalles", status.HTTP_500_INTERNAL_SERVER_ERROR)
        # try:
        #     serializer = PlayerStatsBulkInputSerializer(data=request.data)
        #     if not serializer.is_valid():
        #         logger.error("serializer.errors: %s", serializer.errors)
        #         logger.error("serializer.errors como JSON: %s", json.dumps(serializer.errors, indent=2, default=str))
        #         raise ValidationError(format_serializer_errors(serializer.errors))

        #     players_data = serializer.validated_data['players']
        #     if not players_data:
        #         raise ValidationError("No se enviaron jugadores.")

        #     # Pre-verificar cuáles ya existen para no intentar crearlos
        #     existing_pairs = set(
        #         PlayerStatsConsolidated.objects.filter(
        #             player_id__in=[p['player_id'] for p in players_data],
        #             match_id__in=[p['match_id'] for p in players_data]
        #         ).values_list('player_id', 'match_id')
        #     )
            
        #     created_list = []
        #     skipped_count = 0

        #     for player_data in players_data:
        #         player_id = player_data['player_id']
        #         match_id = player_data['match_id']
                
        #         # Si ya existe, saltarlo
        #         if (player_id, match_id) in existing_pairs:
        #             logger.info(f"Saltando player_id={player_id}, match_id={match_id} (ya existe)")
        #             skipped_count += 1
        #             continue

        #         # Crear nuevo registro
        #         consolidated = PlayerStatsConsolidated.objects.create(
        #             player_id=player_id,
        #             match_id=match_id,
        #             shirt_number=player_data.get('shirt_number'),
        #             team=player_data.get('team'),
        #             team_color=player_data.get('team_color'),
        #             passes=player_data.get('passes', 0),
        #             shots_on_target=player_data.get('shots_on_target', 0),
        #             has_goal=player_data.get('has_goal', False),
        #             avg_speed_kmh=player_data.get('avg_speed_kmh'),
        #             avg_possession_time_s=player_data.get('avg_possession_time_s'),
        #             distance_km=player_data.get('distance_km') or player_data.get('km_run'),
        #             heatmap_image_path=player_data.get('heatmap_image_path', ''),
        #         )
                
        #         created_list.append(consolidated)
        #         logger.info(f"Creado nuevo consolidado: player_id={player_id}, match_id={match_id}")

        #     logger.info(f"Proceso completado: {len(created_list)} creados, {skipped_count} saltados")
            
        #     return success_response(
        #         f"Estadísticas creadas: {len(created_list)} nuevos, {skipped_count} existentes",
        #         PlayerStatsConsolidatedSerializer(created_list, many=True).data,
        #         status.HTTP_201_CREATED
        #     )

        # except ValidationError as ve:
        #     logger.error(ve.detail)
        #     traceback.print_exc()
        #     return error_response("Error de validación", ve.detail, status.HTTP_400_BAD_REQUEST)
        # except IntegrityError as ie:
        #     logger.error(str(ie))
        #     traceback.print_exc()
        #     return error_response("Error de integridad", str(ie), status.HTTP_400_BAD_REQUEST)
        # except Exception as exc:
        #     logger.error(str(exc))
        #     traceback.print_exc()
        #     return error_response("Error inesperado", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

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
