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
        格式化提醒文本.
        """
        # 基本提醒信息
        if time_str == "现在":
            message = f"【{category}】日程提醒：{title} 即将开始"
        else:
            message = f"【{category}】日程提醒：{title} 将在{time_str}开始"

        # 添加描述信息
        if description:
            message += f"，备注：{description}"

        return message

    async def _mark_reminder_sent(self, event_id: str):
        """
        标记提醒已发送.
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

            logger.debug(f"已标记提醒为已发送: {event_id}")

        except Exception as e:
            logger.error(f"标记提醒已发送失败: {e}", exc_info=True)

    async def check_daily_events(self):
        """
        检查今日事件（可在程序启动时调用）
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
                logger.info(f"今日有 {len(today_events)} 个日程")

                # 构建今日日程摘要
                summary_message = {
                    "type": "daily_schedule",
                    "date": today_start.strftime("%Y-%m-%d"),
                    "total_events": len(today_events),
                    "events": [dict(event) for event in today_events],
                    "message": self._format_daily_summary(today_events),
                }

                summary_json = json.dumps(summary_message, ensure_ascii=False)

                # 获取应用实例并发送日程摘要
                application = self._get_application()
                if application and hasattr(application, "_send_text_tts"):
                    await application._send_text_tts(summary_json)
                    logger.info("已发送今日日程摘要")

            else:
                logger.info("今日无日程安排")

        except Exception as e:
            logger.error(f"检查今日事件失败: {e}", exc_info=True)

    def _format_daily_summary(self, events) -> str:
        """
        格式化今日日程摘要.
        """
        if not events:
            return "今天没有安排任何日程"

        summary = f"今天共有{len(events)}个日程："

        for i, event in enumerate(events, 1):
            start_dt = datetime.fromisoformat(event["start_time"])
            time_str = start_dt.strftime("%H:%M")
            summary += f" {i}.{time_str} {event['title']}"

            if i < len(events):
                summary += "，"

        return summary

    async def reset_reminder_flags_for_future_events(self):
        """
        重置未来事件的提醒标志（程序重启时调用）
        """
        try:
            now = datetime.now()

            with self.db._get_connection() as conn:
                # 重置所有未来事件的提醒标志
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
                logger.info(f"已重置 {reset_count} 个未来事件的提醒标志")

        except Exception as e:
            logger.error(f"重置提醒标志失败: {e}", exc_info=True)

    async def _cleanup_expired_reminders(self):
        """
        清理过期事件的提醒标志（超过24小时的过期事件）
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
                logger.info(f"已清理 {cleanup_count} 个过期事件的提醒标志")

        except Exception as e:
            logger.error(f"清理过期提醒标志失败: {e}", exc_info=True)


# 全局提醒服务实例
_reminder_service = None


def get_reminder_service() -> CalendarReminderService:
    """
    获取提醒服务单例.
    """
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = CalendarReminderService()
    return _reminder_service
