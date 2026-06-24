"""
cit411_utils.weather — Weather-Fetching Helpers
================================================

Retrieve current conditions and multi-day forecasts from the
`Open-Meteo <https://open-meteo.com/>`_ free weather API — **no API key required**.

All network calls are made with ``requests`` and return plain Python dicts so
they are easy to serialize to JSON or hand off to a DataFrame.

Typical usage
-------------
>>> from cit411_utils.weather import get_current_weather, get_forecast
>>> current = get_current_weather(latitude=25.96, longitude=-80.35)
>>> print(current["description"])
Clear sky | 82.4 °F | Wind: 9.2 mph
>>> forecast = get_forecast(latitude=25.96, longitude=-80.35, days=3)
>>> for day in forecast:
...     print(day["date"], day["temp_max_f"], day["weather_desc"])
"""

from __future__ import annotations

import datetime
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL     = "https://api.open-meteo.com/v1/forecast"
_GEOCODE_URL  = "https://geocoding-api.open-meteo.com/v1/search"

# WMO Weather interpretation codes → human description
_WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round(c * 9 / 5 + 32, 1)


def geocode(city_name: str, country_code: str = "") -> dict[str, Any]:
    """
    Resolve a city name to latitude/longitude via Open-Meteo Geocoding API.

    Parameters
    ----------
    city_name:
        City name, e.g. ``"Miami"``.
    country_code:
        Optional ISO-3166 two-letter country code, e.g. ``"US"``.

    Returns
    -------
    dict
        Keys: ``name``, ``latitude``, ``longitude``, ``country``, ``admin1``.

    Raises
    ------
    ValueError
        If no results are found.
    requests.HTTPError
        On non-200 HTTP responses.

    Examples
    --------
    >>> loc = geocode("Pembroke Pines", "US")
    >>> print(loc["latitude"], loc["longitude"])
    """
    params: dict[str, Any] = {"name": city_name, "count": 5, "language": "en", "format": "json"}
    if country_code:
        params["countryCode"] = country_code.upper()

    resp = requests.get(_GEOCODE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if not results:
        raise ValueError(f"No geocoding results for: {city_name!r}")

    r = results[0]
    return {
        "name":      r.get("name", city_name),
        "latitude":  r["latitude"],
        "longitude": r["longitude"],
        "country":   r.get("country", ""),
        "admin1":    r.get("admin1", ""),
    }


def get_current_weather(
    *,
    latitude: float,
    longitude: float,
    temperature_unit: str = "fahrenheit",
    wind_speed_unit: str  = "mph",
) -> dict[str, Any]:
    """
    Fetch current weather conditions for a coordinate pair.

    Parameters
    ----------
    latitude:
        Decimal latitude, e.g. ``25.96``.
    longitude:
        Decimal longitude, e.g. ``-80.35``.
    temperature_unit:
        ``"fahrenheit"`` (default) or ``"celsius"``.
    wind_speed_unit:
        ``"mph"`` (default), ``"kmh"``, ``"ms"``, or ``"kn"``.

    Returns
    -------
    dict
        Keys: ``latitude``, ``longitude``, ``timestamp``, ``temperature``,
        ``temperature_unit``, ``wind_speed``, ``wind_speed_unit``,
        ``weather_code``, ``weather_desc``, ``description``.

    Examples
    --------
    >>> w = get_current_weather(latitude=25.96, longitude=-80.35)
    >>> w["temperature"]
    82.4
    """
    params = {
        "latitude":         latitude,
        "longitude":        longitude,
        "current_weather":  True,
        "temperature_unit": temperature_unit,
        "wind_speed_unit":  wind_speed_unit,
        "timezone":         "auto",
    }

    resp = requests.get(_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    cw   = data["current_weather"]
    code = int(cw.get("weathercode", 0))
    desc = _WMO_CODES.get(code, "Unknown")
    temp = cw["temperature"]
    wind = cw["windspeed"]
    t_sym = "°F" if temperature_unit == "fahrenheit" else "°C"

    return {
        "latitude":         latitude,
        "longitude":        longitude,
        "timestamp":        cw.get("time", ""),
        "temperature":      temp,
        "temperature_unit": t_sym,
        "wind_speed":       wind,
        "wind_speed_unit":  wind_speed_unit,
        "weather_code":     code,
        "weather_desc":     desc,
        "description":      f"{desc} | {temp} {t_sym} | Wind: {wind} {wind_speed_unit}",
    }


def get_forecast(
    *,
    latitude: float,
    longitude: float,
    days: int = 7,
    temperature_unit: str = "fahrenheit",
) -> list[dict[str, Any]]:
    """
    Fetch a daily forecast for up to 16 days.

    Parameters
    ----------
    latitude:
        Decimal latitude.
    longitude:
        Decimal longitude.
    days:
        Number of forecast days (1–16).
    temperature_unit:
        ``"fahrenheit"`` (default) or ``"celsius"``.

    Returns
    -------
    list[dict]
        One dict per day.  Each dict contains: ``date``, ``temp_max``,
        ``temp_min``, ``weather_code``, ``weather_desc``, ``precipitation_mm``,
        ``wind_max``.

    Examples
    --------
    >>> forecast = get_forecast(latitude=25.96, longitude=-80.35, days=3)
    >>> forecast[0]["date"]
    '2026-06-24'
    """
    days = max(1, min(days, 16))

    params = {
        "latitude":         latitude,
        "longitude":        longitude,
        "daily":            [
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max",
        ],
        "temperature_unit": temperature_unit,
        "wind_speed_unit":  "mph",
        "timezone":         "auto",
        "forecast_days":    days,
    }

    resp = requests.get(_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    daily = data.get("daily", {})

    t_sym = "°F" if temperature_unit == "fahrenheit" else "°C"
    result = []

    for i, date in enumerate(daily.get("time", [])):
        code = int(daily["weathercode"][i])
        result.append({
            "date":           date,
            "temp_max":       daily["temperature_2m_max"][i],
            "temp_min":       daily["temperature_2m_min"][i],
            "temperature_unit": t_sym,
            "weather_code":   code,
            "weather_desc":   _WMO_CODES.get(code, "Unknown"),
            "precipitation_mm": daily["precipitation_sum"][i],
            "wind_max_mph":   daily["windspeed_10m_max"][i],
        })

    return result


def weather_report(
    *,
    latitude: float,
    longitude: float,
    location_name: str = "",
    forecast_days: int = 5,
) -> str:
    """
    Return a formatted multi-line weather report string.

    Parameters
    ----------
    latitude:
        Decimal latitude.
    longitude:
        Decimal longitude.
    location_name:
        Human-readable label for the header, e.g. ``"Pembroke Pines, FL"``.
    forecast_days:
        Number of forecast days to include (1–16).

    Returns
    -------
    str
        A printable weather report.
    """
    current  = get_current_weather(latitude=latitude, longitude=longitude)
    forecast = get_forecast(latitude=latitude, longitude=longitude, days=forecast_days)
    label    = location_name or f"{latitude:.2f}, {longitude:.2f}"

    lines = [
        f"{'=' * 50}",
        f"  Weather Report — {label}",
        f"  As of: {current['timestamp']}",
        f"{'=' * 50}",
        f"  Current:  {current['description']}",
        "",
        f"  {forecast_days}-Day Forecast:",
    ]

    for day in forecast:
        lines.append(
            f"    {day['date']}  {day['weather_desc']:<25} "
            f"High {day['temp_max']}{day['temperature_unit']}  "
            f"Low {day['temp_min']}{day['temperature_unit']}  "
            f"Rain {day['precipitation_mm']} mm"
        )

    lines.append("=" * 50)
    return "\n".join(lines)
