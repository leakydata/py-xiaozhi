"""
Calendar reminder service. Periodically checks events in the database and announces reminders via TTS when the reminder time is reached.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

from src.utils.logging_config import get_logger

from .database import get_calendar_database

logger = get_logger(__name__)


class CalendarReminderService:
    """
    Calendar reminder service.
    """

    def __init__(self):
        self.db = get_calendar_database()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.check_interval = 30  # Check interval (seconds)

    def _get_application(self):
        """
        Lazy-load and get the application instance.
        """
        try:
            from src.application import Application

            return Application.get_instance()
        except Exception as e:
            logger.warning(f"Failed to get application instance: {e}")
            return None

    async def start(self):
        """
        Start the reminder service.
        """
        if self.is_running:
            logger.warning("Reminder service is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._reminder_loop())
        logger.info("Calendar reminder service started")

        # Reset reminder flags for future events on startup
        await self.reset_reminder_flags_for_future_events()

    async def stop(self):
        """
        Stop the reminder service.
        """
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Calendar reminder service stopped")

    async def _reminder_loop(self):
        """
        Reminder check loop.
        """
        logger.info("Starting calendar reminder check loop")

        while self.is_running:
            try:
                await self._check_and_send_reminders()
                # Periodically clean up reminder flags for expired events
                await self._cleanup_expired_reminders()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reminder check loop error: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def _check_and_send_reminders(self):
        """
        Check and send reminders.
        """
        try:
            now = datetime.now()

            # Query all events where reminder has not been sent and reminder time has arrived
            # Also ensure the event has not expired (start time is after now or within a reasonable expiry window)
            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE reminder_sent = 0
                    AND reminder_time IS NOT NULL
                    AND reminder_time <= ?
                    AND start_time > ?
                    ORDER BY reminder_time
                """,
                    (now.isoformat(), (now - timedelta(hours=1)).isoformat()),
                )

                pending_reminders = cursor.fetchall()

            if not pending_reminders:
                return

            logger.info(f"Found {len(pending_reminders)} pending reminders to send")

            # Process each reminder
            for reminder in pending_reminders:
                await self._send_reminder(dict(reminder))

        except Exception as e:
            logger.error(f"Failed to check reminders: {e}", exc_info=True)

    async def _send_reminder(self, event_data: dict):
        """
        Send a single reminder.
        """
        try:
            event_id = event_data["id"]
            title = event_data["title"]
            start_time = event_data["start_time"]
            description = event_data.get("description", "")
            category = event_data.get("category", "default")

            # Calculate time until start
            start_dt = datetime.fromisoformat(start_time)
            now = datetime.now()
            time_until = start_dt - now

            if time_until.total_seconds() > 0:
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)

                if hours > 0:
                    time_str = f"in {hours} hours {minutes} minutes"
                else:
                    time_str = f"in {minutes} minutes"
            else:
                time_str = "now"

            # Build reminder message
            reminder_message = {
                "type": "calendar_reminder",
                "event": {
                    "id": event_id,
                    "title": title,
                    "start_time": start_time,
                    "description": description,
                    "category": category,
                    "time_until": time_str,
                },
                "message": self._format_reminder_text(
                    title, time_str, category, description
                ),
            }

            # Serialize to JSON string
            reminder_json = json.dumps(reminder_message, ensure_ascii=False)

            # Get application instance and call TTS method
            application = self._get_application()
            if application and hasattr(application, "_send_text_tts"):
                await application._send_text_tts(reminder_json)
                logger.info(f"Reminder sent: {title} ({time_str})")
            else:
                logger.warning("Cannot send reminder: application instance or TTS method unavailable")

            # Mark reminder as sent
            await self._mark_reminder_sent(event_id)

        except Exception as e:
            logger.error(f"Failed to send reminder: {e}", exc_info=True)

    def _format_reminder_text(
        self, title: str, time_str: str, category: str, description: str
    ) -> str:
        """
        Format reminder text for TTS output.
        """
        # Basic reminder message
        if time_str == "now":
            message = f"[{category}] Reminder: {title} is about to start"
        else:
            message = f"[{category}] Reminder: {title} starts {time_str}"

        # Add description
        if description:
            message += f", note: {description}"

        return message

    async def _mark_reminder_sent(self, event_id: str):
        """
        Mark reminder as sent.
        """
        try:
            with self.db._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE events
                    SET reminder_sent = 1, updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), event_id),
                )
                conn.commit()

            logger.debug(f"Marked reminder as sent: {event_id}")

        except Exception as e:
            logger.error(f"Failed to mark reminder as sent: {e}", exc_info=True)

    async def check_daily_events(self):
        """
        Check today's events (can be called on program startup).
        """
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE start_time >= ? AND start_time < ?
                    ORDER BY start_time
                """,
                    (today_start.isoformat(), today_end.isoformat()),
                )

                today_events = cursor.fetchall()

            if today_events:
                logger.info(f"Today has {len(today_events)} scheduled events")

                # Build today's schedule summary
                summary_message = {
                    "type": "daily_schedule",
                    "date": today_start.strftime("%Y-%m-%d"),
                    "total_events": len(today_events),
                    "events": [dict(event) for event in today_events],
                    "message": self._format_daily_summary(today_events),
                }

                summary_json = json.dumps(summary_message, ensure_ascii=False)

                # Get application instance and send schedule summary
                application = self._get_application()
                if application and hasattr(application, "_send_text_tts"):
                    await application._send_text_tts(summary_json)
                    logger.info("Sent today's schedule summary")

            else:
                logger.info("No events scheduled for today")

        except Exception as e:
            logger.error(f"Failed to check today's events: {e}", exc_info=True)

    def _format_daily_summary(self, events) -> str:
        """
        Format today's schedule summary for TTS output.
        """
        if not events:
            return "No events scheduled for today"

        summary = f"You have {len(events)} events today:"

        for i, event in enumerate(events, 1):
            start_dt = datetime.fromisoformat(event["start_time"])
            time_str = start_dt.strftime("%H:%M")
            summary += f" {i}.{time_str} {event['title']}"

            if i < len(events):
                summary += ","

        return summary

    async def reset_reminder_flags_for_future_events(self):
        """
        Reset reminder flags for future events (called on program restart).
        """
        try:
            now = datetime.now()

            with self.db._get_connection() as conn:
                # Reset reminder flags for all future events
                cursor = conn.execute(
                    """
                    UPDATE events
                    SET reminder_sent = 0, updated_at = ?
                    WHERE start_time > ? AND reminder_sent = 1
                """,
                    (now.isoformat(), now.isoformat()),
                )

                reset_count = cursor.rowcount
                conn.commit()

            if reset_count > 0:
                logger.info(f"Reset reminder flags for {reset_count} future events")

        except Exception as e:
            logger.error(f"Failed to reset reminder flags: {e}", exc_info=True)

    async def _cleanup_expired_reminders(self):
        """
        Clean up reminder flags for expired events (events expired for over 24 hours).
        """
        try:
            now = datetime.now()
            cleanup_threshold = now - timedelta(hours=24)

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE events
                    SET reminder_sent = 1, updated_at = ?
                    WHERE start_time < ? AND reminder_sent = 0
                """,
                    (now.isoformat(), cleanup_threshold.isoformat()),
                )

                cleanup_count = cursor.rowcount
                conn.commit()

            if cleanup_count > 0:
                logger.info(f"Cleaned up reminder flags for {cleanup_count} expired events")

        except Exception as e:
            logger.error(f"Failed to clean up expired reminder flags: {e}", exc_info=True)


# Global reminder service instance
_reminder_service = None


def get_reminder_service() -> CalendarReminderService:
    """
    Get the reminder service singleton.
    """
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = CalendarReminderService()
    return _reminder_service
