import json
from django.db import transaction, IntegrityError
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
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
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models import Sum, Avg, Count, Max
from django.http import HttpResponse
from django.utils.timezone import now
from io import BytesIO
from reportlab.platypus import Image, HRFlowable, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from PIL import Image as PILImage
import requests
from requests.adapters import HTTPAdapter, Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

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

class TeamStatsPdfView(APIView):
    """
    Descarga en PDF las estadísticas consolidadas de un partido (equipo),
    incluyendo mapa de calor del equipo y mapas individuales por jugador.
    GET /api/matches/<match_id>/stats/pdf/
    """

    # --- Paleta de colores del PDF ---
    PDF_PRIMARY = colors.HexColor("#0f3d2e")   # verde cancha
    PDF_ACCENT = colors.HexColor("#c9a227")    # dorado
    PDF_LIGHT_BG = colors.HexColor("#f4f4f2")
    PDF_GREY_TEXT = colors.HexColor("#555555")
    PDF_BORDER = colors.HexColor("#dddddd")

    # Sesión HTTP reutilizable con reintentos automáticos, compartida
    # entre todas las peticiones a esta vista
    _http_session = requests.Session()
    _retry_strategy = Retry(
        total=2,
        backoff_factor=0.4,
        status_forcelist=[500, 502, 503, 504],
    )
    _http_session.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
    _http_session.mount("http://", HTTPAdapter(max_retries=_retry_strategy))

    def get(self, request, match_id):
        stats = PlayerStatsConsolidated.objects.filter(match_id=match_id)

        if not stats.exists():
            return Response(
                {"error": "No hay estadísticas para este partido"}, status=404
            )

        per_player = (
            stats.values("player_id")
            .annotate(
                total_goals=Sum("goals"),
                total_km=Sum("distance_km"),
                avg_acceleration=Avg("avg_acceleration"),
                avg_speed=Avg("avg_speed_kmh"),
            )
            .order_by("-total_goals")
        )

        team_totals = stats.aggregate(
            total_goals=Sum("goals"),
            total_km=Sum("distance_km"),
            avg_km=Avg("distance_km"),
        )

        team_heatmap_row = stats.exclude(team_heatmap_path="").first()
        team_heatmap_path = team_heatmap_row.team_heatmap_path if team_heatmap_row else None

        player_rows = list(stats.order_by("shirt_number", "player_id"))

        # Datos reales de los jugadores (nombre, apellido, posición, foto de respaldo)
        player_ids = {row.player_id for row in player_rows}
        jugadores_map = {
            j.idjugador: j for j in Jugadores.objects.filter(idjugador__in=player_ids)
        }

        # Descargar todas las imágenes necesarias en paralelo
        image_paths = set()
        if team_heatmap_path:
            image_paths.add(team_heatmap_path)
        for row in player_rows:
            for path in (row.player_crop_path, row.heatmap_image_path, row.movement_trajectories_path):
                if path:
                    image_paths.add(path)

        image_cache = self._fetch_images_concurrently(image_paths)

        pdf_buffer = self._build_pdf(
            match_id, per_player, team_totals, team_heatmap_path,
            player_rows, image_cache, jugadores_map,
        )

        filename = f"team_stats_match_{match_id}.pdf"
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ---------------------------------------------------------------------
    # Helpers de estilo
    # ---------------------------------------------------------------------

    def _pdf_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="TitleBanner", fontName="Helvetica-Bold", fontSize=20,
            textColor=colors.white, spaceAfter=2,
        ))
        styles.add(ParagraphStyle(
            name="SubtitleBanner", fontName="Helvetica", fontSize=10,
            textColor=colors.HexColor("#d9d9d9"),
        ))
        styles.add(ParagraphStyle(
            name="SectionHeader", fontName="Helvetica-Bold", fontSize=13,
            textColor=self.PDF_PRIMARY, spaceBefore=14, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="PlayerLabel", fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.HexColor("#333333"), alignment=1, leading=12,
        ))
        styles.add(ParagraphStyle(
            name="ImageCaption", fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=colors.grey, alignment=1,
        ))
        styles.add(ParagraphStyle(
            name="EmptyNote", fontName="Helvetica-Oblique", fontSize=9,
            textColor=self.PDF_GREY_TEXT,
        ))
        return styles

    # ---------------------------------------------------------------------
    # Helpers de imágenes
    # ---------------------------------------------------------------------

    def _fetch_image_bytes(self, path_or_url, timeout=8):
        if not path_or_url:
            return None
        try:
            if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
                resp = self._http_session.get(path_or_url, timeout=timeout)
                resp.raise_for_status()
                return resp.content
            with open(path_or_url, "rb") as f:
                return f.read()
        except (requests.RequestException, OSError) as exc:
            logger.warning("No se pudo descargar la imagen '%s': %s", path_or_url, exc)
            return None

    def _fetch_images_concurrently(self, urls, max_workers=8):
        cache = {}
        unique_urls = [u for u in dict.fromkeys(urls) if u]
        if not unique_urls:
            return cache

        with ThreadPoolExecutor(max_workers=min(max_workers, len(unique_urls))) as executor:
            future_map = {
                executor.submit(self._fetch_image_bytes, url): url for url in unique_urls
            }
            for future in as_completed(future_map):
                url = future_map[future]
                try:
                    cache[url] = future.result()
                except Exception as exc:
                    logger.warning("Error inesperado descargando '%s': %s", url, exc)
                    cache[url] = None
        return cache

    def _image_flowable_from_bytes(self, img_bytes, max_width, max_height, placeholder_text="Imagen no disponible"):
        styles = self._pdf_styles()

        if not img_bytes:
            return Paragraph(f"<i>{placeholder_text}</i>", styles["ImageCaption"])

        try:
            img_buffer = BytesIO(img_bytes)
            pil_img = PILImage.open(img_buffer)
            img_w, img_h = pil_img.size
            ratio = min(max_width / img_w, max_height / img_h, 1)
            img_buffer.seek(0)
            return Image(img_buffer, width=img_w * ratio, height=img_h * ratio)
        except (OSError, ValueError) as exc:
            logger.warning("Imagen inválida o corrupta: %s", exc)
            return Paragraph(f"<i>{placeholder_text}</i>", styles["ImageCaption"])

    def _player_display_name(self, jugador_obj, fallback_id):
        if jugador_obj:
            return f"{jugador_obj.nombrejugador} {jugador_obj.apellidojugador}"
        return f"Jugador ID {fallback_id}"

    def _pdf_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.5 * cm, 1 * cm, "Estadísticas del partido — generado automáticamente")
        canvas.drawRightString(doc.pagesize[0] - 1.5 * cm, 1 * cm, f"Página {doc.page}")
        canvas.restoreState()

    # ---------------------------------------------------------------------
    # Construcción del PDF
    # ---------------------------------------------------------------------

    def _build_pdf(self, match_id, per_player, team_totals, team_heatmap_path,
                    player_rows, image_cache, jugadores_map):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=1.2 * cm,
            bottomMargin=1.8 * cm,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
        )
        styles = self._pdf_styles()
        story = []
        
        styles["TitleBanner"].spaceAfter = 2
        styles["SubtitleBanner"].spaceBefore = 2

        # --- Encabezado / banner ---
        banner_data = [
            [Paragraph("Estadísticas consolidadas", styles["TitleBanner"])],
            [Paragraph(
                f"Partido #{match_id} &bull; Generado el {now().strftime('%d/%m/%Y %H:%M')}",
                styles["SubtitleBanner"],
            )],
        ]
        banner = Table(banner_data, colWidths=[18.3 * cm])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.PDF_PRIMARY),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (0, 0), 12),
            ("BOTTOMPADDING", (0, 0), (0, 0), 2),
            ("BOTTOMPADDING", (0, 1), (0, 1), 12),
        ]))
        story.append(banner)
        story.append(Spacer(1, 18))

        # --- Mapa de calor del equipo ---
        story.append(Paragraph("Mapa de calor del equipo", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PDF_ACCENT, spaceAfter=8))
        if team_heatmap_path:
            story.append(self._image_flowable_from_bytes(
                image_cache.get(team_heatmap_path), max_width=16 * cm, max_height=9 * cm
            ))
            story.append(Paragraph(
                "Distribución consolidada de movimiento de todos los jugadores",
                styles["ImageCaption"],
            ))
        else:
            story.append(Paragraph(
                "No hay mapa de calor de equipo disponible para este partido.",
                styles["EmptyNote"],
            ))
        story.append(Spacer(1, 16))

        # --- Resumen del equipo ---
        story.append(Paragraph("Resumen del equipo", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PDF_ACCENT, spaceAfter=8))
        resumen_data = [
            ["Goles totales", str(team_totals["total_goals"] or 0)],
            ["Km recorridos (total)", f"{team_totals['total_km'] or 0:.2f}"],
            ["Km recorridos (promedio)", f"{team_totals['avg_km'] or 0:.2f}"],
        ]
        resumen_table = Table(resumen_data, colWidths=[8 * cm, 6 * cm])
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), self.PDF_PRIMARY),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("BACKGROUND", (1, 0), (1, -1), self.PDF_LIGHT_BG),
            ("GRID", (0, 0), (-1, -1), 0.5, self.PDF_BORDER),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(resumen_table)
        story.append(Spacer(1, 18))

        # --- Detalle por jugador ---
        story.append(Paragraph("Detalle por jugador", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PDF_ACCENT, spaceAfter=8))
        table_data = [["Jugador", "Goles", "Km Recorridos", "Aceleracion Prom. (m/s²)", "Velocidad Prom. (km/h)"]]
        for row in per_player:
            jugador_obj = jugadores_map.get(row["player_id"])
            name = self._player_display_name(jugador_obj, row["player_id"])
            table_data.append([
                name,
                str(row["total_goals"] or 0),
                f"{row['total_km'] or 0:.2f}",
                f"{row['avg_acceleration'] or 0:.2f}",
                f"{row['avg_speed'] or 0:.2f}",
            ])

        player_table = Table(table_data, colWidths=[6 * cm, 2.2 * cm, 3 * cm, 4 * cm, 4 * cm])
        player_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.PDF_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, self.PDF_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.PDF_LIGHT_BG]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(player_table)
        story.append(Spacer(1, 18))

        # --- Mapas individuales por jugador ---
        story.append(Paragraph("Mapas individuales por jugador", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PDF_ACCENT, spaceAfter=8))

        if not player_rows:
            story.append(Paragraph("No hay mapas individuales disponibles.", styles["EmptyNote"]))
        else:
            for row in player_rows:
                jugador_obj = jugadores_map.get(row.player_id)
                name = self._player_display_name(jugador_obj, row.player_id)

                sub_parts = []
                if row.shirt_number:
                    sub_parts.append(f"#{row.shirt_number}")
                if jugador_obj and jugador_obj.posicionjugador:
                    sub_parts.append(jugador_obj.posicionjugador)
                sublabel = " • ".join(sub_parts)

                label_html = name
                if sublabel:
                    label_html += f"<br/><font size=7 color='#777777'>{sublabel}</font>"

                crop_bytes = image_cache.get(row.player_crop_path) if row.player_crop_path else None
                if not crop_bytes and jugador_obj and jugador_obj.imagenjugador:
                    crop_bytes = bytes(jugador_obj.imagenjugador)

                crop_img = self._image_flowable_from_bytes(
                    crop_bytes, max_width=3 * cm, max_height=3 * cm, placeholder_text="Sin foto"
                )
                heatmap_img = self._image_flowable_from_bytes(
                    image_cache.get(row.heatmap_image_path), max_width=5.5 * cm, max_height=5.5 * cm
                )
                traj_img = self._image_flowable_from_bytes(
                    image_cache.get(row.movement_trajectories_path), max_width=5.5 * cm, max_height=5.5 * cm
                )

                card_data = [
                    [Paragraph(label_html, styles["PlayerLabel"]), "", ""],
                    [crop_img, heatmap_img, traj_img],
                    [
                        Paragraph("Foto", styles["ImageCaption"]),
                        Paragraph("Mapa de calor", styles["ImageCaption"]),
                        Paragraph("Trayectoria", styles["ImageCaption"]),
                    ],
                ]
                card = Table(card_data, colWidths=[3.5 * cm, 6.4 * cm, 6.4 * cm])
                card.setStyle(TableStyle([
                    ("SPAN", (0, 0), (-1, 0)),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, self.PDF_BORDER),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, self.PDF_BORDER),
                    ("BACKGROUND", (0, 0), (-1, 0), self.PDF_LIGHT_BG),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                    ("TOPPADDING", (0, 1), (-1, 1), 6),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ]))
                story.append(KeepTogether([card, Spacer(1, 10)]))

        doc.build(story, onFirstPage=self._pdf_footer, onLaterPages=self._pdf_footer)
        buffer.seek(0)
        return buffer
