from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from jugadores.models import Jugadores
import base64

class JugadoresAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Imagen ejemplo (bytes) y su representación base64 tipo data URI
        self.sample_image_bytes = b"\x89PNG\r\n\x1a\n"
        self.sample_image_b64 = "data:image/png;base64," + base64.b64encode(self.sample_image_bytes).decode()

        # Jugador inicial en DB
        self.jugador = Jugadores.objects.create(
            idbanner="BNR000001",
            nombrejugador="Juan",
            apellidojugador="Lopez",
            numerocamisetajugador=10,
            imagenjugador=self.sample_image_bytes,
            posicionjugador="Delantero",
            jugadoractivo=True
        )

    # ---------- LIST / PAGINACIÓN ----------
    def test_list_jugadores_ok_usa_json(self):
        url = reverse("jugador-list-create")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        payload = resp.json()
        # el view devuelve un dict con keys: count,page,offset,pages,results
        self.assertIn("results", payload)
        self.assertEqual(payload.get("count"), 1)
        self.assertIsInstance(payload["results"], list)

    def test_list_jugadores_pagination_invalid_params(self):
        url = reverse("jugador-list-create") + "?page=0&offset=-5"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        payload = resp.json()
        self.assertIn("error", payload)

    # ---------- CREATE ----------
    def test_create_jugador_success_con_base64(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000002",
            "nombrejugador": "Carlos",
            "apellidojugador": "Perez",
            "numerocamisetajugador": 9,
            "imagenjugador": self.sample_image_b64,
            "posicionjugador": "Defensa",
            "jugadoractivo": False
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        payload = resp.json()
        self.assertIn("mensaje", payload)
        self.assertIn("jugador", payload)
        self.assertEqual(payload["jugador"]["idbanner"], "BNR000002")

        # confirmar que en la BD se guardaron bytes (no el data URI)
        nuevo_jugador = Jugadores.objects.get(idbanner="BNR000002")
        self.assertEqual(bytes(nuevo_jugador.imagenjugador), self.sample_image_bytes) # type: ignore 

    def test_create_jugador_duplicate_idbanner_returns_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000001",  # ya existe
            "nombrejugador": "Duplicado",
            "apellidojugador": "Uno",
            "numerocamisetajugador": 11,
            "posicionjugador": "Mediocampista"
        }
        resp = self.client.post(url, data, format="json")
        # puede venir del serializer o del IntegrityError; el view devuelve 400
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        payload = resp.json()
        # la validación en serializer lanza error en 'idbanner' o se devolvió error general
        self.assertTrue(any(k in payload for k in ("idbanner", "error")))

    def test_create_jugador_invalid_base64_returns_validation_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000003",
            "nombrejugador": "MalImage",
            "apellidojugador": "Test",
            "numerocamisetajugador": 7,
            "imagenjugador": "data:image/png;base64,###NOTBASE64###",
            "posicionjugador": "Portero"
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        payload = resp.json()
        # serializer lanza ValidationError con key imagenjugador
        self.assertIn("imagenjugador", payload)

    # ---------- DETAIL (BY BANNER / BY ID) ----------
    def test_get_jugador_by_banner_ok(self):
        url = reverse("jugador-detail", args=["BNR000001"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = resp.json()
        self.assertEqual(payload.get("idbanner"), "BNR000001")
        # imagen debe venir como data URI o None (según serializer)
        self.assertIn("imagenjugador", payload)

    def test_get_jugador_by_id_ok(self):
        url = reverse("jugador-detail-id", args=[self.jugador.idjugador])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = resp.json()
        self.assertEqual(payload.get("idjugador"), self.jugador.idjugador)

    def test_get_jugador_not_found_returns_404(self):
        url = reverse("jugador-detail", args=["NO_EXISTE"])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- UPDATE (PATCH) ----------
    def test_patch_update_jugador_ok(self):
        url = reverse("jugador-update", args=[self.jugador.idjugador])
        resp = self.client.patch(url, {"nombrejugador": "Juan Actualizado"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = resp.json()
        self.assertIn("mensaje", payload)
        self.jugador.refresh_from_db()
        self.assertEqual(self.jugador.nombrejugador, "Juan Actualizado")

    def test_patch_update_jugador_inexistent_returns_404(self):
        url = reverse("jugador-update", args=[9999])  # id que no existe
        resp = self.client.patch(url, {"nombrejugador": "X"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- DELETE ----------
    def test_delete_jugador_by_banner_ok(self):
        url = reverse("jugador-delete", args=["BNR000001"])
        resp = self.client.delete(url)
        # tu view retorna 200 con mensaje
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = resp.json()
        self.assertIn("mensaje", payload)
        self.assertFalse(Jugadores.objects.filter(idbanner="BNR000001").exists())

    def test_delete_jugador_not_found_returns_404(self):
        url = reverse("jugador-delete", args=["NO_EXISTE"])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
