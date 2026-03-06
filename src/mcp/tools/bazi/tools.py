"""
BaZi MCP tool functions. Provides async tool functions for MCP server invocation.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .bazi_calculator import get_bazi_calculator
from .engine import get_bazi_engine

logger = get_logger(__name__)


async def get_bazi_detail(args: Dict[str, Any]) -> str:
    """
    Get BaZi information based on time (solar or lunar) and gender.
    """
    try:
        solar_datetime = args.get("solar_datetime")
        lunar_datetime = args.get("lunar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not solar_datetime and not lunar_datetime:
            return json.dumps(
                {
                    "success": False,
                    "message": "Either solar_datetime or lunar_datetime must be provided, but not both",
                },
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()
        result = calculator.build_bazi(
            solar_datetime=solar_datetime,
            lunar_datetime=lunar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        return json.dumps(
            {"success": True, "data": result.to_dict()}, ensure_ascii=False, indent=2
        )

    except Exception as e:
        logger.error(f"Failed to get BaZi details: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get BaZi details: {str(e)}"},
            ensure_ascii=False,
        )


async def get_solar_times(args: Dict[str, Any]) -> str:
    """
    Get a list of solar times based on BaZi.
    """
    try:
        bazi = args.get("bazi")
        if not bazi:
            return json.dumps(
                {"success": False, "message": "BaZi parameter cannot be empty"}, ensure_ascii=False
            )

        calculator = get_bazi_calculator()
        result = calculator.get_solar_times(bazi)

        return json.dumps(
            {"success": True, "data": {"possible_times": result, "total": len(result)}},
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to get solar times: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get solar times: {str(e)}"},
            ensure_ascii=False,
        )


async def get_chinese_calendar(args: Dict[str, Any]) -> str:
    """
    Get Chinese calendar (Huang Li) information for the specified solar time (defaults to today).
    """
    try:
        solar_datetime = args.get("solar_datetime")

        engine = get_bazi_engine()

        # If time is provided, parse it; otherwise use current time
        if solar_datetime:
            solar_time = engine.parse_solar_time(solar_datetime)
            result = engine.get_chinese_calendar(solar_time)
        else:
            result = engine.get_chinese_calendar()  # Use current time

        return json.dumps(
            {"success": True, "data": result.to_dict()}, ensure_ascii=False, indent=2
        )

    except Exception as e:
        logger.error(f"Failed to get Chinese calendar info: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get Chinese calendar info: {str(e)}"},
            ensure_ascii=False,
        )


async def build_bazi_from_lunar_datetime(args: Dict[str, Any]) -> str:
    """
    Get BaZi information from lunar time and gender (deprecated, use get_bazi_detail instead).
    """
    try:
        lunar_datetime = args.get("lunar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not lunar_datetime:
            return json.dumps(
                {"success": False, "message": "lunar_datetime parameter cannot be empty"},
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()
        result = calculator.build_bazi(
            lunar_datetime=lunar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        return json.dumps(
            {
                "success": True,
                "message": "This method is deprecated, please use get_bazi_detail",
                "data": result.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to get BaZi from lunar time: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get BaZi from lunar time: {str(e)}"},
            ensure_ascii=False,
        )


async def build_bazi_from_solar_datetime(args: Dict[str, Any]) -> str:
    """
    Get BaZi information from solar time and gender (deprecated, use get_bazi_detail instead).
    """
    try:
        solar_datetime = args.get("solar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not solar_datetime:
            return json.dumps(
                {"success": False, "message": "solar_datetime parameter cannot be empty"},
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()
        result = calculator.build_bazi(
            solar_datetime=solar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        return json.dumps(
            {
                "success": True,
                "message": "This method is deprecated, please use get_bazi_detail",
                "data": result.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to get BaZi from solar time: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get BaZi from solar time: {str(e)}"},
            ensure_ascii=False,
        )
