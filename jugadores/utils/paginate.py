from math import ceil
from rest_framework import status
from jugadores.utils.responses import error_response, pagination_response


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