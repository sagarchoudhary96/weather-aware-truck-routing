import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from planner import providers
from planner.providers.errors import NoRouteError, ProviderError
from planner.service import TripRequest, build_risk_heatmap, plan_trip

from .presenters import heatmap_to_json, plan_to_json
from .serializers import HeatmapRequestSerializer, PlanRequestSerializer

log = logging.getLogger(__name__)

PLACES_CACHE_SECONDS = 24 * 3600


def _provider_error(exc: ProviderError) -> Response:
    code = status.HTTP_422_UNPROCESSABLE_ENTITY if isinstance(exc, NoRouteError) else status.HTTP_502_BAD_GATEWAY
    return Response({"detail": str(exc)}, status=code)


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class PlacesView(APIView):
    """Address autocomplete: GET /api/places/?q=chicago"""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 3:
            return Response([])
        key = f"places:{query.lower()}"
        if (cached := cache.get(key)) is not None:
            return Response(cached)
        try:
            places = [{"label": p.label, "lat": p.lat, "lon": p.lon} for p in providers.routing_client().search_places(query)]
        except ProviderError as exc:
            return _provider_error(exc)
        cache.set(key, places, PLACES_CACHE_SECONDS)
        return Response(places)


class PlanView(APIView):
    def post(self, request):
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        trip = TripRequest(
            origin=(data["origin"]["lat"], data["origin"]["lon"]),
            destination=(data["destination"]["lat"], data["destination"]["lon"]),
            departure=data["departure"],
            load_lb=data["load_lb"],
            interval_mi=data["interval_mi"],
            apply_hos=data["apply_hos"],
        )
        try:
            plan = plan_trip(trip, providers.routing_client(), providers.weather_client())
        except ProviderError as exc:
            return _provider_error(exc)
        return Response(plan_to_json(plan))


class HeatmapView(APIView):
    def post(self, request):
        serializer = HeatmapRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        lines = [[(lat, lon) for lon, lat in route] for route in data["routes"]]
        checkpoints = [(lat, lon) for lon, lat in data["checkpoints"]]
        try:
            heatmap = build_risk_heatmap(lines, data["departure"], data["load_lb"], providers.weather_client(), checkpoints)
        except ProviderError as exc:
            return _provider_error(exc)
        return Response(heatmap_to_json(heatmap))
