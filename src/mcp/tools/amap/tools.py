"""Amap MCP tool functions.

Provides asynchronous tool functions for the MCP server, including geocoding, route planning, search, etc.
"""

import asyncio
import json
import os
from typing import Any, Dict

import aiohttp

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_amap_api_key() -> str:
    """Get Amap API key."""
    # api_key = os.getenv("AMAP_API_KEY")
    # if not api_key:
    #     raise ValueError("AMAP_API_KEY environment variable is not set")
    return ''


async def maps_regeocode(args: Dict[str, Any]) -> str:
    """Convert latitude and longitude coordinates to address information.
    
    Args:
        args: A dictionary containing the following parameters
            - location: Latitude and longitude coordinates (format: longitude,latitude)
            
    Returns:
        str: Address information in JSON format
    """
    try:
        location = args["location"]
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "location": location,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Reverse geocoding failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        result = {
            "success": True,
            "data": {
                "province": data["regeocode"]["addressComponent"]["province"],
                "city": data["regeocode"]["addressComponent"]["city"], 
                "district": data["regeocode"]["addressComponent"]["district"],
                "formatted_address": data["regeocode"]["formatted_address"]
            }
        }
        
        logger.info(f"[AmapTools] Reverse geocoding successful: {location}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Reverse geocoding failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_geo(args: Dict[str, Any]) -> str:
    """Convert address to latitude and longitude coordinates.
    
    Args:
        args: A dictionary containing the following parameters
            - address: The address to be parsed
            - city: Specify the city for the query (optional)
            
    Returns:
        str: Coordinate information in JSON format
    """
    try:
        address = args["address"]
        city = args.get("city", "")
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "address": address,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        if city:
            params["city"] = city
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Geocoding failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        geocodes = data.get("geocodes", [])
        result_data = []
        
        for geo in geocodes:
            result_data.append({
                "country": geo.get("country"),
                "province": geo.get("province"),
                "city": geo.get("city"),
                "citycode": geo.get("citycode"),
                "district": geo.get("district"),
                "street": geo.get("street"),
                "number": geo.get("number"),
                "adcode": geo.get("adcode"),
                "location": geo.get("location"),
                "level": geo.get("level"),
                "formatted_address": geo.get("formatted_address")
            })
            
        result = {
            "success": True,
            "data": result_data
        }
        
        logger.info(f"[AmapTools] Geocoding successful: {address}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Geocoding failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_ip_location(args: Dict[str, Any]) -> str:
    """Get location information based on IP address.
    
    Args:
        args: A dictionary containing the following parameters
            - ip: IP address
            
    Returns:
        str: Location information in JSON format
    """
    try:
        ip = args["ip"]
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/ip"
        params = {
            "ip": ip,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"IP location failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        result = {
            "success": True,
            "data": {
                "province": data.get("province"),
                "city": data.get("city"),
                "adcode": data.get("adcode"),
                "rectangle": data.get("rectangle")
            }
        }
        
        logger.info(f"[AmapTools] IP location successful: {ip}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"IP location failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_weather(args: Dict[str, Any]) -> str:
    """Query city weather information.
    
    Args:
        args: A dictionary containing the following parameters
            - city: City name or adcode
            
    Returns:
        str: Weather information in JSON format
    """
    try:
        city = args["city"]
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "city": city,
            "key": api_key,
            "source": "py_xiaozhi",
            "extensions": "all"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Weather query failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        forecasts = data.get("forecasts", [])
        if not forecasts:
            error_msg = "Weather data not found"
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        forecast = forecasts[0]
        result = {
            "success": True,
            "data": {
                "city": forecast.get("city"),
                "reporttime": forecast.get("reporttime"),
                "casts": forecast.get("casts", [])
            }
        }
        
        logger.info(f"[AmapTools] Weather query successful: {city}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Weather query failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_direction_walking(args: Dict[str, Any]) -> str:
    """Walking route planning.
    
    Args:
        args: A dictionary containing the following parameters
            - origin: Origin coordinates (format: longitude,latitude)
            - destination: Destination coordinates (format: longitude,latitude)
            
    Returns:
        str: Walking route information in JSON format
    """
    try:
        origin = args["origin"]
        destination = args["destination"]
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/direction/walking"
        params = {
            "origin": origin,
            "destination": destination,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Walking route planning failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        route = data.get("route", {})
        paths = route.get("paths", [])
        
        result_paths = []
        for path in paths:
            steps_data = []
            for step in path.get("steps", []):
                steps_data.append({
                    "instruction": step.get("instruction"),
                    "road": step.get("road"),
                    "distance": step.get("distance"),
                    "orientation": step.get("orientation"),
                    "duration": step.get("duration")
                })
                
            result_paths.append({
                "distance": path.get("distance"),
                "duration": path.get("duration"),
                "steps": steps_data
            })
            
        result = {
            "success": True,
            "data": {
                "origin": route.get("origin"),
                "destination": route.get("destination"),
                "paths": result_paths
            }
        }
        
        logger.info(f"[AmapTools] Walking route planning successful: {origin} -> {destination}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Walking route planning failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_direction_driving(args: Dict[str, Any]) -> str:
    """Driving route planning.
    
    Args:
        args: A dictionary containing the following parameters
            - origin: Origin coordinates (format: longitude,latitude)
            - destination: Destination coordinates (format: longitude,latitude)
            
    Returns:
        str: Driving route information in JSON format
    """
    try:
        origin = args["origin"]
        destination = args["destination"]
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/direction/driving"
        params = {
            "origin": origin,
            "destination": destination,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Driving route planning failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        route = data.get("route", {})
        paths = route.get("paths", [])
        
        result_paths = []
        for path in paths:
            steps_data = []
            for step in path.get("steps", []):
                steps_data.append({
                    "instruction": step.get("instruction"),
                    "road": step.get("road"),
                    "distance": step.get("distance"),
                    "orientation": step.get("orientation"),
                    "duration": step.get("duration")
                })
                
            result_paths.append({
                "distance": path.get("distance"),
                "duration": path.get("duration"),
                "tolls": path.get("tolls"),
                "toll_distance": path.get("toll_distance"),
                "steps": steps_data
            })
            
        result = {
            "success": True,
            "data": {
                "origin": route.get("origin"),
                "destination": route.get("destination"),
                "taxi_cost": route.get("taxi_cost"),
                "paths": result_paths
            }
        }
        
        logger.info(f"[AmapTools] Driving route planning successful: {origin} -> {destination}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Driving route planning failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_text_search(args: Dict[str, Any]) -> str:
    """Keyword search for POI.
    
    Args:
        args: A dictionary containing the following parameters
            - keywords: Search keywords
            - city: Query city (optional)
            - types: POI type (optional)
            
    Returns:
        str: Search results in JSON format
    """
    try:
        keywords = args["keywords"]
        city = args.get("city", "")
        types = args.get("types", "")
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/place/text"
        params = {
            "keywords": keywords,
            "key": api_key,
            "source": "py_xiaozhi",
            "citylimit": "false"
        }
        if city:
            params["city"] = city
        if types:
            params["types"] = types
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Search failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        pois = data.get("pois", [])
        result_pois = []
        
        for poi in pois:
            result_pois.append({
                "id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "typecode": poi.get("typecode"),
                "type": poi.get("type"),
                "tel": poi.get("tel"),
                "distance": poi.get("distance")
            })
            
        result = {
            "success": True,
            "data": {
                "count": data.get("count"),
                "pois": result_pois
            }
        }
        
        logger.info(f"[AmapTools] Search successful: {keywords}, number of results: {len(result_pois)}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_around_search(args: Dict[str, Any]) -> str:
    """Nearby search for POI.
    
    Args:
        args: A dictionary containing the following parameters
            - location: Center point coordinates (format: longitude,latitude)
            - keywords: Search keywords (optional)
            - radius: Search radius in meters (optional, default 1000)
            
    Returns:
        str: Nearby search results in JSON format
    """
    try:
        location = args["location"]
        keywords = args.get("keywords", "")
        radius = args.get("radius", "1000")
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/place/around"
        params = {
            "location": location,
            "radius": radius,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        if keywords:
            params["keywords"] = keywords
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Nearby search failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        pois = data.get("pois", [])
        result_pois = []
        
        for poi in pois:
            result_pois.append({
                "id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "typecode": poi.get("typecode"),
                "type": poi.get("type"),
                "tel": poi.get("tel"),
                "distance": poi.get("distance")
            })
            
        result = {
            "success": True,
            "data": {
                "count": data.get("count"),
                "pois": result_pois
            }
        }
        
        logger.info(f"[AmapTools] Nearby search successful: {location}, number of results: {len(result_pois)}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Nearby search failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_search_detail(args: Dict[str, Any]) -> str:
    """Query POI details.
    
    Args:
        args: A dictionary containing the following parameters
            - id: POI ID
            
    Returns:
        str: Detailed information in JSON format
    """
    try:
        poi_id = args["id"]
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/place/detail"
        params = {
            "id": poi_id,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"POI detail query failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        pois = data.get("pois", [])
        if not pois:
            error_msg = "POI details not found"
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        poi = pois[0]
        biz_ext = poi.get("biz_ext", {})
        
        result = {
            "success": True,
            "data": {
                "id": poi.get("id"),
                "name": poi.get("name"),
                "location": poi.get("location"),
                "address": poi.get("address"),
                "business_area": poi.get("business_area"),
                "cityname": poi.get("cityname"),
                "type": poi.get("type"),
                "alias": poi.get("alias"),
                "tel": poi.get("tel"),
                "website": poi.get("website"),
                "email": poi.get("email"),
                "postcode": poi.get("postcode"),
                "rating": biz_ext.get("rating"),
                "cost": biz_ext.get("cost"),
                "opentime": biz_ext.get("opentime")
            }
        }
        
        logger.info(f"[AmapTools] POI detail query successful: {poi_id}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"POI detail query failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def maps_distance(args: Dict[str, Any]) -> str:
    """Distance measurement.
    
    Args:
        args: A dictionary containing the following parameters
            - origins: Origin coordinates, multiple allowed, separated by semicolons
            - destination: Destination coordinates
            - type: Distance measurement type (optional, default 1: driving, 0: straight line, 3: walking)
            
    Returns:
        str: Distance information in JSON format
    """
    try:
        origins = args["origins"]
        destination = args["destination"]
        distance_type = args.get("type", "1")
        api_key = get_amap_api_key()
        
        url = "https://restapi.amap.com/v3/distance"
        params = {
            "origins": origins,
            "destination": destination,
            "type": distance_type,
            "key": api_key,
            "source": "py_xiaozhi"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        if data.get("status") != "1":
            error_msg = f"Distance measurement failed: {data.get('info', data.get('infocode'))}"
            logger.error(f"[AmapTools] {error_msg}")
            return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
            
        results = data.get("results", [])
        result_data = []
        
        for result_item in results:
            result_data.append({
                "origin_id": result_item.get("origin_id"),
                "dest_id": result_item.get("dest_id"),
                "distance": result_item.get("distance"),
                "duration": result_item.get("duration")
            })
            
        result = {
            "success": True,
            "data": {
                "results": result_data
            }
        }
        
        logger.info(f"[AmapTools] Distance measurement successful: {origins} -> {destination}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[AmapTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Distance measurement failed: {str(e)}"
        logger.error(f"[AmapTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)