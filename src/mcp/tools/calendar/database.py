"""
Schedule management SQLite database operation module.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Database file path
DATABASE_FILE = "cache/calendar.db"


class CalendarDatabase:
    """
    Schedule management database operation class.
    """

    def __init__(self):
        self.db_file = DATABASE_FILE
        self._ensure_database()

    def _ensure_database(self):
        """
        Ensure that the database and tables exist.
        """
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

        with self._get_connection() as conn:
            # Create events table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'Default',
                    reminder_minutes INTEGER DEFAULT 15,
                    reminder_time TEXT,
                    reminder_sent BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            # Create categories table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """
            )

            # Insert default categories
            default_categories = ["Default", "Work", "Personal", "Meeting", "Reminder"]
            for category in default_categories:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,)
                )

            conn.commit()

            # Check and add new fields (database upgrade)
            self._upgrade_database(conn)

            logger.info("Database initialization complete")

    @contextmanager
    def _get_connection(self):
        """
        Context manager to get a database connection.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row  # Allows accessing results by column name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def add_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Add an event.
        """
        try:
            with self._get_connection() as conn:
                # Check for time conflicts
                if self._has_conflict(conn, event_data):
                    return False

                conn.execute(
                    """
                    INSERT INTO events (
                        id, title, start_time, end_time, description,
                        category, reminder_minutes, reminder_time, reminder_sent,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event_data["id"],
                        event_data["title"],
                        event_data["start_time"],
                        event_data["end_time"],
                        event_data["description"],
                        event_data["category"],
                        event_data["reminder_minutes"],
                        event_data.get("reminder_time"),
                        event_data.get("reminder_sent", False),
                        event_data["created_at"],
                        event_data["updated_at"],
                    ),
                )
                conn.commit()
                logger.info(f"Event added successfully: {event_data['title']}")
                return True
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            return False

    def get_events(
        self, start_date: str = None, end_date: str = None, category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get a list of events.
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM events WHERE 1=1"
                params = []

                if start_date:
                    query += " AND start_time >= ?"
                    params.append(start_date)

                if end_date:
                    query += " AND start_time <= ?"
                    params.append(end_date)

                if category:
                    query += " AND category = ?"
                    params.append(category)

                query += " ORDER BY start_time"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                events = []
                for row in rows:
                    events.append(dict(row))

                return events
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

    def update_event(self, event_id: str, **kwargs) -> bool:
        """
        Update an event.
        """
        try:
            with self._get_connection() as conn:
                # Build update query
                set_clauses = []
                params = []

                for key, value in kwargs.items():
                    if key in [
                        "title",
                        "start_time",
                        "end_time",
                        "description",
                        "category",
                        "reminder_minutes",
                    ]:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                if not set_clauses:
                    return False

                # Add update time
                set_clauses.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(event_id)

                query = f"UPDATE events SET {', '.join(set_clauses)} WHERE id = ?"

                cursor = conn.execute(query, params)
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Event updated successfully: {event_id}")
                    return True
                else:
                    logger.warning(f"Event does not exist: {event_id}")
                    return False
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Event deleted successfully: {event_id}")
                    return True
                else:
                    logger.warning(f"Event does not exist: {event_id}")
                    return False
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False

    def delete_events_batch(
        self,
        start_date: str = None,
        end_date: str = None,
        category: str = None,
        delete_all: bool = False,
    ) -> Dict[str, Any]:
        """Batch delete events.

        Args:
            start_date: Start date, ISO format
            end_date: End date, ISO format
            category: Category filter
            delete_all: Whether to delete all events

        Returns:
            A dictionary containing the deletion result
        """
        try:
            with self._get_connection() as conn:
                if delete_all:
                    # Delete all events
                    cursor = conn.execute("SELECT COUNT(*) FROM events")
                    total_count = cursor.fetchone()[0]

                    if total_count == 0:
                        return {
                            "success": True,
                            "deleted_count": 0,
                            "message": "No events to delete",
                        }

                    cursor = conn.execute("DELETE FROM events")
                    conn.commit()

                    logger.info(f"Successfully deleted all events, total {total_count} events deleted")
                    return {
                        "success": True,
                        "deleted_count": total_count,
                        "message": f"Successfully deleted all {total_count} events",
                    }

                else:
                    # Delete events by condition
                    # First, query for matching events
                    query = "SELECT id, title FROM events WHERE 1=1"
                    params = []

                    if start_date:
                        query += " AND start_time >= ?"
                        params.append(start_date)

                    if end_date:
                        query += " AND start_time <= ?"
                        params.append(end_date)

                    if category:
                        query += " AND category = ?"
                        params.append(category)

                    cursor = conn.execute(query, params)
                    events_to_delete = cursor.fetchall()

                    if not events_to_delete:
                        return {
                            "success": True,
                            "deleted_count": 0,
                            "message": "No matching events to delete",
                        }

                    # Execute deletion
                    delete_query = "DELETE FROM events WHERE 1=1"
                    delete_params = []

                    if start_date:
                        delete_query += " AND start_time >= ?"
                        delete_params.append(start_date)

                    if end_date:
                        delete_query += " AND start_time <= ?"
                        delete_params.append(end_date)

                    if category:
                        delete_query += " AND category = ?"
                        delete_params.append(category)

                    cursor = conn.execute(delete_query, delete_params)
                    deleted_count = cursor.rowcount
                    conn.commit()

                    # Record the titles of deleted events
                    deleted_titles = [event[1] for event in events_to_delete]
                    logger.info(
                        f"Batch delete successful, {deleted_count} events deleted: "
                        f"{', '.join(deleted_titles[:3])}"
                        f"{'...' if len(deleted_titles) > 3 else ''}"
                    )

                    return {
                        "success": True,
                        "deleted_count": deleted_count,
                        "deleted_titles": deleted_titles,
                        "message": f"Successfully deleted {deleted_count} events",
                    }

        except Exception as e:
            logger.error(f"Batch delete events failed: {e}")
            return {
                "success": False,
                "deleted_count": 0,
                "message": f"Batch delete failed: {str(e)}",
            }

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an event by ID.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get event: {e}")
            return None

    def get_categories(self) -> List[str]:
        """
        Get all categories.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT name FROM categories ORDER BY name")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return ["Default"]

    def add_category(self, category_name: str) -> bool:
        """
        Add a new category.
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                    (category_name,),
                )
                conn.commit()
                logger.info(f"Category added successfully: {category_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to add category: {e}")
            return False

    def delete_category(self, category_name: str) -> bool:
        """
        Delete a category (if not used by any events)
        """
        try:
            with self._get_connection() as conn:
                # Check if any events are using this category
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE category = ?", (category_name,)
                )
                count = cursor.fetchone()[0]

                if count > 0:
                    logger.warning(f"Category '{category_name}' is in use and cannot be deleted")
                    return False

                cursor = conn.execute(
                    "DELETE FROM categories WHERE name = ?", (category_name,)
                )
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Category deleted successfully: {category_name}")
                    return True
                else:
                    logger.warning(f"Category does not exist: {category_name}")
                    return False
        except Exception as e:
            logger.error(f"Failed to delete category: {e}")
            return False

    def _has_conflict(
        self, conn: sqlite3.Connection, event_data: Dict[str, Any]
    ) -> bool:
        """
        Check for time conflicts.
        """
        cursor = conn.execute(
            """
            SELECT title FROM events
            WHERE id != ? AND (
                (start_time < ? AND end_time > ?) OR
                (start_time < ? AND end_time > ?)
            )
        """,
            (
                event_data["id"],
                event_data["end_time"],
                event_data["start_time"],
                event_data["start_time"],
                event_data["end_time"],
            ),
        )

        conflicting_events = cursor.fetchall()

        if conflicting_events:
            for event in conflicting_events:
                logger.warning(f"Time conflict: Conflicts with event '{event[0]}'")
            return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics.
        """
        try:
            with self._get_connection() as conn:
                # Total number of events
                cursor = conn.execute("SELECT COUNT(*) FROM events")
                total_events = cursor.fetchone()[0]

                # Statistics by category
                cursor = conn.execute(
                    """
                    SELECT category, COUNT(*)
                    FROM events
                    GROUP BY category
                    ORDER BY COUNT(*) DESC
                """
                )
                category_stats = dict(cursor.fetchall())

                # Number of events today
                today = datetime.now().strftime("%Y-%m-%d")
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE date(start_time) = ?
                """,
                    (today,),
                )
                today_events = cursor.fetchone()[0]

                return {
                    "total_events": total_events,
                    "category_stats": category_stats,
                    "today_events": today_events,
                }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def migrate_from_json(self, json_file_path: str) -> bool:
        """
        Migrate data from a JSON file.
        """
        try:
            import json

            if not os.path.exists(json_file_path):
                logger.info("JSON file does not exist, skipping migration")
                return True

            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            events_data = data.get("events", [])
            categories_data = data.get("categories", [])

            with self._get_connection() as conn:
                # Migrate categories
                for category in categories_data:
                    conn.execute(
                        "INSERT OR IGNORE INTO categories (name) VALUES (?)",
                        (category,),
                    )

                # Migrate events
                for event_data in events_data:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO events (
                            id, title, start_time, end_time, description,
                            category, reminder_minutes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event_data["id"],
                            event_data["title"],
                            event_data["start_time"],
                            event_data["end_time"],
                            event_data.get("description", ""),
                            event_data.get("category", "Default"),
                            event_data.get("reminder_minutes", 15),
                            event_data.get("created_at", datetime.now().isoformat()),
                            event_data.get("updated_at", datetime.now().isoformat()),
                        ),
                    )

                conn.commit()
                logger.info(
                    f"Successfully migrated {len(events_data)} events and {len(categories_data)} categories"
                )
                return True

        except Exception as e:
            logger.error(f"Data migration failed: {e}")
            return False

    def _upgrade_database(self, conn: sqlite3.Connection):
        """
        Upgrade the database structure.
        """
        try:
            # Check if new fields exist
            cursor = conn.execute("PRAGMA table_info(events)")
            columns = [col[1] for col in cursor.fetchall()]

            # Add reminder_time field
            if "reminder_time" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN reminder_time TEXT")
                logger.info("Added reminder_time field")

            # Add reminder_sent field
            if "reminder_sent" not in columns:
                conn.execute(
                    "ALTER TABLE events ADD COLUMN reminder_sent BOOLEAN DEFAULT 0"
                )
                logger.info("Added reminder_sent field")

            # Calculate and set reminder_time for existing events
            cursor = conn.execute(
                "SELECT id, start_time, reminder_minutes "
                "FROM events WHERE reminder_time IS NULL"
            )
            events_to_update = cursor.fetchall()

            for event in events_to_update:
                event_id, start_time, reminder_minutes = event
                try:
                    from datetime import timedelta

                    start_dt = datetime.fromisoformat(start_time)
                    reminder_dt = start_dt - timedelta(minutes=reminder_minutes)

                    conn.execute(
                        "UPDATE events SET reminder_time = ? WHERE id = ?",
                        (reminder_dt.isoformat(), event_id),
                    )
                except Exception as e:
                    logger.warning(f"Failed to calculate reminder time for event {event_id}: {e}")

            if events_to_update:
                logger.info(f"Set reminder time for {len(events_to_update)} existing events")

            conn.commit()

        except Exception as e:
            logger.error(f"Database upgrade failed: {e}", exc_info=True)


# Global database instance
_calendar_db = None


def get_calendar_database() -> CalendarDatabase:
    """
    Get a singleton instance of the database.
    """
    global _calendar_db
    if _calendar_db is None:
        _calendar_db = CalendarDatabase()
    return _calendar_db
