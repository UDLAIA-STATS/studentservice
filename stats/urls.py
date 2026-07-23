from django.urls import path
from stats.views import (
    PlayerStatsBulkCreateView,
    PlayerStatsListView,
    PlayerStatsDetailView,
    PlayerStatsPartialUpdateView,
    PlayerStatsCorrectionView,
    GeneralStatsView,
    AnalyzedMatchsView,
    PlayerStatsByMatchView,
)

app_name = "stats"

urlpatterns = [
    path("events/bulk/", PlayerStatsBulkCreateView.as_view(), name="event-bulk"),
    path("consolidated/", PlayerStatsListView.as_view(), name="consolidated-list"),
    path(
        "consolidated/<pk>/",
        PlayerStatsDetailView.as_view(),
        name="consolidated-detail",
    ),
    path(
        "consolidated/<pk>/",
        PlayerStatsPartialUpdateView.as_view(),
        name="consolidated-patch",
    ),
    path(
        "consolidated/stat/correction/",
        PlayerStatsCorrectionView.as_view(),
    ),
    path(
        "general-stats/",
        GeneralStatsView.as_view(),
        name="general-stats",
    ),
    path(
        "events/analyzed/matchs/",
        AnalyzedMatchsView.as_view(),
        name="analyzed-matchs",
    ),
    path(
        "events/by-match/<int:match_id>/",
        PlayerStatsByMatchView.as_view(),
        name="player-stats-by-match",
    ),
]
