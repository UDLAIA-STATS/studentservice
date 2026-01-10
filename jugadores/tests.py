from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from jugadores.models import Jugadores
import base64
from unittest.mock import patch
from django.db import IntegrityError


class JugadoresAPITestCase(TestCase):
    """
    Pruebas unitarias siguiendo lineamientos ISTQB:
    - Casos positivos (funcionamiento esperado)
    - Casos negativos (validaciones de entrada)
    - Casos de excepción (errores no funcionales / manejo de excepciones)

    Nota: estas pruebas no se ejecutan aquí; se han diseñado para validar
    comportamiento observable del API y coverar ramas de manejo de errores.
    """

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

    # -----------------
    # Casos positivos
    # -----------------
    def test_list_jugadores_ok_usa_json(self):
        url = reverse("jugador-list-create")
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK

        payload = resp.json()
        # el view devuelve un dict con keys: count,page,offset,pages,results
        assert "results" in payload
        assert payload.get("count") == 1
        assert isinstance(payload["results"], list)

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
        assert resp.status_code == status.HTTP_201_CREATED

        payload = resp.json()
        assert "mensaje" in payload
        assert "jugador" in payload
        assert payload["jugador"]["idbanner"] == "BNR000002"

        # confirmar que en la BD se guardaron bytes (no el data URI)
        nuevo_jugador = Jugadores.objects.get(idbanner="BNR000002")
        assert bytes(nuevo_jugador.imagenjugador) == self.sample_image_bytes  # type: ignore

    def test_get_jugador_by_banner_ok(self):
        url = reverse("jugador-detail", args=["BNR000001"])
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        payload = resp.json()
        assert payload.get("idbanner") == "BNR000001"
        assert "imagenjugador" in payload

    def test_patch_update_jugador_ok(self):
        url = reverse("jugador-update", args=[self.jugador.idjugador])
        resp = self.client.patch(url, {"nombrejugador": "Juan Actualizado"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        payload = resp.json()
        assert "mensaje" in payload
        self.jugador.refresh_from_db()
        assert self.jugador.nombrejugador == "Juan Actualizado"

    def test_delete_jugador_by_banner_ok(self):
        url = reverse("jugador-delete", args=["BNR000001"])
        resp = self.client.delete(url)
        assert resp.status_code == status.HTTP_200_OK
        payload = resp.json()
        assert "mensaje" in payload
        assert not Jugadores.objects.filter(idbanner="BNR000001").exists()

    # -----------------
    # Casos negativos
    # -----------------
    def test_list_jugadores_pagination_invalid_params(self):
        url = reverse("jugador-list-create") + "?page=0&offset=-5"
        resp = self.client.get(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert "error" in payload

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
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        # la validación en serializer lanza error en 'idbanner' o se devolvió error general
        assert any(k in payload for k in ("idbanner", "error"))

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
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        # serializer lanza ValidationError con key imagenjugador
        assert "imagenjugador" in payload

    def test_create_invalid_idbanner_format_returns_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "123_INVALID",
            "nombrejugador": "X",
            "apellidojugador": "Y",
            "numerocamisetajugador": 5,
            "posicionjugador": "Defensa"
        }
        resp = self.client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert any(k in payload for k in ("idbanner", "error"))

    def test_create_invalid_posicion_returns_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000004",
            "nombrejugador": "BadPos",
            "apellidojugador": "Test",
            "numerocamisetajugador": 3,
            "posicionjugador": "ArqueroInvalido"
        }
        resp = self.client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert any(k in payload for k in ("posicionjugador", "error"))

    def test_create_invalid_jersey_number_returns_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000005",
            "nombrejugador": "BadNum",
            "apellidojugador": "Test",
            "numerocamisetajugador": 150,
            "posicionjugador": "Defensa"
        }
        resp = self.client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert any(k in payload for k in ("numerocamisetajugador", "error"))

    def test_update_invalid_boolean_jugadoractivo_returns_error(self):
        url = reverse("jugador-update", args=[self.jugador.idjugador])
        resp = self.client.patch(url, {"jugadoractivo": "notaboolean"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert any(k in payload for k in ("jugadoractivo", "error"))

    # -----------------
    # Casos de excepción
    # -----------------
    def test_create_raises_integrityerror_returns_bad_request(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000006",
            "nombrejugador": "Ex",
            "apellidojugador": "Test",
            "numerocamisetajugador": 12,
            "posicionjugador": "Delantero"
        }
        # parchear el save del serializer para que lance IntegrityError
        with patch("jugadores.views.JugadorSerializer.save", side_effect=IntegrityError()):
            resp = self.client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert "error" in payload
        assert "Ya existe un jugador" in payload["error"]

    def test_create_unhandled_exception_returns_bad_request(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "BNR000007",
            "nombrejugador": "Ex2",
            "apellidojugador": "Test",
            "numerocamisetajugador": 13,
            "posicionjugador": "Mediocampista"
        }
        with patch("jugadores.views.JugadorSerializer.save", side_effect=Exception("boom")):
            resp = self.client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert "error" in payload
        assert "No se pudo crear el jugador" in payload["error"]

    def test_patch_raises_validation_error_handled(self):
        url = reverse("jugador-update", args=[self.jugador.idjugador])
        # forzar que el serializer sea inválido y provoque la rama de validación
        with patch("jugadores.views.JugadorSerializer.is_valid", return_value=False), \
             patch("jugadores.views.JugadorSerializer.errors", new_callable=lambda: {"idbanner": ["error"]}):
            resp = self.client.patch(url, {"idbanner": "BNR000001"}, format="json")
        # esperamos 400 y que se retorne un payload con 'error' o el campo
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        payload = resp.json()
        assert any(k in payload for k in ("idbanner", "error"))

