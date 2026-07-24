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
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models import Sum, Avg, Count, Max
from django.http import HttpResponse
from django.utils.timezone import now
from io import BytesIO

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

class TeamStatsPdfView(APIView):
    """
    Descarga en PDF las estadísticas consolidadas de un partido (equipo).
    GET /api/matches/<match_id>/stats/pdf/
    """

    def get(self, request, match_id):
        stats = PlayerStats.objects.filter(match_id=match_id)

        if not stats.exists():
            return Response(
                {"error": "No hay estadísticas para este partido"}, status=404
            )

        # Agregación por jugador
        per_player = (
            stats.values("player_id")
            .annotate(
                total_goals=Sum("has_goal"),
                total_km=Sum("km_run"),
                total_shots=Sum("shots_on_target"),
                frames=Count("id"),
                last_update=Max("created_at"),
            )
            .order_by("-total_goals", "-total_shots")
        )

        # Totales del equipo
        team_totals = stats.aggregate(
            total_goals=Sum("has_goal"),
            total_km=Sum("km_run"),
            total_shots=Sum("shots_on_target"),
            avg_km=Avg("km_run"),
        )

        pdf_buffer = self._build_pdf(match_id, per_player, team_totals)

        filename = f"team_stats_match_{match_id}.pdf"
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def _build_pdf(self, match_id, per_player, team_totals):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        story = []

        # Título
        story.append(Paragraph(f"Estadísticas consolidadas - Partido #{match_id}", styles["Title"]))
        story.append(Paragraph(f"Generado el {now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 16))

        # Resumen del equipo
        story.append(Paragraph("Resumen del equipo", styles["Heading2"]))
        resumen_data = [
            ["Goles totales", str(team_totals["total_goals"] or 0)],
            ["Km recorridos (total)", f"{team_totals['total_km'] or 0:.2f}"],
            ["Km recorridos (promedio)", f"{team_totals['avg_km'] or 0:.2f}"],
            ["Remates al arco", str(team_totals["total_shots"] or 0)],
        ]
        resumen_table = Table(resumen_data, colWidths=[8 * cm, 6 * cm])
        resumen_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(resumen_table)
        story.append(Spacer(1, 20))

        # Detalle por jugador
        story.append(Paragraph("Detalle por jugador", styles["Heading2"]))
        table_data = [["Jugador", "Goles", "Km", "Remates", "Frames"]]
        for row in per_player:
            table_data.append(
                [
                    str(row["player_id"]),
                    str(row["total_goals"] or 0),
                    f"{row['total_km'] or 0:.2f}",
                    str(row["total_shots"] or 0),
                    str(row["frames"]),
                ]
            )

        player_table = Table(table_data, colWidths=[4 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        player_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(player_table)

        doc.build(story)
        buffer.seek(0)
        return buffer