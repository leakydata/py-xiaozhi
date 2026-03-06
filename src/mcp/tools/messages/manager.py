"""
Messages Manager - Manages message-taking tools for away/receptionist mode.
"""

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_manager_instance = None


class MessagesManager:
    """Manager for message-taking MCP tools."""

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """Register message tools with the MCP server."""
        from .tools import check_away_status, get_messages, mark_messages_read, take_message

        # Take a message from a visitor
        take_msg_props = PropertyList(
            [
                Property("visitor_name", PropertyType.STRING),
                Property("message", PropertyType.STRING),
                Property("summary", PropertyType.STRING),
            ]
        )
        add_tool(
            (
                "self.messages.take_message",
                "Save a message from a visitor or person at the desk.\n"
                "Use this tool when:\n"
                "1. Someone wants to leave a message for the user who is away\n"
                "2. A visitor asks you to tell the user something\n"
                "3. You need to note that someone stopped by\n"
                "\nArgs:\n"
                "  visitor_name: Name of the visitor (required)\n"
                "  message: The full message to save (required)\n"
                "  summary: A brief one-line summary (optional)",
                take_msg_props,
                take_message,
            )
        )

        # Get messages
        get_msg_props = PropertyList(
            [
                Property("unread_only", PropertyType.BOOLEAN),
            ]
        )
        add_tool(
            (
                "self.messages.get_messages",
                "Retrieve messages from the message board.\n"
                "Use this tool when:\n"
                "1. The user asks about messages or who stopped by\n"
                "2. The user returns from being away\n"
                "3. Checking for any new messages\n"
                "\nArgs:\n"
                "  unread_only: If true, only return unread messages (default: true)",
                get_msg_props,
                get_messages,
            )
        )

        # Mark messages as read
        mark_read_props = PropertyList([])
        add_tool(
            (
                "self.messages.mark_read",
                "Mark all messages as read.\n"
                "Use this tool after the user has reviewed their messages.",
                mark_read_props,
                mark_messages_read,
            )
        )

        # Check away status
        status_props = PropertyList([])
        add_tool(
            (
                "self.messages.check_away_status",
                "Check if the user is currently away from their desk.\n"
                "Use this tool to:\n"
                "1. Determine if you should greet a visitor\n"
                "2. Check how long the user has been away\n"
                "3. Get the appropriate greeting for visitors",
                status_props,
                check_away_status,
            )
        )

        logger.info("Messages tools registered successfully")


def get_messages_manager() -> MessagesManager:
    """Get or create the MessagesManager singleton."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MessagesManager()
    return _manager_instance


async def cleanup_messages_manager():
    """Cleanup the messages manager."""
    global _manager_instance
    _manager_instance = None
