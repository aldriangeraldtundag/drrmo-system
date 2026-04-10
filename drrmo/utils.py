import json
import urllib.request
from urllib.error import URLError

from django.conf import settings
from django.utils import timezone

from .models import WeatherData

WEATHER_CACHE_MINUTES = 30
SILAY_LATITUDE = 10.70
SILAY_LONGITUDE = 122.95


def fetch_weather_payload():
    url = (
        'https://api.open-meteo.com/v1/forecast?'
        f'latitude={SILAY_LATITUDE}&longitude={SILAY_LONGITUDE}'
        '&current_weather=true'
        '&hourly=precipitation,relativehumidity_2m,windspeed_10m,temperature_2m'
        '&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windgusts_10m_max'
        '&timezone=auto'
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.load(response)
            return payload
    except URLError:
        return None


def get_weather_data():
    refresh_threshold = timezone.now() - timezone.timedelta(minutes=WEATHER_CACHE_MINUTES)
    recent = WeatherData.objects.filter(fetched_at__gte=refresh_threshold).first()
    if recent:
        return recent.payload

    payload = fetch_weather_payload()
    if payload is None:
        if recent:
            return recent.payload
        return {}

    WeatherData.objects.create(payload=payload)
    return payload
