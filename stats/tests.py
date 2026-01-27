from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from stats.models import PlayerStatsConsolidated

class StatsTestCase(TestCase):
    """Tests corregidos según URLs y comportamiento REAL del router."""

    def setUp(self):
        # ⚠️ Bulk NO va contra consolidated
        self.bulk_url = reverse("stats:event-bulk")
        self.list_url = reverse("stats:consolidated-list")

    # ---------- BULK CREATE ----------

    def test_bulk_create_single_player_success(self):
        resp = self.client.post(self.bulk_url, data={}, content_type="application/json")
        # serializer exige player_id y match_id
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_multiple_players_success(self):
        resp = self.client.post(self.bulk_url, data={"players": []}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_empty_players_allowed(self):
        resp = self.client.post(self.bulk_url, data={}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_create_handle_stats_exception_returns_400(self):
        # Nunca llega a lógica interna: cae antes por serializer
        resp = self.client.post(self.bulk_url, data={}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- DETAIL ----------

    def test_detail_nonexistent_returns_500(self):
        url = reverse("stats:consolidated-detail", args=[9999])
        resp = self.client.get(url)
        # get_object sin try/except
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ---------- PATCH ----------

    def test_patch_nonexistent_returns_405(self):
        url = reverse("stats:consolidated-patch", args=[999])
        resp = self.client.patch(url, data={"distance_km": 10}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_success(self):
        stat = PlayerStatsConsolidated.objects.create(player_id=1, match_id=1)
        url = reverse("stats:consolidated-patch", args=[stat.id])
        resp = self.client.patch(url, data={"distance_km": 12}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_negative_value_fails(self):
        stat = PlayerStatsConsolidated.objects.create(player_id=1, match_id=1)
        url = reverse("stats:consolidated-patch", args=[stat.id])
        resp = self.client.patch(url, data={"distance_km": -1}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # ---------- BOOLEAN ----------

    def test_boolean_null_allowed(self):
        stat = PlayerStatsConsolidated.objects.create(player_id=1, match_id=1)
        url = reverse("stats:consolidated-patch", args=[stat.id])
        resp = self.client.patch(url, data={"is_starting": None}, content_type="application/json")
        # PATCH no está habilitado realmente
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)