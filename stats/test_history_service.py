from decimal import Decimal

from django.test import TestCase

from jugadores.models import Jugadores
from stats.history_service import (
    get_analyzed_matches,
    get_general_stats,
    player_stats_by_match,
)
from stats.models import PlayerStatsConsolidated, PlayerStatsHist


class HistoryServiceTests(TestCase):

    def setUp(self):

        self.player = Jugadores.objects.create(
            idjugador=1,
            nombrejugador="Cristiano",
            apellidojugador="Ronaldo",
            numerocamisetajugador=7,
            jugadoractivo=True,
        )

        PlayerStatsHist.objects.create(
            jugador=self.player,
            partidos_jugados=1,
            total_passes=20,
            total_shots_on_target=2,
            total_goals=1,
            total_distance_km=Decimal("8.50"),
            total_possession_time_s=Decimal("120.00"),
            avg_speed_global_kmh=Decimal("6.20"),
        )

        PlayerStatsConsolidated.objects.create(
            player_id=self.player.idjugador,
            match_id=10,
            shirt_number=7,
            goals=2,
            team_goals=3,
            distance_km=Decimal("9.10"),
            avg_speed_kmh=Decimal("6.80"),
            team="A",
            team_color="WHITE",
            heatmap_image_path="/heat.png",
            player_crop_path="/crop.png",
            team_heatmap_path="/team_heat.png",
            movement_trajectories_path="/traj.png",
            player_movement_trajectories_path="/player_traj.png",
            team_color_time_kde_path="/kde.png",
            voronoi_territories_path="/voronoi.png",
        )

    def test_get_general_stats(self):

        stats = get_general_stats()

        self.assertEqual(stats["partidos_analizados"], 1)
        self.assertEqual(stats["jugadores_analizados"], 1)
        self.assertEqual(
            stats["distancia_promedio"],
            Decimal("8.50"),
        )
        self.assertEqual(
            stats["velocidad_promedio"],
            Decimal("6.20"),
        )

    def test_get_general_stats_without_history(self):

        PlayerStatsHist.objects.all().delete()
        PlayerStatsConsolidated.objects.all().delete()

        stats = get_general_stats()

        self.assertEqual(stats["partidos_analizados"], 0)
        self.assertEqual(stats["jugadores_analizados"], 0)
        self.assertEqual(stats["distancia_promedio"], 0)
        self.assertEqual(stats["velocidad_promedio"], 0)

    def test_get_analyzed_matches(self):

        response = get_analyzed_matches()

        self.assertEqual(len(response), 1)

        match = response[0]

        self.assertEqual(match["match_id"], 10)
        self.assertEqual(match["avg_distance"], Decimal("9.10"))
        self.assertEqual(match["avg_speed"], Decimal("6.80"))

    def test_player_stats_by_match(self):

        response = player_stats_by_match(10)

        self.assertEqual(len(response), 1)

        player = response[0]

        self.assertEqual(player["player_id"], self.player.idjugador)
        self.assertEqual(player["player_name"], "Cristiano Ronaldo")
        self.assertEqual(player["shirt_number"], 7)
        self.assertEqual(player["goals"], 2)
        self.assertEqual(player["team"], "A")
        self.assertEqual(player["team_color"], "WHITE")

    def test_player_stats_by_match_returns_empty_list(self):

        response = player_stats_by_match(999)

        self.assertEqual(response, [])

    def test_player_stats_by_match_skips_missing_player(self):

        PlayerStatsConsolidated.objects.create(
            player_id=999,
            match_id=10,
            shirt_number=99,
            goals=1,
        )

        response = player_stats_by_match(10)

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["player_id"], self.player.idjugador)
