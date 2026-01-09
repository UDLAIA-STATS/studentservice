import base64
import re
from typing import Tuple
from django.db import IntegrityError
from rest_framework import serializers
from.models import (Jugadores)

POSICIONES_VALIDAS = ("Delantero", "Mediocampista", "Defensa", "Portero")
ID_BANNER_REGEX = r'^[A-Za-z](?!0{8}$)\d{8}$'
NAME_REGEX = r'^[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?: [A-Za-zÁÉÍÓÚáéíóúÑñ]+)?$'
LASTNAME_REGEX = r'^[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?: [A-Za-zÁÉÍÓÚáéíóúÑñ]+)?$'

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

    def validate_nombrejugador(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El nombre no puede estar vacío."
            )
        if not re.match(NAME_REGEX, value):
            raise serializers.ValidationError(
                "El nombre solo puede contener letras y un espacio opcional."
            )
        return value

    def validate_apellidojugador(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El apellido no puede estar vacío."
            )
        if not re.match(LASTNAME_REGEX, value):
            raise serializers.ValidationError(
                "El apellido solo puede contener letras y un espacio opcional."
            )
        return value

    def validate_idbanner(self, value):
        if not re.match(ID_BANNER_REGEX, value):
            raise serializers.ValidationError(
                "Debe tener una letra seguida de hasta 8 números. Los números no pueden ser todos ceros (ej: A123)."
            )
        
        # Solo validar duplicados en creación
        if not self.instance:
            if Jugadores.objects.filter(idbanner=value).exists():
                raise serializers.ValidationError(
                    "Ya existe un jugador con ese ID Banner."
                )
        return value

    def validate_numerocamisetajugador(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El número debe ser positivo."
            )
        return value

    def validate_posicionjugador(self, value):
        if value not in POSICIONES_VALIDAS:
            raise serializers.ValidationError(
                "Debe seleccionar una posición válida."
            )
        return value

    def validate(self, attrs):
        # Validar número de camiseta para jugadores activos
        numero = attrs.get('numerocamisetajugador')
        activo = attrs.get('jugadoractivo', True)
        
        if activo and numero:
            query = Jugadores.objects.filter(
                numerocamisetajugador=numero,
                jugadoractivo=True
            )
            
            # Si es actualización, excluir el registro actual
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise serializers.ValidationError(
                    "El número ya está asignado a otro jugador activo."
                )

        return attrs
    
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

class JugadorUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Jugadores
        fields = [
            'nombrejugador',
            'apellidojugador',
            'numerocamisetajugador',
            'imagenjugador',
            'posicionjugador',
            'jugadoractivo',
            'idbanner'
        ]

    def validate_nombrejugador(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El nombre no puede estar vacío."
            )
        return value

    def validate_apellidojugador(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El apellido no puede estar vacío."
            )
        return value

    def validate_idbanner(self, value):
        if not re.match(ID_BANNER_REGEX, value):
            raise serializers.ValidationError(
                "Debe tener una letra seguida de hasta 8 números. Los números no pueden ser todos ceros (ej: A123)."
            )
        
        if self.instance:
            if Jugadores.objects.exclude(
                pk=self.instance.pk
            ).filter(idbanner=value).exists():
                raise serializers.ValidationError(
                    "Ya existe otro jugador con este ID Banner."
                )
        return value

    def validate_numerocamisetajugador(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El número de camiseta debe ser positivo."
            )
        return value

    def validate_posicionjugador(self, value):
        if value not in POSICIONES_VALIDAS:
            raise serializers.ValidationError(
                "Debe seleccionar una posición válida."
            )
        return value

    def validate_jugadoractivo(self, value):
        if not isinstance(value, bool):
            raise serializers.ValidationError(
                "Debe ser un valor booleano."
            )
        return value

    def validate(self, attrs):
        if not self.instance:
            raise serializers.ValidationError(
                "La instancia del jugador no está disponible para la validación."
            )

        numero = attrs.get(
            'numerocamisetajugador',
            self.instance.numerocamisetajugador
        )
        activo = attrs.get(
            'jugadoractivo',
            self.instance.jugadoractivo
        )

        if activo and numero > 0:
            if Jugadores.objects.exclude(
                pk=self.instance.pk
            ).filter(
                numerocamisetajugador=numero,
                jugadoractivo=True
            ).exists():
                raise serializers.ValidationError(
                    "El número de camiseta ya está asignado a otro jugador activo."
                )

        return attrs

    def to_internal_value(self, data):
        internal = super().to_internal_value(data)
        imagen = data.get('imagenjugador')

        if isinstance(imagen, str) and imagen.startswith("data:image"):
            try:
                _, base64_data = imagen.split(',', 1)
                internal['imagenjugador'] = base64.b64decode(base64_data)
            except Exception:
                raise serializers.ValidationError(
                    "Formato Base64 inválido."
                )
        elif imagen in ("", None):
            internal['imagenjugador'] = None

        return internal
