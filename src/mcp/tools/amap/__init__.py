"""Amap MCP tool module.

Provides a set of MCP tools for Amap API functions, including geocoding, route planning, POI search, weather query, etc.
"""

from .manager import get_amap_manager

__all__ = ["get_amap_manager"]