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
        fields = ['idJugador', 'nombreJugador', 'apellidoJugador', 'numeroCamisetaJugador', 'posicionJugador', 'jugadorActivo', 'idBanner']
        
    def validate_idBannerJugador(self, value):
        if self.instance is None and Jugadores.objects.filter(idBanner = value).exists():
            raise serializers.ValidationError("Ya existe un jugador asociado a ese ID Banner")
        return value
    