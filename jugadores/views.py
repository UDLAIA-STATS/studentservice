from django.shortcuts import render

# Create your views here.
# ============================================
# Función auxiliar de paginación
# ============================================
def paginate_queryset(queryset, serializer_class, request):
    """Aplica paginación con parámetros opcionales: ?page=N&offset=M"""
    try:
        page = int(request.query_params.get("page", 1))
        offset = int(request.query_params.get("offset", 10))
    except ValueError:
        return {"error": "Los parámetros 'page' y 'offset' deben ser números enteros."}

    total = queryset.count()
    start = (page - 1) * offset
    end = start + offset
    paginated = queryset[start:end]

    serializer = serializer_class(paginated, many=True)
    return {
        "count": total,
        "page": page,
        "offset": offset,
        "pages": ceil(total / offset) if offset else 1,
        "results": serializer.data,
    }

# ===========================================
# JUGADORES VIEWS
# ===========================================

@api_view(['GET'])
def jugadores_list(request):
    jugadores = Jugadores.objects.all()
    serializer = JugadoresSerializer(jugadores, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def jugadores_detail(request, idJugador):
    jugador = Jugadores.objects.get(idJugador=idJugador)
    serializer = JugadoresSerializer(jugador)
    return Response(serializer.data)

@api_view(['POST'])
def jugadores_create(request):
    serializer = JugadoresSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT', 'PATCH'])
def jugadores_update(request, idJugador):
    jugador = Jugadores.objects.get(idJugador=idJugador)
    serializer = JugadoresSerializer(jugador, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def jugadores_delete(request, idJugador):
    jugador = Jugadores.objects.get(idJugador=idJugador)
    jugador.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)