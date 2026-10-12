from django.urls import path

from .views import HealthView, HeatmapView, PlacesView, PlanView

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("places/", PlacesView.as_view()),
    path("plan/", PlanView.as_view()),
    path("heatmap/", HeatmapView.as_view()),
]
