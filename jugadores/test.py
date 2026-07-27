from django.urls import reverse
from django.test import TestCase
import json
import base64
from unittest.mock import patch
from django.db import IntegrityError
from rest_framework.response import Response

from jugadores.models import Jugadores


class JugadoresTestCase(TestCase):
    def setUp(self):
        self.sample_image_bytes = b"\x89PNG\r\n\x1a\n"
        self.sample_image_b64 = (
            "data:image/png;base64,"
            + base64.b64encode(self.sample_image_bytes).decode()
        )

        self.jugador = Jugadores.objects.create(
            idbanner="A00000001",
            nombrejugador="Juan",
            apellidojugador="Lopez",
            numerocamisetajugador=10,
            imagenjugador=self.sample_image_bytes,
            posicionjugador="Delantero",
            jugadoractivo=True,
        )

    def post_json(self, url, data):
        return self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

    def patch_json(self, url, data):
        return self.client.patch(
            url, data=json.dumps(data), content_type="application/json"
        )

    def parse(self, resp):
        try:
            return json.loads(resp.content.decode("utf-8"))
        except Exception:
            return {}

    def test_create_jugador_min_jersey_success(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000002",
            "nombrejugador": "Ana",
            "apellidojugador": "Perez",
            "numerocamisetajugador": 1,
            "imagenjugador": self.sample_image_b64,
            "posicionjugador": "Portero",
            "jugadoractivo": True,
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 201)
        payload = self.parse(resp)
        self.assertIn("mensaje", payload)
        self.assertIn("data", payload)
        self.assertEqual(payload["data"]["idbanner"], "A00000002")

        nuevo = Jugadores.objects.get(idbanner="A00000002")
        self.assertEqual(bytes(nuevo.imagenjugador), self.sample_image_bytes)

    def test_create_jugador_max_jersey_success(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000099",
            "nombrejugador": "Luis",
            "apellidojugador": "Garcia",
            "numerocamisetajugador": 99,
            "posicionjugador": "Defensa",
            "imagenjugador": self.sample_image_b64,
            "jugadoractivo": True,
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 201)

    def test_create_jugador_medium_jersey_success(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000050",
            "nombrejugador": "Marta",
            "apellidojugador": "Lopez",
            "numerocamisetajugador": 50,
            "posicionjugador": "Mediocampista",
            "imagenjugador": self.sample_image_b64,
            "jugadoractivo": False,
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 201)

    def test_create_jugador_name_two_words_allowed(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000013",
            "nombrejugador": "Juan Carlos",
            "apellidojugador": "Sanchez",
            "numerocamisetajugador": 22,
            "posicionjugador": "Defensa",
            "imagenjugador": self.sample_image_b64,
            "jugadoractivo": True,
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 201)

    def test_create_jugador_imagen_empty_becomes_null(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000014",
            "nombrejugador": "Sofia",
            "apellidojugador": "Diaz",
            "numerocamisetajugador": 15,
            "imagenjugador": "",
            "posicionjugador": "Delantero",
            "jugadoractivo": True,
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 201)
        nuevo = Jugadores.objects.get(idbanner="A00000014")
        self.assertIsNone(nuevo.imagenjugador)

    # -----------------
    # Casos negativos
    # -----------------
    def test_create_jersey_zero_fails(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000015",
            "nombrejugador": "Bad",
            "apellidojugador": "Num",
            "numerocamisetajugador": 0,
            "posicionjugador": "Defensa",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertTrue("error" in payload or "data" in payload)

    def test_create_jersey_above_max_fails(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000016",
            "nombrejugador": "Bad",
            "apellidojugador": "Num",
            "numerocamisetajugador": 100,
            "posicionjugador": "Delantero",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertTrue("error" in payload or "data" in payload)

    def test_create_name_too_many_words_fails(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000017",
            "nombrejugador": "Juan Carlos Alberto",
            "apellidojugador": "Torres",
            "numerocamisetajugador": 8,
            "posicionjugador": "Mediocampista",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn(
            "El nombre solo puede contener letras y un espacio opcional.",
            payload["data"],
        )

    def test_create_apellido_empty_fails(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000018",
            "nombrejugador": "Ana",
            "apellidojugador": "   ",
            "numerocamisetajugador": 7,
            "posicionjugador": "Portero",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("error", payload)

    def test_create_idbanner_all_zeros_fails(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000000",
            "nombrejugador": "Zero",
            "apellidojugador": "Test",
            "numerocamisetajugador": 3,
            "posicionjugador": "Defensa",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("error", payload)
        self.assertIn(
            "Debe tener una letra seguida de hasta 8 números."
            "Los números no pueden ser todos ceros (ej: A00088860).",
            payload["data"],
        )

    def test_create_invalid_idbanner_format_fails(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "123_INVALID",
            "nombrejugador": "X",
            "apellidojugador": "Y",
            "numerocamisetajugador": 5,
            "posicionjugador": "Defensa",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("error", payload)

    def test_create_invalid_posicion_returns_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000019",
            "nombrejugador": "BadPos",
            "apellidojugador": "Test",
            "numerocamisetajugador": 3,
            "posicionjugador": "ArqueroInvalido",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("ArqueroInvalido", payload["data"])
        self.assertIn("error", payload)

    def test_create_invalid_base64_returns_validation_error(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000020",
            "nombrejugador": "MalImage",
            "apellidojugador": "Test",
            "numerocamisetajugador": 7,
            "imagenjugador": "data:image/png;base64,###NOTBASE64###",
            "posicionjugador": "Portero",
        }
        resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("Formato Base64 inválido.", payload["data"])

    # -----------------
    # Casos de excepción
    # -----------------
    def test_create_raises_integrityerror_returns_bad_request(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000021",
            "nombrejugador": "Ex",
            "apellidojugador": "Test",
            "numerocamisetajugador": 12,
            "posicionjugador": "Delantero",
        }
        with patch(
            "jugadores.views.JugadorSerializer.save", side_effect=IntegrityError()
        ):
            resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("error", payload)

    def test_create_unhandled_exception_returns_bad_request(self):
        url = reverse("jugador-list-create")
        data = {
            "idbanner": "A00000023",
            "nombrejugador": "Ex2",
            "apellidojugador": "Test",
            "numerocamisetajugador": 13,
            "posicionjugador": "Mediocampista",
        }
        with patch(
            "jugadores.views.JugadorSerializer.save", side_effect=Exception("boom")
        ):
            resp = self.post_json(url, data)
        self.assertEqual(resp.status_code, 400)
        payload = self.parse(resp)
        self.assertIn("error", payload)

    def test_patch_raises_validation_error_handled(self):
        url = reverse("jugador-update", args=[self.jugador.idjugador])
        with (
            patch("jugadores.views.JugadorSerializer.is_valid", return_value=False),
            patch(
                "jugadores.views.JugadorSerializer.errors",
                new_callable=lambda: {"idbanner": ["error"]},
            ),
        ):
            resp = self.patch_json(url, {"idbanner": "A00000001"})
        self.assertEqual(resp.status_code, 200)
        payload = self.parse(resp)
        self.assertTrue("error" in payload or "data" in payload)


    @patch("jugadores.views.paginate_queryset")
    def test_get_all_players_success(self, mock_paginate):
        mock_paginate.return_value = Response(
            {"mensaje": "ok"},
            status=200,
        )

        response = self.client.get(reverse("jugador-all"))

        self.assertEqual(response.status_code, 200)

    def test_active_players_shirts(self):
        response = self.client.get(reverse("jugadores-activos"))

        self.assertEqual(response.status_code, 200)

        payload = self.parse(response)

        self.assertEqual(payload["mensaje"], "Shirts de jugadores activos")

    # -----------------
    # DETAIL BANNER
    # -----------------

    def test_detail_banner_success(self):
        response = self.client.get(
            reverse("jugador-detail", args=[self.jugador.idbanner])
        )

        self.assertEqual(response.status_code, 200)

    def test_detail_banner_not_found(self):
        response = self.client.get(reverse("jugador-detail", args=["A99999999"]))

        self.assertEqual(response.status_code, 404)

    # -----------------
    # DETAIL ID
    # -----------------

    def test_detail_id_success(self):
        response = self.client.get(
            reverse("jugador-detail-id", args=[self.jugador.idjugador])
        )

        self.assertEqual(response.status_code, 200)

    def test_detail_id_not_found(self):
        response = self.client.get(reverse("jugador-detail-id", args=[999]))

        self.assertEqual(response.status_code, 400)

    # -----------------
    # DETAIL SHIRT
    # -----------------

    def test_detail_shirt_success(self):
        response = self.client.get(
            reverse(
                "jugador-detail-shirt-number",
                args=[10],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_detail_shirt_not_found(self):
        response = self.client.get(
            reverse(
                "jugador-detail-shirt-number",
                args=[99],
            )
        )

        self.assertEqual(response.status_code, 404)

    @patch("jugadores.views.get_object_or_404")
    def test_detail_shirt_exception(self, mock_get):

        mock_get.side_effect = Exception("boom")

        response = self.client.get(
            reverse(
                "jugador-detail-shirt-number",
                args=[10],
            )
        )

        self.assertEqual(response.status_code, 400)

    # -----------------
    # UPDATE
    # -----------------

    def test_patch_success(self):

        response = self.patch_json(
            reverse(
                "jugador-update",
                args=[self.jugador.idjugador],
            ),
            {"nombrejugador": "Pedro"},
        )

        self.assertEqual(response.status_code, 200)

    @patch(
        "jugadores.views.JugadorUpdateSerializer.save",
        side_effect=IntegrityError(),
    )
    def test_patch_integrity_error(
        self,
        mock_save,
    ):

        response = self.patch_json(
            reverse(
                "jugador-update",
                args=[self.jugador.idjugador],
            ),
            {"nombrejugador": "Pedro"},
        )

        self.assertEqual(response.status_code, 400)

    @patch(
        "jugadores.views.JugadorUpdateSerializer.save",
        side_effect=Exception("boom"),
    )
    def test_patch_exception(
        self,
        mock_save,
    ):

        response = self.patch_json(
            reverse(
                "jugador-update",
                args=[self.jugador.idjugador],
            ),
            {"nombrejugador": "Pedro"},
        )

        self.assertEqual(response.status_code, 400)

    # -----------------
    # DELETE
    # -----------------

    def test_delete_success(self):

        response = self.client.delete(
            reverse(
                "jugador-delete",
                args=[self.jugador.idbanner],
            )
        )

        self.assertEqual(response.status_code, 200)

        self.jugador.refresh_from_db()

        self.assertFalse(self.jugador.jugadoractivo)

    def test_delete_already_inactive(self):

        self.jugador.jugadoractivo = False

        self.jugador.save()

        response = self.client.delete(
            reverse(
                "jugador-delete",
                args=[self.jugador.idbanner],
            )
        )

        self.assertEqual(response.status_code, 200)

    @patch("jugadores.views.get_object_or_404")
    def test_delete_exception(
        self,
        mock_get,
    ):

        mock_get.side_effect = Exception("boom")

        response = self.client.delete(
            reverse(
                "jugador-delete",
                args=[self.jugador.idbanner],
            )
        )

        self.assertEqual(response.status_code, 400)

    # -----------------
    # SERIALIZER
    # -----------------

    def test_create_duplicate_banner(self):

        response = self.post_json(
            reverse("jugador-list-create"),
            {
                "idbanner": "A00000001",
                "nombrejugador": "Nuevo",
                "apellidojugador": "Jugador",
                "numerocamisetajugador": 20,
                "posicionjugador": "Delantero",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_create_duplicate_active_shirt(self):

        response = self.post_json(
            reverse("jugador-list-create"),
            {
                "idbanner": "A00000088",
                "nombrejugador": "Nuevo",
                "apellidojugador": "Jugador",
                "numerocamisetajugador": 10,
                "posicionjugador": "Delantero",
                "jugadoractivo": True,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_create_same_shirt_inactive_allowed(self):

        response = self.post_json(
            reverse("jugador-list-create"),
            {
                "idbanner": "A00000077",
                "nombrejugador": "Nuevo",
                "apellidojugador": "Jugador",
                "numerocamisetajugador": 10,
                "posicionjugador": "Delantero",
                "jugadoractivo": False,
            },
        )

        self.assertEqual(response.status_code, 201)
