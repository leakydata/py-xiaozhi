"""
Message Board - Persistent storage for visitor messages and notes left during away mode.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VisitorMessage:
    """A message left by a visitor during away mode."""
    visitor_name: str
    message: str
    timestamp: float = field(default_factory=time.time)
    read: bool = False
    summary: Optional[str] = None

    @property
    def time_str(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(self.timestamp))


class MessageBoard:
    """
    Persistent message board for storing visitor messages.
    Messages are saved to a JSON file so they survive app restarts.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MessageBoard()
        return cls._instance

    def __init__(self, max_messages: int = 100):
        self._messages: List[VisitorMessage] = []
        self._max_messages = max_messages
        self._storage_path = Path.home() / ".xiaozhi" / "messages.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def add_message(self, visitor_name: str, message: str, summary: str = None) -> VisitorMessage:
        """Add a visitor message."""
        msg = VisitorMessage(
            visitor_name=visitor_name,
            message=message,
            summary=summary,
        )
        self._messages.append(msg)

        # Trim old messages
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

        self._save()
        logger.info(f"Message from {visitor_name}: {message[:50]}...")
        return msg

    def get_unread(self) -> List[VisitorMessage]:
        """Get all unread messages."""
        return [m for m in self._messages if not m.read]

    def get_all(self, limit: int = 50) -> List[VisitorMessage]:
        """Get recent messages."""
        return self._messages[-limit:]

    def mark_all_read(self):
        """Mark all messages as read."""
        for m in self._messages:
            m.read = True
        self._save()

    def mark_read(self, index: int):
        """Mark a specific message as read by index."""
        if 0 <= index < len(self._messages):
            self._messages[index].read = True
            self._save()

    @property
    def unread_count(self) -> int:
        return sum(1 for m in self._messages if not m.read)

    def get_summary_text(self) -> str:
        """Get a readable summary of unread messages."""
        unread = self.get_unread()
        if not unread:
            return "No new messages."

        lines = [f"You have {len(unread)} new message(s):\n"]
        for i, msg in enumerate(unread, 1):
            lines.append(f"{i}. From {msg.visitor_name} at {msg.time_str}:")
            if msg.summary:
                lines.append(f"   Summary: {msg.summary}")
            else:
                lines.append(f"   {msg.message[:100]}")
            lines.append("")

        return "\n".join(lines)

    def clear(self):
        """Clear all messages."""
        self._messages.clear()
        self._save()

    def _save(self):
        """Save messages to disk."""
        try:
            data = [asdict(m) for m in self._messages]
            self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save messages: {e}")

    def _load(self):
        """Load messages from disk."""
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                self._messages = [VisitorMessage(**m) for m in data]
                logger.info(f"Loaded {len(self._messages)} messages ({self.unread_count} unread)")
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")
            self._messages = []
