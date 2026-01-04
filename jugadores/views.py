from math import ceil
from django.db import IntegrityError
from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Jugadores
from .serializers import JugadorSerializer
from utils import (
    pagination_response,
    error_response,
    success_response,
    format_serializer_errors)


# ============================================
# Función auxiliar de paginación
# ============================================
def paginate_queryset(queryset, serializer_class, request):
    """Aplica paginación con parámetros opcionales: ?page=N&offset=M"""
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
        try:
            jugadores = Jugadores.objects.all().order_by("idjugador")
            paginated_data = paginate_queryset(jugadores, JugadorSerializer, request)
            return paginated_data
        except Exception as err:
            return error_response("No se pudo obtener los jugadores", err, status.HTTP_400_BAD_REQUEST)
            

class JugadorListCreateView(APIView):
    """Crea un jugador."""

    def post(self, request):
        serializer = JugadorSerializer(data=request.data)
        if not serializer.is_valid():
            errors = format_serializer_errors(serializer.errors)
            raise ValidationError(message=errors)
        try:
            jugador = serializer.save()
            jugador_data = JugadorSerializer(jugador).data
            return success_response("Jugador creado correctamente", jugador_data, status.HTTP_201_CREATED)
        except IntegrityError:
            return error_response("Ya existe un jugador con los mismos datos.", None, status.HTTP_400_BAD_REQUEST)


class JugadorDetailView(APIView):
    """Obtiene el detalle de un jugador por su ID."""

    def get(self, request, banner):
        jugador = get_object_or_404(Jugadores, idbanner=banner)
        return Response(JugadorSerializer(jugador).data, status=status.HTTP_200_OK)


class JugadorDetailViewById(APIView):
    """Obtiene el detalle de un jugador por su ID."""

    def get(self, request, pk):
        jugador = get_object_or_404(Jugadores, idjugador=pk)
        return Response(JugadorSerializer(jugador).data, status=status.HTTP_200_OK)



class JugadorUpdateView(APIView):
    """Actualiza parcialmente los datos de un jugador."""

    def patch(self, request, pk):
        jugador = get_object_or_404(Jugadores, pk=pk)
        serializer = JugadorSerializer(jugador, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            jugador_actualizado = serializer.save()
            return Response({
                "mensaje": "Jugador actualizado correctamente",
                "jugador": JugadorSerializer(jugador_actualizado).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JugadorDeleteView(APIView):
    """Elimina un jugador por su ID."""

    def delete(self, request, banner):
        jugador = get_object_or_404(Jugadores, idbanner=banner)
        jugador.delete()
        return Response({"mensaje": "Jugador eliminado correctamente"}, status=status.HTTP_200_OK)
