from math import ceil
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import status

from .models import Jugadores
from .serializers import JugadorSerializer
from jugadores.utils import (
    pagination_response,
    error_response,
    success_response,
    format_serializer_errors)


# ============================================
# Función auxiliar de paginación
# ============================================
def paginate_queryset(queryset, serializer_class, request):
    """
    Pagina un queryset utilizando los parámetros 'page' y 'offset' de la request.

    Parámetros:
        queryset (QuerySet): El queryset a paginar
        serializer_class (serializers.ModelSerializer): La clase de serializer a utilizar para serializar los objetos
        request (Request): La request que contiene los parámetros 'page' y 'offset'

    Retorna:
        Response: La respuesta HTTP con la lista de objetos paginada
    """
    try:
        page = int(request.query_params.get("page", 1))
        offset = int(request.query_params.get("offset", 10))
        if page <= 0 or offset <= 0:
            raise ValueError
    except ValueError:
        return error_response("Los parámetros 'page' y 'offset' deben ser enteros positivos.", None, status.HTTP_400_BAD_REQUEST)

    total = queryset.count()
    start = (page - 1) * offset
    end = start + offset
    paginated = queryset[start:end]

    serializer = serializer_class(paginated, many=True)
    return pagination_response(
        data=serializer.data,
        offset=offset,
        page=page,
        pages= ceil(total / offset) if offset else 1,
        status=status.HTTP_200_OK,
        total_items=total
    ) 

# ============================================
# VIEWS DE JUGADORES (solo JSON)
# ============================================

class JugadorAllView(APIView):
    """Lista todos los jugadores con paginación (modo JSON)."""

    def get(self, request):
        """
        Obtiene la lista de todos los jugadores con paginación (modo JSON).

        Parámetros:
            page (int): La página a obtener (opcional, default=1)
            offset (int): La cantidad de elementos a obtener por página (opcional, default=10)

        Retorna:
            Response: La respuesta HTTP con la lista de jugadores paginada
        """
        try:
            jugadores = Jugadores.objects.all().order_by("idjugador")
            paginated_data = paginate_queryset(jugadores, JugadorSerializer, request)
            return paginated_data
        except Exception as err:
            return error_response("No se pudo obtener los jugadores", err, status.HTTP_400_BAD_REQUEST)
            

class JugadorListCreateView(APIView):
    """Crea un jugador."""

    def post(self, request):
        """
        Crea un usuario.

        Args:
            request (Request): La petición HTTP

        Returns:
            Response: La respuesta HTTP con el resultado de la operación
        """
        
        serializer = JugadorSerializer(data=request.data)
        if not serializer.is_valid():
            errors = format_serializer_errors(serializer.errors)
            raise ValidationError(detail=errors)
        try:
            jugador = serializer.save()
            jugador_data = JugadorSerializer(jugador).data
            return success_response("Jugador creado correctamente", jugador_data, status.HTTP_201_CREATED)
        except IntegrityError:
            return error_response("Ya existe un jugador con los mismos datos.", None, status.HTTP_400_BAD_REQUEST)
        except ValidationError as ve:
            return error_response("Error de validación al crear el jugador.", ve.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            return error_response("No se pudo crear el jugador.", str(err), status.HTTP_400_BAD_REQUEST)


class JugadorDetailView(APIView):
    """Obtiene el detalle de un jugador por su ID."""

    def get(self, request, banner):
        """
        Obtiene el detalle de un usuario por su ID.

        Args:
            request (Request): La petición HTTP
            banner (str): La ID del usuario a obtener

        Returns:
            Response: La respuesta HTTP con el resultado de la operación
        """
        jugador = get_object_or_404(Jugadores, idbanner=banner)
        return success_response("Jugador obtenido correctamente", JugadorSerializer(jugador).data, status.HTTP_200_OK)

class JugadorDetailViewById(APIView):
    """Obtiene el detalle de un jugador por su ID."""

    def get(self, request, pk):
        """
        Obtiene el detalle de un usuario por su ID.

        Args:
            request (Request): La petición HTTP
            pk (int): La ID del usuario a obtener

        Returns:
            Response: La respuesta HTTP con el resultado de la operación
        """
        jugador = get_object_or_404(Jugadores, idjugador=pk)
        return success_response("Jugador obtenido correctamente", JugadorSerializer(jugador).data, status.HTTP_200_OK)



class JugadorUpdateView(APIView):
    """Actualiza parcialmente los datos de un jugador."""

    def patch(self, request, pk):
        """
        Actualiza parcialmente los datos de un usuario.

        Args:
            request (Request): La petición HTTP
            pk (int): La ID del usuario a actualizar

        Returns:
            Response: La respuesta HTTP con el resultado de la operación
        """
        try:
            jugador = get_object_or_404(Jugadores, pk=pk)
            serializer = JugadorSerializer(jugador, data=request.data, partial=True, context={'request': request})
            if not serializer.is_valid():
                errors = format_serializer_errors(serializer.errors)
                raise ValidationError(detail=errors)
            jugador_actualizado = serializer.save()
            return success_response("Jugador actualizado correctamente", JugadorSerializer(jugador_actualizado).data, status.HTTP_200_OK)
        except IntegrityError:
            return error_response("Ya existe un jugador con los mismos datos.", None, status.HTTP_400_BAD_REQUEST)
        except ValidationError as ve:
            return error_response("Error de validación al actualizar el jugador.", ve.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            return error_response("No se pudo actualizar el jugador.", str(err), status.HTTP_400_BAD_REQUEST)


class JugadorDeleteView(APIView):
    """
    Desactiva (soft delete) un jugador por su ID Banner.
    """

    def delete(self, request, banner):
        """
        Desactiva un jugador del sistema utilizando su ID Banner.

        - No elimina el registro de la base de datos.
        - Solo marca el jugador como inactivo.

        **Respuesta exitosa**
        - Código: 200
        - Mensaje: "Jugador desactivado correctamente"
        """
        try:
            jugador = get_object_or_404(Jugadores, idbanner=banner)

            if not jugador.jugadoractivo:
                return success_response(
                    "El jugador ya se encuentra desactivado.",
                    None,
                    status.HTTP_200_OK
                )

            jugador.jugadoractivo = False
            jugador.save(update_fields=["jugadoractivo"])

            return success_response(
                "Jugador desactivado correctamente.",
                None,
                status.HTTP_200_OK
            )

        except Exception as err:
            return error_response(
                "No se pudo desactivar el jugador.",
                str(err),
                status.HTTP_400_BAD_REQUEST
            )