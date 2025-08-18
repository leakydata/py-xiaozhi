"""
MCP Server Implementation for Python
Reference: https://modelcontextprotocol.io/specification/2024-11-05
"""

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.constants.system import SystemConstants
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Return value type
ReturnValue = Union[bool, int, str]


class PropertyType(Enum):
    """
    Property type enumeration.
    """

    BOOLEAN = "boolean"
    INTEGER = "integer"
    STRING = "string"


@dataclass
class Property:
    """
    MCP tool property definition.
    """

    name: str
    type: PropertyType
    default_value: Optional[Any] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None

    @property
    def has_default_value(self) -> bool:
        return self.default_value is not None

    @property
    def has_range(self) -> bool:
        return self.min_value is not None and self.max_value is not None

    def value(self, value: Any) -> Any:
        """
        Validate and return the value.
        """
        if self.type == PropertyType.INTEGER and self.has_range:
            if value < self.min_value:
                raise ValueError(
                    f"Value {value} is below minimum allowed: " f"{self.min_value}"
                )
            if value > self.max_value:
                raise ValueError(
                    f"Value {value} exceeds maximum allowed: " f"{self.max_value}"
                )
        return value

    def to_json(self) -> Dict[str, Any]:
        """
        Convert to JSON format.
        """
        result = {"type": self.type.value}

        if self.has_default_value:
            result["default"] = self.default_value

        if self.type == PropertyType.INTEGER:
            if self.min_value is not None:
                result["minimum"] = self.min_value
            if self.max_value is not None:
                result["maximum"] = self.max_value

        return result


@dataclass
class PropertyList:
    """
    Property list.
    """

    properties: List[Property] = field(default_factory=list)

    def __init__(self, properties: Optional[List[Property]] = None):
        """
        Initialize the property list.
        """
        self.properties = properties or []

    def add_property(self, prop: Property):
        self.properties.append(prop)

    def __getitem__(self, name: str) -> Property:
        for prop in self.properties:
            if prop.name == name:
                return prop
        raise KeyError(f"Property not found: {name}")

    def get_required(self) -> List[str]:
        """
        Get a list of required property names.
        """
        return [p.name for p in self.properties if not p.has_default_value]

    def to_json(self) -> Dict[str, Any]:
        """
        Convert to JSON format.
        """
        return {prop.name: prop.to_json() for prop in self.properties}

    def parse_arguments(self, arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse and validate arguments.
        """
        result = {}

        for prop in self.properties:
            if arguments and prop.name in arguments:
                value = arguments[prop.name]
                # Type check
                if prop.type == PropertyType.BOOLEAN and isinstance(value, bool):
                    result[prop.name] = value
                elif prop.type == PropertyType.INTEGER and isinstance(
                    value, (int, float)
                ):
                    result[prop.name] = prop.value(int(value))
                elif prop.type == PropertyType.STRING and isinstance(value, str):
                    result[prop.name] = value
                else:
                    raise ValueError(f"Invalid type for property {prop.name}")
            elif prop.has_default_value:
                result[prop.name] = prop.default_value
            else:
                raise ValueError(f"Missing required argument: {prop.name}")

        return result


@dataclass
class McpTool:
    """
    MCP tool definition.
    """

    name: str
    description: str
    properties: PropertyList
    callback: Callable[[Dict[str, Any]], ReturnValue]

    def to_json(self) -> Dict[str, Any]:
        """
        Convert to JSON format.
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.properties.to_json(),
                "required": self.properties.get_required(),
            },
        }

    async def call(self, arguments: Dict[str, Any]) -> str:
        """
        Call the tool.
        """
        try:
            # Parse arguments
            parsed_args = self.properties.parse_arguments(arguments)

            # Call the callback function
            if asyncio.iscoroutinefunction(self.callback):
                result = await self.callback(parsed_args)
            else:
                result = self.callback(parsed_args)

            # Format the return value
            if isinstance(result, bool):
                text = "true" if result else "false"
            elif isinstance(result, int):
                text = str(result)
            else:
                text = str(result)

            return json.dumps(
                {"content": [{"type": "text", "text": text}], "isError": False}
            )

        except Exception as e:
            logger.error(f"Error calling tool {self.name}: {e}", exc_info=True)
            return json.dumps(
                {"content": [{"type": "text", "text": str(e)}], "isError": True}
            )


