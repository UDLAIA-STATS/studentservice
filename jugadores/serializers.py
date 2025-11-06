import base64
from django.db import IntegrityError
from rest_framework import serializers
from.models import (Jugadores)

# ===============================================
# JUGADORES
# ===============================================

class JugadorSerializer (serializers.ModelSerializer):
    class Meta:
        model = Jugadores
        fields = [
            'idjugador',
            'nombrejugador',
            'apellidojugador',
            'numerocamisetajugador',
            'posicionjugador',
            'jugadoractivo',
            'idbanner'
            ]

    def validate_idbanner(self, value):
        if self.instance is None and Jugadores.objects.filter(idbanner=value).exists():
            raise serializers.ValidationError("Ya existe un jugador asociado a ese ID Banner")
        return value
    