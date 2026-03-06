"""
Weather Manager - Responsible for managing weather lookups via the Open-Meteo API.
"""

from typing import Optional, Tuple

import aiohttp

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherManager:
    """
    Weather Manager - Handles geocoding and weather data retrieval from Open-Meteo.
    Uses US-friendly units (Fahrenheit, mph) by default.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Ensures the aiohttp session is open."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def cleanup(self):
        """Closes the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------

    async def geocode_city(
        self, city: str
    ) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]]:
        """Resolve a city name to latitude, longitude, display name, country, and state.

        Args:
            city: City name to look up.

        Returns:
            Tuple of (latitude, longitude, resolved_name, country, admin1/state).
            All values are None when the city cannot be found.
        """
        await self._ensure_session()

        params = {"name": city, "count": 1, "language": "en", "format": "json"}

        try:
            async with self._session.get(GEOCODING_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Geocoding API returned status {resp.status}")
                    return None, None, None, None, None

                data = await resp.json()
                results = data.get("results")
                if not results:
                    return None, None, None, None, None

                loc = results[0]
                return (
                    loc.get("latitude"),
                    loc.get("longitude"),
                    loc.get("name"),
                    loc.get("country"),
                    loc.get("admin1"),  # state / province
                )
        except Exception as e:
            logger.error(f"Geocoding request failed: {e}")
            return None, None, None, None, None

    # ------------------------------------------------------------------
    # Current weather
    # ------------------------------------------------------------------

    async def fetch_current_weather(self, lat: float, lon: float) -> Optional[dict]:
        """Fetch current weather for a coordinate pair.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dictionary of current weather values, or None on failure.
        """
        await self._ensure_session()

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m,relative_humidity_2m,weather_code",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
        }

        try:
            async with self._session.get(FORECAST_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Weather API returned status {resp.status}")
                    return None
                data = await resp.json()
                return data.get("current")
        except Exception as e:
            logger.error(f"Current weather request failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------

    async def fetch_forecast(self, lat: float, lon: float, days: int = 7) -> Optional[dict]:
        """Fetch a multi-day forecast for a coordinate pair.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of forecast days (1-16)

        Returns:
            Dictionary of daily forecast arrays, or None on failure.
        """
        await self._ensure_session()

        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "forecast_days": days,
        }

        try:
            async with self._session.get(FORECAST_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Forecast API returned status {resp.status}")
                    return None
                data = await resp.json()
                return data.get("daily")
        except Exception as e:
            logger.error(f"Forecast request failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Tool registration (MCP pattern)
    # ------------------------------------------------------------------

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initializes and registers all weather tools with the MCP server.
        """
        from .tools import get_current_weather, get_weather_forecast

        # Current weather tool
        current_weather_props = PropertyList(
            [
                Property("city", PropertyType.STRING),
            ]
        )
        add_tool(
            (
                "self.weather.get_current_weather",
                "Get the current weather conditions for a city.\n"
                "Use this tool when the user wants to:\n"
                "1. Know the current temperature in a city\n"
                "2. Check wind speed or humidity right now\n"
                "3. See what the weather is like outside\n"
                "4. Get a quick weather snapshot for any US or world city\n"
                "\nFeatures:\n"
                "- Resolves city names to coordinates automatically\n"
                "- Returns temperature in Fahrenheit, wind speed in mph\n"
                "- Provides human-readable weather condition descriptions\n"
                "- Uses the free Open-Meteo API (no API key required)\n"
                "\nArgs:\n"
                "  city: Name of the city (required, e.g. 'New York', 'San Francisco')",
                current_weather_props,
                get_current_weather,
            )
        )

        # Weather forecast tool
        forecast_props = PropertyList(
            [
                Property("city", PropertyType.STRING),
                Property("days", PropertyType.INTEGER, default_value=7),
            ]
        )
        add_tool(
            (
                "self.weather.get_forecast",
                "Get a multi-day weather forecast for a city.\n"
                "Use this tool when the user wants to:\n"
                "1. Plan ahead based on upcoming weather\n"
                "2. Know if it will rain or snow this week\n"
                "3. See high and low temperatures for the coming days\n"
                "4. Get a weekly weather outlook for any US or world city\n"
                "\nFeatures:\n"
                "- Up to 16-day forecast\n"
                "- Daily high/low temperatures in Fahrenheit\n"
                "- Precipitation amounts converted to inches\n"
                "- Human-readable weather condition per day\n"
                "- Uses the free Open-Meteo API (no API key required)\n"
                "\nArgs:\n"
                "  city: Name of the city (required, e.g. 'Chicago', 'Miami')\n"
                "  days: Number of forecast days (default: 7, max: 16)",
                forecast_props,
                get_weather_forecast,
            )
        )


# Global manager instance
_weather_manager = None


def get_weather_manager() -> WeatherManager:
    """
    Gets the singleton instance of the weather manager.
    """
    global _weather_manager
    if _weather_manager is None:
        _weather_manager = WeatherManager()
    return _weather_manager


async def cleanup_weather_manager():
    """
    Cleans up the weather manager resources.
    """
    global _weather_manager
    if _weather_manager:
        await _weather_manager.cleanup()
        _weather_manager = None
