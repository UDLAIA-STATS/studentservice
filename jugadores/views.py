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

