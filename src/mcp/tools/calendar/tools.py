"""
Calendar management MCP tool functions providing async tool functions for MCP server calls.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .manager import get_calendar_manager
from .models import CalendarEvent

logger = get_logger(__name__)


async def create_event(args: Dict[str, Any]) -> str:
    """
    Create a calendar event.
    """
    try:
        title = args["title"]
        start_time = args["start_time"]
        end_time = args.get("end_time")
        description = args.get("description", "")
        category = args.get("category", "default")
        reminder_minutes = args.get("reminder_minutes", 15)

        # If no end time, intelligently set default duration based on category
        if not end_time:
            start_dt = datetime.fromisoformat(start_time)

            # Set different default durations based on category
            if category in ["reminder", "rest", "stand"]:
                # Short activity: 5 minutes
                end_dt = start_dt + timedelta(minutes=5)
            elif category in ["meeting", "work"]:
                # Work-related: 1 hour
                end_dt = start_dt + timedelta(hours=1)
            elif (
                "reminder" in title.lower()
                or "stand" in title.lower()
                or "rest" in title.lower()
            ):
                # Determine by title: short activity
                end_dt = start_dt + timedelta(minutes=5)
            else:
                # Default case: 30 minutes
                end_dt = start_dt + timedelta(minutes=30)

            end_time = end_dt.isoformat()

        # Validate time format
        datetime.fromisoformat(start_time)
        datetime.fromisoformat(end_time)

        # Create event
        event = CalendarEvent(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            category=category,
            reminder_minutes=reminder_minutes,
        )

        manager = get_calendar_manager()
        if manager.add_event(event):
            return json.dumps(
                {
                    "success": True,
                    "message": "Event created successfully",
                    "event_id": event.id,
                    "event": event.to_dict(),
                },
                ensure_ascii=False,
            )
        else:
            return json.dumps(
                {"success": False, "message": "Failed to create event, possible time conflict"},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to create event: {str(e)}"}, ensure_ascii=False
        )


async def get_events_by_date(args: Dict[str, Any]) -> str:
    """
    Query events by date.
    """
    try:
        date_type = args.get("date_type", "today")  # today, tomorrow, week, month
        category = args.get("category")

        now = datetime.now()

        if date_type == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif date_type == "tomorrow":
            start_date = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + timedelta(days=1)
        elif date_type == "week":
            # This week
            days_since_monday = now.weekday()
            start_date = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date = start_date + timedelta(days=7)
        elif date_type == "month":
            # This month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end_date = start_date.replace(year=now.year + 1, month=1)
            else:
                end_date = start_date.replace(month=now.month + 1)
        else:
            # Custom date range
            start_date = (
                datetime.fromisoformat(args["start_date"])
                if args.get("start_date")
                else None
            )
            end_date = (
                datetime.fromisoformat(args["end_date"])
                if args.get("end_date")
                else None
            )

        manager = get_calendar_manager()
        events = manager.get_events(
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            category=category,
        )

        # Format output
        events_data = []
        for event in events:
            event_dict = event.to_dict()
            # Add human-readable time display
            start_dt = datetime.fromisoformat(event.start_time)
            end_dt = datetime.fromisoformat(event.end_time)
            event_dict["display_time"] = (
                f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"
            )
            events_data.append(event_dict)

        return json.dumps(
            {
                "success": True,
                "date_type": date_type,
                "total_events": len(events_data),
                "events": events_data,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to query events: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to query events: {str(e)}"}, ensure_ascii=False
        )


async def update_event(args: Dict[str, Any]) -> str:
    """
    Update a calendar event.
    """
    try:
        event_id = args["event_id"]

        # Build update fields
        update_fields = {}
        for field in [
            "title",
            "start_time",
            "end_time",
            "description",
            "category",
            "reminder_minutes",
        ]:
            if field in args:
                update_fields[field] = args[field]

        if not update_fields:
            return json.dumps(
                {"success": False, "message": "No fields provided to update"},
                ensure_ascii=False,
            )

        manager = get_calendar_manager()
        if manager.update_event(event_id, **update_fields):
            return json.dumps(
                {
                    "success": True,
                    "message": "Event updated successfully",
                    "updated_fields": list(update_fields.keys()),
                },
                ensure_ascii=False,
            )
        else:
            return json.dumps(
                {"success": False, "message": "Failed to update event, event not found"},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Failed to update event: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to update event: {str(e)}"}, ensure_ascii=False
        )


async def delete_event(args: Dict[str, Any]) -> str:
    """
    Delete a calendar event.
    """
    try:
        event_id = args["event_id"]

        manager = get_calendar_manager()
        if manager.delete_event(event_id):
            return json.dumps(
                {"success": True, "message": "Event deleted successfully"}, ensure_ascii=False
            )
        else:
            return json.dumps(
                {"success": False, "message": "Failed to delete event, event not found"},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Failed to delete event: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to delete event: {str(e)}"}, ensure_ascii=False
        )


async def delete_events_batch(args: Dict[str, Any]) -> str:
    """
    Batch delete calendar events.
    """
    try:
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        category = args.get("category")
        delete_all = args.get("delete_all", False)
        date_type = args.get("date_type")

        # Handle date_type parameter (similar to get_events_by_date)
        if date_type and not (start_date and end_date):
            now = datetime.now()

            if date_type == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif date_type == "tomorrow":
                start_date = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_date = start_date + timedelta(days=1)
            elif date_type == "week":
                # This week
                days_since_monday = now.weekday()
                start_date = (now - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_date = start_date + timedelta(days=7)
            elif date_type == "month":
                # This month
                start_date = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if now.month == 12:
                    end_date = start_date.replace(year=now.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=now.month + 1)

            # Convert to ISO format strings
            if isinstance(start_date, datetime):
                start_date = start_date.isoformat()
            if isinstance(end_date, datetime):
                end_date = end_date.isoformat()

        manager = get_calendar_manager()
        result = manager.delete_events_batch(
            start_date=start_date,
            end_date=end_date,
            category=category,
            delete_all=delete_all,
        )

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to batch delete events: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to batch delete events: {str(e)}"},
            ensure_ascii=False,
        )


async def get_categories(args: Dict[str, Any]) -> str:
    """
    Get all event categories.
    """
    try:
        manager = get_calendar_manager()
        categories = manager.get_categories()

        return json.dumps(
            {"success": True, "categories": categories}, ensure_ascii=False
        )

    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get categories: {str(e)}"}, ensure_ascii=False
        )


async def get_upcoming_events(args: Dict[str, Any]) -> str:
    """
    Get upcoming events (within the next 24 hours).
    """
    try:
        hours = args.get("hours", 24)  # Default: query next 24 hours

        now = datetime.now()
        end_time = now + timedelta(hours=hours)

        manager = get_calendar_manager()
        events = manager.get_events(
            start_date=now.isoformat(), end_date=end_time.isoformat()
        )

        # Calculate reminder times
        upcoming_events = []
        for event in events:
            event_dict = event.to_dict()
            start_dt = datetime.fromisoformat(event.start_time)

            # Calculate time until start
            time_until = start_dt - now
            if time_until.total_seconds() > 0:
                hours_until = int(time_until.total_seconds() // 3600)
                minutes_until = int((time_until.total_seconds() % 3600) // 60)

                if hours_until > 0:
                    time_display = f"in {hours_until} hours {minutes_until} minutes"
                else:
                    time_display = f"in {minutes_until} minutes"

                event_dict["time_until"] = time_display
                event_dict["time_until_minutes"] = int(time_until.total_seconds() // 60)
                upcoming_events.append(event_dict)

        return json.dumps(
            {
                "success": True,
                "query_hours": hours,
                "total_events": len(upcoming_events),
                "events": upcoming_events,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to get upcoming events: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get upcoming events: {str(e)}"},
            ensure_ascii=False,
        )