class McpServer:
    """
    MCP server implementation.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance.
        """
        if cls._instance is None:
            cls._instance = McpServer()
        return cls._instance

    def __init__(self):
        self.tools: List[McpTool] = []
        self._send_callback: Optional[Callable] = None
        self._camera = None

    def set_send_callback(self, callback: Callable):
        """
        Set the callback function for sending messages.
        """
        self._send_callback = callback

    def add_tool(self, tool: Union[McpTool, Tuple[str, str, PropertyList, Callable]]):
        """
        Add a tool.
        """
        if isinstance(tool, tuple):
            # Create McpTool from parameters
            name, description, properties, callback = tool
            tool = McpTool(name, description, properties, callback)

        # Check if it already exists
        if any(t.name == tool.name for t in self.tools):
            logger.warning(f"Tool {tool.name} already added")
            return

        logger.info(f"Add tool: {tool.name}")
        self.tools.append(tool)

    def add_common_tools(self):
        """
        Add common tools.
        """
        # Backup the original tool list
        original_tools = self.tools.copy()
        self.tools.clear()

        # Add system tools
        from src.mcp.tools.system import get_system_tools_manager

        system_manager = get_system_tools_manager()
        system_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add calendar management tools
        from src.mcp.tools.calendar import get_calendar_manager

        calendar_manager = get_calendar_manager()
        calendar_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add countdown timer tools
        from src.mcp.tools.timer import get_timer_manager

        timer_manager = get_timer_manager()
        timer_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add music player tools
        from src.mcp.tools.music import get_music_tools_manager

        music_manager = get_music_tools_manager()
        music_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add 12306 railway query tools
        from src.mcp.tools.railway import get_railway_tools_manager

        railway_manager = get_railway_tools_manager()
        railway_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add search tools
        from src.mcp.tools.search import get_search_manager

        search_manager = get_search_manager()
        search_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add recipe tools
        from src.mcp.tools.recipe import get_recipe_manager

        recipe_manager = get_recipe_manager()
        recipe_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add camera tools
        from src.mcp.tools.camera import take_photo

        # Register the take_photo tool
        properties = PropertyList([Property("question", PropertyType.STRING)])
        self.add_tool(
            McpTool(
                "take_photo",
                "Take a photo and analyze the image content. Can perform object recognition, text recognition, scene analysis, question answering, etc. Suitable for: what is this, take a photo to identify, read text, analyze the scene, answer questions, etc. Take photo and analyze image content including object recognition, text recognition, scene analysis, and question answering.",
                properties,
                take_photo,
            )
        )

        # Add Gaode Map tools
        from src.mcp.tools.amap import get_amap_manager

        amap_manager = get_amap_manager()
        amap_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add Bazi numerology tools
        from src.mcp.tools.bazi import get_bazi_manager

        bazi_manager = get_bazi_manager()
        bazi_manager.init_tools(self.add_tool, PropertyList, Property, PropertyType)

        # Add web reader tools
        from src.mcp.tools.web_reader.manager import get_web_reader_manager

        web_reader_manager = get_web_reader_manager()
        web_reader_manager.init_tools(
            self.add_tool, PropertyList, Property, PropertyType
        )

        # Add Python interpreter tools
        from src.mcp.tools.python_interpreter.manager import get_python_interpreter_manager

        python_interpreter_manager = get_python_interpreter_manager()
        python_interpreter_manager.init_tools(
            self.add_tool, PropertyList, Property, PropertyType
        )

        # Restore original tools
        self.tools.extend(original_tools)

    async def parse_message(self, message: Union[str, Dict[str, Any]]):
        """
        Parse an MCP message.
        """
        try:
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message

            logger.info(
                f"[MCP] Parsing message: {json.dumps(data, ensure_ascii=False, indent=2)}"
            )

            # Check JSONRPC version
            if data.get("jsonrpc") != "2.0":
                logger.error(f"Invalid JSONRPC version: {data.get('jsonrpc')}")
                return

            method = data.get("method")
            if not method:
                logger.error("Missing method")
                return

            # Ignore notifications
            if method.startswith("notifications"):
                logger.info(f"[MCP] Ignoring notification message: {method}")
                return

            params = data.get("params", {})
            id = data.get("id")

            if id is None:
                logger.error(f"Invalid id for method: {method}")
                return

            logger.info(f"[MCP] Processing method: {method}, ID: {id}, Parameters: {params}")

            # Handle different methods
            if method == "initialize":
                await self._handle_initialize(id, params)
            elif method == "tools/list":
                await self._handle_tools_list(id, params)
            elif method == "tools/call":
                await self._handle_tool_call(id, params)
            else:
                logger.error(f"Method not implemented: {method}")
                await self._reply_error(id, f"Method not implemented: {method}")

        except Exception as e:
            logger.error(f"Error parsing MCP message: {e}", exc_info=True)
            if "id" in locals():
                await self._reply_error(id, str(e))

    async def _handle_initialize(self, id: int, params: Dict[str, Any]):
        """
        Handle initialization request.
        """
        # Parse capabilities
        capabilities = params.get("capabilities", {})
        await self._parse_capabilities(capabilities)

        # Return server information
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": SystemConstants.APP_NAME,
                "version": SystemConstants.APP_VERSION,
            },
        }

        await self._reply_result(id, result)

    async def _handle_tools_list(self, id: int, params: Dict[str, Any]):
        """
        Handle tool list request.
        """
        cursor = params.get("cursor", "")
        max_payload_size = 8000

        tools_json = []
        total_size = 0
        found_cursor = not cursor
        next_cursor = ""

        for tool in self.tools:
            # If the starting position has not been found yet, continue searching
            if not found_cursor:
                if tool.name == cursor:
                    found_cursor = True
                else:
                    continue

            # Check size
            tool_json = tool.to_json()
            tool_size = len(json.dumps(tool_json))

            if total_size + tool_size + 100 > max_payload_size:
                next_cursor = tool.name
                break

            tools_json.append(tool_json)
            total_size += tool_size

        result = {"tools": tools_json}
        if next_cursor:
            result["nextCursor"] = next_cursor

        await self._reply_result(id, result)

    async def _handle_tool_call(self, id: int, params: Dict[str, Any]):
        """
        Handle tool call request.
        """
        logger.info(f"[MCP] Received tool call request! ID={id}, Parameters={params}")

        tool_name = params.get("name")
        if not tool_name:
            await self._reply_error(id, "Missing tool name")
            return

        logger.info(f"[MCP] Attempting to call tool: {tool_name}")

        # Find the tool
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            await self._reply_error(id, f"Unknown tool: {tool_name}")
            return

        # Get arguments
        arguments = params.get("arguments", {})

        logger.info(f"[MCP] Starting to execute tool {tool_name}, Parameters: {arguments}")

        # Call the tool asynchronously
        try:
            result = await tool.call(arguments)
            logger.info(f"[MCP] Tool {tool_name} executed successfully, result: {result}")
            await self._reply_result(id, json.loads(result))
        except Exception as e:
            logger.error(f"[MCP] Tool {tool_name} execution failed: {e}", exc_info=True)
            await self._reply_error(id, str(e))

    async def _parse_capabilities(self, capabilities):
        """
        Parse capabilities.
        """
        vision = capabilities.get("vision", {})
        if vision and isinstance(vision, dict):
            url = vision.get("url")
            token = vision.get("token")
            if url:
                from src.mcp.tools.camera import get_camera_instance

                camera = get_camera_instance()
                if hasattr(camera, "set_explain_url"):
                    camera.set_explain_url(url)
                if token and hasattr(camera, "set_explain_token"):
                    camera.set_explain_token(token)
                logger.info(f"Vision service configured with URL: {url}")

    async def _reply_result(self, id: int, result: Any):
        """
        Send a success response.
        """
        payload = {"jsonrpc": "2.0", "id": id, "result": result}

        result_len = len(json.dumps(result))
        logger.info(f"[MCP] Sending success response: ID={id}, Result length={result_len}")

        if self._send_callback:
            await self._send_callback(json.dumps(payload))
        else:
            logger.error("[MCP] Send callback not set!")

    async def _reply_error(self, id: int, message: str):
        """
        Send an error response.
        """
        payload = {"jsonrpc": "2.0", "id": id, "error": {"message": message}}

        logger.error(f"[MCP] Sending error response: ID={id}, Error={message}")

        if self._send_callback:
            await self._send_callback(json.dumps(payload))
