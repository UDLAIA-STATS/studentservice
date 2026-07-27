from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from jugadores.models import Jugadores
from stats.models import PlayerStatsConsolidated
from stats.services import _copy_player_information, _merge_average, _merge_path, _merge_sum, _to_decimal, actualizar_estadisticas_generales, get_jugador_activo_por_camiseta
from stats.views import TeamStatsPdfView


class StatsTestCase(TestCase):

    def setUp(self):
        self.bulk_url = reverse("stats:event-bulk")
        self.list_url = reverse("stats:consolidated-list")

    # ------------------------------------------------------------------
    # BULK
    # ------------------------------------------------------------------

    def test_bulk_invalid_payload_returns_400(self):
        response = self.client.post(
            self.bulk_url,
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("stats.views.handle_player_stats.handle_stats")
    @patch("stats.views.PlayerStatsInputSerializer.is_valid")
    @patch("stats.views.PlayerStatsInputSerializer.validated_data", new_callable=dict)
    def test_bulk_valid_payload(
        self,
        validated_data,
        mock_is_valid,
        mock_handle,
    ):
        mock_is_valid.return_value = True

        response = self.client.post(
            self.bulk_url,
            data=validated_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_handle.assert_called_once()

    @patch("stats.views.handle_player_stats.handle_stats")
    @patch("stats.views.PlayerStatsInputSerializer.is_valid")
    @patch("stats.views.PlayerStatsInputSerializer.validated_data", new_callable=dict)
    def test_bulk_internal_exception_returns_500(
        self,
        validated_data,
        mock_is_valid,
        mock_handle,
    ):
        mock_is_valid.return_value = True
        mock_handle.side_effect = Exception("boom")

        response = self.client.post(
            self.bulk_url,
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def test_list_empty(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_filter_by_match(self):
        PlayerStatsConsolidated.objects.create(
            player_id=1,
            match_id=1,
        )

        PlayerStatsConsolidated.objects.create(
            player_id=2,
            match_id=2,
        )

        response = self.client.get(self.list_url, {"match_id": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------------------

    def test_detail_success(self):
        stat = PlayerStatsConsolidated.objects.create(
            player_id=1,
            match_id=1,
        )

        url = reverse("stats:consolidated-detail", args=[stat.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_nonexistent_returns_500(self):
        url = reverse("stats:consolidated-detail", args=[999])

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def test_correction_missing_data_returns_400(self):
        url = reverse("stats:consolidated-correction")

        response = self.client.post(
            url,
            {},
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_correction_invalid_stat_returns_400(self):
        url = reverse("stats:consolidated-correction")

        response = self.client.post(
            url,
            {
                "stats_id": 999,
                "player_id": 1,
                "shirt_number": 10,
            },
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch("stats.views.get_general_stats")
    def test_general_stats(self, mock_stats):

        mock_stats.return_value = {
            "partidos_analizados": 1,
            "jugadores_analizados": 5,
            "distancia_promedio": 8,
            "velocidad_promedio": 12,
        }

        url = reverse("stats:general-stats")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # ANALYZED MATCHES
    # ------------------------------------------------------------------

    @patch("stats.views.get_analyzed_matches")
    def test_analyzed_matches(self, mock_matches):

        mock_matches.return_value = []

        url = reverse("stats:analyzed-matchs")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # PLAYER BY MATCH
    # ------------------------------------------------------------------

    @patch("stats.views.player_stats_by_match")
    def test_player_stats_by_match(self, mock_service):

        mock_service.return_value = []

        url = reverse("stats:player-stats-by-match", args=[1])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_team_pdf_without_stats_returns_404(self):
        url = reverse("stats:team-stats-pdf", args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


    @patch("stats.views.TeamStatsPdfView._build_pdf")
    @patch("stats.views.TeamStatsPdfView._fetch_images_concurrently")
    @patch("stats.views.TeamStatsPdfView._extract_team_image_paths")
    @patch("stats.views.TeamStatsPdfView._aggregate_stats")
    def test_team_pdf_success(
        self,
        mock_aggregate,
        mock_extract,
        mock_fetch,
        mock_build,
    ):

        PlayerStatsConsolidated.objects.create(
            player_id=1,
            match_id=1,
            shirt_number=10,
        )

        mock_aggregate.return_value = ([], {})
        mock_extract.return_value = {}
        mock_fetch.return_value = {}
        mock_build.return_value = b"pdf"

        url = reverse("stats:team-stats-pdf", args=[1])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_aggregate_stats(self):
        view = TeamStatsPdfView()

        row = PlayerStatsConsolidated(
            player_id=1,
            goals=2,
            distance_km=Decimal("3.5"),
            avg_speed_kmh=Decimal("12"),
            avg_acceleration=Decimal("4"),
        )

        players, totals = view._aggregate_stats([row])

        self.assertEqual(len(players),1)

        self.assertEqual(
            players[0]["total_goals"],
            2,
        )

        self.assertEqual(
            totals["total_goals"],
            2,
        )

    def test_aggregate_empty(self):
        view = TeamStatsPdfView()
        players, totals = view._aggregate_stats([])

        self.assertEqual(players, [])

        self.assertEqual(
            totals["total_goals"],
            0,
        )

    def test_extract_team_paths(self):
        view = TeamStatsPdfView()
        row = PlayerStatsConsolidated(
            team_heatmap_path="heat.png",
            movement_trajectories_path="traj.png",
        )

        result = view._extract_team_image_paths([row])

        self.assertEqual(
            result["team_heatmap_path"],
            "heat.png",
        )

        self.assertEqual(
            result["movement_trajectories_path"],
            "traj.png",
        )

    def test_player_display_name(self):
        jugador = MagicMock()

        jugador.nombrejugador="Juan"
        jugador.apellidojugador="Perez"

        view=TeamStatsPdfView()

        self.assertEqual(
            view._player_display_name(
                jugador,
                1,
            ),
            "Juan Perez",
        )

    def test_player_display_name_without_player(self):
        view = TeamStatsPdfView()

        self.assertEqual(
            view._player_display_name(
                None,
                99,
            ),
            "Jugador ID 99",
        )

    def test_image_flowable_none(self):
        view = TeamStatsPdfView()
        styles = view._pdf_styles()

        result = view._image_flowable_from_bytes(
            styles,
            None,
            100,
            100,
        )

        self.assertIsNotNone(result)

    def test_fetch_image_invalid_file(self):
        view = TeamStatsPdfView()
        result = view._fetch_image_bytes(
            "archivo_que_no_existe.png"
        )

        self.assertIsNone(result)

    def test_to_decimal_none(self):
        self.assertEqual(_to_decimal(None), Decimal("0"))

    def test_to_decimal_int(self):
        self.assertEqual(_to_decimal(5), Decimal("5"))

    def test_to_decimal_decimal(self):
        self.assertEqual(
            _to_decimal(Decimal("4.2")),
            Decimal("4.2"),
        )

    def test_merge_sum(self):
        self.assertEqual(
            _merge_sum(2,3),
            Decimal("5"),
        )

    def test_merge_sum_none(self):
        self.assertEqual(
            _merge_sum(None,4),
            Decimal("4"),
        )

    def test_merge_average(self):
        result = _merge_average(10,20)

        self.assertEqual(
            result,
            Decimal("13"),
        )

    def test_merge_average_current_zero(self):
        self.assertEqual(
            _merge_average(0,20),
            Decimal("20"),
        )

    def test_merge_average_incoming_zero(self):
        self.assertEqual(
            _merge_average(20,0),
            Decimal("20"),
        )

    def test_merge_average_none(self):
        self.assertEqual(
            _merge_average(None,None),
            Decimal("0"),
        )

    def test_merge_path_use_new(self):
        self.assertEqual(
            _merge_path(None,"img.png"),
            "img.png",
        )

    def test_merge_path_keep_old(self):
        self.assertEqual(
            _merge_path("old.png","new.png"),
            "old.png",
        )

    def test_merge_path_empty(self):
        self.assertEqual(
            _merge_path("",None),
            "",
        )

    def test_copy_player_information(self):

        stat=MagicMock()

        player=MagicMock()

        player.idjugador=15
        player.numerocamisetajugador=8

        _copy_player_information(
            stat,
            player,
        )

        self.assertEqual(stat.player_id,15)
        self.assertEqual(stat.shirt_number,8)

    @patch("stats.services.Jugadores.objects.filter")
    def test_get_player(self,mock_filter):

        jugador=MagicMock()

        mock_filter.return_value.first.return_value=jugador

        self.assertEqual(
            get_jugador_activo_por_camiseta(10),
            jugador,
        )

    @patch("stats.services.get_jugador_activo_por_camiseta")
    def test_update_stats_without_player(self,mock_player):

        mock_player.return_value=None

        actualizar_estadisticas_generales(10)

    @patch("stats.services.get_jugador_activo_por_camiseta")
    @patch("stats.services.PlayerStatsConsolidated.objects.filter")
    def test_update_stats_without_matches(
        self,
        mock_filter,
        mock_player,
    ):
        mock_player.return_value=MagicMock()
        mock_filter.return_value.exists.return_value=False
        actualizar_estadisticas_generales(10)

    def test_correction_inactive_player_returns_400(self):
        jugador = Jugadores.objects.create(
            idbanner="A00000030",
            nombrejugador="Juan",
            apellidojugador="Perez",
            numerocamisetajugador=10,
            posicionjugador="Defensa",
            jugadoractivo=False,
        )

        stat = PlayerStatsConsolidated.objects.create(
            player_id=99,
            match_id=1,
            shirt_number=99,
        )

        response = self.client.post(
            reverse("stats:consolidated-correction"),
            {
                "stats_id": stat.id,
                "player_id": jugador.idjugador,
                "shirt_number": 10,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


    def test_correction_wrong_shirt_returns_400(self):
        jugador = Jugadores.objects.create(
            idbanner="A00000031",
            nombrejugador="Juan",
            apellidojugador="Perez",
            numerocamisetajugador=10,
            posicionjugador="Defensa",
            jugadoractivo=True,
        )

        stat = PlayerStatsConsolidated.objects.create(
            player_id=5,
            match_id=1,
            shirt_number=5,
        )

        response = self.client.post(
            reverse("stats:consolidated-correction"),
            {
                "stats_id": stat.id,
                "player_id": jugador.idjugador,
                "shirt_number": 99,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


    def test_correction_same_player_returns_400(self):
        jugador = Jugadores.objects.create(
            idbanner="A00000032",
            nombrejugador="Juan",
            apellidojugador="Perez",
            numerocamisetajugador=10,
            posicionjugador="Defensa",
            jugadoractivo=True,
        )

        stat = PlayerStatsConsolidated.objects.create(
            player_id=jugador.idjugador,
            shirt_number=10,
            match_id=1,
        )

        response = self.client.post(
            reverse("stats:consolidated-correction"),
            {
                "stats_id": stat.id,
                "player_id": jugador.idjugador,
                "shirt_number": 10,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


    @patch("stats.views.merge_player_stats")
    @patch("stats.views.actualizar_estadisticas_generales")
    def test_correction_duplicate_merges(
        self,
        mock_update,
        mock_merge,
    ):
        jugador = Jugadores.objects.create(
            idbanner="A00000033",
            nombrejugador="Juan",
            apellidojugador="Perez",
            numerocamisetajugador=10,
            posicionjugador="Defensa",
            jugadoractivo=True,
        )

        source = PlayerStatsConsolidated.objects.create(
            player_id=50,
            shirt_number=50,
            match_id=1,
        )

        PlayerStatsConsolidated.objects.create(
            player_id=jugador.idjugador,
            shirt_number=10,
            match_id=1,
        )

        response = self.client.post(
            reverse("stats:consolidated-correction"),
            {
                "stats_id": source.id,
                "player_id": jugador.idjugador,
                "shirt_number": 10,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        mock_merge.assert_called_once()
        mock_update.assert_called_once()


    @patch("stats.views.actualizar_estadisticas_generales")
    def test_correction_without_duplicate_updates_stat(
        self,
        mock_update,
    ):
        jugador = Jugadores.objects.create(
            idbanner="A00000034",
            nombrejugador="Juan",
            apellidojugador="Perez",
            numerocamisetajugador=10,
            posicionjugador="Defensa",
            jugadoractivo=True,
        )

        stat = PlayerStatsConsolidated.objects.create(
            player_id=50,
            shirt_number=50,
            match_id=1,
        )

        response = self.client.post(
            reverse("stats:consolidated-correction"),
            {
                "stats_id": stat.id,
                "player_id": jugador.idjugador,
                "shirt_number": 10,
            },
            content_type="application/json",
        )

        stat.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(stat.player_id, jugador.idjugador)
        self.assertEqual(stat.shirt_number, 10)


    @patch("stats.views.actualizar_estadisticas_generales")
    def test_correction_exception_returns_500(self, mock_update):
        mock_update.side_effect = Exception("boom")

        jugador = Jugadores.objects.create(
            idbanner="A00000035",
            nombrejugador="Juan",
            apellidojugador="Perez",
            numerocamisetajugador=10,
            posicionjugador="Defensa",
            jugadoractivo=True,
        )

        stat = PlayerStatsConsolidated.objects.create(
            player_id=50,
            shirt_number=50,
            match_id=1,
        )

        response = self.client.post(
            reverse("stats:consolidated-correction"),
            {
                "stats_id": stat.id,
                "player_id": jugador.idjugador,
                "shirt_number": 10,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)




    @patch("stats.views.PlayerStatsPartialUpdateView.perform_update")
    def test_patch_integrity_error(
        self,
        mock_update,
    ):
        mock_update.side_effect = IntegrityError("boom")

        stat = PlayerStatsConsolidated.objects.create(
            player_id=1,
            match_id=1,
        )

        response = self.client.patch(
            reverse("stats:consolidated-patch", args=[stat.id]),
            {"goals": 2},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 405)


    @patch("stats.views.PlayerStatsPartialUpdateView.perform_update")
    def test_patch_unexpected_exception(
        self,
        mock_update,
    ):
        mock_update.side_effect = Exception("boom")

        stat = PlayerStatsConsolidated.objects.create(
            player_id=1,
            match_id=1,
        )

        response = self.client.patch(
            reverse("stats:consolidated-patch", args=[stat.id]),
            {"goals": 2},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 405)


    # ------------------------------------------------------------------
    # List / Detail / General
    # ------------------------------------------------------------------

    @patch("stats.views.paginate_queryset")
    def test_list_exception(
        self,
        mock_paginate,
    ):
        mock_paginate.side_effect = Exception("boom")

        response = self.client.get(reverse("stats:consolidated-list"))

        self.assertEqual(response.status_code, 500)


    @patch("stats.views.get_general_stats")
    def test_general_stats_exception(
        self,
        mock_stats,
    ):
        mock_stats.side_effect = Exception("boom")

        response = self.client.get(reverse("stats:general-stats"))

        self.assertEqual(response.status_code, 500)


    @patch("stats.views.get_analyzed_matches")
    def test_analyzed_matches_exception(
        self,
        mock_matches,
    ):
        mock_matches.side_effect = Exception("boom")

        response = self.client.get(reverse("stats:analyzed-matchs"))

        self.assertEqual(response.status_code, 500)


    @patch("stats.views.player_stats_by_match")
    def test_player_stats_by_match_exception(
        self,
        mock_service,
    ):
        mock_service.side_effect = Exception("boom")

        response = self.client.get(
            reverse("stats:player-stats-by-match", args=[1])
        )

        self.assertEqual(response.status_code, 500)


    # ------------------------------------------------------------------
    # Helpers PDF
    # ------------------------------------------------------------------

    def test_extract_team_paths_empty(self):
        view = TeamStatsPdfView()

        result = view._extract_team_image_paths([])

        self.assertIsNone(result["team_heatmap_path"])


    @patch("stats.views.requests.Session.get")
    def test_fetch_image_http(
        self,
        mock_get,
    ):
        mock_response = MagicMock()
        mock_response.content = b"abc"
        mock_response.raise_for_status.return_value = None

        mock_get.return_value = mock_response

        view = TeamStatsPdfView()

        result = view._fetch_image_bytes(
            "http://localhost/test.png"
        )

        self.assertEqual(result, b"abc")


    @patch.object(
        TeamStatsPdfView,
        "_fetch_image_bytes",
    )
    def test_fetch_images_concurrently(
        self,
        mock_fetch,
    ):
        mock_fetch.return_value = b"img"

        view = TeamStatsPdfView()

        result = view._fetch_images_concurrently(
            [
                "a.png",
                "b.png",
                "a.png",
            ]
        )

        self.assertEqual(len(result), 2)