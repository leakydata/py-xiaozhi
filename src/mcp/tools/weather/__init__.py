"""
Weather tool module - provides current weather and forecast using the Open-Meteo API
"""

from .manager import cleanup_weather_manager, get_weather_manager

__all__ = ["get_weather_manager", "cleanup_weather_manager"]
