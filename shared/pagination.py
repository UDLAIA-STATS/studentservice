from math import ceil
from rest_framework import status

from shared import error_response, pagination_response


def paginate_queryset(queryset, serializer_class, request):
    """Aplica paginación con parámetros opcionales: ?page=N&offset=M"""
    try:
        page = int(request.query_params.get("page", 1))
        offset = int(request.query_params.get("offset", 10))
    except ValueError:
        return error_response(message="Paginación inválida", data=None, status=status.HTTP_400_BAD_REQUEST)

    total = queryset.count()
    start = (page - 1) * offset
    end = start + offset
    paginated = queryset[start:end]

    serializer = serializer_class(paginated, many=True)
    return pagination_response(
        data=serializer.data,
        page=page,
        offset=offset,
        pages=ceil(total / offset) if offset > 0 else 1,
        total_items=total,
        status=status.HTTP_200_OK
    )
