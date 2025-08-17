"""Amap Tools Manager.

Responsible for the initialization, configuration, and MCP tool registration of Amap tools
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .tools import (
    maps_around_search,
    maps_direction_driving,
    maps_direction_walking,
    maps_distance,
    maps_geo,
    maps_ip_location,
    maps_regeocode,
    maps_search_detail,
    maps_text_search,
    maps_weather,
)

logger = get_logger(__name__)


class AmapToolsManager:
    """
    Amap Tools Manager.
    """

    def __init__(self):
        """
        Initialize the Amap Tools Manager.
        """
        self._initialized = False
        logger.info("[AmapManager] Amap Tools Manager initialized")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initialize and register all Amap tools.
        """
        try:
            logger.info("[AmapManager] Starting to register Amap tools")

            # Register regeocode tool
            self._register_regeocode_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register geocode tool
            self._register_geo_tool(add_tool, PropertyList, Property, PropertyType)

            # Register IP location tool
            self._register_ip_location_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register weather query tool
            self._register_weather_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register walking navigation tool
            self._register_walking_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register driving navigation tool
            self._register_driving_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register text search tool
            self._register_text_search_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register around search tool
            self._register_around_search_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register POI detail tool
            self._register_search_detail_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register distance tool
            self._register_distance_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            self._initialized = True
            logger.info("[AmapManager] Amap tools registration complete")

        except Exception as e:
            logger.error(f"[AmapManager] Failed to register Amap tools: {e}", exc_info=True)
            raise

    def _register_regeocode_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register regeocode tool.
        """
        props = PropertyList(
            [
                Property(
                    "location",
                    PropertyType.STRING,
                ),
            ]
        )

        add_tool(
            (
                "amap.regeocode",
                "Converts longitude and latitude coordinates to detailed address information. Input longitude and latitude coordinates (format: longitude,latitude), "
                "and it returns corresponding address information such as province, city, and district. Suitable for scenarios like: finding an address from known coordinates, reverse location lookup, and coordinate parsing."
                "Convert longitude and latitude coordinates to detailed address information.",
                props,
                maps_regeocode,
            )
        )
        logger.debug("[AmapManager] Successfully registered regeocode tool")

    def _register_geo_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register geocode tool.
        """
        props = PropertyList(
            [
                Property(
                    "address",
                    PropertyType.STRING,
                ),
                Property(
                    "city",
                    PropertyType.STRING,
                    default_value="",
                ),
            ]
        )

        add_tool(
            (
                "amap.geo",
                "Converts a detailed address into longitude and latitude coordinates. Supports parsing landmarks and building names into coordinates. "
                "Input address information, optionally specify a city, and it returns the corresponding longitude and latitude coordinates. "
                "Suitable for scenarios like: finding coordinates from an address, setting navigation start and end points, and location calibration."
                "Convert detailed address to longitude and latitude coordinates.",
                props,
                maps_geo,
            )
        )
        logger.debug("[AmapManager] Successfully registered geocode tool")

    def _register_ip_location_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register IP location tool.
        """
        props = PropertyList(
            [
                Property(
                    "ip",
                    PropertyType.STRING,
                ),
            ]
        )

        add_tool(
            (
                "amap.ip_location",
                "Gets location information based on an IP address. Input an IP address, and it returns the corresponding province and city information. "
                "Suitable for scenarios like: IP geolocation query, network location analysis, and geographical location statistics."
                "Get location information based on IP address.",
                props,
                maps_ip_location,
            )
        )
        logger.debug("[AmapManager] Successfully registered IP location tool")

    def _register_weather_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register weather query tool.
        """
        props = PropertyList(
            [
                Property(
                    "city",
                    PropertyType.STRING,
                ),
            ]
        )

        add_tool(
            (
                "amap.weather",
                "Queries weather information for a specified city. Input a city name or adcode, and it returns detailed weather forecast information. "
                "Suitable for scenarios like: weather queries, travel planning, and weather forecasting."
                "Query weather information for specified city.",
                props,
                maps_weather,
            )
        )
        logger.debug("[AmapManager] Successfully registered weather query tool")

    def _register_walking_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register walking navigation tool.
        """
        props = PropertyList(
            [
                Property(
                    "origin",
                    PropertyType.STRING,
                ),
                Property(
                    "destination",
                    PropertyType.STRING,
                ),
            ]
        )

        add_tool(
            (
                "amap.direction_walking",
                "Plans walking routes. Input the longitude and latitude coordinates of the start and end points, and it returns a detailed walking navigation plan. "
                "Supports walking route planning within 100km, including information on distance, time, and detailed steps. "
                "Suitable for scenarios like: walking navigation, route planning, and travel plans."
                "Plan walking routes with detailed navigation information.",
                props,
                maps_direction_walking,
            )
        )
        logger.debug("[AmapManager] Successfully registered walking navigation tool")

    def _register_driving_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register driving navigation tool.
        """
        props = PropertyList(
            [
                Property(
                    "origin",
                    PropertyType.STRING,
                ),
                Property(
                    "destination",
                    PropertyType.STRING,
                ),
            ]
        )

        add_tool(
            (
                "amap.direction_driving",
                "Plans driving routes. Input the longitude and latitude coordinates of the start and end points, and it returns a detailed driving navigation plan. "
                "Includes information on distance, time, tolls, and detailed steps. Suitable for scenarios like: driving navigation, route planning, and travel plans."
                "Plan driving routes with detailed navigation information.",
                props,
                maps_direction_driving,
            )
        )
        logger.debug("[AmapManager] Successfully registered driving navigation tool")

    def _register_text_search_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register text search tool.
        """
        props = PropertyList(
            [
                Property(
                    "keywords",
                    PropertyType.STRING,
                ),
                Property(
                    "city",
                    PropertyType.STRING,
                    default_value="",
                ),
                Property(
                    "types",
                    PropertyType.STRING,
                    default_value="",
                ),
            ]
        )

        add_tool(
            (
                "amap.text_search",
                "Searches for POIs by keyword. Input search keywords, and you can specify the city and POI type, "
                "and it returns a list of relevant location information. Suitable for scenarios like: location search, business lookup, and facility query."
                "Search POI by keywords with optional city and type filters.",
                props,
                maps_text_search,
            )
        )
        logger.debug("[AmapManager] Successfully registered text search tool")

    def _register_around_search_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register around search tool.
        """
        props = PropertyList(
            [
                Property(
                    "location",
                    PropertyType.STRING,
                ),
                Property(
                    "keywords",
                    PropertyType.STRING,
                    default_value="",
                ),
                Property(
                    "radius",
                    PropertyType.STRING,
                    default_value="1000",
                ),
            ]
        )

        add_tool(
            (
                "amap.around_search",
                "Searches for nearby POIs by coordinates. Input the center point coordinates, and you can specify search keywords and radius, "
                "and it returns a list of nearby location information. Suitable for scenarios like: nearby search, finding surrounding places, and querying nearby facilities."
                "Search nearby POI around given coordinates.",
                props,
                maps_around_search,
            )
        )
        logger.debug("[AmapManager] Successfully registered around search tool")

    def _register_search_detail_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register POI detail tool.
        """
        props = PropertyList(
            [
                Property(
                    "id",
                    PropertyType.STRING,
                ),
            ]
        )

        add_tool(
            (
                "amap.search_detail",
                "Queries for detailed information about a POI. Input the POI's ID (obtained through a search), "
                "and it returns detailed location information, including contact information, business hours, ratings, etc. "
                "Suitable for scenarios like: location detail query, obtaining business information, and viewing detailed information."
                "Get detailed information of POI by ID.",
                props,
                maps_search_detail,
            )
        )
        logger.debug("[AmapManager] Successfully registered POI detail tool")

    def _register_distance_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register distance tool.
        """
        props = PropertyList(
            [
                Property(
                    "origins",
                    PropertyType.STRING,
                ),
                Property(
                    "destination",
                    PropertyType.STRING,
                ),
                Property(
                    "type",
                    PropertyType.STRING,
                    default_value="1",
                ),
            ]
        )

        add_tool(
            (
                "amap.distance",
                "Measures the distance between two points. Input the coordinates of the start and end points, and you can choose the measurement type "
                "(1: driving distance, 0: straight-line distance, 3: walking distance), and it returns distance and time information. "
                "Suitable for scenarios like: distance calculation, route estimation, and time estimation."
                "Measure distance between coordinates with different travel modes.",
                props,
                maps_distance,
            )
        )
        logger.debug("[AmapManager] Successfully registered distance tool")

    def is_initialized(self) -> bool:
        """
        Check if the manager is initialized.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Get the manager's status.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 10,  # Number of currently registered tools
            "available_tools": [
                "regeocode",
                "geo",
                "ip_location",
                "weather",
                "direction_walking",
                "direction_driving",
                "text_search",
                "around_search",
                "search_detail",
                "distance",
            ],
        }


# Global manager instance
_amap_tools_manager = None


def get_amap_manager() -> AmapToolsManager:
    """
    Get the Amap Tools Manager singleton.
    """
    global _amap_tools_manager
    if _amap_tools_manager is None:
        _amap_tools_manager = AmapToolsManager()
        logger.debug("[AmapManager] Created Amap Tools Manager instance")
    return _amap_tools_manager