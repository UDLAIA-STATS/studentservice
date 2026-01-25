import json
from django.db import transaction, IntegrityError
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
import logging
from stats.management import handle_player_stats
from stats.models import PlayerStatsConsolidated
from stats.serializer import (
    PlayerStatsConsolidatedSerializer,
    PlayerStatsConsolidatedPatchSerializer,
    PlayerStatsInputSerializer,
)
from shared import (
    format_serializer_errors,
    success_response,
    error_response,
    paginate_queryset,
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
                logger.error(
                    "serializer.errors como JSON: %s",
                    json.dumps(serializer.errors, indent=2, default=str),
                )
                raise ValidationError(format_serializer_errors(serializer.errors))
            handle_player_stats.handle_stats(serializer.validated_data)

            return success_response(
                "Eventos de estadísticas publicados", None, status.HTTP_200_OK
            )

        except ValidationError as ve:
            logger.error("Error de validación en PlayerStatsBulkCreateView", exc_info=True)
            return error_response(
                "Error de validación",
                ve.detail,
                status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            logger.error("Error inesperado en PlayerStatsBulkCreateView", exc_info=True)
            return error_response(
                "Error inesperado",
                str(exc),
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlayerStatsPartialUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/players/stats/<pk>/
    """

    queryset = PlayerStatsConsolidated.objects.all()
    serializer_class = PlayerStatsConsolidatedPatchSerializer
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", True)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            if not serializer.is_valid():
                raise ValidationError(format_serializer_errors(serializer.errors))

            self.perform_update(serializer)
            regenerate_player_child_tables(serializer.instance)

            return success_response(
                "Estadística actualizada",
                PlayerStatsConsolidatedSerializer(serializer.instance).data,
                status.HTTP_200_OK,
            )

        except ValidationError as ve:
            return error_response(
                "Error de validación", ve.detail, status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as ie:
            return error_response(
                "Error de integridad", str(ie), status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return error_response(
                "Error inesperado", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlayerStatsListView(generics.ListAPIView):
    """
    GET /api/players/stats/?match_id=<id>&page=<n>&offset=<m>
    """

    serializer_class = PlayerStatsConsolidatedSerializer

    def get_queryset(self):
        qs = PlayerStatsConsolidated.objects.all()
        match_id = self.request.query_params.get("match_id")
        if match_id:
            qs = qs.filter(match_id=match_id)
        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            return paginate_queryset(queryset, self.get_serializer_class(), request)
        except Exception as exc:
            return error_response(
                "Error al listar", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlayerStatsDetailView(generics.RetrieveAPIView):
    """
    GET /api/players/stats/<pk>/
    """

    queryset = PlayerStatsConsolidated.objects.all()
    serializer_class = PlayerStatsConsolidatedSerializer
    lookup_field = "pk"

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return success_response("Estadística", serializer.data, status.HTTP_200_OK)
        except Exception as exc:
            return error_response(
                "Error al recuperar", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
