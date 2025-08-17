#!/usr/bin/env python3
"""
Calendar query script for viewing and managing schedules.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path - must be done before importing src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.tools.calendar import get_calendar_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CalendarQueryScript:
    """
    Calendar query script class.
    """

    def __init__(self):
        self.manager = get_calendar_manager()

    def format_event_display(self, event, show_details=True):
        """
        Format event display.
        """
        start_dt = datetime.fromisoformat(event.start_time)
        end_dt = datetime.fromisoformat(event.end_time)

        # Basic Information
        time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"
        basic_info = f"📅 {time_str} | [{event.category}] {event.title}"

        if not show_details:
            return basic_info

        # Detailed Information
        details = []
        if event.description:
            details.append(f"   📝 Notes: {event.description}")

        # Reminder Information
        if event.reminder_minutes > 0:
            details.append(f"   ⏰ Reminder: {event.reminder_minutes} minutes in advance")
            if hasattr(event, "reminder_sent") and event.reminder_sent:
                details.append("   ✅ Reminder Status: Sent")
            else:
                details.append("   ⏳ Reminder Status: Pending")

        # Time Distance
        now = datetime.now()
        time_diff = start_dt - now
        if time_diff.total_seconds() > 0:
            days = time_diff.days
            hours = int(time_diff.seconds // 3600)
            minutes = int((time_diff.seconds % 3600) // 60)

            time_until_parts = []
            if days > 0:
                time_until_parts.append(f"{days} days")
            if hours > 0:
                time_until_parts.append(f"{hours} hours")
            if minutes > 0:
                time_until_parts.append(f"{minutes} minutes")

            if time_until_parts:
                details.append(f"   🕐 Time until start: {' '.join(time_until_parts)}")
            else:
                details.append("   🕐 Time until start: Starting soon")
        elif start_dt <= now <= end_dt:
            details.append("   🔴 Status: In Progress")
        else:
            details.append("   ✅ Status: Finished")

        if details:
            return basic_info + "\n" + "\n".join(details)
        return basic_info

    async def query_today(self):
        """
        Query today's schedule.
        """
        print("📅 Today's Schedule")
        print("=" * 50)

        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        events = self.manager.get_events(
            start_date=today_start.isoformat(), end_date=today_end.isoformat()
        )

        if not events:
            print("🎉 No events scheduled for today")
            return

        print(f"📊 Total of {len(events)} events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. {self.format_event_display(event)}")
            if i < len(events):
                print()

    async def query_tomorrow(self):
        """
        Query tomorrow's schedule.
        """
        print("📅 Tomorrow's Schedule")
        print("=" * 50)

        now = datetime.now()
        tomorrow_start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        tomorrow_end = tomorrow_start + timedelta(days=1)

        events = self.manager.get_events(
            start_date=tomorrow_start.isoformat(), end_date=tomorrow_end.isoformat()
        )

        if not events:
            print("🎉 No events scheduled for tomorrow")
            return

        print(f"📊 Total of {len(events)} events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. {self.format_event_display(event)}")
            if i < len(events):
                print()

    async def query_week(self):
        """
        Query this week's schedule.
        """
        print("📅 This Week's Schedule")
        print("=" * 50)

        now = datetime.now()
        # This Monday
        days_since_monday = now.weekday()
        week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7)

        events = self.manager.get_events(
            start_date=week_start.isoformat(), end_date=week_end.isoformat()
        )

        if not events:
            print("🎉 No events scheduled for this week")
            return

        print(f"📊 Total of {len(events)} events:\n")

        # Group by date
        events_by_date = {}
        for event in events:
            event_date = datetime.fromisoformat(event.start_time).date()
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)

        for date in sorted(events_by_date.keys()):
            weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
                date.weekday()
            ]
            print(f"📆 {date.strftime('%m-%d')} ({weekday})")
            print("-" * 30)

            for event in events_by_date[date]:
                print(f"  {self.format_event_display(event, show_details=False)}")
            print()

    async def query_upcoming(self, hours=24):
        """
        Query upcoming events.
        """
        print(f"📅 Events in the next {hours} hours")
        print("=" * 50)

        now = datetime.now()
        end_time = now + timedelta(hours=hours)

        events = self.manager.get_events(
            start_date=now.isoformat(), end_date=end_time.isoformat()
        )

        if not events:
            print(f"🎉 No events scheduled in the next {hours} hours")
            return

        print(f"📊 Total of {len(events)} events:\n")
        for i, event in enumerate(events, 1):
            print(f"{i}. {self.format_event_display(event)}")
            if i < len(events):
                print()

    async def query_by_category(self, category=None):
        """
        Query events by category.
        """
        if category:
            print(f"📅 Events in category [{category}]")
            print("=" * 50)

            events = self.manager.get_events(category=category)

            if not events:
                print(f"🎉 No events in category [{category}]")
                return

            print(f"📊 Total of {len(events)} events:\n")
            for i, event in enumerate(events, 1):
                print(f"{i}. {self.format_event_display(event)}")
                if i < len(events):
                    print()
        else:
            print("📅 All Category Statistics")
            print("=" * 50)

            categories = self.manager.get_categories()

            if not categories:
                print("🎉 No categories yet")
                return

            print("📊 Category List:")
            for i, cat in enumerate(categories, 1):
                # Count events for each category
                events = self.manager.get_events(category=cat)
                print(f"{i}. [{cat}] - {len(events)} events")

    async def query_all(self):
        """
        Query all events.
        """
        print("📅 All Schedules")
        print("=" * 50)

        events = self.manager.get_events()

        if not events:
            print("🎉 No schedules yet")
            return

        print(f"📊 Total of {len(events)} events:\n")

        # Sort by time and group
        now = datetime.now()
        past_events = []
        current_events = []
        future_events = []

        for event in events:
            start_dt = datetime.fromisoformat(event.start_time)
            end_dt = datetime.fromisoformat(event.end_time)

            if end_dt < now:
                past_events.append(event)
            elif start_dt <= now <= end_dt:
                current_events.append(event)
            else:
                future_events.append(event)

        # Show in-progress events
        if current_events:
            print("🔴 In Progress:")
            for event in current_events:
                print(f"  {self.format_event_display(event, show_details=False)}")
            print()

        # Show future events
        if future_events:
            print("⏳ Upcoming:")
            for event in future_events[:5]:  # Show only the first 5
                print(f"  {self.format_event_display(event, show_details=False)}")
            if len(future_events) > 5:
                print(f"  ... and {len(future_events) - 5} more events")
            print()

        # Show recent past events
        if past_events:
            recent_past = sorted(past_events, key=lambda e: e.start_time, reverse=True)[
                :3
            ]
            print("✅ Recently Finished:")
            for event in recent_past:
                print(f"  {self.format_event_display(event, show_details=False)}")
            if len(past_events) > 3:
                print(f"  ... and {len(past_events) - 3} more finished events")

    async def search_events(self, keyword):
        """
        Search events.
        """
        print(f"🔍 Searching for events containing '{keyword}'")
        print("=" * 50)

        all_events = self.manager.get_events()
        matched_events = []

        for event in all_events:
            if (
                keyword.lower() in event.title.lower()
                or (event.description and keyword.lower() in event.description.lower())
                or keyword.lower() in event.category.lower()
            ):
                matched_events.append(event)

        if not matched_events:
            print(f"🎉 No events found containing '{keyword}'")
            return

        print(f"📊 Found {len(matched_events)} matching events:\n")
        for i, event in enumerate(matched_events, 1):
            print(f"{i}. {self.format_event_display(event)}")
            if i < len(matched_events):
                print()


async def main():
    """
    Main function.
    """
    parser = argparse.ArgumentParser(description="Calendar query script")
    parser.add_argument(
        "command",
        nargs="?",
        default="today",
        choices=["today", "tomorrow", "week", "upcoming", "category", "all", "search"],
        help="Query type",
    )
    parser.add_argument("--hours", type=int, default=24, help="Number of hours for upcoming query")
    parser.add_argument("--category", type=str, help="Specify category name")
    parser.add_argument("--keyword", type=str, help="Search keyword")

    args = parser.parse_args()

    script = CalendarQueryScript()

    try:
        if args.command == "today":
            await script.query_today()
        elif args.command == "tomorrow":
            await script.query_tomorrow()
        elif args.command == "week":
            await script.query_week()
        elif args.command == "upcoming":
            await script.query_upcoming(args.hours)
        elif args.command == "category":
            await script.query_by_category(args.category)
        elif args.command == "all":
            await script.query_all()
        elif args.command == "search":
            if not args.keyword:
                print("❌ Search requires a keyword, use the --keyword argument")
                return
            await script.search_events(args.keyword)

        print("\n" + "=" * 50)
        print("💡 Usage Help:")
        print("  python scripts/calendar_query.py today      # View today's schedule")
        print("  python scripts/calendar_query.py tomorrow   # View tomorrow's schedule")
        print("  python scripts/calendar_query.py week       # View this week's schedule")
        print(
            "  python scripts/calendar_query.py upcoming --hours 48  # View schedule for the next 48 hours"
        )
        print(
            "  python scripts/calendar_query.py category --category Work  # View Work category"
        )
        print("  python scripts/calendar_query.py all        # View all schedules")
        print("  python scripts/calendar_query.py search --keyword Development  # Search schedules")

    except Exception as e:
        logger.error(f"Failed to query schedule: {e}", exc_info=True)
        print(f"❌ Query failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
