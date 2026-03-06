"""
Messages MCP tool functions - save and retrieve visitor messages.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger
from src.utils.message_board import MessageBoard
from src.utils.presence_manager import PresenceManager

logger = get_logger(__name__)


async def take_message(args: Dict[str, Any]) -> str:
    """Save a message from a visitor."""
    visitor_name = args.get("visitor_name", "Unknown visitor")
    message = args.get("message", "")
    summary = args.get("summary", None)

    if not message:
        return json.dumps({"error": "No message provided"})

    board = MessageBoard.get_instance()
    msg = board.add_message(visitor_name, message, summary)

    return json.dumps({
        "status": "saved",
        "visitor_name": msg.visitor_name,
        "time": msg.time_str,
        "message_preview": msg.message[:100],
    })


async def get_messages(args: Dict[str, Any]) -> str:
    """Get messages from the message board."""
    unread_only = args.get("unread_only", True)
    board = MessageBoard.get_instance()

    if unread_only:
        messages = board.get_unread()
    else:
        messages = board.get_all()

    result = []
    for msg in messages:
        result.append({
            "visitor_name": msg.visitor_name,
            "message": msg.message,
            "time": msg.time_str,
            "read": msg.read,
            "summary": msg.summary,
        })

    return json.dumps({
        "total": len(result),
        "unread_count": board.unread_count,
        "messages": result,
    })


async def mark_messages_read(args: Dict[str, Any]) -> str:
    """Mark all messages as read."""
    board = MessageBoard.get_instance()
    board.mark_all_read()
    return json.dumps({"status": "all messages marked as read"})


async def check_away_status(args: Dict[str, Any]) -> str:
    """Check if the user is currently away."""
    presence = PresenceManager.get_instance()
    board = MessageBoard.get_instance()

    return json.dumps({
        "is_away": presence.is_away,
        "away_duration": presence.away_duration_str if presence.is_away else None,
        "unread_messages": board.unread_count,
        "greeting": presence.get_greeting() if presence.is_away else None,
    })
