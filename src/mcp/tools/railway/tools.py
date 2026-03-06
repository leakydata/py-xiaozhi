"""12306 tool function implementations.

Provides various 12306-related query features.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .client import get_railway_client

logger = get_logger(__name__)


async def get_current_date(args: Dict[str, Any]) -> str:
    """
    Get current date (Shanghai timezone).
    """
    try:
        client = await get_railway_client()
        current_date = client.get_current_date()
        logger.info(f"Get current date: {current_date}")
        return current_date

    except Exception as e:
        logger.error(f"Failed to get current date: {e}", exc_info=True)
        return f"Failed to get current date: {str(e)}"


async def get_stations_in_city(args: Dict[str, Any]) -> str:
    """
    Get all stations in a city.
    """
    try:
        city = args.get("city", "")
        if not city:
            return "Error: City name cannot be empty"

        client = await get_railway_client()
        stations = client.get_stations_in_city(city)

        if not stations:
            return f"No station information found for city '{city}'"

        result = {
            "city": city,
            "stations": [
                {
                    "station_code": station.station_code,
                    "station_name": station.station_name,
                    "station_pinyin": station.station_pinyin,
                }
                for station in stations
            ],
        }

        logger.info(f"Query stations in city {city}: found {len(stations)} stations")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to query city stations: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


async def get_city_station_code(args: Dict[str, Any]) -> str:
    """
    Get main station codes for cities.
    """
    try:
        cities = args.get("cities", "")
        if not cities:
            return "Error: City name cannot be empty"

        client = await get_railway_client()
        city_list = cities.split("|")
        result = {}

        for city in city_list:
            city = city.strip()
            station = client.get_city_main_station(city)

            if station:
                result[city] = {
                    "station_code": station.station_code,
                    "station_name": station.station_name,
                }
            else:
                result[city] = {"error": "Main station not found for city"}

        logger.info(f"Query main stations for cities: {cities}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to query main city stations: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


async def get_station_by_name(args: Dict[str, Any]) -> str:
    """
    Get station information by station name.
    """
    try:
        station_names = args.get("station_names", "")
        if not station_names:
            return "Error: Station name cannot be empty"

        client = await get_railway_client()
        name_list = station_names.split("|")
        result = {}

        for name in name_list:
            name = name.strip()
            station = client.get_station_by_name(name)

            if station:
                result[name] = {
                    "station_code": station.station_code,
                    "station_name": station.station_name,
                    "city": station.city,
                }
            else:
                result[name] = {"error": "Station not found"}

        logger.info(f"Query station by name: {station_names}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to query station by name: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


async def get_station_by_code(args: Dict[str, Any]) -> str:
    """
    Get station information by station code.
    """
    try:
        station_code = args.get("station_code", "")
        if not station_code:
            return "Error: Station code cannot be empty"

        client = await get_railway_client()
        station = client.get_station_by_code(station_code)

        if not station:
            return f"No station found for station code '{station_code}'"

        result = {
            "station_code": station.station_code,
            "station_name": station.station_name,
            "station_pinyin": station.station_pinyin,
            "city": station.city,
            "code": station.code,
        }

        logger.info(f"Query station by code: {station_code}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to query station by code: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


async def query_train_tickets(args: Dict[str, Any]) -> str:
    """
    Query train tickets.
    """
    try:
        date = args.get("date", "")
        from_station = args.get("from_station", "")
        to_station = args.get("to_station", "")
        train_filters = args.get("train_filters", "")
        sort_by = args.get("sort_by", "")
        reverse = args.get("reverse", False)
        limit = args.get("limit", 0)

        if not all([date, from_station, to_station]):
            return "Error: Date, departure station, and arrival station are all required parameters"

        client = await get_railway_client()
        success, tickets, message = await client.query_tickets(
            date, from_station, to_station, train_filters, sort_by, reverse, limit
        )

        if not success:
            return f"Query failed: {message}"

        if not tickets:
            return "No matching trains found"

        # Format output
        result = _format_tickets(tickets)

        logger.info(f"Query tickets: {date} {from_station}->{to_station}, {message}")
        return result

    except Exception as e:
        logger.error(f"Failed to query tickets: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


async def query_transfer_tickets(args: Dict[str, Any]) -> str:
    """
    Query transfer tickets.
    """
    try:
        date = args.get("date", "")
        from_station = args.get("from_station", "")
        to_station = args.get("to_station", "")
        middle_station = args.get("middle_station", "")
        show_wz = args.get("show_wz", False)
        train_filters = args.get("train_filters", "")
        sort_by = args.get("sort_by", "")
        reverse = args.get("reverse", False)
        limit = args.get("limit", 10)

        if not all([date, from_station, to_station]):
            return "Error: Date, departure station, and arrival station are all required parameters"

        client = await get_railway_client()
        success, transfers, message = await client.query_transfer_tickets(
            date,
            from_station,
            to_station,
            middle_station,
            show_wz,
            train_filters,
            sort_by,
            reverse,
            limit,
        )

        if not success:
            return f"Query failed: {message}"

        if not transfers:
            return "No matching transfer options found"

        # Format output
        result = _format_transfer_tickets(transfers)

        logger.info(f"Query transfer tickets: {date} {from_station}->{to_station}, {message}")
        return result

    except Exception as e:
        logger.error(f"Failed to query transfer tickets: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


async def query_train_route(args: Dict[str, Any]) -> str:
    """
    Query train route stops.
    """
    try:
        # Temporarily return unsupported message
        return "Train route stop query feature is under development, please try again later"

    except Exception as e:
        logger.error(f"Failed to query train route stops: {e}", exc_info=True)
        return f"Query failed: {str(e)}"


def _format_tickets(tickets: list) -> str:
    """
    Format ticket information.
    """
    if not tickets:
        return "No train information found"

    result_lines = []
    result_lines.append("Train | Departure -> Arrival | Dep. Time -> Arr. Time | Duration")
    result_lines.append("-" * 80)

    for ticket in tickets:
        # Train basic information
        basic_info = (
            f"{ticket.start_train_code} | "
            f"{ticket.from_station} -> {ticket.to_station} | "
            f"{ticket.start_time} -> {ticket.arrive_time} | "
            f"{ticket.duration}"
        )
        result_lines.append(basic_info)

        # Seat and price information
        for price in ticket.prices:
            ticket_status = _format_ticket_status(price.num)
            price_info = f"  - {price.seat_name}: {ticket_status} {price.price} CNY"
            result_lines.append(price_info)

        # Feature flags
        if ticket.features:
            features_info = f"  - Features: {', '.join(ticket.features)}"
            result_lines.append(features_info)

        result_lines.append("")  # Blank line separator

    return "\n".join(result_lines)


def _format_ticket_status(num: str) -> str:
    """
    Format ticket availability status.
    """
    if num.isdigit():
        count = int(num)
        if count == 0:
            return "Sold out"
        else:
            return f"{count} tickets remaining"

    # Handle special statuses
    status_map = {
        "有": "Available",
        "充足": "Available",
        "无": "Sold out",
        "--": "Sold out",
        "": "Sold out",
        "候补": "Sold out (waitlist available)",
    }

    return status_map.get(num, f"{num} tickets")


def _format_transfer_tickets(transfers: list) -> str:
    """
    Format transfer ticket information.
    """
    if not transfers:
        return "No transfer options found"

    result_lines = []
    result_lines.append(
        "Dep. Time -> Arr. Time | Dep. Station -> Transfer Station -> Arr. Station | Transfer Type | Transfer Wait | Total Duration"
    )
    result_lines.append("=" * 120)

    for transfer in transfers:
        # Basic information
        basic_info = (
            f"{transfer.start_date} {transfer.start_time} -> {transfer.arrive_date} {transfer.arrive_time} | "
            f"{transfer.from_station_name} -> {transfer.middle_station_name} -> {transfer.end_station_name} | "
            f"{'Same_Train' if transfer.same_train else 'Same_Station' if transfer.same_station else 'Different_Station'} | "
            f"{transfer.wait_time} | {transfer.duration}"
        )
        result_lines.append(basic_info)
        result_lines.append("-" * 80)

        # Train details
        for i, ticket in enumerate(transfer.ticket_list, 1):
            segment_info = (
                f"  Leg {i}: {ticket.start_train_code} | "
                f"{ticket.from_station} -> {ticket.to_station} | "
                f"{ticket.start_time} -> {ticket.arrive_time} | "
                f"{ticket.duration}"
            )
            result_lines.append(segment_info)

            # Seat and price information
            for price in ticket.prices:
                ticket_status = _format_ticket_status(price.num)
                price_info = f"    - {price.seat_name}: {ticket_status} {price.price} CNY"
                result_lines.append(price_info)

            # Feature flags
            if ticket.features:
                features_info = f"    - Features: {', '.join(ticket.features)}"
                result_lines.append(features_info)

        result_lines.append("")  # Blank line separator

    return "\n".join(result_lines)


def _format_ticket_status(num: str) -> str:
    """
    Format ticket availability status.
    """
    if num.isdigit():
        count = int(num)
        if count == 0:
            return "Sold out"
        else:
            return f"{count} tickets remaining"

    # Handle special statuses
    status_map = {
        "有": "Available",
        "充足": "Available",
        "无": "Sold out",
        "--": "Sold out",
        "": "Sold out",
        "候补": "Sold out (waitlist available)",
    }

    return status_map.get(num, f"{num} tickets")
