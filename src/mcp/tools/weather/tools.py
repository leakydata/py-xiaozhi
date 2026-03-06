"""
Weather MCP tool functions - asynchronous tool functions provided for MCP server calls.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .manager import get_weather_manager

logger = get_logger(__name__)

# WMO Weather Interpretation Codes (WW)
# https://www.noaa.gov/weather
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _describe_weather_code(code: int) -> str:
    """Convert a WMO weather code to a human-readable description."""
    return WMO_WEATHER_CODES.get(code, f"Unknown (code {code})")


async def get_current_weather(args: Dict[str, Any]) -> str:
    """Get the current weather for a given city.

    Args:
        args: A dictionary containing weather parameters
            - city: City name (required)

    Returns:
        Current weather data in JSON format
    """
    try:
        city = args.get("city")
        if not city:
            return json.dumps(
                {"success": False, "message": "City name cannot be empty"},
                ensure_ascii=False,
            )

        manager = get_weather_manager()
        lat, lon, resolved_name, country, state = await manager.geocode_city(city)

        if lat is None:
            return json.dumps(
                {"success": False, "message": f"Could not find location: {city}"},
                ensure_ascii=False,
            )

        current = await manager.fetch_current_weather(lat, lon)

        if current is None:
            return json.dumps(
                {"success": False, "message": f"Could not retrieve weather for {city}"},
                ensure_ascii=False,
            )

        weather_code = current.get("weather_code", -1)
        location_parts = [resolved_name]
        if state:
            location_parts.append(state)
        if country:
            location_parts.append(country)

        result = {
            "success": True,
            "location": ", ".join(location_parts),
            "coordinates": {"latitude": lat, "longitude": lon},
            "current": {
                "temperature_f": current.get("temperature_2m"),
                "wind_speed_mph": current.get("wind_speed_10m"),
                "relative_humidity_pct": current.get("relative_humidity_2m"),
                "weather_code": weather_code,
                "condition": _describe_weather_code(weather_code),
            },
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to get current weather: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get current weather: {str(e)}"},
            ensure_ascii=False,
        )


async def get_weather_forecast(args: Dict[str, Any]) -> str:
    """Get a 7-day weather forecast for a given city.

    Args:
        args: A dictionary containing forecast parameters
            - city: City name (required)
            - days: Number of forecast days (default: 7, max: 16)

    Returns:
        Forecast data in JSON format
    """
    try:
        city = args.get("city")
        if not city:
            return json.dumps(
                {"success": False, "message": "City name cannot be empty"},
                ensure_ascii=False,
            )

        days = args.get("days", 7)
        if days < 1:
            days = 1
        elif days > 16:
            days = 16

        manager = get_weather_manager()
        lat, lon, resolved_name, country, state = await manager.geocode_city(city)

        if lat is None:
            return json.dumps(
                {"success": False, "message": f"Could not find location: {city}"},
                ensure_ascii=False,
            )

        daily = await manager.fetch_forecast(lat, lon, days)

        if daily is None:
            return json.dumps(
                {"success": False, "message": f"Could not retrieve forecast for {city}"},
                ensure_ascii=False,
            )

        location_parts = [resolved_name]
        if state:
            location_parts.append(state)
        if country:
            location_parts.append(country)

        forecast_days = []
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        precip = daily.get("precipitation_sum", [])

        for i in range(len(dates)):
            code = codes[i] if i < len(codes) else -1
            forecast_days.append(
                {
                    "date": dates[i],
                    "high_f": highs[i] if i < len(highs) else None,
                    "low_f": lows[i] if i < len(lows) else None,
                    "weather_code": code,
                    "condition": _describe_weather_code(code),
                    "precipitation_inches": (
                        round(precip[i] / 25.4, 2) if i < len(precip) and precip[i] is not None else 0.0
                    ),
                }
            )

        result = {
            "success": True,
            "location": ", ".join(location_parts),
            "coordinates": {"latitude": lat, "longitude": lon},
            "forecast_days": len(forecast_days),
            "daily": forecast_days,
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to get weather forecast: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get weather forecast: {str(e)}"},
            ensure_ascii=False,
        )
