"""
Conversation History Manager - Tracks multi-turn dialogue for natural conversation flow.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """A single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    emotion: str = "neutral"


class ConversationHistory:
    """
    Manages conversation history with context awareness.

    Tracks user/assistant messages, detects conversation patterns,
    and provides context for more natural multi-turn dialogue.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ConversationHistory()
        return cls._instance

    def __init__(self, max_messages: int = 50, session_timeout: float = 300.0):
        self._messages: deque = deque(maxlen=max_messages)
        self._session_timeout = session_timeout
        self._session_start: float = time.time()
        self._last_activity: float = time.time()
        self._turn_count: int = 0
        self._topics: List[str] = []

    def add_message(self, role: str, content: str, emotion: str = "neutral"):
        """Add a message to the conversation history."""
        now = time.time()

        # Auto-start new session if timeout exceeded
        if now - self._last_activity > self._session_timeout:
            logger.info("Session timeout, starting new conversation session")
            self.clear()
            self._session_start = now

        self._last_activity = now
        self._messages.append(ChatMessage(
            role=role,
            content=content,
            timestamp=now,
            emotion=emotion,
        ))

        if role == "user":
            self._turn_count += 1

    def get_messages(self, limit: int = 20) -> List[ChatMessage]:
        """Get recent messages."""
        messages = list(self._messages)
        return messages[-limit:] if len(messages) > limit else messages

    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        for msg in reversed(self._messages):
            if msg.role == "user":
                return msg.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the most recent assistant message."""
        for msg in reversed(self._messages):
            if msg.role == "assistant":
                return msg.content
        return None

    def is_follow_up(self) -> bool:
        """Detect if the current turn is likely a follow-up to the previous one."""
        if self._turn_count < 2:
            return False

        # If the last activity was recent, it's likely a follow-up
        messages = list(self._messages)
        if len(messages) >= 2:
            last_two = messages[-2:]
            time_gap = last_two[1].timestamp - last_two[0].timestamp
            return time_gap < 30.0  # Within 30 seconds

        return False

    def ended_with_question(self) -> bool:
        """Check if the last assistant message ended with a question."""
        last = self.get_last_assistant_message()
        if not last:
            return False
        stripped = last.strip()
        return stripped.endswith("?") or stripped.endswith("?")

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def is_active(self) -> bool:
        """Check if the conversation session is still active."""
        return (time.time() - self._last_activity) < self._session_timeout

    def get_context_summary(self) -> dict:
        """Get a summary of the conversation context."""
        return {
            "turn_count": self._turn_count,
            "message_count": len(self._messages),
            "is_active": self.is_active,
            "is_follow_up": self.is_follow_up(),
            "ended_with_question": self.ended_with_question(),
            "session_duration": time.time() - self._session_start,
        }

    def clear(self):
        """Clear the conversation history."""
        self._messages.clear()
        self._turn_count = 0
        self._topics.clear()
        logger.info("Conversation history cleared")
