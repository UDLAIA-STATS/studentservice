import json
from django.db import transaction, IntegrityError
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
import logging
from jugadores.models import Jugadores
from stats.history_service import get_general_stats, get_analyzed_matches, player_stats_by_match
from stats.management import handle_player_stats
from stats.models import PlayerStatsConsolidated
from stats.serializer import (
    PlayerStatsConsolidatedSerializer,
    PlayerStatsConsolidatedPatchSerializer,
    PlayerStatsInputSerializer,
)
from stats.services import actualizar_estadisticas_generales, merge_player_stats
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
            logger.error(
                "Error de validación en PlayerStatsBulkCreateView", exc_info=True
            )
            return error_response(
                "Error de validación", ve.detail, status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            logger.error("Error inesperado en PlayerStatsBulkCreateView", exc_info=True)
            return error_response(
                "Error inesperado", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlayerStatsCorrectionView(APIView):

    @transaction.atomic
    def post(self, request):
        try:
            stats_id = request.data.get("stats_id")
            player_id = request.data.get("player_id")
            shirt_number = request.data.get("shirt_number")

            if not all([stats_id, player_id, shirt_number]):
                return error_response(
                    "Datos inválidos",
                    "Los datos recibidos son incorrectos, no se pudo actualizar la estadística.",
                    status.HTTP_400_BAD_REQUEST,
                )

            stat = PlayerStatsConsolidated.objects.filter(id=stats_id).first()

            if stat is None:
                return error_response(
                    "Estadística no encontrada",
                    "La estadística indicada no existe.",
                    status.HTTP_400_BAD_REQUEST,
                )

            jugador = Jugadores.objects.filter(
                idjugador=player_id,
                jugadoractivo=True,
            ).first()

            if jugador is None:
                return error_response(
                    "Jugador inválido",
                    "El jugador indicado no existe o está inactivo.",
                    status.HTTP_400_BAD_REQUEST,
                )

            if jugador.numerocamisetajugador != shirt_number:
                return error_response(
                    "Datos inválidos",
                    "El número de camiseta no corresponde al jugador indicado.",
                    status.HTTP_400_BAD_REQUEST,
                )

            if stat.player_id == player_id and stat.shirt_number == shirt_number:
                return error_response(
                    "Sin cambios",
                    "La estadística ya pertenece al jugador indicado.",
                    status.HTTP_400_BAD_REQUEST,
                )

            duplicates = PlayerStatsConsolidated.objects.filter(
                match_id=stat.match_id,
                player_id=player_id,
                shirt_number=shirt_number,
            ).exclude(id=stat.id)

            if duplicates.count() > 1:
                return error_response(
                    "Duplicados encontrados",
                    (
                        "Se encontraron múltiples estadísticas para el mismo "
                        "jugador y partido. La consolidación debe realizarse manualmente."
                    ),
                    status.HTTP_400_BAD_REQUEST,
                )

            if duplicates.exists():
                merge_player_stats(
                    source_stat=stat,
                    target_stat=duplicates.first(),
                    player=jugador,
                )
            else:
                stat.player_id = jugador.idjugador
                stat.shirt_number = jugador.numerocamisetajugador
                stat.save(update_fields=["player_id", "shirt_number"])

            actualizar_estadisticas_generales(jugador.numerocamisetajugador)

            return success_response(
                "Estadística corregida correctamente.",
                {},
                status.HTTP_200_OK,
            )

        except Exception as exc:
            return error_response(
                "Error inesperado",
                str(exc),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                "Error al obtener la estadística", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GeneralStatsView(generics.RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        try:
            return success_response(
                "Estadísticas generales", get_general_stats(), status.HTTP_200_OK
            )
        except Exception as exc:
            return error_response(
                "Error al obtener las estadísticas generales", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyzedMatchsView(generics.RetrieveAPIView):
    def retrieve(self, request, *args, **kwargs):
        try:
            return success_response(
                "Partidos analizados", get_analyzed_matches(), status.HTTP_200_OK
            )
        except Exception as exc:
            return error_response(
                "Error al obtener los partidos analizados", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlayerStatsByMatchView(APIView):
    def get(self, request, match_id):
        try:
            return success_response(
                "Estadísticas por partido",
                player_stats_by_match(match_id),
                status.HTTP_200_OK,
            )
        except Exception as exc:
            return error_response(  
                "Error al recuperar las estadísticas por partido", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
