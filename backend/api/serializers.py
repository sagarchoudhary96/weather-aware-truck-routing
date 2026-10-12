from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from planner.domain.geometry import straight_line_distance_m

MAX_DEPARTURE_AHEAD = timedelta(days=7)  # keeps the whole trip inside the forecast range
DEPARTURE_GRACE = timedelta(hours=1)
MAX_LOAD_LB = 80_000  # US federal gross weight limit, no load can exceed it


def validate_departure(value):
    now = timezone.now()
    if value < now - DEPARTURE_GRACE:
        raise serializers.ValidationError("Departure cannot be in the past.")
    if value > now + MAX_DEPARTURE_AHEAD:
        raise serializers.ValidationError("Departure must be within the next 7 days (forecast range).")
    return value


class PointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class PlanRequestSerializer(serializers.Serializer):
    origin = PointSerializer()
    destination = PointSerializer()
    departure = serializers.DateTimeField(validators=[validate_departure])
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)
    apply_hos = serializers.BooleanField(default=True)

    def validate(self, data):
        o, d = data["origin"], data["destination"]
        if straight_line_distance_m((o["lat"], o["lon"]), (d["lat"], d["lon"])) < 1000:
            raise serializers.ValidationError("Origin and destination are the same place.")
        return data


class HeatmapRequestSerializer(serializers.Serializer):
    # Each route as [[lon, lat], ...], as returned in the plan response.
    routes = serializers.ListField(
        child=serializers.ListField(
            child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
            min_length=2,
            max_length=20_000,
        ),
        min_length=1,
        max_length=3,
    )
    departure = serializers.DateTimeField(validators=[validate_departure])
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
