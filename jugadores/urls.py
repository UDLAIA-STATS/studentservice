from django.urls import path
from jugadores.views import (
    JugadorDetailViewByShirtNumber,
    JugadorListCreateView,
    JugadorDetailViewByBanner,
    JugadorAllView,
    JugadorUpdateView,
    JugadorDeleteView,
    JugadorDetailViewById,
)

urlpatterns = [
    path("jugadores/", JugadorListCreateView.as_view(), name="jugador-list-create"),
    path("jugadores/all/", JugadorAllView.as_view(), name="jugador-all"),
    path(
        "jugadores/<str:banner>/",
        JugadorDetailViewByBanner.as_view(),
        name="jugador-detail",
    ),
    path(
        "jugadores/id/<int:pk>/",
        JugadorDetailViewById.as_view(),
        name="jugador-detail-id",
    ),
    path(
        "jugadores/shirt/<int:numero_camiseta>/",
        JugadorDetailViewByShirtNumber.as_view(),
        name="jugador-detail-shirt-number",
    ),
    path(
        "jugadores/<int:pk>/update/", JugadorUpdateView.as_view(), name="jugador-update"
    ),
    path(
        "jugadores/<str:banner>/delete/",
        JugadorDeleteView.as_view(),
        name="jugador-delete",
    ),
]
