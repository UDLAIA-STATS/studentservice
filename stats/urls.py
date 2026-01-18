from django.urls import path
from stats.views import (
    PlayerStatsBulkCreateView,
    PlayerStatsListView,
    PlayerStatsDetailView,
    PlayerStatsPartialUpdateView
)

app_name = 'stats'

urlpatterns = [
    path('events/bulk/',   PlayerStatsBulkCreateView.as_view(),  name='event-bulk'),
    path('consolidated/', PlayerStatsListView.as_view(), name='consolidated-list'),
    path('consolidated/<pk>/', PlayerStatsDetailView.as_view(), name='consolidated-detail'),
    path('consolidated/<pk>/', PlayerStatsPartialUpdateView.as_view(),  name='consolidated-patch'),
]