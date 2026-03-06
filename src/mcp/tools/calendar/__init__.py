"""Calendar management tool package.

Provides complete calendar management features including event creation, querying, updating, and deletion.
"""

from .database import CalendarDatabase, get_calendar_database
from .manager import CalendarManager, get_calendar_manager
from .models import CalendarEvent
from .reminder_service import CalendarReminderService, get_reminder_service
from .tools import (
    create_event,
    delete_event,
    delete_events_batch,
    get_categories,
    get_events_by_date,
    get_upcoming_events,
    update_event,
)

__all__ = [
    "CalendarManager",
    "get_calendar_manager",
    "CalendarEvent",
    "CalendarDatabase",
    "get_calendar_database",
    "CalendarReminderService",
    "get_reminder_service",
    "create_event",
    "delete_event",
    "delete_events_batch",
    "get_categories",
    "get_events_by_date",
    "get_upcoming_events",
    "update_event",
]
