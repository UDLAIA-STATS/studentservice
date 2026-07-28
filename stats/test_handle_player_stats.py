from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from jugadores.models import Jugadores
from stats.management.handle_player_stats import handle_stats
from stats.models import PlayerStatsConsolidated


class HandlePlayerStatsTests(TestCase):

    def setUp(self):
        self.player = Jugadores.objects.create(
            idjugador=1,
            nombrejugador="Lionel",
            apellidojugador="Messi",
            numerocamisetajugador=10,
            jugadoractivo=True,
        )

    @patch("stats.management.handle_player_stats.actualizar_estadisticas_generales")
    def test_handle_stats_creates_record(self, mock_update):

        message = {
            "shirt_number": 10,
            "team_color": "BLUE",
            "match_id": 5,
            "passes": 40,
            "goals": 2,
            "distance_km": Decimal("8.50"),
            "avg_speed_kmh": Decimal("6.25"),
            "avg_acceleration": Decimal("1.75"),
            "team": "A",
            "heatmap_image_path": "/heat.png",
        }

        result = handle_stats(message)

        self.assertTrue(result)

        stat = PlayerStatsConsolidated.objects.get()

        self.assertEqual(stat.player_id, self.player.idjugador)
        self.assertEqual(stat.match_id, 5)
        self.assertEqual(stat.goals, 2)
        self.assertEqual(stat.team_color, "BLUE")

        mock_update.assert_called_once_with(10)

    def test_handle_stats_returns_false_when_required_fields_missing(self):

        result = handle_stats({"shirt_number": 10})

        self.assertFalse(result)
        self.assertEqual(PlayerStatsConsolidated.objects.count(), 0)

    def test_handle_stats_returns_false_when_player_not_found(self):

        message = {
            "shirt_number": 99,
            "team_color": "BLUE",
            "match_id": 5,
        }

        result = handle_stats(message)

        self.assertTrue(result)

    @patch(
        "stats.management.handle_player_stats.PlayerStatsConsolidated.objects.create"
    )
    def test_handle_stats_returns_false_when_exception_occurs(self, mock_create):

        mock_create.side_effect = Exception("db failure")

        result = handle_stats(
            {
                "shirt_number": 10,
                "team_color": "BLUE",
                "match_id": 5,
            }
        )

        self.assertFalse(result)