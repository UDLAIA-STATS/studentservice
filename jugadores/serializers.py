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
            'imagenjugador',
            'posicionjugador',
            'jugadoractivo',
            'idbanner'
            ]

    def validate_idbanner(self, value):
        if self.instance is None and Jugadores.objects.filter(idbanner=value).exists():
            raise serializers.ValidationError("Ya existe un jugador asociado a ese ID Banner")
        return value
    
    def to_internal_value(self, data):
        """
        Convierte el valor de 'imagenjugador' en base64 a bytes.
        Si el valor es None o una cadena vacía, se deja como None.
        Si el valor es una cadena que comienza con "data:image", se intenta
        convertir a bytes. Si no se puede parsear, se devuelve un
        ValidationError con el mensaje "Formato Base64 inválido.".
        """
        internal = super().to_internal_value(data)
        imagen = data.get('imagenjugador')

        # Si viene como base64, la convertimos a bytes
        if isinstance(imagen, str) and imagen.startswith("data:image"):
            try:
                _, base64_data = imagen.split(',', 1)
                internal['imagenjugador'] = base64.b64decode(base64_data)
            except Exception:
                raise serializers.ValidationError({"imagenjugador": "Formato Base64 inválido."})
        elif imagen is None or imagen == "":
            internal['imagenjugador'] = None
        return internal

    def to_representation(self, instance):
        """
        Convierte una instancia de Jugadores en un objeto JSON.
        Se convierte el campo 'imagenjugador' de bytes a base64
        para enviar al frontend. Si el campo es None o una cadena
        vacía, se deja como None.
        """
        rep = super().to_representation(instance)
        # Convertimos los bytes a base64 para enviar al frontend
        if instance.imagenjugador:
            rep['imagenjugador'] = f"data:image/png;base64,{base64.b64encode(instance.imagenjugador).decode('utf-8')}"
        else:
            rep['imagenjugador'] = None
        return rep
