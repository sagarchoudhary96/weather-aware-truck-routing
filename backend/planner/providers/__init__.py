from functools import cache

from django.conf import settings

from .open_meteo import OpenMeteoClient
from .tomtom import TomTomClient


@cache
def routing_client() -> TomTomClient:
    return TomTomClient(settings.TOMTOM_API_KEY)


@cache
def weather_client() -> OpenMeteoClient:
    return OpenMeteoClient()
